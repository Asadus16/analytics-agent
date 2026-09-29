"""Generate a rich, landscape ERD from the LIVE analytics schema.

Columns, types, PK/FK flags and relationships are read from demo.db +
query_log.db via PRAGMA. Boxes are grouped into zones with relationship verbs, a
legend and schema stats. Writes erd-real.html; render with headless Chrome
(command printed at the end).

    python3 docs/gen_erd.py
"""

from __future__ import annotations

import html
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEMO = ROOT / "data" / "demo.db"
QLOG = ROOT / "data" / "query_log.db"
W, H = 1480, 720
ACCENT, PKBG, DOT = "#0d9488", "#ccfbf1", "#e6fffb"

TABLES = ["regions", "plans", "customers", "subscriptions", "monthly_revenue", "query_log"]
POS = {"regions": (60, 190), "plans": (60, 440), "customers": (430, 190),
       "subscriptions": (800, 190), "monthly_revenue": (800, 480), "query_log": (1180, 190)}

ZONES = [
    (30, 160, 300, 470, "Dimensions", "rgba(13,148,136,.06)", "rgba(13,148,136,.35)"),
    (400, 160, 710, 540, "Facts", "rgba(2,132,199,.06)", "rgba(2,132,199,.35)"),
    (1150, 160, 300, 380, "Audit", "rgba(100,116,139,.06)", "rgba(100,116,139,.35)"),
]

LINES = [
    ("M300,240 H430", [(312, 232, "1"), (412, 232, "&#8734;")], (335, 224, "located in")),
    ("M670,250 H800", [(682, 242, "1"), (790, 242, "&#8734;")], (700, 234, "subscribes")),
    ("M300,500 V400 H800", [(312, 492, "1"), (790, 392, "&#8734;")], (470, 392, "on plan")),
    ("M550,333 V500 H800", [(558, 470, "1"), (790, 492, "&#8734;")], (600, 492, "bills")),
]


def introspect(db, tables):
    con = sqlite3.connect(db)
    out, nfk = {}, 0
    for t in tables:
        cols = [(r[1], r[2], bool(r[5])) for r in con.execute(f"PRAGMA table_info({t})")]
        fks = {r[3] for r in con.execute(f"PRAGMA foreign_key_list({t})")}
        nfk += len(list(con.execute(f"PRAGMA foreign_key_list({t})")))
        out[t] = {"cols": cols, "fks": fks}
    con.close()
    return out, nfk


def card(name, meta, x, y):
    lis = []
    for cname, ctype, pk in meta["cols"]:
        badge = ('<span class="k pk">PK</span>' if pk
                 else ('<span class="k fk">FK</span>' if cname in meta["fks"] else ""))
        lis.append(f'<li>{badge}<span class="nm">{html.escape(cname)}</span>'
                   f'<span class="ty">{html.escape((ctype or "").lower())}</span></li>')
    return (f'<div class="entity" style="left:{x}px; top:{y}px;">'
            f'<div class="h">{html.escape(name)}</div><ul>{"".join(lis)}</ul></div>')


CSS = """<style>
 :root {{ --accent:{accent}; --pkbg:{pkbg}; --dot:{dot}; }}
 *{{box-sizing:border-box;margin:0;padding:0;}} html,body{{width:{W}px;height:{H}px;}}
 body{{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;color:#0f172a;background:#fff;position:relative;}}
 .bg{{position:absolute;inset:0;background-image:radial-gradient(var(--dot) 1.4px,transparent 1.4px);background-size:26px 26px;opacity:.55;}}
 header{{position:absolute;top:26px;left:44px;z-index:5;}} h1{{font-size:27px;letter-spacing:-.02em;}} h1 .tag{{color:var(--accent);}}
 .sub{{color:#64748b;font-size:14px;margin-top:5px;}}
 .legend{{position:absolute;top:32px;right:46px;z-index:5;display:flex;gap:16px;align-items:center;font-size:12.5px;color:#475569;}}
 .legend .k{{font-size:9px;font-weight:700;padding:1px 5px;border-radius:4px;margin-right:5px;}}
 .pk{{background:var(--pkbg);color:var(--accent);}} .fk{{background:#f1f5f9;color:#64748b;}}
 .zone{{position:absolute;z-index:0;border:1.5px dashed;border-radius:16px;}}
 .zone-label{{position:absolute;z-index:1;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#475569;}}
 svg.lines{{position:absolute;inset:0;z-index:1;}}
 .entity{{position:absolute;z-index:2;width:240px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 6px 20px rgba(15,23,42,.08);overflow:hidden;}}
 .entity .h{{background:var(--accent);color:#fff;font-weight:700;font-size:14px;padding:9px 13px;}}
 .entity ul{{list-style:none;padding:6px 0;}}
 .entity li{{font-size:11.5px;padding:2.5px 13px;display:flex;align-items:center;gap:7px;color:#334155;}}
 .entity li .nm{{flex:1;}} .entity li .ty{{color:#94a3b8;font-size:9.5px;}}
 .entity li .k{{font-size:8.5px;font-weight:700;padding:1px 5px;border-radius:4px;}}
 .rel{{fill:#64748b;font-size:12px;font-weight:700;}}
 .verb{{fill:#0d9488;font-size:11.5px;font-style:italic;}}
</style>"""


def main():
    data, nfk = introspect(DEMO, ["regions", "plans", "customers", "subscriptions", "monthly_revenue"])
    q, qfk = introspect(QLOG, ["query_log"])
    data.update(q); nfk += qfk
    ncols = sum(len(v["cols"]) for v in data.values())
    zones = "".join(
        f'<div class="zone" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;'
        f'background:{fill};border-color:{bc};"></div>'
        f'<div class="zone-label" style="left:{x+16}px;top:{y+12}px;">{lbl}</div>'
        for (x, y, w, h, lbl, fill, bc) in ZONES)
    cards = "".join(card(t, data[t], *POS[t]) for t in TABLES)
    svg = ""
    for path, labels, verb in LINES:
        svg += f'<path d="{path}" stroke="#94a3b8" stroke-width="2" fill="none"/>'
        for lx, ly, tx in labels:
            svg += f'<text class="rel" x="{lx}" y="{ly}">{tx}</text>'
        if verb:
            svg += f'<text class="verb" x="{verb[0]}" y="{verb[1]}">{verb[2]}</text>'
    legend = (
        '<div class="legend">'
        '<span><span class="k pk">PK</span>primary key</span>'
        '<span><span class="k fk">FK</span>foreign key</span>'
        '<span>1 &mdash;&mdash; &#8734; one&#8209;to&#8209;many</span></div>')
    page = ("<!doctype html><html><head><meta charset='utf-8'>"
            + CSS.format(accent=ACCENT, pkbg=PKBG, dot=DOT, W=W, H=H)
            + "</head><body><div class='bg'></div>"
            "<header><h1>Deterministic Analytics <span class='tag'>&mdash; database schema</span></h1>"
            f"<div class='sub'>Auto-generated from the live SQLite schema (demo.db + query_log.db) &middot; "
            f"{len(TABLES)} tables &middot; {ncols} columns &middot; {nfk} relationships.</div></header>"
            + legend
            + f"<svg class='lines' width='{W}' height='{H}'>{svg}</svg>{zones}{cards}</body></html>")
    (HERE / "erd-real.html").write_text(page)
    print(f"wrote erd-real.html ({len(TABLES)} tables, {ncols} cols, {nfk} rels)\nRender:")
    print(f'  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless '
          f'--disable-gpu --hide-scrollbars --force-device-scale-factor=2 '
          f'--window-size={W},{H} --screenshot="{HERE}/erd-real.png" "file://{HERE}/erd-real.html"')


if __name__ == "__main__":
    main()
