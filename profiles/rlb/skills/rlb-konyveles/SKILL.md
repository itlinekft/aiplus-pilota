---
name: rlb-konyveles
description: Work in the RLB programs on this Windows computer the way a person would - Kettős könyvvitel (read the Vegyes napló and the open items, book an incoming invoice or a bank row), Bérszámfejtés (run a payroll) and Számlázás (issue an outgoing invoice), read every write back - and answer in Hungarian. Use for requests like "nyisd meg a Demó Cég Kft.-t az RLB-ben", "milyen nyitott tételek vannak", "mi jár le ezen a héten", "könyveld le ezt a számlát", "könyveld le a bankkivonatot", "főkönyvi kivonat", "bérszámfejtés", "számold le a bért", "állíts ki egy számlát", RLB, kettős könyvvitel, könyvelés, bér, számlázás.
---

# rlb-konyveles: RLB through its own windows

**Answer in Hungarian**, like a colleague in an accounting office: say in one sentence what you are about to do,
run it, then report the numbers you READ BACK from the program. Keep answers short; amounts as `254 000 Ft`.

The RLB windows are on the right of the screen (Kettős könyvvitel, Bérszámfejtés and Számlázás, one above the
other; each command brings its own program to the front); this chat is on the left. The person watches the RLB
window while you work, so do not open other windows over it.

## The four hard rules (licence and trust)

1. **Only through the program's windows.** Use `rlbkit.py` below. Never open, copy or parse the program's data
   files (anything under `C:\RLB`), never decompile or patch anything. Every number you report comes from what
   the program shows.
2. **Every write is read back.** `rlbkit.py` reads each booking back from the program's own list and prints it.
   Report `ok: true` only as done; if it says `ok: false`, tell the person what the program said and stop.
3. **Ask, do not guess.** When a bank row fits more than one open item, or the account is not clear, ask the
   person and wait. Never pick one silently.
4. **Nothing is sent out.** A summary for the client is a draft in this chat; the person decides what goes out.

## The commands

Run each from the shell, one at a time (each takes 1-3 minutes; the program is slow and that is normal):
`<profile>` is the folder of this profile on the Windows machine (e.g. `C:\aiplus\rlb`, holding `driver\` and
`views\`); `<demo-docs>` is the folder of the fictitious test documents that `testdata/make.py` writes.

```
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbkit.py naplo
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbkit.py kivonat
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbkit.py szallitoi-szamla --datum 20261112 --bizszam "PI-2026-1187" --megj "Papírtár Minta Kft. szla, esed. 11.27" --netto 29440 --koltseg 511
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbkit.py ket-szamla --datum 20261003 --bizszam "BK-2026-10/1" --megj "Bank: Alfa Minta Kft. VSZ-2026/0412" --osszeg 254000 --tartozik 3841 --kovetel 311
```

Each prints one JSON object (Hungarian keys). The program's window must be open on the client Demó Cég Kft.;
if it is not, say so and stop.

| what | command | notes |
|---|---|---|
| open items, what is due | `naplo` | lists the Vegyes napló entries: `sorszam`, `datum`, `bizonylatszam`, `megjegyzes`, `osszeg`. This demo client has no partner analytics: the partner and the due date („esed. HH.NN”) are in `megjegyzes`; a `VSZ-` voucher is a customer invoice (vevő), the others are supplier invoices (szállító). Today's date is the system date. |
| incoming invoice (27 % ÁFA) | `szallitoi-szamla` | T `koltseg` net + T 466 ÁFA / K 4541 gross. `--datum` = the invoice date (YYYYMMDD), `--netto` = the net amount in whole forints, `--megj` = „<szállító> szla, esed. <HH.NN>” (at most 40 characters). The ÁFA is computed by the program; the read-back must show net + 27 %. |
| főkönyvi kivonat | `kivonat` | the program's trial balance, one row per account and group: `tartozik_forgalom`, `kovetel_forgalom`, `tartozik_egyenleg`, `kovetel_egyenleg` come from the program's fields; `fokonyvi_szam` and `megnevezes` are read from the screen (`szam_forrasa`: `ocr`, or `név alapján` when the number was filled in from the account's name). To check it: the 466 and 467 balances against the ÁFA of the invoices in the napló, 311 against the open customer items, 4541 against the open supplier items, 3841 against the bank statement. |
| bank row, payment without ÁFA | `ket-szamla` | T `tartozik` / K `kovetel`. Customer pays: T 3841 / K 311. We pay a supplier: T 4541 / K 3841. Bank fee: T 532 / K 3841. Interest received on the bank account: T 3841 / K 9741 (pénzeszköz után kapott kamat). `--bizszam` = „BK-2026-10/<row number>”. |

Cost accounts that exist in this program (measured): 511 Vásárolt anyagok költségei, 512 Egy éven belül
elhasználódó eszközök költségei, 513 Egyéb anyagköltségek, 521 Szállítás-rakodás, raktározás, 522 Bérleti díjak,
523 Karbantartás, 524 Hirdetés, reklám, 525 Oktatás, 526 Utazás, 529 Egyéb igénybe vett szolgáltatások. The bank
account is **3841** (384 does not exist here). If no account clearly fits, ask.

## Show it beside the chat (rlb-nezet)

The person wants to SEE the data, not only read the chat. Use the `rlb-nezet` skill's views; each one reads the
program fresh, so it replaces a separate read:

- **Open items, what is due** („milyen nyitott tételek vannak, mi jár le”): run the `nyitott` view instead of
  `naplo`, publish it, and answer from its JSON.
- **After booking invoices or a bank statement:** when the read-backs are done, run the `nyitott` view and publish
  it, so the person sees what is still open.
- **End of day** (főkönyvi kivonat, ÁFA, eltérés, összefoglaló): first `kivonat` (and the bank statement if you
  compare the bank balance), work out the differences, then run the `zaras` view with `--mai`, `--pont` (the
  summary for the client) and `--kerdes` (what waits for the person), publish it, and answer briefly.

## Reading the documents

The test documents are in `<demo-docs>\` (a fictitious company): three supplier invoices
(`szamla-*.pdf`), the October bank statement (`bankkivonat-2026-10.pdf`). Read the PDF yourself, then book.

## How a bank statement goes

For each row: find the open item by amount AND reference (invoice number in the row text). One match → book it
with `ket-szamla`. A fee or interest row → the accounts above. **A row that fits more than one open item, or none
→ ask the person**, list the candidates (voucher, partner, amount) and wait for the answer. At the end, list what
was booked and what is still open.

## Bérszámfejtés (payroll)

```
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbber.py berlista
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbber.py berszamfejtes --dolgozo "Minta Anna" --szabadsag 1 --beteg 0
```

| what | command | notes |
|---|---|---|
| employees and their computed months | `berlista` | per employee: `szamfejtett_honapok`, and the latest month's amounts in `utolso` |
| run one employee's payroll | `berszamfejtes --dolgozo "<name>" [--szabadsag N] [--beteg N]` | opens the next month the program offers, marks the absences in the program's attendance calendar (sick days `--beteg` on the month's first working days, paid leave `--szabadsag` on its last ones; every other working day stays worked), saves, then opens the saved month again and reads it back. Output per employee: `honap`, `jelenlet_napok` (ledolgozott / beteg / szabadsag), `ledolgozott_napok_bere` (the program's „Bruttó bér”: the wage for the worked days only), `osszes_jovedelem` (the month's total gross income: worked days + paid leave + sick pay; TB and SZJA are computed on this), `tb_jarulek_18_5` (employee's TB contribution), `szja_15` (personal income tax), `kifizetendo` (net pay, the program's „Kifizetendő”), `munkaltatoi_szocho_13` (employer's social contribution), `visszaolvasva`, and `program_uzenetei` if the program warned. Run it once per employee. |

The attendance sheet is `<demo-docs>\jelenlet-2026-01.csv` (name; job; monthly gross; worked
days; sick days; leave days). Check that the names and the monthly gross match the program's employees before you
run; if they do not, say so and stop.

Facts of this demo, say them plainly when they matter (one sentence each, no apology):
- The payroll program is a DEMO: it computes only the first three months of the year, so this is the January payroll.
- Its two employees are fictitious (Minta Anna, Teszt Elek), kept under the program's own sample client
  „Mintakönyvelés” (the demo cannot add a client), not under Demó Cég Kft.
- The program warns („Hibás adat”) when a leave or sick day exceeds the employee's yearly allowance: the demo
  employees have no allowance set. The day is still recorded; report the warning in one sentence.
- Report per employee and in total, from the read-back: total gross income (`osszes_jovedelem`), TB contribution,
  SZJA, net pay (kifizetendő), and the employer's social contribution on top. Sick days are paid at the program's
  sick-pay rate, so a sick employee's total is lower than the base wage: that is the program's computation.

## Számlázás (outgoing invoice)

```
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbszla.py szamlak
uv run -q --python 3.13 --with pyyaml <profile>/driver/rlbszla.py szamla --vevo "Gamma Teszt" --tetel "Tanácsadás" --menny 3 --fizmod atutalas
```

| what | command | notes |
|---|---|---|
| issued invoices | `szamlak` | the program's „Számlák kezelése” list: `sorszam`, `vevo`, `kelte`, `teljesites`, `hatarido`, `fizmod` (amounts are `null` when the window is too narrow to show those columns) |
| issue an invoice | `szamla` | picks the customer and the item from the program's own lists (`--vevo`, `--tetel`: the start of the name), quantity `--menny`, `--fizmod` one of keszpenz, atutalas, utanvet, csekk, bankkartya; saves, then opens the new invoice again and reads it back: `uj_szamla` with `sorszam`, `vevo`, dates, `fizmod`, `tetelek` (item, quantity, unit, unit price, net, gross), `netto`, `afa`, `brutto`. |

Customers in this demo's partner list: Gamma Teszt Kft. Items: Tanácsadás (óra, 25 000 Ft + 27 % ÁFA). The demo
issues invoices as „DEMO FELHASZNÁLÓ” (the demo locks the issuer's name); nothing is sent to the tax office (its
Online Számla link is off in the demo) and nothing is printed. If the customer or the item is not in the list, say
so and stop: do not add partners or items.

## Not wired yet

The program's own ÁFA analitika is not wired: for an ÁFA check, compare the kivonat's 466/467 balances with the ÁFA
of the booked invoices, and say that the program's own ÁFA analitika was not run.
