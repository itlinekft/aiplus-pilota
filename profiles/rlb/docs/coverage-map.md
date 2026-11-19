# RLB coverage map

What each screen of the three RLB programs shows, and whether Claude can read it or write it through the program's own
window. Measured on 2026-11-18 on a Windows 11 test VM against the DEMO versions (Kettős könyvvitel 26.6.0,
Bérszámfejtés 26.12.0, Számlázás és készletnyilvántartás 2 9.91) with fictitious data only.

**Method.** Breadth-first, read-only. Each Gyorsmenü tile and each list on the Számlázó desktop was opened with one real
click. The program's UI Automation tree was dumped and a frame was saved. A parameter dialog got one
`Tovább`. The screen was then closed with its own exit button; a quit question was answered „Nem”. Nothing was typed,
saved or posted. Create forms were opened only in Kettős Könyvelés, and closed unsaved. Afterwards the Vegyes napló
still had 13 entries, the invoice list still had 1 invoice and the payroll list was unchanged (read back with
`rlbkit naplo`, `rlbszla szamlak`, `rlbber berlista`). The raw dumps and frames are not published: they carry the
test machine's status bar and paths.

## Legend

| mark | meaning |
|---|---|
| **R✔** | read proven: a driver command reads it and the values were checked against the screen |
| **R** | readable: the list's headers and the visible cells' values are in the UI Automation tree (seen in the dump) |
| **R?** | the screen opens but its values are not exposed, or it is empty here, so readability is not shown |
| **W✔** | write proven: a driver recipe writes it, backup first, read back from the program's own list |
| **W** | writable in principle: a create or edit form opens and exposes its fields; no recipe yet |
| **W–** | a posting, export or settings action: deliberately not touched |
| **demo** | blocked or limited by the DEMO version |
| **data** | empty here: needs data, or a client's real install, to show populated |
| **real** | can only be verified on a client's real install |

## Built-in sample data

| program | sample client | what it holds | used here |
|---|---|---|---|
| Kettős könyvvitel | „Mintakönyvelés 2026” (seen in Szerviz → Mentés), beside „Demó Cég Kft. 2026” | not opened: switching client goes through the Alapadatok menu, which the driver cannot reach (see Limits) | Demó Cég Kft. with our 13 fictitious entries |
| Bérszámfejtés | „Mintakönyvelés” is the only client the demo offers | 2 sample employees (Minta Anna, Teszt Elek), 51 jogcímek, 9 jogviszonyok, 22 nyugdíjpénztárak, 2 sample company cars; Bérösszesítő 132 rows | yes, with our January payroll |
| Számlázás | shipped sample partner „Gamma Teszt Kft.” and sample item „Tanácsadás”; the issuer is locked to „DEMO FELHASZNÁLÓ” | 1 partner, 1 cikk (both shipped), 1 invoice (ours) | yes |

No program offers a „load demo data” option. Kettős does ship a second client, „Mintakönyvelés”; how much it holds is not yet seen. The richest data is the Bér sample client, then our own Kettős entries.

## Kettős könyvvitel

### Lekérdezés

| screen | purpose | shows | read | write | notes |
|---|---|---|---|---|---|
| Pénzügyi nyilvántartás | open items and their settlement | parameter dialog (current state / at a date), then a list: Lejár, Naplósorszám, Fők.sz., Kelt, Telj., Áfa esed., Fiz.hat., Kiegyen., Fiz.mód, Bizonylatszám, Msz., Part.kód… | R | W (Új vevő / száll. tétel, Kiegyenlítés könyvelése) | empty for Demó Cég Kft.: our entries are Vegyes, not vevő/szállító; **data** |
| Pénztár- és banknapló | cash and bank journal | Naplósorszám, Fők.sz., Dátum, Biz.szám, Eredeti biz.sz., Hivatkozás, Msz., Part.kód, Partner neve, Megjegyzés | R | W (Új pénztári / banki tétel) | empty; **data** |
| Vegyes napló | general journal | Naplósorszám, Dátum, Bizszám, Hivatkozás, Msz., Part.kód, Partner neve, Megjegyzés, Összeg | **R✔** (`rlbkit naplo`) | **W✔** (szállítói / vevői / két számla recipes) | 13 entries; demo max 30 per client |
| Nyitó napló | opening entries | Naplósorszám, Dátum, Fők.szám, Ellenszámla, Part.kód, Partner neve, Megjegyzés, Tartozik, Követel | R | W (Könyvelés → Nyitó) | empty; **data** |
| Záró napló | closing entries | same columns as Nyitó | R | W– | empty; **data** |
| Összes napló | every journal in one list | Naplósorszám, N., Fők.sz., Kelt/Dátum, Telj., Fiz.hat, Bizonylatszám, Hivatkozás, Part.kód, Partner neve, Msz., Megjegyzés | R (13 rows, values exposed) | edit/delete buttons, W– | populated |
| Főkönyvi kivonat | trial balance per account | 614 accounts; Dátum, Naplósorsz., Fők.szám, Biz.szám, P.kód, Partner neve, Megjegyzés, Ellen fők.számok, Munkasz., Tartozik, Követel, Egyenleg, T/K | **R✔** (`rlbkit kivonat`) | — | populated |
| Főkönyvi kartonok | ledger card of one account | Biz.szám, P.kód, Partner neve, Megjegyzés, Ellen fők.számok | R? (the account is chosen first) | — | needs an account picked; next step |
| Gyorsmérleg | quick balance sheet and P&L | tabs Mérleg, Eredménykimutatás, Hibakeresés; Megnevezés, Tárgyév, Tartozik, Követel, egyenlegek | R (113 rows, amounts exposed) | W– (Mérleg beállítások) | populated |
| Házipénztár | cash book of one cash account | 3811 / 3821 choice; Sorszám, Dátum, Bizonylatszám, Partner, Bevétel, Kiadás, Záró egyenleg, Kerekítés | R | — | empty; **data** |
| ÁFA-analitika | VAT analytics and return | month list + Tovább, then tabs ÁFA lista, ÁFA összesítés, Éves ÁFA összesítő, ÁFA bevallás, Összesítő nyilatkozat, Fordított áfás nyilatkozat, Tételes adatszolgáltatás; Sorszám, Napló, ÁFA esed., Bizonylatszám, Partner, ÁFA%, Nettó, Fizetendő ÁFA… | R (values exposed) | W– (ÁNYK export) | readable; no driver command yet; the bevallás itself is **real** (ÁNYK, Ügyfélkapu) |

### Törzsadatok

| screen | purpose | shows | read | write | notes |
|---|---|---|---|---|---|
| Partner törzs | partners | Azon., Partner neve, Adószám, Város; tabs Személyes adatok, Egyéb adatok, Őstermelő 1–2, Kontírozás | R | W | empty; **demo**: new partners cannot be added |
| Főkönyvi törzs | chart of accounts | Főkönyvi szám, Megnevezés (614) | R | W (Új tétel, Import) | populated |
| Munkaszám törzs | cost centres | Munkaszám, Megnevezés | R | W | empty; **data** |
| Gazdasági események | posting templates | — | — | — | **demo**: disabled |
| Levelezés törzs | letter texts | Megnevezés, Cím (1) | R | W | populated (1) |
| Deviza törzs | currencies | Devizanem, Megnevezés (2: EUR and one more) | R | W | populated |

### Könyvelés (entry forms: opened, nothing saved)

| screen | shows | write | notes |
|---|---|---|---|
| Vevő számla | header fields; tabs Számlasorok, Kontírozás, Számla jegyzet; Megjegyzés, Áfa%, Nettó, ÁFA, Bruttó, Fők.szám, M.szám, Tartozik, Követel, devizás oszlopok; Gépi kontírozás | W | partner needed: **demo** (no new partners) |
| Szállító számla | same as Vevő, plus E.bizszám | W | partner needed: **demo** |
| Pénztár | as Vevő, without the partner columns; Számla kiválasztása | W | next recipe candidate |
| Bank | as Pénztár | W | next recipe candidate: the bank row now goes through Vegyes |
| Vegyes | Számlasorok, Kontírozás; MNB árfolyam | **W✔** | the recipes in use |
| Nyitó | Partner, Megnevezés, Tartozik, Követel, Fők.szám; Mentés+Kilépés | W | |

### Tárgyieszköz

| screen | shows | read | write | notes |
|---|---|---|---|---|
| Tárgyi eszközök | Leltári szám, Megnevezés, Státusz, Mennyiség, Dátum, Bruttó, ÉCS; tabs Eszköz alapadatai, Értékcsökkenés adatok, Tartozékok, Értékváltozások | R | W (Új tétel) | empty; **data** |
| Eszközlisták | Leltári szám, Fők.szám, Típus, Megnevezés, Beszerzés, Üzembeh., Bruttó érték, Sztv.% | R | — | empty; **data** |
| Mozgások listája | Dátum, Mozgáskód, Lelt.szám, Bruttó ért. vált., ÉCS vált. | R | — | empty; **data** |
| Beállítások | settings form | R? | W– | |
| ÉCS csoportos elszámolása, Feladás | posting actions | — | W– | not opened |

### Szerviz

| screen | shows | notes |
|---|---|---|
| Beállítások | tabs Beállítások 1–2, Táblázat beállítások, Internet, Könyvtárak | settings, W– |
| Könyvelés beállításai | tabs Sorszámok, Fők. számok 1–4, Beállítások | settings, W– |
| Mentés | the program's own backup: a client list (Demó Cég Kft. 2026, Mintakönyvelés 2026) | **the backup step before every write session**; R |
| Statisztika | Megnevezés, Tételszám (32 rows) | R |
| Állományok rendezése, Visszatöltés | reindex, restore | not opened: W– |

### Menu-only items (Alapadatok, Tárgyi eszközök menus)

Catalogued from a frame, not opened: Ügyfél választása, Könyvelési év váltása, Törzsadatok/nyitó tételek átvétele,
csv import, ÁNYK küldeménynapló, Ügyfél törzs, Partnerfigyelő, Partnerek összevonása, Adónem törzs, Pénztár/Bank
egyenlegek és sorszámok, E-mail küldés, Napló, Ügyfélkapu+ beállítások, Nyomtatók, Program frissítése, Regisztrálás;
Eszközök értékének éves változása, KIVA csökkentő érték, Mozgáskódok, Leltári szám csere. Disabled in the demo:
Gazdasági esemény törzs, Felhasználói jogok, Importálás, Kijelentkezés. The Cashbook menu is greyed out.

## Bérszámfejtés

| screen | purpose | shows | read | write | notes |
|---|---|---|---|---|---|
| Béradatok | the month's payroll per employee | employees (Név, Törzsszám); Hónap, Bruttó bér, Kifizetve, Hóközi kifizetés, 08M | **R✔** (`rlbber berlista`) | **W✔** (`rlbber berszamfejtes`) | January for both sample employees; **demo**: only January–March |
| Nyomtatványok | tax and social forms per employee | Név, Törzsszám, Adószám, Tajszám, Jogviszony; form list, Nyomtatás, Beküldött bevallások | R | W– (print, submit) | submission is **real** |
| Munkabér előleg | wage advances | Kifizetett előleg, Lejárat dátuma, Kif. bizonylat száma | R | W (Új tétel) | empty; **data** |
| Hóközi számfejtés | mid-month payments, dividend | Dátum, Jogcím megnevezése, Bruttó, Nettó | R | W (Új hóközi / osztalék számfejtés) | empty; **data** |
| Kieső idő | absences | Kód, Dátumtól, Dátumig | R | W (Új tétel) | empty; **data** |
| 08M (column) | monthly 08 return state | „Nem készült” | R | W– | |
| Alkalmazott törzs | employee master | Név, Törzsszám, Adóazonosító, TAJ; tabs Személyes adatok 1–2, Címek, Eltartottak, Jogviszony | R (2 employees) | W | the status bar says Record 2/2, but the first frame showed one row: check the grid read before relying on it |
| Adatok rögzítése (EFO) | casual workers | Név, Napok, Jövedelem, Közteher; M2M lekérdezések, EFO CSV betöltés, Lezárás | R | W | empty; **data**; M2M is **real** (online) |
| Cégtelefon magáncélú használata | private phone use tax | Hónap, Számla összege, Adóalap, SZJA, Szoc. adó, KIVA | R | W (Adatrögzítés) | empty; **data** |
| Reprezentáció | entertainment tax | Hónap, SZJA alap, SZJA, Szoc. adó, KIVA, Összes adó | R | W (Adatrögzítés) | empty; **data** |
| Bérlisták | payslip list per month | Kifiz. napja, Név, Led. nap, Bruttó bér, Összes lev., Utalandó bér, Kifizetendő, E-mail cím | R (January rows, values exposed) | W– (export, print, e-mail) | populated |
| Béren kívüli juttatások listája | fringe benefits per month | Név, Jogcím, Összeg, Törzsszám, Munkaszám | R | — | empty; **data** |
| Alkalmazotti törzs, Jogcím törzs, Jogviszony törzs, Munkaszám törzs, Nyugdíjpénztár törzs | master data | Kód, Megnevezés (51 jogcímek, 9 jogviszonyok, 22 nyugdíjpénztárak) | R | W | populated, except Munkaszám |
| Cégautó törzs | company cars | Rendszám, Megnevezés (2 sample cars) | R | W | populated |
| Cégautó járulékok havi lista | company-car tax per month | Rendszám, Megnevezés, Cégautóadó, Gépjármű adó, Fizetendő | R | — | empty; **data** |
| Cégautó járulékok számfejtése, XX01 export | computation, export | — | — | W– | not opened |
| Bér adatszolgáltatás (xx08) | the monthly 08 return | Név, Adóazonosító; Adatok rögzítése, ABEV export, Beküldött bevallások | R | W– | submission is **real** |
| Bérösszesítő (adott időszakra) | payroll summary for a period | Név, Törzsszám, Jogviszony, Adószám, Megnevezés, An. kód, Bankszámlaszám, Összeg (132 rows) | R (values exposed) | W– (export) | populated |
| Bérösszesítő (havi bontásban) | the same by month | Megnevezés, An. kód, Bankszámlaszám, Január…December; Utalási lista, Feltöltés cashbook-ba | R | W– | populated |
| Bérfeladás | posting the payroll to the ledger | — | — | W– | not opened: it writes into Kettős |
| Szerviz: Beállítások, Bérszámfejtés beállításai, Mentés | settings; the program's own backup (Mintakönyvelés 2026) | | R | W– | Mentés is the backup step |
| Munkaidő Import | import from a time-keeping program | — | — | — | the button is in the tree but hidden and does nothing here; **real** |

## Számlázás és készletnyilvántartás

All the lists show the same top bar: Partner információk, Cikk információk, Forgalmi információk, Eladási információk.

| screen | purpose | shows | read | write | notes |
|---|---|---|---|---|---|
| Számlák kezelése | invoices | Ny, Jel, Sorszám, Számla, Vevő, Kelte, Teljesítés, Fiz.hat.idő, Fiz.mód, Nettó, ÁFA, Bruttó | **R✔** (`rlbszla szamlak`) | **W✔** (`rlbszla szamla`) | 1 invoice (2026/00001); **demo**: issuer locked |
| Szállítólevelek kezelése | delivery notes | Sorszám, Fogadó, Kelte, Nettó, ÁFA, Bruttó, devizás oszlopok | R | W (Új szállítólevél) | empty; **data** |
| Árajánlatok kezelése | quotes | Sorszám, Ajánlatkérő, Kelte, Érvényes, Nettó, ÁFA, Bruttó | R | W (Új árajánlat) | empty; **data** |
| Bolti eladások kezelése | shop sales (receipts) | Sorszám, Kelte, Nettó, Áfa, Bruttó, Számlasorszám, Vevőnév, Eredeti nyugta | R | W (Új nyugta) | empty; **data** |
| Megrendelések kezelése | orders | Sorszám, Megrendelő, Kelte, Határidő, Állapot, Nettó, ÁFA, Bruttó | R | W (Új megrendelés) | empty; **data** |
| Bevételezések kezelése | goods received | Sorszám, Hivatkozás, Szállító, Kelte, Nettó, ÁFA, Bruttó | R | W (Új bevételezés) | empty; **data** |
| Partnertörzs kezelése / lista | customers and suppliers | Név, Város, Kapcsolattartó; tabs Alapadatok, Elérhetőségek, Egyéb adatok, Fizetés; the list adds Árkategória, Deviza, Cím, Tel.szám | R (1) | W | **demo**: no new partners |
| Cikktörzs kezelése / lista | items | Cikkszám, Rend.szám, Vonalkód, Megnevezés; list adds Besorolás, Menny., Minimális, Lefoglalt, Beszerzés; tabs Alapadatok, Egyéb adatok, Egyéb ár adatok, Webáruház | R (1) | W | **demo**: no new items |
| Gyáriszám törzs / lista | serial numbers | Cikkszám, Megnevezés, Gyáriszám, Eladva, Vevő, Bizonylat | R | W | empty; **data** |
| Mozgások listája | stock movements | Dátum, Bizonylat, Partner, Cikkszám, Változás, Egyenleg, Egységár | R | — | empty: our invoice has no stock item; **data** |
| Kiegyenlítések listája | settlements | Sorszám, Vevő, Fiz.hat.idő, Bruttó, Kiegy. dátum, Kiegy. bruttó, Egyenleg | R (1 row, values exposed) | W (Kiegyenlítés on the invoice) | populated |
| Rendezetlen tételek | unsettled items | Típus, Sorszám, Dátum, Vevő, Cikkszám, Menny., Egységár, Nettó | R | — | empty; **data** |
| Partner információk (top bar) | partner turnover | — | — | — | **crashed the program** (szla2.exe APPCRASH in MSVCR71.dll, Windows event 1001) on its first click from the main window; restarted, no data lost; the other three info buttons were not tried |

Menu-only items, catalogued from a frame and not opened: Új egyszerűsített számla, Számlák sablonból, Bankszámlatörténet,
Utánvét lista, Kiszámlázott tételek, ÁFA lista, Garanciális tételek, Súlyadatok, Termékdíj adatok, Előlegek listája;
Árajánlat tételek listája, Eladott bolti tételek; Web (Cikktörzs / Készlet feltöltése, Megrendelések letöltése);
Alapadatok (Recepttörzs, Termékdíj törzs, Saját adatok, Láblécek, Sablonok, Jogcímek, Évzárás, Leltár, Adatok
könyvelésre, Adatok ÁNYK programba, Online Számla adatszolgáltatás, Archiválás…). Online Számla (NAV) is **real**.

## Not on the test machine

Only the three programs are installed: there is no Pénztárkönyv/CashBook program and no Naplófőkönyv. The Cashbook menu
in Kettős and Bér is greyed out.

## Limits of this survey

- **Menus.** A FoxPro drop-down menu is its own pop-up window. The driver's click on a menu item lands on the main
  window instead, because the focus step closes the menu first, and the keyboard (Alt, F10, Ctrl+F2) does not reach
  the menu. So menu-only screens, and switching to the Kettős sample client, are not reachable yet. That needs a
  click with no focus step, which is a desktape engine change.
- **Esc does not close a form.** The survey closes every form with its own exit button.
- **Empty lists** are mapped by their headers. Whether their cell values are exposed is shown only for populated lists;
  the same grid control is used everywhere, so it is likely, not proven.
- **Grids show the visible rows only.** A long list (kivonat, Bérösszesítő) is read by scrolling, as `rlbkit kivonat`
  does.

## Proven and readable screens, at a glance

Vegyes napló, Főkönyvi kivonat, Béradatok, and Számlák kezelése are driver-proven with read-back. Összes napló,
ÁFA-analitika, Gyorsmérleg, Bérlisták, Bérösszesítő and Kiegyenlítések listája are populated and their values were
seen in the dump; they can be shown as „Claude reads this screen”, but not yet as a driver command.

## Next steps, by value

1. Read commands for ÁFA-analitika (ÁFA lista tab), Gyorsmérleg, Összes napló and Bérösszesítő: same grid read as
   `kivonat`.
2. Pénztár and Bank forms as write recipes (they fit the demo's no-new-partner limit).
3. A menu click without the focus step in desktape, then the menu-only screens and the Kettős sample client.
4. On a client's real install: partners, Pénzügyi nyilvántartás populated, ÁNYK and Online Számla, Munkaidő Import.
