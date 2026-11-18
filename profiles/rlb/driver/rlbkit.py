#!/usr/bin/env python3
"""rlbkit: RLB Kettős könyvvitel (demo) through its own windows, for the rlb-konyveles skill.

Part of the AI+ pilóta RLB profile (profiles/rlb/driver). Runs on the Windows machine itself (DESKTAPE_HOST=local)
or from a controller (DESKTAPE_HOST=<a desktape target>). DESKTAPE_DIR names the folder of desktape.py.
Every input goes through desktape: a real click at a screen point (os_input's exact click mode), keys through
Windows' own SendKeys (os_input), buttons by their UI Automation name. Every write is read back from the
program's own list. It never reads the program's data files.

  python rlbkit.py naplo
  python rlbkit.py szallitoi-szamla --datum 20261112 --bizszam PI-1 --megj "Szállító Kft. szla" --netto 29440 [--koltseg 511]
  python rlbkit.py vevoi-szamla     --datum 20261005 --bizszam VSZ-1 --megj "Vevő Bt. vevő" --netto 100000 [--arbevetel 911]
  python rlbkit.py ket-szamla       --datum 20261003 --bizszam BK-1 --megj "Bank: ..." --osszeg 254000 --tartozik 384 --kovetel 311
  python rlbkit.py torles --sorszam V/000009
Output: one JSON object (Hungarian keys) on stdout; "ok": false with "hiba" when something went wrong.

Measured traps (desktape knowledge/windows.md, FoxPro): never Backspace past a field's start (it jumps to the
previous field and erases it): clear with {HOME}{DEL n}; send a click alone, wait, then its keys; input shows up
about two seconds late.
"""
import argparse
import json
import logging
import os
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DT_DIR = os.environ.get("DESKTAPE_DIR") or next(
    (d for d in (HERE, os.path.join(os.path.expanduser("~"), "desktape-app")) if os.path.exists(os.path.join(d, "desktape.py"))),
    HERE)
if not os.path.exists(os.path.join(DT_DIR, "desktape.py")):
    sys.exit("rlbkit: desktape.py not found; set DESKTAPE_DIR to the folder that holds it")
sys.path.insert(0, DT_DIR)
import desktape  # noqa: E402

logger = logging.getLogger("desktape")
HOST = os.environ.get("DESKTAPE_HOST") or ("local" if os.name == "nt" else None)
if not HOST:
    sys.exit("rlbkit: set DESKTAPE_HOST (local on the Windows machine, or a desktape target from a controller)")
WIN = "Kettős könyvvitel (hálózatos) 26.6.0 [DEMO VERZIÓ]"
STATE = os.environ.get("RLB_STATE") or os.path.join(HERE, "state")
os.makedirs(STATE, exist_ok=True)
AUDIT = open(os.path.join(STATE, "os-input-audit.jsonl"), "a", encoding="utf-8")
CUA = desktape.Cua(HOST, os.path.join(STATE, "driver-audit.jsonl"))
TAPES = os.path.join(HERE, "recipes")

# Quick-menu points, as screen pixels with the window MAXIMISED (1920x1080); shifted to the window's real place.
TABS = {"Könyvelés": (960, 288), "Lekérdezés": (1150, 288)}
ITEMS = {"Vegyes": (1102, 386), "Vegyes napló": (910, 386), "Összes napló": (1204, 386),
         "Főkönyvi kivonat": (718, 456), "Főkönyvi kartonok": (816, 456), "Áfa-analitika": (1124, 456)}


class RlbError(Exception):
    pass


def window():
    w = next((x for x in CUA.call("list_windows", {})[0].get("windows", []) if x.get("title") == WIN), None)
    if not w:
        raise RlbError("a Kettős könyvvitel ablaka nincs nyitva")
    return w


def front():
    """Bring the program to the front (the chat window is in front while a command runs); return (hwnd, shift)."""
    w = window()
    r = CUA.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})[0]
    if not r.get("landed_on_target"):
        raise RlbError(f"nem sikerült előtérbe hozni a programot: {r}")
    b = w.get("bounds") or {}
    maxed = b.get("x") == 0 and b.get("width") == 1920
    # forms are centred in the window; the code pickers sit at its left edge (both measured)
    return w["window_id"], {"centre": (0, 0), "left": (0, 0)} if maxed else \
        {"centre": (round(b["x"] + b["width"] / 2 - 960), 4), "left": (b["x"] + 1, 4)}


def click_xy(hwnd, shift, x, y, anchor="centre"):
    x, y = x + shift[anchor][0], y + shift[anchor][1]
    out = desktape.os_input(HOST, WIN, "", AUDIT, hwnd=hwnd, xy=[x, y])
    if not (out or {}).get("sent"):
        raise RlbError(f"a kattintás ({x},{y}) nem a program ablakára esett: {out}")
    time.sleep(0.4)


def keys(k):
    desktape.os_input(HOST, WIN, k, AUDIT)


def elements():
    w = window()
    return w, CUA.call("get_window_state", {"pid": w["pid"], "window_id": w["window_id"], "timeout_ms": 10000})[0].get("elements") or []


def name(e):
    return e.get("label") or e.get("name") or ""


def ui_click(label, role="Button"):
    for attempt in range(4):           # a list window answers UI Automation a moment after it is drawn
        w, els = elements()
        e = next((e for e in els if name(e) == label and e.get("role") == role), None)
        if e:
            break
        time.sleep(1.5)
    else:
        raise RlbError(f"nincs ilyen gomb a képernyőn: {label}")
    CUA.call("click", {"pid": w["pid"], "window_id": w["window_id"], "element_token": e["element_token"]})


def popups():
    """Message boxes of the program that are open now: [(title, text)]."""
    ws = CUA.call("list_windows", {})[0].get("windows", [])
    main = next((x for x in ws if x.get("title") == WIN), None)
    out = []
    for x in ws:
        if main and x.get("pid") == main["pid"] and x.get("title") and x.get("title") != WIN:
            st = CUA.call("get_window_state", {"pid": x["pid"], "window_id": x["window_id"]})[0]
            text = " / ".join(dict.fromkeys(name(e) for e in st.get("elements") or [] if e.get("role") == "Text" and name(e)))
            out.append((x["title"], text))
    return out


def play(tape, values):
    """Play a tape's steps one by one (no runner reads in between: measured, they made a click lose the focus)."""
    t = yaml.safe_load(open(os.path.join(TAPES, tape), encoding="utf-8"))
    vals = {k: str(v["default"]) for k, v in (t.get("vars") or {}).items() if isinstance(v, dict) and "default" in v}
    vals.update({k: str(v) for k, v in values.items() if v is not None})
    hwnd, shift = front()
    for i, step in enumerate(t["steps"]):
        txt = json.dumps(step, ensure_ascii=False)
        for k, v in vals.items():
            txt = txt.replace("${" + k + "}", json.dumps(v, ensure_ascii=False)[1:-1])
        kind, arg = next(iter(json.loads(txt).items()))
        logger.info("%s step %d: %s", tape, i, txt[:120])
        if kind == "pause":
            time.sleep(float(arg))
        elif kind == "key":
            if arg.get("at"):
                click_xy(hwnd, shift, round(-8 + 1936 * arg["at"][0]), arg["at"][1] - 8, arg.get("anchor", "centre"))
                if arg["key"]:
                    time.sleep(1.5)   # measured 2026-11-17: 1 s lost the field's clearing keys on a just-started program
            if arg["key"]:
                keys(arg["key"])
        elif kind == "type":
            keys("".join("{" + c + "}" if c in "+^%~(){}[]" else c for c in arg["text"]))
        elif kind == "click":
            ui_click(arg["label"], arg.get("role", "Button"))
        if kind in ("click", "key", "type"):
            p = popups()
            if p:
                raise RlbError(f"a program üzenete a(z) {i}. lépés után: " + "; ".join(f"{a}: {b}" for a, b in p))


def naplo():
    hwnd, shift = front()
    click_xy(hwnd, shift, *TABS["Lekérdezés"])
    time.sleep(1.2)
    click_xy(hwnd, shift, *ITEMS["Vegyes napló"])
    time.sleep(3)
    for attempt in range(4):
        _, els = elements()
        cells = [e.get("value") for e in els if e.get("role") == "Edit" and name(e) == "Text1"]
        if any(v and v.startswith("V/") for v in cells) or attempt == 3:
            break
        time.sleep(1.5)
    rows, cur = [], None
    for v in cells:
        if v and v.startswith("V/"):
            cur = [v]
            rows.append(cur)
        elif cur is not None and v is not None:
            cur.append(v)
    keys_ = ("sorszam", "datum", "bizonylatszam", "partnerkod", "megjegyzes", "osszeg")
    out = [dict(zip(keys_, r)) for r in rows if len(r) >= 6]
    ui_click("Kilépés")
    time.sleep(1)
    return out


# Account names as the program shows them (read from its Főkönyvi kivonat and Főkönyvi törzs on 2026-11-17): used
# to fill in an account number the OCR missed, by the row's (OCR-read) name.
NAMES = {
    "3": "KÖVETELÉSEK, PÉNZÜGYI ESZKÖZÖK ÉS AKTÍV IDŐBELI ELHATÁROLÁSOK", "31": "KÖVETELÉSEK ÁRUSZÁLLÍTÁSBÓL ÉS SZOLGÁLTATÁSBÓL",
    "311": "Belföldi vevő követelések forintban", "38": "PÉNZESZKÖZÖK", "384": "Bankszámlák",
    "3841": "Elszámolási betétszámla", "4": "FORRÁSOK", "45": "RÖVID LEJÁRATÚ KÖTELEZETTSÉGEK", "454": "Szállítók",
    "4541": "Belföldi anyag és áruszállítók", "466": "Előzetesen felszámított ÁFA", "467": "Fizetendő általános forgalmi adó",
    "5": "KÖLTSÉGNEMEK", "51": "ANYAGKÖLTSÉGEK", "511": "Vásárolt anyagok költségei",
    "512": "Egy éven belül elhasználódó eszközök költségei", "513": "Egyéb anyagköltségek",
    "52": "IGÉNYBE VETT SZOLGÁLTATÁSOK KÖLTSÉGEI", "529": "Egyéb igénybe vett szolgáltatások költségei",
    "53": "EGYÉB SZOLGÁLTATÁSOK KÖLTSÉGEI", "532": "Pénzügyi, befektetési szolgáltatási díjak",
    "9": "ÉRTÉKESÍTÉS ÁRBEVÉTELE ÉS BEVÉTELEK", "91": "BELFÖLDI ÉRTÉKESÍTÉS ÁRBEVÉTELE", "911": "Alaptevékenység árbevétele",
    "97": "PÉNZÜGYI MŰVELETEK BEVÉTELEI", "974": "Egyéb kapott kamatok és kamatjellegű bevételek",
    "9741": "Forgóeszközök között kimutatott kölcsön, váltókövetelés, pénzeszköz után kapott kamat",
}


def plain(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t.upper()) if not unicodedata.combining(c))


def by_name(text):
    import difflib
    best, score = "", 0.0
    for acc, nm in NAMES.items():
        r = difflib.SequenceMatcher(None, plain(text), plain(nm)[:len(text) + 4]).ratio()
        if r > score:
            best, score = acc, r
    return best if score >= 0.75 else ""


def ocr_rows():
    """The screen's text lines from Windows' own OCR: [(x, y, text)]."""
    out = []
    for line in desktape.ocr_lines(HOST):
        xy, _, text = line.partition(" ")
        try:
            x, y = (int(v) for v in xy.split(","))
        except ValueError:
            logger.warning("OCR line without a position: %r", line)
            continue
        out.append((x, y, text))
    return out


def kivonat():
    """Főkönyvi kivonat: the numbers by UI Automation value (row by row, in column order), the account numbers
    and names by OCR of the same screen rows (the program does not expose those two columns)."""
    hwnd, shift = front()
    click_xy(hwnd, shift, *TABS["Lekérdezés"])
    time.sleep(1.2)
    click_xy(hwnd, shift, *ITEMS["Főkönyvi kivonat"])
    time.sleep(5)
    _, els = elements()
    head = next((e["frame"] for e in els if e.get("role") == "Header" and name(e) == "Tartozik nyitó" and e.get("frame")), None)
    if not head:
        raise RlbError("a főkönyvi kivonat nem nyílt meg")
    def grid(els):
        rows = {}
        for e in els:
            f = e.get("frame")
            if e.get("role") == "Edit" and name(e) == "Text1" and f and f["h"] > 0 and head["y"] < f["y"] < head["y"] + 560:
                rows.setdefault(f["y"], []).append(e.get("value") or "0")
        return rows
    rows = grid(els)
    # the grid's current row (the first one on open) does not expose its values: read again with the second row
    # current, and take the first row from that read (measured: the first row came back as zeros)
    ys = sorted(rows)
    if len(ys) > 1:
        click_xy(hwnd, {"centre": (0, 0)}, head["x"] + 330, ys[1] + 8)
        time.sleep(2)
        again = grid(elements()[1])
        if ys[0] in again:
            rows[ys[0]] = again[ys[0]]
    left = head["x"]
    text = [(x, y, t) for x, y, t in ocr_rows() if left - 15 <= x < left + 270]   # measured: the two columns draw where UIA puts the first numbers
    out = []
    for y, v in sorted(rows.items()):
        line = sorted((x, t) for x, ty, t in text if abs(ty - (y + 4)) <= 8)
        acc = next((t for x, t in line if t.replace(" ", "").isdigit()), "")
        nm = " ".join(t for x, t in line if not t.replace(" ", "").isdigit())
        num = [int(n) if n.lstrip("-").isdigit() else 0 for n in v[:6]]
        acc = acc.replace(" ", "")
        src = "ocr" if acc else ""
        if not acc and nm:
            acc = by_name(nm)
            src = "név alapján" if acc else ""
        out.append({"fokonyvi_szam": acc, "szam_forrasa": src, "megnevezes": nm, "tartozik_forgalom": num[2],
                    "kovetel_forgalom": num[3], "tartozik_egyenleg": num[4], "kovetel_egyenleg": num[5]})
    ui_click("Kilépés")
    time.sleep(1)
    return out


def readback(bizszam, gross):
    rows = naplo()
    hit = [r for r in rows if r["bizonylatszam"] == bizszam]
    ok = len(hit) == 1 and int(hit[0]["osszeg"]) == int(gross)
    return {"ok": ok, "visszaolvasva": hit, "vart_osszeg": int(gross),
            **({} if ok else {"hiba": "a visszaolvasott tétel nem egyezik a könyvelni kívánttal"})}


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError) as e:
            logger.warning("stream encoding unchanged: %s", e)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("op")
    for a in ("--datum", "--bizszam", "--megj", "--netto", "--osszeg", "--tartozik", "--kovetel", "--sorszam",
              "--koltseg", "--arbevetel"):
        p.add_argument(a)
    a = p.parse_args()
    try:
        if a.op == "naplo":
            res = {"ok": True, "tetelek": naplo()}
        elif a.op == "kivonat":
            res = {"ok": True, "megjegyzes": "a főkönyvi számot és a megnevezést OCR olvassa a képernyőről; "
                   "az összegek a program mezőiből jönnek", "sorok": kivonat()}
        elif a.op == "szallitoi-szamla":
            play("vegyes-afas-szamla.yaml", {"datum": a.datum, "bizszam": a.bizszam, "megj": a.megj,
                                             "netto": a.netto, "koltseg": a.koltseg})
            res = readback(a.bizszam, int(a.netto) + round(int(a.netto) * 0.27))
        elif a.op == "vevoi-szamla":
            play("vegyes-vevo-szamla.yaml", {"datum": a.datum, "bizszam": a.bizszam, "megj": a.megj,
                                             "netto": a.netto, "arbevetel": a.arbevetel})
            res = readback(a.bizszam, int(a.netto) + round(int(a.netto) * 0.27))
        elif a.op == "ket-szamla":
            play("vegyes-ket-szamla.yaml", {"datum": a.datum, "bizszam": a.bizszam, "megj": a.megj,
                                            "osszeg": a.osszeg, "tartozik": a.tartozik, "kovetel": a.kovetel})
            res = readback(a.bizszam, int(a.osszeg))
        else:
            raise RlbError(f"ismeretlen művelet: {a.op}")
    except RlbError as e:
        logger.error("%s", e)
        res = {"ok": False, "hiba": str(e), "nyitott_uzenetek": popups()}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
