"""rlb-nezet: build one read-only HTML view of what the RLB program shows right now.

The data comes only from a fresh read of the program's own windows (rlbkit's napló and főkönyvi kivonat reads, UI
only). The page is static: no script, no web font, no image, no link, no form; every value from the program, and
every sentence Claude passes in (--pont, --kerdes), is HTML-escaped. Claude publishes the written file as a private
artifact, unchanged. The look is ITLine's own.

    nezet.py nyitott --out <profile>/views/nyitott.html
    nezet.py kivonat --out ...
    nezet.py afa --out ...
    nezet.py napi --out ... --mai V/000006,V/000007 --pont "Lekönyveltem a 3 bejövő számlát." --kerdes "..."
    nezet.py zaras --out ... --mai ... --pont ... --kerdes ...     (napi + kivonat + ÁFA on one page)
"""
import argparse
import datetime as dt
import html
import json
import logging
import os
import re
import sys

logger = logging.getLogger("desktape")

HETNAP = ("hétfő", "kedd", "szerda", "csütörtök", "péntek", "szombat", "vasárnap")
CEG = "Demó Cég Kft."
MINTA = True        # the demo client is fictitious: the page says so (a real client's page sets this False)


def e(v):
    return html.escape(str(v), quote=True)


def ft(n, unit=True):
    s = f"{abs(int(n)):,}".replace(",", "\u00a0")
    return ("−" if int(n) < 0 else "") + s + ("\u00a0Ft" if unit else "")


def datum(d, nap=False):
    s = f"{d.year}. {d.month:02d}. {d.day:02d}."
    return s + (f", {HETNAP[d.weekday()]}" if nap else "")


def rovid(d):
    return f"{d.month:02d}.{d.day:02d}."


def parse_datum(s):
    try:
        y, m, d = (int(x) for x in s.split("."))
        return dt.date(y, m, d)
    except (ValueError, AttributeError):
        logger.warning("not a date: %r", s)
        return None


# ---------------------------------------------------------------- data from the napló


def tetelek(rows, ma):
    """Split the napló into invoices and bank rows, and pair them by the voucher number in the bank row's text.
    The demo client has no partner analytics, so partner and due date are read from the entry text
    („<partner> vevő, esed. HH.NN” / „<partner> szla, esed. HH.NN” / „Bank: <partner> <voucher>”)."""
    bank = [r for r in rows if r.get("megjegyzes", "").startswith("Bank:")]
    out = []
    for r in rows:
        mj = r.get("megjegyzes", "")
        if mj.startswith("Bank:"):
            continue
        d = parse_datum(r.get("datum", ""))
        m = re.search(r"esed\.?\s*(\d{1,2})\.(\d{1,2})", mj)
        esed = None
        if m and d:
            mo, da = int(m.group(1)), int(m.group(2))
            try:
                esed = dt.date(d.year + (1 if mo < d.month else 0), mo, da)
            except ValueError:
                logger.warning("bad due date in %r", mj)
        vevo = " vevő" in mj or r.get("bizonylatszam", "").startswith("VSZ-")
        partner = re.split(r"\s+(vevő|szla)\b", mj)[0].strip(" ,")
        biz = r.get("bizonylatszam", "")
        par = [b for b in bank if biz and biz in b.get("megjegyzes", "")]
        out.append({
            "sorszam": r.get("sorszam", ""), "datum": d, "biz": biz, "partner": partner, "esed": esed,
            "oldal": "vevő" if vevo else "szállító", "osszeg": int(r.get("osszeg") or 0),
            "kiegyenlitve": par[0]["sorszam"] if par else "",
            "keses": (ma - esed).days if esed and esed < ma and not par else 0,
        })
    return out, bank


def het_vege(ma):
    return ma + dt.timedelta(days=6 - ma.weekday())


def lejarat(t, ma):
    """(css class, label) for the due-date tag."""
    d = t["esed"]
    if not d:
        return "josh", "–"
    if t["keses"]:
        return "ma", f"késés: {t['keses']} nap · {rovid(d)}"
    if d == ma:
        return "ma", f"ma · {rovid(d)}"
    if d == ma + dt.timedelta(days=1):
        return "holnap", f"holnap · {rovid(d)}"
    if d <= het_vege(ma):
        return "holnap", f"{HETNAP[d.weekday()]} · {rovid(d)}"
    if d <= het_vege(ma) + dt.timedelta(days=7):
        return "josh", f"jövő hét · {rovid(d)}"
    return "josh", rovid(d)


def item_json(t):
    return {"sorszam": t["sorszam"], "bizonylat": t["biz"], "partner": t["partner"], "osszeg": t["osszeg"],
            "esedekes": t["esed"].isoformat() if t["esed"] else None, "keses_nap": t["keses"]}


# ---------------------------------------------------------------- page

CSS = """
:root{--bg:#f3f5f6;--surface:#fff;--surface-2:#eef1f2;--line:#d9dfe1;--fg:#16211f;--muted:#5d6b69;--accent:#0f7066;
--accent-soft:#d8ebe8;--danger:#b3261e;--danger-soft:#f7dcd9;--ok:#1f7a43;--ok-soft:#d9efe1;--warn:#8a5a00;
--warn-soft:#f6e8cc;color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0e1514;--surface:#16201e;--surface-2:#1d2a28;
--line:#2a3a37;--fg:#e8efed;--muted:#9bada9;--accent:#46b3a4;--accent-soft:#123430;--danger:#f06a60;--danger-soft:#3a1b18;
--ok:#5ec884;--ok-soft:#15311f;--warn:#e0a94a;--warn-soft:#33280f;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0e1514;--surface:#16201e;--surface-2:#1d2a28;--line:#2a3a37;--fg:#e8efed;--muted:#9bada9;
--accent:#46b3a4;--accent-soft:#123430;--danger:#f06a60;--danger-soft:#3a1b18;--ok:#5ec884;--ok-soft:#15311f;
--warn:#e0a94a;--warn-soft:#33280f;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0 auto;max-width:760px;padding:18px 16px;background:var(--bg);color:var(--fg);
font:14px/1.5 "Segoe UI",system-ui,-apple-system,sans-serif}
h1,h2{font-weight:600;margin:0}
.head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.head h1{font-size:1.3rem;letter-spacing:-.01em}
.head .ceg{color:var(--muted);font-size:.95rem}
.sub{color:var(--muted);font-size:.8rem;margin:4px 0 16px;display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center}
.badge{display:inline-block;font-size:.7rem;font-weight:600;letter-spacing:.03em;text-transform:uppercase;padding:2px 8px;
border-radius:999px;background:var(--warn-soft);color:var(--warn)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:13px;padding:14px;margin-bottom:12px}
.card>h2{font-size:1.02rem;margin-bottom:2px}
.note{color:var(--muted);font-size:.8rem;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600}
td.num,th.num{text-align:right;white-space:nowrap}
tr:last-child td{border-bottom:none}
.m{color:var(--muted);font-size:.76rem}
.tag{display:inline-block;font-size:.72rem;font-weight:600;padding:1px 7px;border-radius:999px;white-space:nowrap;margin-top:3px}
.tag.ma{background:var(--danger-soft);color:var(--danger)}
.tag.holnap{background:var(--warn-soft);color:var(--warn)}
.tag.josh{background:var(--surface-2);color:var(--muted)}
.tag.ok{background:var(--ok-soft);color:var(--ok)}
.total td{font-weight:700;border-top:2px solid var(--line)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px}
.tile{background:var(--surface-2);border-radius:10px;padding:10px 12px}
.tile .k{font-size:.74rem;color:var(--muted)}
.tile .v{font-size:1.15rem;font-weight:600;margin-top:2px;font-variant-numeric:tabular-nums;white-space:nowrap}
.tile .v.red{color:var(--danger)}
.tile .v.green{color:var(--ok)}
ul.sum{margin:10px 0 0;padding-left:18px}
ul.sum li{margin-bottom:6px}
.flag{background:var(--danger-soft);color:var(--danger);border-radius:10px;padding:10px 12px;font-size:.86rem;margin-top:10px}
.flag.ok{background:var(--ok-soft);color:var(--ok)}
.ask{margin-top:12px;padding:12px;border:1px dashed var(--accent);border-radius:11px;background:var(--accent-soft)}
.ask p{margin:0 0 6px;font-size:.84rem}
.ask ul{margin:0;padding-left:18px;font-weight:600}
.afa-line{display:flex;justify-content:space-between;gap:12px;padding:9px 2px;border-bottom:1px solid var(--line);
font-variant-numeric:tabular-nums}
.afa-line .lbl small{display:block;color:var(--muted);font-weight:400;font-size:.74rem}
.afa-line>span:last-child{white-space:nowrap}
.afa-line.res{font-weight:700;border-bottom:none;border-top:2px solid var(--line);margin-top:2px}
.foot{color:var(--muted);font-size:.74rem;margin-top:16px;border-top:1px solid var(--line);padding-top:10px}
@media (max-width:440px){body{padding:14px 12px}.card{padding:12px}th,td{padding:7px 4px}}
"""


def page(cim, kiolvasva, body, forras):
    sub = (('<span class="badge">Minta adat</span>' if MINTA else "") +
           f"<span>Kiolvasva: {e(kiolvasva)}</span><span>Forrás: RLB Kettős könyvvitel (képernyőről)</span>")
    foot = ("Ez a nézet csak olvas: a program adatát jeleníti meg, és nem ír vissza. " + forras +
            (" Kitalált cég és kitalált adat." if MINTA else ""))
    return f"""<!doctype html>
<html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(cim)} · {e(CEG)}</title><style>{CSS}</style></head>
<body>
<div class="head"><h1>{e(cim)}</h1><span class="ceg">{e(CEG)}</span></div>
<div class="sub">{sub}</div>
{body}
<p class="foot">{e(foot)}</p>
</body></html>
"""


def card(cim, note, inner):
    return f'<div class="card"><h2>{e(cim)}</h2>' + (f'<p class="note">{e(note)}</p>' if note else "") + inner + "</div>"


def tile(k, v, cls=""):
    return f'<div class="tile"><div class="k">{e(k)}</div><div class="v {cls}">{e(v)}</div></div>'


def nyitott_tabla(items, ma, fej):
    rows = []
    for t in sorted(items, key=lambda t: (t["esed"] or dt.date.max, t["biz"])):
        cls, lbl = lejarat(t, ma)
        rows.append(f'<tr><td>{e(t["partner"])}<div class="m">{e(t["biz"])} · {e(t["sorszam"])}</div></td>'
                    f'<td class="num">{e(ft(t["osszeg"]))}<br><span class="tag {cls}">{e(lbl)}</span></td></tr>')
    rows.append(f'<tr class="total"><td>Összesen ({len(items)})</td>'
                f'<td class="num">{e(ft(sum(t["osszeg"] for t in items)))}</td></tr>')
    return (f'<table><thead><tr><th>{e(fej)} · bizonylat</th><th class="num">Összeg · lejárat</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def nyitott_kartyak(nyitott, ma):
    vevo = [t for t in nyitott if t["oldal"] == "vevő"]
    szall = [t for t in nyitott if t["oldal"] == "szállító"]
    out = card("Nyitott vevői tételek", "Követelés: amit nekünk fizetnek.",
               nyitott_tabla(vevo, ma, "Vevő") if vevo else '<p class="note">Nincs nyitott vevői tétel.</p>')
    out += card("Nyitott szállítói tételek", "Kötelezettség: amit mi fizetünk.",
                nyitott_tabla(szall, ma, "Szállító") if szall else '<p class="note">Nincs nyitott szállítói tétel.</p>')
    return out, vevo, szall


def view_nyitott(rows, ma, kiolvasva):
    items, _ = tetelek(rows, ma)
    nyitott = [t for t in items if not t["kiegyenlitve"]]
    het = sorted([t for t in nyitott if t["esed"] and t["esed"] <= het_vege(ma)], key=lambda t: t["esed"])
    late = [t for t in nyitott if t["keses"]]
    kartyak, vevo, szall = nyitott_kartyak(nyitott, ma)
    if het:
        tiles = "".join(tile(f'{t["partner"]} · {lejarat(t, ma)[1]}', ft(t["osszeg"]),
                             "red" if t["esed"] <= ma else "") for t in het)
        nev = ", ".join(f'{t["partner"]} ({lejarat(t, ma)[1]})' for t in het)
        heti = card("Ezen a héten jár le", f"{len(het)} tétel vasárnapig ({rovid(het_vege(ma))}): {nev}.",
                    f'<div class="tiles">{tiles}</div>')
    else:
        heti = card("Ezen a héten jár le", f"Vasárnapig ({rovid(het_vege(ma))}) nem jár le nyitott tétel.", "")
    body = heti + kartyak
    if late:
        body += f'<div class="flag">Lejárt, kiegyenlítetlen: {e(", ".join(t["partner"] + " " + t["biz"] for t in late))}</div>'
    forras = (f"Az RLB Vegyes naplójából, {len(rows)} sor. Egy számla akkor kiegyenlített, ha egy banki sor szövegében "
              "szerepel a bizonylatszáma; a partner és a lejárat a tétel megjegyzéséből jön (a demó cégnél nincs "
              "partneranalitika).")
    return page("Nyitott tételek", kiolvasva, body, forras), {
        "vevo_db": len(vevo), "vevo_osszeg": sum(t["osszeg"] for t in vevo),
        "szallito_db": len(szall), "szallito_osszeg": sum(t["osszeg"] for t in szall),
        "e_heten_lejar": [item_json(t) for t in het], "lejart": [item_json(t) for t in late],
        "nyitott_vevo": [item_json(t) for t in vevo], "nyitott_szallito": [item_json(t) for t in szall]}


# ---------------------------------------------------------------- data from the főkönyvi kivonat


def szamlak(sorok, nevek):
    accs = [s["fokonyvi_szam"] for s in sorok if s["fokonyvi_szam"]]
    out = []
    for s in sorok:
        a = s["fokonyvi_szam"]
        grp = bool(a) and any(o != a and o.startswith(a) for o in accs)
        out.append({**s, "csoport": grp, "nev": nevek.get(a) or s["megnevezes"]})
    return out


def egyenleg(s):
    return s["tartozik_egyenleg"] - s["kovetel_egyenleg"]


def kivonat_adat(sorok, nevek):
    rows = szamlak(sorok, nevek)
    leaf = [r for r in rows if not r["csoport"]]
    ismeretlen = [r for r in rows if not r["fokonyvi_szam"]]
    t = sum(r["tartozik_egyenleg"] for r in leaf)
    k = sum(r["kovetel_egyenleg"] for r in leaf)
    tf = sum(r["tartozik_forgalom"] for r in leaf)
    kf = sum(r["kovetel_forgalom"] for r in leaf)
    return leaf, ismeretlen, t, k, tf, kf, (t == k and tf == kf and not ismeretlen)


def kivonat_kartya(sorok, nevek):
    leaf, ismeretlen, t, k, tf, kf, egyezik = kivonat_adat(sorok, nevek)
    tr = []
    for r in sorted(leaf, key=lambda r: r["fokonyvi_szam"] or "~"):
        eg = egyenleg(r)
        tr.append(f'<tr><td>{e(r["fokonyvi_szam"] or "?")}<div class="m">{e(r["nev"])}</div></td>'
                  f'<td class="num">{e(ft(eg, False)) if eg > 0 else "—"}</td>'
                  f'<td class="num">{e(ft(-eg, False)) if eg < 0 else "—"}</td></tr>')
    tr.append(f'<tr class="total"><td>Összesen</td><td class="num">{e(ft(t, False))}</td>'
              f'<td class="num">{e(ft(k, False))}</td></tr>')
    inner = ('<table><thead><tr><th>Számla</th><th class="num">Tartozik</th><th class="num">Követel</th></tr></thead>'
             f'<tbody>{"".join(tr)}</tbody></table>')
    if egyezik:
        inner += f'<div class="flag ok">Egyezik: a tartozik és a követel oldal is {e(ft(t))}.</div>'
    elif t != k:
        inner += f'<div class="flag">Eltérés: a két oldal különbsége {e(ft(abs(t - k)))}.</div>'
    else:
        inner += f'<div class="flag">Ellenőrizendő: {len(ismeretlen)} sor számlaszámát nem sikerült kiolvasni.</div>'
    c = card("Főkönyvi kivonat", "A program kivonatából, egyenlegek forintban; a gyűjtőszámlák nélkül.", inner)
    return c, {"tartozik_forgalom": tf, "kovetel_forgalom": kf, "tartozik_egyenleg": t, "kovetel_egyenleg": k,
               "egyezik": egyezik, "ismeretlen_szamlaszam": len(ismeretlen),
               "szamlak": [{"szam": r["fokonyvi_szam"], "nev": r["nev"], "egyenleg": egyenleg(r)} for r in leaf]}


def view_kivonat(sorok, nevek, kiolvasva):
    c, info = kivonat_kartya(sorok, nevek)
    forras = ("Az összegek a program mezőiből jönnek; a számlaszámot a képernyőről olvastuk, a megnevezés a program "
              "számlatörzse szerint.")
    return page("Főkönyvi kivonat", kiolvasva, c, forras), info


def afa_kartya(sorok, nevek):
    rows = {r["fokonyvi_szam"]: r for r in szamlak(sorok, nevek) if r["fokonyvi_szam"]}
    elo = egyenleg(rows["466"]) if "466" in rows else 0
    fiz = -egyenleg(rows["467"]) if "467" in rows else 0
    arbev = -egyenleg(rows["911"]) if "911" in rows else None
    alap_fiz = round(fiz / 0.27) if fiz else 0
    kul = fiz - elo
    inner = (f'<div class="afa-line"><span class="lbl">Fizetendő ÁFA<small>467</small></span><span>{e(ft(fiz))}</span></div>'
             f'<div class="afa-line"><span class="lbl">Előzetesen felszámított ÁFA<small>466 · levonható</small></span>'
             f'<span>{e(ft(elo))}</span></div>'
             f'<div class="afa-line res"><span class="lbl">{"Befizetendő" if kul >= 0 else "Visszaigényelhető"}'
             f'<small>467 − 466</small></span><span>{e(ft(abs(kul)))}</span></div>')
    if arbev is not None:
        if arbev == alap_fiz:
            inner += (f'<div class="flag ok">Egyezik: az árbevétel (911) {e(ft(arbev))}, és a fizetendő ÁFA ennek '
                      f'27 %-a.</div>')
        else:
            inner += (f'<div class="flag">Eltérés: az árbevétel (911) {e(ft(arbev))}, a fizetendő ÁFA 27 %-os '
                      f'alapja {e(ft(alap_fiz))}.</div>')
    c = card("ÁFA nézet", "A 466 és 467 főkönyvi egyenlegekből, 27 %-kal. A program saját ÁFA-analitikáját nem "
             "futtattuk (a demóban nem érhető el), ez nem bevallás.", inner)
    return c, {"fizetendo_467": fiz, "elozetes_466": elo, "kulonbseg": kul, "arbevetel_911": arbev,
               "arbevetel_egyezik": arbev == alap_fiz if arbev is not None else None}


def view_afa(sorok, nevek, kiolvasva):
    c, info = afa_kartya(sorok, nevek)
    return page("ÁFA nézet", kiolvasva, c, "A 466 és 467 egyenlege a program főkönyvi kivonatából."), info


# ---------------------------------------------------------------- daily summary


def napi_kartyak(rows, ma, mai, pontok, kerdesek):
    items, _ = tetelek(rows, ma)
    by = {r["sorszam"]: r for r in rows}
    hianyzik = [s for s in mai if s not in by]
    konyvelt = [by[s] for s in mai if s in by]
    nyitott = [t for t in items if not t["kiegyenlitve"]]
    vevo = [t for t in nyitott if t["oldal"] == "vevő"]
    szall = [t for t in nyitott if t["oldal"] == "szállító"]
    tiles = ('<div class="tiles">' + tile("Ma könyvelt tétel", f"{len(konyvelt)} db") +
             tile("Nyitott követelés", ft(sum(t["osszeg"] for t in vevo))) +
             tile("Nyitott tartozás", ft(sum(t["osszeg"] for t in szall))) + "</div>")
    inner = tiles
    if pontok:
        inner += '<ul class="sum">' + "".join(f"<li>{e(p)}</li>" for p in pontok) + "</ul>"
    if kerdesek:
        inner += ('<div class="ask"><p>Döntésre vár. A nézet nem ír a programba: a döntés után kérd Claude-tól.</p><ul>' +
                  "".join(f"<li>{e(q)}</li>" for q in kerdesek) + "</ul></div>")
    out = card("Napi összefoglaló", "Rövid, az ügyfélnek is érthető kép a mai könyvelésről. Piszkozat: nem megy ki "
               "magától.", inner)
    if konyvelt:
        tr = "".join(f'<tr><td>{e(r["megjegyzes"])}<div class="m">{e(r["sorszam"])} · {e(r.get("bizonylatszam", ""))}'
                     f'</div></td><td class="num">{e(ft(r.get("osszeg") or 0))}</td></tr>' for r in konyvelt)
        lista = f'<table><tbody>{tr}</tbody></table>'
    else:
        lista = '<p class="note">Ma nem könyveltünk tételt.</p>'
    if hianyzik:
        lista += f'<div class="flag">Nem található a naplóban: {e(", ".join(hianyzik))}</div>'
    out += card("Ma könyvelve", f"{len(konyvelt)} tétel, a naplóból visszaolvasva, sorszám szerint.", lista)
    return out, {"konyvelve": [r["sorszam"] for r in konyvelt], "nem_talalhato": hianyzik,
                 "nyitott_vevo_db": len(vevo), "nyitott_vevo_osszeg": sum(t["osszeg"] for t in vevo),
                 "nyitott_szallito_db": len(szall), "nyitott_szallito_osszeg": sum(t["osszeg"] for t in szall)}


def view_napi(rows, ma, kiolvasva, mai, pontok, kerdesek):
    body, info = napi_kartyak(rows, ma, mai, pontok, kerdesek)
    nyitott = [t for t in tetelek(rows, ma)[0] if not t["kiegyenlitve"]]
    kartyak, _, _ = nyitott_kartyak(nyitott, ma)
    body += kartyak
    return page("Napi összefoglaló", f"{kiolvasva} · {datum(ma, True)}", body,
                "Az RLB Vegyes naplójából, most kiolvasva."), info


def view_zaras(rows, sorok, nevek, ma, kiolvasva, mai, pontok, kerdesek):
    napi, info = napi_kartyak(rows, ma, mai, pontok, kerdesek)
    kiv, kinfo = kivonat_kartya(sorok, nevek)
    afa, ainfo = afa_kartya(sorok, nevek)
    body = napi + kiv + afa
    return page("Napi zárás", f"{kiolvasva} · {datum(ma, True)}", body,
                "Az RLB Vegyes naplójából és főkönyvi kivonatából, most kiolvasva."), {**info, "kivonat": kinfo, "afa": ainfo}


# ---------------------------------------------------------------- CLI


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError) as ex:
            logger.warning("stream encoding unchanged: %s", ex)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    p = argparse.ArgumentParser()
    p.add_argument("nezet", choices=("nyitott", "kivonat", "afa", "napi", "zaras"))
    p.add_argument("--out", required=True)
    p.add_argument("--mai", default="", help="napi/zaras: the V/ numbers booked today, comma separated")
    p.add_argument("--pont", action="append", default=[], help="napi/zaras: one summary sentence per flag")
    p.add_argument("--kerdes", action="append", default=[], help="napi/zaras: one open question per flag")
    a = p.parse_args()
    fixture = os.environ.get("RLB_NEZET_FIXTURE")   # offline tests only: a JSON with "tetelek" and "sorok"
    ma = dt.date.today()
    try:
        if fixture:
            data = json.load(open(fixture, encoding="utf-8"))
            ma = dt.date.fromisoformat(data.get("ma", ma.isoformat()))
            read_naplo, read_kivonat, nevek = (lambda: data["tetelek"]), (lambda: data["sorok"]), data.get("nevek", {})
        else:
            import rlbkit
            read_naplo, read_kivonat, nevek = rlbkit.naplo, rlbkit.kivonat, rlbkit.NAMES
        mai = [s.strip() for s in a.mai.split(",") if s.strip()]
        rows = read_naplo() if a.nezet in ("nyitott", "napi", "zaras") else None
        sorok = read_kivonat() if a.nezet in ("kivonat", "afa", "zaras") else None
        kiolvasva = dt.datetime.now().strftime("%Y. %m. %d. %H:%M")
        if a.nezet == "nyitott":
            doc, info = view_nyitott(rows, ma, kiolvasva)
        elif a.nezet == "napi":
            doc, info = view_napi(rows, ma, kiolvasva, mai, a.pont, a.kerdes)
        elif a.nezet == "zaras":
            doc, info = view_zaras(rows, sorok, nevek, ma, kiolvasva, mai, a.pont, a.kerdes)
        else:
            doc, info = (view_kivonat if a.nezet == "kivonat" else view_afa)(sorok, nevek, kiolvasva)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(doc)
        logger.info("view %s written: %s (%d bytes)", a.nezet, a.out, len(doc))
        res = {"ok": True, "nezet": a.nezet, "fajl": os.path.abspath(a.out), "kiolvasva": kiolvasva, **info}
    except Exception as ex:   # the skill reports any failure in Hungarian and stops
        logger.error("view %s failed: %s", a.nezet, ex)
        res = {"ok": False, "nezet": a.nezet, "hiba": str(ex)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
