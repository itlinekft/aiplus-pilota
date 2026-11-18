#!/usr/bin/env python3
"""rlbszla: RLB Számlázás és készletnyilvántartás 2 (demo) through its own windows, for the rlb-konyveles skill.

Part of the AI+ pilóta RLB profile (profiles/rlb/driver).
Same rules as rlbkit.py: real clicks at points taken from the program's own UI Automation frames (so the window may
sit anywhere), keys through Windows' SendKeys, every write read back from the program's own list, no data files.

  python rlbszla.py szamlak
  python rlbszla.py szamla --vevo "Gamma Teszt" --tetel "Tanácsadás" --menny 3 [--fizmod atutalas]
Output: one JSON object (Hungarian keys) on stdout; "ok": false with "hiba" when something went wrong.

Measured on the demo (2026-11-18): the partner and item pickers open with their search box focused; the item line
form opens with the quantity selected; saving shows a print preview (Esc closes it), then asks „Biztos benne?”
(Mentés) and whether to print (Nyomtatás). The demo does not send anything to the tax office (its Online Számla
setup is disabled in the demo).
"""
import argparse
import json
import logging
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlbkit  # noqa: E402  (desktape import, host, audit files)
desktape = rlbkit.desktape

logger = logging.getLogger("desktape")


def osin(*a, wait=None, **k):
    """desktape.os_input; an older desktape copy (the Windows box's) has no `wait`: sleep after the call instead."""
    try:
        return desktape.os_input(*a, wait=wait, **k)
    except TypeError as e:
        if "wait" not in str(e):
            raise
        out = desktape.os_input(*a, **k)
        time.sleep(wait or 0)
        return out
HOST, AUDIT, CUA = rlbkit.HOST, rlbkit.AUDIT, rlbkit.CUA
WIN = "Számlázás és készletnyilvántartás 2 (hálózatos) 9.91"
ICON_SZAMLAK = (-130, 470)   # „Számlák kezelése” on the quick menu: pixels from the window's centre / top (measured)
FIZMOD = {"keszpenz": 0, "atutalas": 1, "utanvet": 2, "csekk": 3, "bankkartya": 4}
COLS = {"Sorszám": "sorszam", "Számla": "tipus", "Vevő": "vevo", "Kelte": "kelte", "Teljesítés": "teljesites",
        "Fiz.hat.idő": "hatarido", "Fiz.mód": "fizmod", "Nettó": "netto", "ÁFA": "afa", "Bruttó": "brutto"}


class SzlaError(rlbkit.RlbError):
    pass


def window():
    w = next((x for x in CUA.call("list_windows", {})[0].get("windows", []) if x.get("title") == WIN), None)
    if not w:
        raise SzlaError("a Számlázás program ablaka nincs nyitva")
    return w


def front():
    w = window()
    r = CUA.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})[0]
    if not r.get("landed_on_target"):
        raise SzlaError(f"nem sikerült előtérbe hozni a Számlázást: {r}")
    return w


def elements(w=None):
    w = w or window()
    st = CUA.call("get_window_state", {"pid": w["pid"], "window_id": w["window_id"], "timeout_ms": 15000})[0]
    return w, st.get("elements") or []


def find(label, role=None, tries=5):
    for _ in range(tries):
        w, els = elements()
        hit = [e for e in els if e.get("label") == label and (role is None or e.get("role") == role) and e.get("enabled", True)]
        if hit:
            return w, hit[0]
        time.sleep(1.2)
    raise SzlaError(f"nincs ilyen elem a képernyőn: {label}")


def click_at(w, x, y, keys="", title=WIN, dropdown=False):
    out = osin(HOST, title, keys, AUDIT, hwnd=w["window_id"], xy=[int(x), int(y)], wait=1.0)
    if dropdown and not (out or {}).get("sent") and (out or {}).get("hit"):
        # an open combo list is its own top-level window; the point was computed from the combo's own frame
        out = osin(HOST, "", keys, AUDIT, hwnd=int(out["hit"]), xy=[int(x), int(y)], wait=0.5)
    if not (out or {}).get("sent"):
        raise SzlaError(f"a kattintás ({x},{y}) nem a Számlázás ablakára esett: {out}")
    time.sleep(0.6)


def click(label, role="Button", keys=""):
    w, e = find(label, role)
    f = e["frame"]
    logger.info("click %s %r at %s", role, label, f)
    click_at(w, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2, keys)


def keys(k):
    osin(HOST, WIN, k, AUDIT)
    time.sleep(0.8)


def popups():
    ws = CUA.call("list_windows", {})[0].get("windows", [])
    main = next((x for x in ws if x.get("title") == WIN), None)
    return [x for x in ws if main and x.get("pid") == main["pid"] and x.get("title") and x["title"] != WIN
            and (x.get("bounds") or {}).get("width")]


def answer(title, button, timeout=15, optional=False):
    """Press a button of the program's own message box titled `title` (Mentés, Nyomtatás, ...); return its text."""
    end = time.time() + timeout
    while time.time() < end:
        box = next((p for p in popups() if p["title"] == title), None)
        if box:
            st = CUA.call("get_window_state", {"pid": box["pid"], "window_id": box["window_id"]})[0]
            text = " ".join(dict.fromkeys(e.get("label") or e.get("value") or "" for e in st.get("elements") or []
                                          if e.get("role") in ("Text", "Edit") and (e.get("label") or e.get("value"))))
            b = next((e for e in st.get("elements") or [] if e.get("label") == button and e.get("role") == "Button"), None)
            if not b:
                raise SzlaError(f"a(z) {title} ablakban nincs {button} gomb")
            f = b["frame"]
            out = osin(HOST, title, "", AUDIT, hwnd=box["window_id"],
                                    xy=[int(f["x"] + f["w"] / 2), int(f["y"] + f["h"] / 2)], wait=0.5)
            if not (out or {}).get("sent"):
                raise SzlaError(f"a(z) {title} ablak {button} gombja nem kattintható: {out}")
            time.sleep(1.0)
            logger.info("message box %r: %s -> %s", title, text, button)
            return text or True
        time.sleep(0.8)
    if optional:
        return None
    raise SzlaError(f"nem jött meg a(z) {title} kérdés")


def open_list():
    """The „Számlák kezelése” list, opened from the quick menu when it is not open yet."""
    w = front()
    _, els = elements(w)
    if not any(e.get("label") in ("SI_GRID_SQL1", "Új számla") for e in els):   # an empty list has no grid in UIA
        b = w["bounds"]
        click_at(w, b["x"] + b["width"] / 2 + ICON_SZAMLAK[0], b["y"] + ICON_SZAMLAK[1])
        find("Új számla", "Button", tries=8)
    return w


def szamlak():
    open_list()
    _, els = elements()
    heads = {e["frame"]["x"]: COLS[e["label"]] for e in els if e.get("role") == "Header" and e.get("label") in COLS and e.get("frame")}
    grid_y = min((e["frame"]["y"] for e in els if e.get("role") == "Header" and e.get("label") in COLS and e.get("frame")), default=0)
    rows = {}
    for e in els:
        f = e.get("frame") or {}
        col = next((c for x, c in heads.items() if abs(x - f.get("x", -99)) <= 3), None)
        if e.get("role") == "Edit" and e.get("label") == "Text1" and f.get("y", 0) > grid_y and col:
            rows.setdefault(f["y"], {})[col] = e.get("value") or ""
    out = [r for _, r in sorted(rows.items()) if r.get("sorszam")]
    for r in out:
        for k in ("netto", "afa", "brutto"):    # a narrow window hides these columns: then they are not in the list
            r[k] = int(float(r[k])) if r.get(k) else None
        r["_y"] = next(y for y, row in rows.items() if row is r)
    return out


FIZMOD_NEV = {i + 1: k for k, i in FIZMOD.items()}   # the combo's value is 1-based (measured: készpénz = 1)
TETEL = {"Tétel": "tetel", "Menny.": "menny", "Menny.e.": "egyseg", "Egységár": "egysegar", "Nettó": "netto",
         "Bruttó": "brutto"}


def olvas(row):
    """Read one saved invoice back from the program: open it from the list (Módosítás), read it, leave unchanged."""
    w = open_list()
    click_at(w, w["bounds"]["x"] + 340, row["_y"] + 8)       # the Sorszám/Számla cells of that row
    time.sleep(0.8)
    click("Módosítás")
    find("Kilépés", "Button", tries=8)
    time.sleep(1.5)
    _, els = elements()
    heads = {e["frame"]["x"]: TETEL[e["label"]] for e in els
             if e.get("role") == "Header" and e.get("label") in TETEL and e.get("frame")}
    top = min(heads and [e["frame"]["y"] for e in els if e.get("role") == "Header" and e.get("label") == "Tétel"] or [0])
    lines = {}
    for e in els:
        f = e.get("frame") or {}
        col = next((c for x, c in heads.items() if abs(x - f.get("x", -99)) <= 3), None)
        if col and e.get("role") == "Edit" and f.get("y", 0) > top + 5:
            lines.setdefault(f["y"], {})[col] = e.get("value") or ""
    tetelek = [l for _, l in sorted(lines.items()) if l.get("tetel")]
    for l in tetelek:
        for k in ("netto", "brutto", "egysegar"):
            l[k] = int(float((l.get(k) or "0").replace(" ", "").replace(",", ".")))
    dates = sorted((e["frame"]["y"], e.get("value")) for e in els if e.get("label") == "Sajtextbox1" and e.get("frame"))
    fiz = next((e.get("value") for e in els if e.get("label") == "Sajcombobox2"), None)
    out = {"sorszam": row["sorszam"],
           "vevo": next((e.get("value") for e in els if e.get("label") == "partadat"), ""),
           "kelte": dates[0][1] if dates else "", "teljesites": dates[1][1] if len(dates) > 1 else "",
           "hatarido": dates[2][1] if len(dates) > 2 else "",
           "fizmod": FIZMOD_NEV.get(int(fiz), fiz) if (fiz or "").isdigit() else fiz,
           "tetelek": tetelek, "netto": sum(l["netto"] for l in tetelek), "brutto": sum(l["brutto"] for l in tetelek)}
    out["afa"] = out["brutto"] - out["netto"]
    click("Kilépés")
    answer("Kilépés", "Igen", timeout=6, optional=True)       # „Biztos benne?”: leave without saving
    time.sleep(1.0)
    return out


def szamla(vevo, tetel, menny, fizmod):
    before = {r["sorszam"] for r in szamlak()}
    click("Új számla")
    find("Kiválaszt", "Button", tries=8)          # the partner picker, search box focused
    keys(vevo)
    time.sleep(1.0)
    click("Kiválaszt")
    figyelem = answer("Figyelem", "OK", timeout=5, optional=True)   # the customer's unpaid invoices, if any
    w, _ = find("Új tétel", "Button", tries=8)
    if fizmod != "keszpenz":
        _, combo = find("Sajcombobox2", "ComboBox")
        f = combo["frame"]
        click_at(w, f["x"] + f["w"] - 8, f["y"] + f["h"] / 2)       # opens the list: one item per 17 px (measured)
        time.sleep(0.8)
        click_at(w, f["x"] + 40, f["y"] + f["h"] + 10 + 17 * FIZMOD[fizmod], dropdown=True)
    click("Új tétel")
    find("Kiválaszt módosítással", "Button", tries=8)   # the item picker, search box focused
    keys(tetel)
    time.sleep(1.0)
    click("Kiválaszt módosítással")
    time.sleep(1.5)                                     # the line form, quantity selected
    keys(f"{menny}{{TAB}}")
    click("Kiválaszt")
    time.sleep(1.0)
    click("Mentés")
    time.sleep(3.0)                                     # the print preview
    keys("{ESC}")
    answer("Mentés", "Igen")
    answer("Nyomtatás", "Nem")
    click("Kilépés")
    time.sleep(1.5)
    rows = szamlak()
    new = [r for r in rows if r["sorszam"] not in before]
    ok = len(new) == 1 and new[0]["vevo"].startswith(vevo)
    if ok:
        new = [olvas(new[0])]
        ok = new[0]["vevo"].startswith(vevo) and len(new[0]["tetelek"]) == 1
    return {"ok": ok, "uj_szamla": new[0] if new else None, "szamlak_szama": len(rows), "visszaolvasva": ok,
            **({"program_figyelmeztetese": figyelem if isinstance(figyelem, str) else
                "a vevő kiválasztásakor a program figyelmeztetett (Figyelem ablak, OK-val lezárva)"} if figyelem else {}),
            **({} if ok else {"hiba": "a visszaolvasott számlalista nem a várt egy új számlát mutatja"})}


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError) as e:
            logger.warning("stream encoding unchanged: %s", e)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("op")
    p.add_argument("--vevo")
    p.add_argument("--tetel")
    p.add_argument("--menny", type=float)
    p.add_argument("--fizmod", default="atutalas", choices=sorted(FIZMOD))
    a = p.parse_args()
    try:
        if a.op == "szamlak":
            res = {"ok": True, "szamlak": [{k: v for k, v in r.items() if k != "_y"} for r in szamlak()]}
        elif a.op == "szamla":
            if not (a.vevo and a.tetel and a.menny):
                raise SzlaError("a számlához kell --vevo, --tetel és --menny")
            menny = int(a.menny) if a.menny == int(a.menny) else str(a.menny).replace(".", ",")
            res = szamla(a.vevo, a.tetel, menny, a.fizmod)
        else:
            raise SzlaError(f"ismeretlen művelet: {a.op}")
    except rlbkit.RlbError as e:
        logger.error("%s", e)
        res = {"ok": False, "hiba": str(e), "nyitott_ablakok": [p["title"] for p in popups()]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
