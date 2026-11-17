#!/usr/bin/env python3
"""AI+ pilóta kit: load a profile, check it, and run its tapes through desktape.

A profile (profiles/<id>/) describes how to operate one desktop program through its own windows. Its manifest,
profile.yaml, names the program's desktape maps and tapes; this kit knows nothing about any one program.

    python3 kit/load_profile.py list
    python3 kit/load_profile.py check [ID ...]
    python3 kit/load_profile.py show ID
    python3 kit/load_profile.py run ID read NAME  --target BOX [--var name=value ...] [--dry-run]
    python3 kit/load_profile.py run ID write NAME --target BOX [--var name=value ...] [--dry-run]

The path contract with desktape: a tape names its map by a path relative to this repository's root
(`map: profiles/<id>/maps/<name>.yaml`), and desktape runs with this repository's root as its working directory,
so desktape reads the profile's own files and nothing is copied into desktape.

A write runs three tapes in order, with the same variables, and stops at the first failure: the write tape's
`backup:` tape, the write tape itself, then its `read_back:` tape, whose `expect` steps confirm the written values
in the program's own list. The kit refuses a write tape that does not name both.
"""
import argparse
import logging
import os
import re
import shlex
import subprocess
import sys

import yaml

logger = logging.getLogger("aiplus_pilota")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "kit", "profile_schema.yaml")
PROFILES = os.path.join(ROOT, "profiles")
WRITING_STEPS = {"type", "set", "open_file"}       # step kinds that put data into a program


class ProfileError(Exception):
    """A profile that breaks the schema or the rules; the message names the file and the field."""


# --- the schema: a small JSON Schema subset, checked here so the kit needs only PyYAML -----------------------

def schema_errors(value, schema, where="profile"):
    """Every place `value` breaks `schema`, as 'where: what' lines (empty when it fits)."""
    errs = []
    if "const" in schema and value != schema["const"]:
        errs.append(f"{where}: must be {schema['const']!r}, not {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{where}: must be one of {schema['enum']}, not {value!r}")
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str}
    if kind and not isinstance(value, types[kind]):
        return errs + [f"{where}: must be a{'n' if kind[0] in 'ao' else ''} {kind}"]
    if kind == "string" and "pattern" in schema and not re.search(schema["pattern"], value):
        errs.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if kind == "array" and "items" in schema:
        for i, item in enumerate(value):
            errs += schema_errors(item, schema["items"], f"{where}[{i}]")
    if kind == "object":
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errs.append(f"{where}: missing {key!r}")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                errs += schema_errors(item, props[key], f"{where}.{key}")
            elif extra is False:
                errs.append(f"{where}: unknown field {key!r}")
            elif isinstance(extra, dict):
                errs += schema_errors(item, extra, f"{where}.{key}")
    return errs


# --- loading -------------------------------------------------------------------------------------------------

def read_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def profile_ids(profiles_dir=PROFILES):
    if not os.path.isdir(profiles_dir):
        return []
    return sorted(d for d in os.listdir(profiles_dir) if os.path.isfile(os.path.join(profiles_dir, d, "profile.yaml")))


def load(profile_id, profiles_dir=PROFILES):
    """The manifest of one profile, checked against the schema; raises ProfileError with every problem found."""
    home = os.path.join(profiles_dir, profile_id)
    path = os.path.join(home, "profile.yaml")
    if not os.path.isfile(path):
        raise ProfileError(f"no profile {profile_id!r}: {path} does not exist")
    manifest = read_yaml(path) or {}
    errs = schema_errors(manifest, read_yaml(SCHEMA))
    if not errs and manifest["id"] != profile_id:
        errs.append(f"profile.id {manifest['id']!r} differs from its folder name {profile_id!r}")
    if errs:
        raise ProfileError(f"{path}:\n  " + "\n  ".join(errs))
    manifest["_home"] = home
    logger.debug("loaded profile %s from %s", profile_id, home)
    return manifest


def rel(path):
    """A path as this repository's root sees it: what desktape is given, and what a tape's `map:` must name."""
    return os.path.relpath(path, ROOT)


def tape_path(manifest, kind, name):
    """The repo-relative path of a profile tape (kind: read | write)."""
    entries = manifest["tapes"].get(kind) or {}
    if name not in entries:
        raise ProfileError(f"profile {manifest['id']!r} has no {kind} tape {name!r}; it has: {sorted(entries)}")
    entry = entries[name]
    return rel(os.path.join(manifest["_home"], entry["tape"] if kind == "write" else entry))


# --- the rules a schema cannot express -----------------------------------------------------------------------

def tape_problems(path, manifest, kind):
    """What is wrong with one tape file, given its kind: a missing file, a map outside the profile, a read tape
    that writes, a write tape without its backup and read-back tapes."""
    full = os.path.join(ROOT, path)
    if not os.path.isfile(full):
        return [f"{path}: the tape file does not exist"]
    tape = read_yaml(full) or {}
    probs = []
    home = rel(manifest["_home"])
    if tape.get("map"):
        m = tape["map"]
        if not os.path.isfile(os.path.join(ROOT, m)):
            probs.append(f"{path}: map {m!r} does not resolve from the repository root (write it repo-relative, "
                         f"e.g. {home}/maps/<name>.yaml)")
        elif not os.path.abspath(os.path.join(ROOT, m)).startswith(os.path.abspath(manifest["_home"]) + os.sep):
            probs.append(f"{path}: map {m!r} lies outside the profile {home}/")
    kinds = {next(iter(s)) for s in tape.get("steps") or [] if isinstance(s, dict) and s}
    if not tape.get("steps"):
        probs.append(f"{path}: no steps")
    if kind == "read" and kinds & WRITING_STEPS:
        probs.append(f"{path}: a read tape must not write, but it has {sorted(kinds & WRITING_STEPS)} steps")
    if kind == "write":
        for key in ("backup", "read_back"):
            ref = (tape.get(key) or {}).get("tape") if isinstance(tape.get(key), dict) else None
            if not ref:
                probs.append(f"{path}: a write tape must name its {key} tape ({key}: {{tape: <repo-relative path>}})")
            elif not os.path.isfile(os.path.join(ROOT, ref)):
                probs.append(f"{path}: {key} tape {ref!r} does not exist")
            elif key == "read_back":
                back = read_yaml(os.path.join(ROOT, ref)) or {}
                steps = back.get("steps") or []
                if not any(isinstance(s, dict) and "expect" in s for s in steps):
                    probs.append(f"{ref}: a read-back tape must check values with at least one `expect` step")
                if {next(iter(s)) for s in steps if isinstance(s, dict) and s} & WRITING_STEPS:
                    probs.append(f"{ref}: a read-back tape must not write")
    return probs


def check(manifest):
    """Every rule broken by a loaded profile, beyond the schema: files that must exist, and the tape rules."""
    home = manifest["_home"]
    probs = []
    for name, path in (manifest.get("maps") or {}).items():
        if not os.path.isfile(os.path.join(home, path)):
            probs.append(f"{rel(home)}/{path}: map {name!r} does not exist")
    for kind in ("read", "write"):
        for name in manifest["tapes"].get(kind) or {}:
            probs += tape_problems(tape_path(manifest, kind, name), manifest, kind)
    for skill in manifest.get("skills") or []:
        if not os.path.isfile(os.path.join(home, skill, "SKILL.md")):
            probs.append(f"{rel(home)}/{skill}: the skill has no SKILL.md")
    if manifest.get("views") and not os.path.isdir(os.path.join(home, manifest["views"]["source"])):
        probs.append(f"{rel(home)}/{manifest['views']['source']}: the views folder does not exist")
    return probs


# --- running through desktape --------------------------------------------------------------------------------

def desktape_cmd():
    """How to start desktape: $DESKTAPE (a command, or a path to desktape.py), else `desktape` on PATH."""
    cmd = shlex.split(os.environ.get("DESKTAPE", "desktape"))
    return [sys.executable] + cmd if cmd[0].endswith(".py") else cmd


def plan(manifest, kind, name, target, variables):
    """The desktape commands one run takes, in order: one for a read, backup + write + read-back for a write."""
    path = tape_path(manifest, kind, name)
    probs = tape_problems(path, manifest, kind)
    if probs:
        raise ProfileError("refusing to run:\n  " + "\n  ".join(probs))
    tapes = [path]
    if kind == "write":
        tape = read_yaml(os.path.join(ROOT, path))
        tapes = [tape["backup"]["tape"], path, tape["read_back"]["tape"]]
    extra = [x for v in variables for x in ("--var", v)]
    return [(t, desktape_cmd() + ["run", t, "--target", target] + extra) for t in tapes]


def run(manifest, kind, name, target, variables, dry_run=False):
    """Run a profile tape from the repository root; 0 when every step passed, else desktape's exit code."""
    for tape, cmd in plan(manifest, kind, name, target, variables):
        logger.info("run %s/%s %s: %s", manifest["id"], kind, name, " ".join(shlex.quote(c) for c in cmd))
        if dry_run:
            print(" ".join(shlex.quote(c) for c in cmd))
            continue
        code = subprocess.run(cmd, cwd=ROOT).returncode
        if code:
            logger.error("profile %s %s %s stopped at %s: desktape exited %d", manifest["id"], kind, name, tape, code)
            return code
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aiplus-pilota", description=__doc__.split("\n\n")[0])
    ap.add_argument("--profiles-dir", default=PROFILES, help=argparse.SUPPRESS)
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the profiles in this repository")
    p = sub.add_parser("check", help="check profiles against the schema and the rules (all when none is named)")
    p.add_argument("ids", nargs="*")
    p = sub.add_parser("show", help="a profile's maps, tapes and skills as desktape paths")
    p.add_argument("id")
    p = sub.add_parser("run", help="run a profile tape through desktape")
    p.add_argument("id"); p.add_argument("kind", choices=["read", "write"]); p.add_argument("name")
    p.add_argument("--target", required=True); p.add_argument("--var", action="append", default=[])
    p.add_argument("--dry-run", action="store_true", help="print the desktape commands, run nothing")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        if a.cmd == "list":
            for pid in profile_ids(a.profiles_dir):
                print(pid)
            return 0
        if a.cmd == "check":
            bad = 0
            for pid in a.ids or profile_ids(a.profiles_dir):
                try:
                    probs = check(load(pid, a.profiles_dir))
                except ProfileError as e:
                    probs = [str(e)]
                print(f"{pid}: {'ok' if not probs else 'FAILED'}")
                for line in probs:
                    print(f"  {line}")
                bad += bool(probs)
            return 1 if bad else 0
        m = load(a.id, a.profiles_dir)
        if a.cmd == "show":
            print(f"{m['id']}: {m['title']} ({m['program']['family']}, {m['program']['os']})")
            for name, path in (m.get("maps") or {}).items():
                print(f"  map   {name}: {rel(os.path.join(m['_home'], path))}")
            for kind in ("read", "write"):
                for name in m["tapes"].get(kind) or {}:
                    print(f"  {kind:5} {name}: {tape_path(m, kind, name)}")
            for skill in m.get("skills") or []:
                print(f"  skill {rel(os.path.join(m['_home'], skill))}")
            return 0
        return run(m, a.kind, a.name, a.target, a.var, a.dry_run)
    except ProfileError as e:
        logger.error("%s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
