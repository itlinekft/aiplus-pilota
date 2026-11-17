<p align="center"><b>AI+ pilóta</b> · ITLine AI+ · ingyenes · MIT · <a href="https://www.itline.hu/ai-plus/">itline.hu/ai-plus</a></p>

# AI+ pilóta

## Magyarul

**AI a meglévő asztali programodhoz.** Az AI+ pilóta profilokat ad, amelyekkel a Claude a saját képernyőin át kezeli
a már használt asztali programodat: megnyitja az ablakait, a mezőkbe ír, és a végén érték szerint visszaolvassa, amit
rögzített. A vezérlést a [desktape](https://github.com/itlinekft/aiplus-desktape) végzi.

Egy profil azt írja le, saját szavainkkal, hogy egy adott programban hova kell kattintani és mit kell csinálni,
kizárólag abból, amit a program ablakai mutatnak. Gyártósemleges, így minden program külön profil. Nem nyúlunk a
program adatbázisához, és nem fejtjük vissza. Úgy használjuk, ahogy te is.

Készítette az ITLine. A profilok a saját, jogtiszta programodat vezérlik a te gépeden.

## In English

**AI for the desktop program you already use.** AI+ pilóta ships profiles that let Claude operate your existing
desktop program through its own windows: it opens the windows, types into the fields, and reads back by value what it
recorded. [desktape](https://github.com/itlinekft/aiplus-desktape) does the driving.

A profile describes, in our own words, where to click and what to do in a given program, using only what the
program's windows show. It is vendor neutral, so each program is its own profile. We do not touch the program's
database and we do not reverse engineer it. We use it the way you do.

Made by ITLine. The profiles drive your own licensed program on your own machine.

## Profiles

Each profile lives under `profiles/<name>/`. Writing one follows [docs/profiles/README.md](docs/profiles/README.md).
How the kit loads a profile and hands its tapes to desktape: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```bash
python3 kit/load_profile.py check                 # every profile against its schema and rules
python3 -m unittest discover -s tests             # offline tests
scripts/install-hooks.sh                          # the pre-commit real-data and profile checks
```

## License

MIT. See [LICENSE](LICENSE).
