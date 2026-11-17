"""Tests of the pilóta kit (kit/load_profile.py), offline: no program, no machine, no desktape run.

    python3 -m unittest discover -s tests
"""
import os
import shutil
import sys
import tempfile
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "kit"))
import load_profile as kit  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures", "profiles")


class ScratchProfile:
    """A copy of the jegyzet fixture under tests/, with its repo-relative paths rewritten to the copy, so one
    test can break one thing in it."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix=".tmp-", dir=HERE)
        self.home = os.path.join(self.dir, "jegyzet")
        shutil.copytree(os.path.join(FIXTURES, "jegyzet"), self.home)
        old, new = "tests/fixtures/profiles/jegyzet/", kit.rel(self.home) + "/"
        for root, _, files in os.walk(self.home):
            for f in files:
                if f.endswith(".yaml"):
                    p = os.path.join(root, f)
                    with open(p, encoding="utf-8") as fh:
                        s = fh.read().replace(old, new)
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(s)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir)

    def edit(self, path, change):
        p = os.path.join(self.home, path)
        with open(p, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        change(data)
        with open(p, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, allow_unicode=True)

    def load(self):
        return kit.load("jegyzet", self.dir)


class ProfileSchema(unittest.TestCase):
    def test_fixture_profile_passes(self):
        m = kit.load("jegyzet", FIXTURES)
        self.assertEqual(kit.check(m), [])

    def test_safety_cannot_be_switched_off(self):
        with ScratchProfile() as s:
            s.edit("profile.yaml", lambda d: d["safety"].update(ui_only=False))
            with self.assertRaisesRegex(kit.ProfileError, r"safety.ui_only: must be True"):
                s.load()

    def test_missing_safety_block_is_refused(self):
        with ScratchProfile() as s:
            s.edit("profile.yaml", lambda d: d.pop("safety"))
            with self.assertRaisesRegex(kit.ProfileError, r"missing 'safety'"):
                s.load()

    def test_write_entry_needs_backup_and_read_back(self):
        with ScratchProfile() as s:
            s.edit("profile.yaml", lambda d: d["tapes"]["write"]["uj-jegyzet"].pop("read_back"))
            with self.assertRaisesRegex(kit.ProfileError, r"missing 'read_back'"):
                s.load()

    def test_unknown_field_is_refused(self):
        with ScratchProfile() as s:
            s.edit("profile.yaml", lambda d: d.update(database="notes.dbf"))
            with self.assertRaisesRegex(kit.ProfileError, r"unknown field 'database'"):
                s.load()

    def test_folder_and_id_must_match(self):
        with ScratchProfile() as s:
            s.edit("profile.yaml", lambda d: d.update(id="masik"))
            with self.assertRaisesRegex(kit.ProfileError, r"differs from its folder name"):
                s.load()


class TapeRules(unittest.TestCase):
    def test_write_tape_without_read_back_is_refused(self):
        with ScratchProfile() as s:
            s.edit("tapes/write/uj-jegyzet.yaml", lambda d: d.pop("read_back"))
            m = s.load()
            self.assertTrue(any("must name its read_back tape" in p for p in kit.check(m)))
            with self.assertRaisesRegex(kit.ProfileError, "refusing to run"):
                kit.plan(m, "write", "uj-jegyzet", "test-pc", [])

    def test_write_tape_without_backup_is_refused(self):
        with ScratchProfile() as s:
            s.edit("tapes/write/uj-jegyzet.yaml", lambda d: d.pop("backup"))
            self.assertTrue(any("must name its backup tape" in p for p in kit.check(s.load())))

    def test_read_back_must_check_a_value(self):
        with ScratchProfile() as s:
            s.edit("tapes/read/visszaolvas.yaml", lambda d: d.update(steps=[{"focus": "@window"}]))
            self.assertTrue(any("at least one `expect`" in p for p in kit.check(s.load())))

    def test_read_tape_must_not_write(self):
        with ScratchProfile() as s:
            s.edit("tapes/read/jegyzetek.yaml", lambda d: d["steps"].append({"type": {"text": "x", "into": "@text"}}))
            self.assertTrue(any("a read tape must not write" in p for p in kit.check(s.load())))

    def test_map_must_resolve_from_the_repository_root(self):
        with ScratchProfile() as s:
            s.edit("tapes/read/jegyzetek.yaml", lambda d: d.update(map="maps/jegyzet.yaml"))
            self.assertTrue(any("does not resolve from the repository root" in p for p in kit.check(s.load())))

    def test_map_outside_the_profile_is_refused(self):
        with ScratchProfile() as s:
            s.edit("tapes/read/jegyzetek.yaml", lambda d: d.update(map="tests/fixtures/profiles/jegyzet/maps/jegyzet.yaml"))
            self.assertTrue(any("lies outside the profile" in p for p in kit.check(s.load())))


class Running(unittest.TestCase):
    def test_read_is_one_desktape_run_from_the_repo_root(self):
        os.environ["DESKTAPE"] = "desktape"
        m = kit.load("jegyzet", FIXTURES)
        (tape, cmd), = kit.plan(m, "read", "jegyzetek", "test-pc", [])
        self.assertEqual(tape, "tests/fixtures/profiles/jegyzet/tapes/read/jegyzetek.yaml")
        self.assertEqual(cmd, ["desktape", "run", tape, "--target", "test-pc"])

    def test_write_runs_backup_then_write_then_read_back(self):
        os.environ["DESKTAPE"] = "../desktape/desktape.py"
        m = kit.load("jegyzet", FIXTURES)
        steps = kit.plan(m, "write", "uj-jegyzet", "test-pc", ["szoveg=Teszt jegyzet"])
        self.assertEqual([os.path.basename(t) for t, _ in steps], ["mentes.yaml", "uj-jegyzet.yaml", "visszaolvas.yaml"])
        for _, cmd in steps:
            self.assertEqual(cmd[0], sys.executable)
            self.assertEqual(cmd[-2:], ["--var", "szoveg=Teszt jegyzet"])

    def test_unknown_tape_names_the_ones_there_are(self):
        m = kit.load("jegyzet", FIXTURES)
        with self.assertRaisesRegex(kit.ProfileError, r"has no read tape 'nincs'.*jegyzetek"):
            kit.tape_path(m, "read", "nincs")

    def test_cli_check_and_dry_run(self):
        self.assertEqual(kit.main(["--profiles-dir", FIXTURES, "check"]), 0)
        self.assertEqual(kit.main(["--profiles-dir", FIXTURES, "run", "jegyzet", "write", "uj-jegyzet",
                                   "--target", "test-pc", "--var", "szoveg=x", "--dry-run"]), 0)
        self.assertEqual(kit.main(["--profiles-dir", FIXTURES, "show", "nincs"]), 2)


if __name__ == "__main__":
    unittest.main()
