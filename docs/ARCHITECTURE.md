# How AI+ pilóta is built

AI+ pilóta lets Claude operate a desktop program through the program's own windows. The driving is done by
[desktape](https://github.com/itlinekft/aiplus-desktape). This repository adds **profiles**: one per program. A profile
says where things are in that program and what steps a task takes. A small generic **kit** loads a profile, checks it
and hands its tapes to desktape.

## The parts

| part | where | what it is |
|---|---|---|
| kit | `kit/load_profile.py`, `kit/profile_schema.yaml` | vendor neutral: loads a profile, checks it, runs its tapes through desktape |
| real-data gate | `kit/real_data.py`, `.aiplus-real-data.json` | refuses a commit that carries a real-looking identifier or a program data file |
| profile | `profiles/<id>/` | one program: manifest, maps, tapes, Claude skills, views, a fictitious example |

The kit knows nothing about any one program. A second program is a new `profiles/<id>/` folder with its own manifest,
and the kit runs it the same way.

## A profile

```
profiles/<id>/
  profile.yaml        the manifest: what the profile holds and its guardrails
  maps/               desktape maps: named selectors for the program's fixed screens, plus `ignore:` regions
  tapes/read/         desktape tapes that only navigate and read
  tapes/write/        desktape tapes that enter data; each names its backup and read-back tapes
  skills/<name>/      Claude skills (SKILL.md) that pick a task and call the kit
  views/              static HTML view templates (no script, no network, every value escaped)
  examples/           a fictitious company and the outputs expected from it
```

Maps and tapes use **desktape's own format**, so desktape reads them directly; nothing is copied into desktape.

### The path contract with desktape

desktape takes a tape by path, and reads the tape's `map:` value as a path when that path exists. So:

- a profile tape names its map **relative to this repository's root**: `map: profiles/<id>/maps/<name>.yaml`;
- the kit runs desktape **with this repository's root as the working directory**:
  `desktape run profiles/<id>/tapes/read/<name>.yaml --target <machine>`.

`kit/load_profile.py check` refuses a map path that does not resolve from the root, or one that points outside the
profile.

### The manifest

`profile.yaml` is checked against `kit/profile_schema.yaml`. It names the program (family, modules, the versions
the maps were checked against, the OS), the engine (`desktape`), the maps, the read and write tapes, the skills and
the views. Its `safety` block holds five rules, and each one is fixed to `true` by the schema, so a profile cannot
switch any of them off:

- `own_words_only`: the profile describes the program in our own words, and copies nothing from its manual;
- `ui_only`: only what the program's windows show; never its data files, never reverse engineering;
- `backup_before_write`: a write starts with a backup the program can restore from;
- `read_back_every_write`: a write ends by reading the values back from the program's own list;
- `fictitious_data_only`: examples and tests use invented companies and numbers.

### Read and write tapes

A **read tape** may click and press keys to navigate, but it may not type, set or open a file; the check refuses
one that does.

A **write tape** names two more tapes at its top level:

```yaml
backup: {tape: profiles/<id>/tapes/write/<backup>.yaml}       # the program's own backup, through its screens
read_back: {tape: profiles/<id>/tapes/read/<read-back>.yaml}   # at least one `expect` step on the written values
```

The manifest marks the write entry `backup: true, read_back: true`, and the kit checks the tape itself too. A write
then runs three desktape runs with the same `--var` values, and stops at the first one that fails:

1. the backup tape;
2. the write tape;
3. the read-back tape, whose `expect` steps find the written values in the program's own list.

## Using it

```bash
python3 kit/load_profile.py list
python3 kit/load_profile.py check                     # every profile; also run by the pre-commit hook
python3 kit/load_profile.py show <id>                 # the profile's maps, tapes and skills as desktape paths
python3 kit/load_profile.py run <id> read <tape> --target <machine>
python3 kit/load_profile.py run <id> write <tape> --target <machine> --var name=value --dry-run
```

desktape is found as `$DESKTAPE` (a command, or a path to `desktape.py`), else `desktape` on `PATH`.

A Claude skill in a profile calls the same commands. For an answer that is easier to read as a page, a view skill
fills one of the profile's view templates from a read tape's result and shows it beside the chat.

## Public and private

Everything here is public (MIT). A profile is a description in our own words, made from what the program's screens
show, with invented data. Nothing that shows a real customer's data belongs here: no screenshots or recordings of a
real office, no exported files, no maps or tapes that carry a real company's names. Those stay on the machine where
they were made.

The real-data gate backs this up. `scripts/install-hooks.sh` turns on the pre-commit hook, which runs
`kit/real_data.py --staged` and `kit/load_profile.py check`. The gate refuses an adószám, TAJ or bankszámlaszám whose
check digit is right (an invented number simply gets a wrong one), and refuses program data files, exports and
screen images by name. Files under `tests/fixtures/` are not scanned. The own-words rule cannot be checked by a
program: it is a review item for every new or changed profile.

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests run offline on a made-up profile in `tests/fixtures/profiles/jegyzet/`.
