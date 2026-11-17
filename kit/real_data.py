#!/usr/bin/env python3
"""The real-data gate: refuse a file that carries a real-looking Hungarian identifier.

    python3 kit/real_data.py --staged          # the files staged for commit (the pre-commit hook)
    python3 kit/real_data.py PATH [PATH ...]    # the given files

An identifier counts as real-looking when its check digit is right: adószám (tax number, 8+1+2 digits), TAJ
(social security number, 9 digits) and bankszámlaszám (bank account, 2 or 3 groups of 8 digits). A number whose
check digit is wrong cannot be a real one, so invented numbers in a profile simply break the check digit. Files
under the paths in .aiplus-real-data.json `fixtures` (tests/fixtures/ by default) are not scanned, and the file
names in `forbiddenNames` are refused outright.
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys

logger = logging.getLogger("aiplus_pilota.real_data")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = ".aiplus-real-data.json"
DEFAULTS = {"fixtures": ["tests/fixtures/"], "forbiddenNames": [], "inventedBankPrefix": "999"}

ADOSZAM = re.compile(r"(?<![\d-])(\d{8})-([1-5])-(\d{2})(?![\d-])")
TAJ = re.compile(r"(?<![\d-])(?<!\d )(\d{3})[ -]?(\d{3})[ -]?(\d{3})(?![\d-])(?! \d)")
BANK = re.compile(r"(?<![\d-])(\d{8})-(\d{8})(?:-(\d{8}))?(?![\d-])")


def weighted_ok(digits):
    """The 9-7-3-1 check of a bankszámlaszám group and of the adószám's first 8 digits: the weighted sum ends in 0."""
    return sum(int(d) * w for d, w in zip(digits, [9, 7, 3, 1] * 6)) % 10 == 0


def taj_ok(digits):
    """TAJ: the odd places times 3, the even places times 7, summed; the last digit is that sum mod 10."""
    total = sum(int(d) * (3 if i % 2 == 0 else 7) for i, d in enumerate(digits[:8]))
    return total % 10 == int(digits[8])


def findings(text, invented_prefix="999"):
    """(line number, kind, value) for every real-looking identifier in a text."""
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        for m in ADOSZAM.finditer(line):
            if weighted_ok(m.group(1)):
                out.append((no, "adószám", m.group(0)))
        for m in BANK.finditer(line):
            groups = [g for g in m.groups() if g]
            if m.group(1).startswith(invented_prefix):
                continue
            if weighted_ok(groups[0]) and weighted_ok("".join(groups[1:])):
                out.append((no, "bankszámlaszám", m.group(0)))
        for m in TAJ.finditer(line):
            digits = "".join(m.groups())
            if len(set(digits)) > 1 and taj_ok(digits):
                out.append((no, "TAJ", m.group(0)))
    return out


def load_config(text=None):
    cfg = dict(DEFAULTS)
    if text is None and os.path.isfile(os.path.join(ROOT, CONFIG)):
        text = open(os.path.join(ROOT, CONFIG), encoding="utf-8").read()
    if text:
        cfg.update(json.loads(text))
    return cfg


def staged():
    """The staged files (added, copied, modified, renamed) with their staged content, read from the index."""
    names = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd=ROOT,
                           capture_output=True, check=True).stdout.decode().split("\0")
    for name in filter(None, names):
        blob = subprocess.run(["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=True).stdout
        yield name, blob


def scan(files, cfg):
    """Problems as 'path:line: what' lines; empty when every file is clean."""
    probs = []
    for name, blob in files:
        for pattern, why in cfg["forbiddenNames"]:
            if re.search(pattern, name, re.I):
                probs.append(f"{name}: {why} (refused by file name)")
        if any(name.startswith(f) for f in cfg["fixtures"]):
            continue
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("%s: not UTF-8 text, not scanned", name)
            continue
        for no, kind, value in findings(text, cfg["inventedBankPrefix"]):
            probs.append(f"{name}:{no}: a real-looking {kind} ({value}); use an invented one with a wrong check digit")
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--staged", action="store_true", help="scan the files staged for commit")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.staged:
        try:
            cfg_text = subprocess.run(["git", "show", f":{CONFIG}"], cwd=ROOT, capture_output=True).stdout.decode() or None
        except OSError:
            cfg_text = None
        cfg, files = load_config(cfg_text), list(staged())
    else:
        cfg, files = load_config(), [(p, open(p, "rb").read()) for p in a.paths]
    probs = scan(files, cfg)
    for p in probs:
        print(p, file=sys.stderr)
    logger.info("real-data check: %d file(s), %d finding(s)", len(files), len(probs))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
