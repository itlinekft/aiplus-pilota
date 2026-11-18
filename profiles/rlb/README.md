# RLB profil / RLB profile

## Magyarul

Ezzel a profillal a Claude az RLB könyvelőprogramokat a saját ablakaikon keresztül kezeli: a Kettős könyvvitelt
(Vegyes napló olvasása, nyitott tételek, bejövő számla és banksor könyvelése, főkönyvi kivonat), a Bérszámfejtést
(havi számfejtés a jelenléti adatokból) és a Számlázást (kimenő számla kiállítása). Minden írást a program saját
listájából visszaolvas, és csak azt mondja, amit a program mutat.

**Az ITLine készítette. A profil az iroda saját, jogtiszta RLB programját vezérli az iroda saját gépén. Nem az RLB-60
Bt. terméke, és nem áll kapcsolatban az RLB-60 Bt.-vel.** Az „RLB” név csak azt jelöli, melyik programhoz készült.

## In English

With this profile Claude operates the RLB accounting programs through their own windows: Kettős könyvvitel
(double-entry bookkeeping: read the journal and the open items, book an incoming invoice or a bank row, trial
balance), Bérszámfejtés (payroll from the attendance data) and Számlázás (issue an outgoing invoice). Every write is
read back from the program's own list, and Claude reports only what the program shows.

**Made by ITLine. The profile drives the office's own licensed RLB program on the office's own machine. It is not a
product of RLB-60 Bt. and is not affiliated with RLB-60 Bt.** The name "RLB" only says which program it is for.

## What is here

| path | what it is |
|---|---|
| `profile.yaml` | the manifest the pilota kit checks |
| `driver/rlbkit.py` | Kettős könyvvitel: `naplo`, `kivonat`, `szallitoi-szamla`, `vevoi-szamla`, `ket-szamla` |
| `driver/rlbber.py` | Bérszámfejtés: `berlista`, `berszamfejtes` |
| `driver/rlbszla.py` | Számlázás: `szamlak`, `szamla` |
| `driver/nezet.py` | read-only HTML views (nyitott tételek, kivonat, ÁFA, napi, zárás) built from a fresh read |
| `driver/recipes/` | the Vegyes napló write recipes (desktape tape format) that `rlbkit.py` plays |
| `skills/rlb-konyveles/` | the Claude skill for the bookkeeping, payroll and invoicing work |
| `skills/rlb-nezet/` | the Claude skill for the views beside the chat |
| `testdata/make.py` | makes the fictitious test documents (three supplier invoices, a bank statement, an attendance sheet) |

## Running it

On the Windows machine with the RLB programs and [desktape](https://github.com/itlinekft/aiplus-desktape):

```
set DESKTAPE_DIR=C:\path\to\desktape          (the folder of desktape.py)
set DESKTAPE_HOST=local
uv run -q --python 3.13 --with pyyaml <profile>\driver\rlbkit.py naplo
```

From a controller, set `DESKTAPE_HOST` to the desktape target of the Windows machine instead. The skills name the
commands Claude runs; `<profile>` in them is where this folder sits on the Windows machine.

The scripts assume the layout they were measured in: the RLB window on the right of a 1920x1080 screen (or
maximised), the Claude window on the left. Field points are taken from the program's own UI Automation frames where
the program exposes them, and from the program's centred form otherwise.

## Safety

- UI only: the scripts never open, copy or parse the program's data files, and never decompile or patch anything.
- Back up the program's data with the program's own backup before a write session; every write is read back.
- Fictitious data only in this repository.

## Demo limits (measured on the DEMO versions)

- Kettős könyvvitel: at most 30 entries per client; new partners cannot be added, so partners go in the entry text.
- Bérszámfejtés: only January-March can be computed; only the built-in sample client is available.
- Számlázás: the issuer is locked to „DEMO FELHASZNÁLÓ”; new partners and items cannot be added.

A licensed install has none of these limits; it needs its own check of the recipes before the first write.

## Status

The driver scripts and recipes ran on a Windows 11 test VM against the DEMO versions on 2026-11-17/18: bookings,
payroll and an invoice, all read back. The kit has no tape to run yet (see `profile.yaml`): that needs two desktape
engine additions, a playback without the settle read between steps, and click points relative to the program's form.
