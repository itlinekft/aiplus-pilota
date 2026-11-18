#!/usr/bin/env python3
"""rlbber: RLB Bérszámfejtés (demo) through its own windows, for the rlb-konyveles skill.

Part of the AI+ pilóta RLB profile (profiles/rlb/driver).
Same rules as rlbkit.py: real clicks at points taken from the program's own UI Automation frames, keys through
Windows' SendKeys, every write read back from the program's own list, no data files.

  python rlbber.py berlista
  python rlbber.py berszamfejtes [--dolgozo "Minta Anna"]
Output: one JSON object (Hungarian keys) on stdout; "ok": false with "hiba" when something went wrong.

Measured on the demo (2026-11-18): the demo computes only the first three months of the year („Csak három
hónapot lehet számfejteni!”), so the payroll it offers is the next of January-March for each employee. The
employees are fictitious, saved by name only (the program refuses a tax ID with a wrong check digit, and this
demo uses no real-looking ones).
"""
import argparse
import json
import logging
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlbkit  # noqa: E402
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
WIN = "BÉRSZÁMFEJTÉS RLB 26.12.0 [DEMO VERZIÓ]"
TAB_SZAMFEJTES, ICON_BERADATOK = (-1, 431), (-236, 529)   # quick menu, pixels from the window's centre / top
GRID = {"Hónap": "honap", "Bruttó bér": "brutto", "Kifizetve": "kifizetve"}


class BerError(rlbkit.RlbError):
    pass


def window():
    w = next((x for x in CUA.call("list_windows", {})[0].get("windows", []) if x.get("title") == WIN), None)
    if not w:
        raise BerError("a Bérszámfejtés program ablaka nincs nyitva")
    return w


def front():
    w = window()
    r = CUA.call("bring_to_front", {"pid": w["pid"], "window_id": w["window_id"]})[0]
    if not r.get("landed_on_target"):
        raise BerError(f"nem sikerült előtérbe hozni a Bérszámfejtést: {r}")
    return w


def elements():
    w = window()
    st = CUA.call("get_window_state", {"pid": w["pid"], "window_id": w["window_id"], "timeout_ms": 15000})[0]
    return w, st.get("elements") or []


def find(label, role=None, tries=6):
    for _ in range(tries):
        w, els = elements()
        hit = [e for e in els if e.get("label") == label and (role is None or e.get("role") == role)]
        if hit:
            return w, hit[0]
        time.sleep(1.2)
    raise BerError(f"nincs ilyen elem a képernyőn: {label}")


def click_at(w, x, y, keys=""):
    out = osin(HOST, WIN, keys, AUDIT, hwnd=w["window_id"], xy=[int(x), int(y)], wait=1.0)
    if not (out or {}).get("sent"):
        raise BerError(f"a kattintás ({x},{y}) nem a Bérszámfejtés ablakára esett: {out}")
    time.sleep(0.8)


def click(label, role="Button"):
    w, e = find(label, role)
    f = e["frame"]
    logger.info("click %s %r at %s", role, label, f)
    click_at(w, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2)


def popups():
    ws = CUA.call("list_windows", {})[0].get("windows", [])
    main = next((x for x in ws if x.get("title") == WIN), None)
    return [x for x in ws if main and x.get("pid") == main["pid"] and x.get("title") and x["title"] != WIN
            and (x.get("bounds") or {}).get("width")]


def message():
    """The program's open message box, if any: (title, text); its OK pressed."""
    for box in popups():
        st = CUA.call("get_window_state", {"pid": box["pid"], "window_id": box["window_id"]})[0]
        els = st.get("elements") or []
        text = " ".join(dict.fromkeys(e.get("label") or e.get("value") or "" for e in els
                                      if e.get("role") in ("Text", "Edit") and (e.get("label") or e.get("value"))))
        if not text:
            b = box.get("bounds") or {}
            try:
                text = " ".join(t for x, y, t in rlbkit.ocr_rows() if b.get("x", 0) <= x < b.get("x", 0) + b.get("width", 0)
                                and b.get("y", 0) + 30 <= y < b.get("y", 0) + b.get("height", 0) - 40)
            except Exception as e:     # noqa: BLE001  (OCR is a nice-to-have here)
                logger.warning("OCR of the message box failed: %s", e)
        ok = next((e for e in els if e.get("role") == "Button" and e.get("label") in ("OK", "Ok", "Rendben")), None)
        if ok:
            f = ok["frame"]
            osin(HOST, box["title"], "", AUDIT, hwnd=box["window_id"],
                              xy=[int(f["x"] + f["w"] / 2), int(f["y"] + f["h"] / 2)], wait=0.5)
            time.sleep(1.0)
        return box["title"], text
    return None


def open_beradatok():
    w = front()
    _, els = elements()
    if not any(e.get("label") == "Sajgrid1" for e in els):
        b = w["bounds"]
        cx = b["x"] + b["width"] / 2
        click_at(w, cx + TAB_SZAMFEJTES[0], b["y"] + TAB_SZAMFEJTES[1])
        click_at(w, cx + ICON_BERADATOK[0], b["y"] + ICON_BERADATOK[1])
        find("Sajgrid1", "Table", tries=8)
    return w


def employees(els):
    lst = next((e for e in els if e.get("label") == "list1" and e.get("role") == "Table"), None)
    if not lst:
        raise BerError("nem látom a dolgozók listáját")
    lx = lst["frame"]["x"]
    rows = [e for e in els if e.get("role") == "Edit" and e.get("label") == "Text1" and e.get("value")
            and abs(e["frame"]["x"] - lx) <= 3 and e["frame"]["y"] > lst["frame"]["y"]]
    return sorted(rows, key=lambda e: e["frame"]["y"])


def months(els):
    # the grid's headers come without frames: a row's cells, left to right, are Hónap, Bruttó bér, Kifizetve, ...
    grid = next((e for e in els if e.get("label") == "Sajgrid1" and e.get("frame")), None)
    if not grid:
        return []
    g = grid["frame"]
    cells = {}
    for e in els:
        f = e.get("frame") or {}
        if e.get("role") == "Edit" and g["x"] <= f.get("x", -1) < g["x"] + g["w"] and f.get("y", 0) > g["y"] + 10:
            cells.setdefault(f["y"], []).append((f["x"], e.get("value") or ""))
    rows = []
    for _, cs in sorted(cells.items()):
        vals = [v for _, v in sorted(cs)]
        if len(vals) >= 3 and vals[0]:
            rows.append(dict(zip(("honap", "brutto", "kifizetve"), vals[:3])))
    for r in rows:
        for k in ("brutto", "kifizetve"):
            r[k] = int(float(r.get(k) or 0))
    return rows


def select(name):
    w, els = elements()
    e = next((e for e in employees(els) if e.get("value") == name), None)
    if not e:
        raise BerError(f"nincs ilyen dolgozó a listában: {name}")
    f = e["frame"]
    click_at(w, f["x"] + 40, f["y"] + f["h"] / 2)
    time.sleep(1.0)
    return months(elements()[1])


def berlista():
    open_beradatok()
    _, els = elements()
    out = []
    for e in employees(els):
        months_ = select(e["value"])
        row = {"dolgozo": e["value"], "szamfejtett_honapok": [m["honap"] for m in months_]}
        if months_:                       # the latest month's amounts, from the stored month (the grid is stale)
            click("Módosítás")
            time.sleep(2.0)
            vals = form_values()
            click("Mégsem")
            time.sleep(1.0)
            row["utolso"] = {"honap": months_[-1]["honap"], **vals}
        out.append(row)
    return out


HONAPOK = ("január", "február", "március", "április", "május", "június", "július", "augusztus", "szeptember",
           "október", "november", "december")
# field names measured against the amounts (2026-11-18): 410 000 - 75 850 (18.5 %) - 61 500 (15 %) = 272 650
FIELDS = {"fjov01": "brutto", "ny2": "tb_jarulek_18_5", "szj1": "szja_15", "kpber": "kifizetendo",
          "tbnyx": "munkaltatoi_szocho_13"}


def form_values():
    """The open payroll form's amounts by their field names. The employee's TB contribution is in „szny2” (always
    exposed) and in „ny2” (exposed only after its tab was opened, measured 2026-11-18); ny2 wins when present."""
    for _ in range(8):
        _, els = elements()
        raw = {e["label"]: int(float(e.get("value") or 0)) for e in els
               if e.get("label") in set(FIELDS) | {"szny2"} and (e.get("value") or "").strip().lstrip("-").isdigit()}
        if "ny2" not in raw and "szny2" in raw:
            raw["ny2"] = raw["szny2"]
        if all(k in raw for k in FIELDS):
            return {FIELDS[k]: raw[k] for k in FIELDS}
        time.sleep(1.2)
    raise BerError("a számfejtő ablak értékei nem olvashatók")


KODOK = {"S": "szabadsag", "B": "beteg", "X": "ledolgozott"}


def days(els):
    """The attendance calendar of the open payroll form: {cell number: (code, frame)} (cells Text1..Text42)."""
    out = {}
    for e in els:
        lab = e.get("label") or ""
        if e.get("role") == "Edit" and lab.startswith("Text") and lab[4:].isdigit() and e.get("frame") \
                and 1 <= int(lab[4:]) <= 42 and (e.get("value") or "").strip():
            out[int(lab[4:])] = ((e.get("value") or "").strip(), e["frame"])
    return out


def jelenlet(els):
    d = days(els)
    return {name: sum(1 for c, _ in d.values() if c == k) for k, name in KODOK.items()}


def set_absences(szabadsag, beteg):
    """Mark sick days on the month's first working days and paid leave on its last ones; collect the program's
    messages (it warns when the employee's yearly allowance is used up)."""
    w, els = elements()
    work = sorted(n for n, (c, _) in days(els).items() if c == "X")
    plan = [(n, "B") for n in work[:beteg]] + [(n, "S") for n in (work[-szabadsag:] if szabadsag else [])]
    notes = []
    d = days(els)
    for n, code in plan:
        f = d[n][1]
        click_at(w, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2)
        time.sleep(1.2)
        osin(HOST, WIN, code, AUDIT)
        time.sleep(2.0)
        msg = message()
        if msg:
            notes.append(f"{msg[0]}: {msg[1]}".strip(": "))
            time.sleep(1.0)
    return notes


def berszamfejtes(only=None, szabadsag=0, beteg=0):
    open_beradatok()
    _, els = elements()
    names = [e["value"] for e in employees(els) if not only or e["value"] in only]
    if not names:
        raise BerError("nincs számfejthető dolgozó a listában")
    if (szabadsag or beteg) and len(names) != 1:
        raise BerError("távollétet (--szabadsag, --beteg) egyszerre csak egy dolgozóra adj meg (--dolgozo)")
    done = []
    for name in names:
        before = [m["honap"] for m in select(name)]
        click("Számfejtés")
        time.sleep(2.0)
        msg = message()
        if msg:
            raise BerError(f"{name}: a program nem számfejt: {msg[0]}: {msg[1]}")
        find("Text2", "Edit", tries=8)
        notes = set_absences(szabadsag, beteg) if (szabadsag or beteg) else []
        _, els = elements()
        att = jelenlet(els)
        if att["szabadsag"] != szabadsag or att["beteg"] != beteg:
            raise BerError(f"{name}: a jelenléti naptár nem a kért távollétet mutatja ({att})")
        computed = form_values()
        click("Mentés")
        time.sleep(2.0)
        msg = message()
        if msg:
            notes.append(f"{msg[0]}: {msg[1]}".strip(": "))
        # read back: the stored month, opened again from the list (the list grid itself reports stale values)
        months_ = [m["honap"] for m in select(name)]
        new = [m for m in months_ if m not in before]
        click("Módosítás")
        time.sleep(2.0)
        stored = form_values()
        att2 = jelenlet(elements()[1])
        click("Mégsem")
        time.sleep(1.0)
        same = stored == computed
        if not same or att2 != att or len(new) != 1:
            raise BerError(f"{name}: a visszaolvasott számfejtés eltér ({stored}, {att2} != {computed}, {att})")
        out = {k: v for k, v in stored.items() if k != "brutto"}
        # measured: the form's „Bruttó bér” is the wage for the worked days only; paid leave and sick pay come on top,
        # and TB/SZJA are computed on the total, so the total income is net + TB + SZJA (no other deductions here)
        out = {"ledolgozott_napok_bere": stored["brutto"], "osszes_jovedelem":
               stored["kifizetendo"] + stored["tb_jarulek_18_5"] + stored["szja_15"], **out}
        done.append({"dolgozo": name, "honap": new[0], "jelenlet_napok": att2, **out, "visszaolvasva": True,
                     **({"program_uzenetei": notes} if notes else {})})
    return done


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError) as e:
            logger.warning("stream encoding unchanged: %s", e)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("op")
    p.add_argument("--dolgozo", action="append")
    p.add_argument("--szabadsag", type=int, default=0)
    p.add_argument("--beteg", type=int, default=0)
    a = p.parse_args()
    try:
        if a.op == "berlista":
            res = {"ok": True, "dolgozok": berlista()}
        elif a.op == "berszamfejtes":
            res = {"ok": True, "szamfejtve": berszamfejtes(a.dolgozo, a.szabadsag, a.beteg),
                   "megjegyzes": "a demó program csak az év első három hónapját számfejti"}
        else:
            raise BerError(f"ismeretlen művelet: {a.op}")
    except rlbkit.RlbError as e:
        logger.error("%s", e)
        res = {"ok": False, "hiba": str(e), "nyitott_ablakok": [p["title"] for p in popups()]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res.get("ok") else 1)


if __name__ == "__main__":
    main()
