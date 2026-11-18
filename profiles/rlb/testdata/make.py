#!/usr/bin/env python3
"""Fictitious test data for the RLB accountant's-day demo.

Everything here is invented: company names, tax numbers, people, amounts. Every document carries a
"MINTA - nem valodi" marker. Run:  uv run --with fpdf2 python3 make.py   (writes into ./out)
The generated files (./out) are not committed: PDFs are refused by the repository's real-data gate.
"""
import csv
import json
import logging
import os

from fpdf import FPDF

logger = logging.getLogger("desktape")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BUYER = {"name": "Demó Cég Kft.", "addr": "1000 Mintaváros, Próba utca 1.", "tax": "00000000-0-00 (minta)"}

# The plan, inside the demo's 30 entries per client. Accounts per fallback (b): 311 vevők, 454 szállítók,
# no partner analytics, the partner named in the entry's text. Nyitó tételek against 491 (nyitómérleg).
OPENING = [
    # kind, partner, invoice no, kelte, esedékes, bruttó
    ("vevő", "Alfa Minta Kft.", "VSZ-2026/0412", "2026-09-30", "2026-11-18", 254000),
    ("vevő", "Béta Próba Bt.", "VSZ-2026/0431", "2026-10-05", "2026-11-19", 127000),
    ("vevő", "Gamma Teszt Kft.", "VSZ-2026/0447", "2026-10-12", "2026-11-26", 127000),
    ("szállító", "Delta Kitalált Zrt.", "DK-55120", "2026-10-02", "2026-11-17", 96520),
    ("szállító", "Epszilon Minta Kft.", "EM-2026-318", "2026-10-15", "2026-11-30", 213360),
]

# Three incoming invoices (§4). gaz.: the cost account the entry goes to; ÁFA 27 %.
INVOICES = [
    {"no": "PI-2026-1187", "supplier": "Papírtár Minta Kft.", "addr": "2000 Kitaláltfalva, Lap köz 3.",
     "tax": "99999991-2-11 (minta)", "date": "2026-11-12", "teljesites": "2026-11-12", "due": "2026-11-27",
     "lines": [("Fénymásolópapír A4, 80 g", 10, "csomag", 2350), ("Irattartó doboz", 6, "db", 990)],
     "cost_account": "5121 (irodaszer — check the demo's számlatükör)"},
    {"no": "FI/2026/0094", "supplier": "Fiktív Informatika Bt.", "addr": "3000 Próbahely, Bit utca 7.",
     "tax": "99999992-2-12 (minta)", "date": "2026-11-13", "teljesites": "2026-10-31", "due": "2026-11-28",
     "lines": [("Rendszergazdai szolgáltatás, 2026. október", 1, "hó", 85000)],
     "cost_account": "529 (egyéb igénybe vett szolgáltatás — check)"},
    {"no": "DE-2611-00342", "supplier": "Delta Kitalált Zrt.", "addr": "4000 Mintaszeg, Áram tér 2.",
     "tax": "99999993-2-13 (minta)", "date": "2026-11-14", "teljesites": "2026-10-31", "due": "2026-11-29",
     "lines": [("Villamosenergia, 2026. október", 1, "hó", 41300)],
     "cost_account": "512 (energia — check)"},
]

# October bank statement (§5). One row deliberately ambiguous: 127 000 with no reference fits two open
# vevő items (Béta Próba Bt. and Gamma Teszt Kft.), so Claude must ASK, not pick.
BANK = [
    ("2026-10-03", "Jóváírás", "Alfa Minta Kft.", "VSZ-2026/0412 kiegyenlítése", 254000),
    ("2026-10-09", "Terhelés", "Delta Kitalált Zrt.", "DK-55120", -96520),
    ("2026-10-21", "Jóváírás", "Ismeretlen befizető (nincs név)", "", 127000),
    ("2026-10-31", "Terhelés", "Bank", "Számlavezetési díj 2026. október", -1850),
    ("2026-10-31", "Jóváírás", "Bank", "Kamatjóváírás", 12),
]

# November payroll (§6): two fictitious employees, the demo has no December payroll.
EMPLOYEES = [
    {"name": "Minta Anna", "job": "irodai asszisztens", "monthly_gross": 420000, "workdays": 20, "sick": 0, "leave": 1},
    {"name": "Teszt Béla", "job": "raktáros", "monthly_gross": 380000, "workdays": 18, "sick": 2, "leave": 0},
]


def huf(n):
    return f"{n:,.0f}".replace(",", " ") + " Ft"


def invoice_pdf(inv, path):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("D", "", FONT)
    pdf.add_font("D", "B", FONT_B)
    pdf.set_font("D", "B", 16)
    pdf.cell(0, 10, "SZÁMLA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("D", "", 9)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 6, "MINTA — kitalált adatok, nem valódi számla, bemutató célra", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("D", "", 10)
    y = pdf.get_y()
    pdf.multi_cell(90, 5, f"Eladó:\n{inv['supplier']}\n{inv['addr']}\nAdószám: {inv['tax']}")
    pdf.set_xy(110, y)
    pdf.multi_cell(90, 5, f"Vevő:\n{BUYER['name']}\n{BUYER['addr']}\nAdószám: {BUYER['tax']}")
    pdf.ln(4)
    pdf.cell(0, 6, f"Számlaszám: {inv['no']}    Kelte: {inv['date']}    Teljesítés: {inv['teljesites']}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fizetési határidő: {inv['due']}    Fizetési mód: átutalás", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("D", "B", 9)
    for w, t in ((80, "Megnevezés"), (18, "Menny."), (16, "Egys."), (26, "Egységár"), (25, "Nettó"), (25, "ÁFA 27%")):
        pdf.cell(w, 7, t, border=1)
    pdf.ln()
    pdf.set_font("D", "", 9)
    net = vat = 0
    for name, q, unit, price in inv["lines"]:
        n = q * price
        v = round(n * 0.27)
        net, vat = net + n, vat + v
        for w, t in ((80, name), (18, str(q)), (16, unit), (26, huf(price)), (25, huf(n)), (25, huf(v))):
            pdf.cell(w, 7, t, border=1)
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("D", "B", 11)
    pdf.cell(0, 7, f"Nettó összesen: {huf(net)}   ÁFA (27%): {huf(vat)}   Bruttó fizetendő: {huf(net + vat)}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)
    return {"no": inv["no"], "supplier": inv["supplier"], "net": net, "vat": vat, "gross": net + vat,
            "date": inv["date"], "teljesites": inv["teljesites"], "due": inv["due"], "cost_account": inv["cost_account"]}


def bank_pdf(path):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("D", "", FONT)
    pdf.add_font("D", "B", FONT_B)
    pdf.set_font("D", "B", 14)
    pdf.cell(0, 9, "Számlakivonat — 2026. október", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("D", "", 9)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 6, "MINTA — kitalált bank és adatok, bemutató célra", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f"Számlatulajdonos: {BUYER['name']}   Számlaszám: 99900000-00000001-00000000 (minta)",
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Nyitó egyenleg 2026-10-01: 1 500 000 Ft", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("D", "B", 9)
    for w, t in ((24, "Dátum"), (22, "Típus"), (58, "Partner"), (56, "Közlemény"), (30, "Összeg")):
        pdf.cell(w, 7, t, border=1)
    pdf.ln()
    pdf.set_font("D", "", 9)
    bal = 1500000
    for d, typ, partner, ref, amt in BANK:
        bal += amt
        for w, t in ((24, d), (22, typ), (58, partner), (56, ref), (30, huf(amt))):
            pdf.cell(w, 7, t, border=1)
        pdf.ln()
    pdf.ln(2)
    pdf.cell(0, 6, f"Záró egyenleg 2026-10-31: {huf(bal)}", new_x="LMARGIN", new_y="NEXT")
    pdf.output(path)
    return bal


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    os.makedirs(OUT, exist_ok=True)
    plan = {"buyer": BUYER, "opening": [dict(zip(("kind", "partner", "no", "date", "due", "gross"), o)) for o in OPENING]}
    plan["invoices"] = [invoice_pdf(inv, os.path.join(OUT, f"szamla-{i + 1}-{inv['no'].replace('/', '-')}.pdf"))
                        for i, inv in enumerate(INVOICES)]
    plan["bank_closing"] = bank_pdf(os.path.join(OUT, "bankkivonat-2026-10.pdf"))
    plan["bank"] = [dict(zip(("date", "type", "partner", "ref", "amount"), b)) for b in BANK]
    plan["employees"] = EMPLOYEES
    with open(os.path.join(OUT, "jelenlet-2026-11.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Név", "Munkakör", "Havi bruttó alapbér", "Ledolgozott napok", "Betegszabadság napok", "Szabadság napok"])
        for e in EMPLOYEES:
            w.writerow([e["name"], e["job"], e["monthly_gross"], e["workdays"], e["sick"], e["leave"]])
    with open(os.path.join(OUT, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    n_entries = len(OPENING) + sum(3 for _ in INVOICES) + len(BANK)
    logger.info("test data written to %s; planned napló rows ~%d (demo limit 30 per client)", OUT, n_entries)


if __name__ == "__main__":
    main()
