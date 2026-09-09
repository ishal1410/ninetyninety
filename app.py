"""NinetyNinety -- draft an IRS Form 990-EZ from a nonprofit's raw ledger.

Built with Strands Agents.

Front: cinematic dark page (Outfit + IBM Plex Mono, one green accent), motion
on CSS scroll-driven animations and sticky pinning so it lives in the page
scroll, no iframe. Below it, the working tool.
"""
import base64
import html
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from ninetyninety.ledger import load_ledger
from ninetyninety.lines import EXPENSE_LINES, REVENUE_LINES, form_order, line_by_number
from ninetyninety.pdffill import download_form, fill_form
from ninetyninety.prepare import prepare_ledger, trace_rows
from ninetyninety.recorded import load_recorded_run

BASE = Path(__file__).parent
st.set_page_config(page_title="NinetyNinety", page_icon=str(BASE / "assets" / "favicon.png"),
                   layout="wide")


@st.cache_data
def asset(name: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode((BASE / "assets" / name).read_bytes()).decode()


def esc(text) -> str:
    return html.escape(str(text))


def money(n: int) -> str:
    """Accountant's style: negatives in parentheses."""
    return f"({abs(n):,})" if n < 0 else f"{n:,}"


CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{--bg:#07090F;--bg2:#0E121B;--line:#1E2533;--ink:#EDEFF5;--muted:#9AA3B5;--acc:#62D39A;--acc-ink:#07090F;--danger:#F0716B;--ease:cubic-bezier(.32,.72,0,1)}
#MainMenu, footer, header[data-testid="stHeader"]{visibility:hidden;height:0}
.block-container{max-width:100%;padding:0 1rem 6rem}
html{scroll-behavior:smooth}
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:3;opacity:.045;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
*{box-sizing:border-box}
.wrap{max-width:1240px;margin:0 auto;padding:0 2rem}
.nn{position:relative}
.nn h1,.nn h2,.nn h3,.nn p{font-family:'Outfit',sans-serif;margin:0}
.nn a,.nn a:hover{text-decoration:none!important}
.nn p{color:var(--muted);line-height:1.6}
.mono{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}

/* Nav: floating glass pill */
.nav{position:absolute;top:18px;left:50%;transform:translateX(-50%);z-index:5;width:max-content;white-space:nowrap;display:flex;gap:.25rem;align-items:center;padding:.35rem .4rem .35rem 1rem;border-radius:999px;background:rgba(14,18,27,.62);border:1px solid rgba(255,255,255,.1);box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 20px 50px -20px rgba(0,0,0,.8);backdrop-filter:blur(18px) saturate(160%);-webkit-backdrop-filter:blur(18px) saturate(160%)}
.nav .mark{font-family:'Outfit',sans-serif;font-weight:700;color:var(--ink);margin-right:.9rem;letter-spacing:-.01em}
.nav a{font-family:'Outfit',sans-serif;color:var(--muted);text-decoration:none;font-size:.9rem;padding:.45rem .8rem;border-radius:999px;transition:color .3s var(--ease),background .3s var(--ease)}
.nav a:hover{color:var(--ink);background:rgba(255,255,255,.06)}
.nav a.go{background:var(--acc);color:var(--acc-ink);font-weight:600}
.nav a.go:hover{background:#7BE3AE;color:var(--acc-ink)}

/* Hero: cinematic center over the real product */
.hero{position:relative;min-height:100dvh;display:grid;place-items:center;text-align:center;overflow:hidden;padding:5rem 0 20rem}
.hero .bg{position:absolute;inset:-10% -5% auto;top:57%;width:110%;opacity:.62;filter:contrast(1.05);transform:perspective(1600px) rotateX(38deg) scale(1.02);transform-origin:top center;mask-image:linear-gradient(to bottom,rgba(0,0,0,.95) 10%,transparent 85%);-webkit-mask-image:linear-gradient(to bottom,rgba(0,0,0,.95) 10%,transparent 85%)}
.hero .wash{position:absolute;inset:0;background:radial-gradient(60% 50% at 50% 30%,rgba(98,211,154,.16),transparent 60%),radial-gradient(40% 40% at 80% 70%,rgba(60,120,200,.14),transparent 60%),linear-gradient(to bottom,rgba(7,9,15,.2),var(--bg) 88%)}
.hero .c{position:relative;max-width:1180px;padding:0 2rem}
.hero h1{font-size:clamp(2.8rem,5.4vw,5.6rem);font-weight:800;line-height:1.02;letter-spacing:-.035em;color:var(--ink);text-wrap:balance}
.hero h1 .pill{display:inline-block;vertical-align:middle;width:1.7em;height:.62em;border-radius:999px;background-size:cover;background-position:12% 40%;margin:0 .12em 0 .08em;box-shadow:0 0 0 2px rgba(255,255,255,.14);transform:translateY(-.06em)}
.hero p{font-size:clamp(1.05rem,1.4vw,1.3rem);max-width:56ch;margin:1.6rem auto 2.4rem;color:#B8C0D0}
.ctas{display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap}
.btn{font-family:'Outfit',sans-serif;font-weight:600;font-size:1.02rem;padding:.9rem 1.5rem;border-radius:999px;text-decoration:none;transition:transform .5s var(--ease),background .3s var(--ease),border-color .3s var(--ease)}
.btn.p{background:var(--acc);color:var(--acc-ink)}
.btn.p:hover{background:#7BE3AE;transform:translateY(-2px);color:var(--acc-ink)}
.btn.g{color:var(--ink);border:1px solid rgba(255,255,255,.22)}
.btn.g:hover{border-color:rgba(255,255,255,.5);transform:translateY(-2px);color:var(--ink)}
.btn:active{transform:translateY(1px)}
.btn:focus-visible{outline:2px solid var(--acc);outline-offset:3px}
.hero .in{opacity:0;transform:translateY(18px);animation:rise 1s var(--ease) forwards}
.hero .in.d1{animation-delay:.1s}.hero .in.d2{animation-delay:.22s}.hero .in.d3{animation-delay:.34s}
.hero .bg{animation:bgin 1.6s var(--ease) forwards;opacity:0}
@keyframes rise{to{opacity:1;transform:none}}
@keyframes bgin{to{opacity:.62}}

/* Marquee */
.marq{overflow:hidden;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:1.1rem 0;margin:2rem 0 0}
.marq .track{display:flex;gap:3.5rem;width:max-content;animation:slide 38s linear infinite;font-family:'Outfit',sans-serif;font-weight:500;color:var(--muted);font-size:1rem;white-space:nowrap}
.marq .track span::after{content:'';display:inline-block;width:6px;height:6px;border-radius:2px;background:var(--acc);margin-left:3.5rem;vertical-align:middle;opacity:.7}
@keyframes slide{to{transform:translateX(-50%)}}

/* Sections */
.sec{padding:9rem 0}
.sec h2{font-size:clamp(2rem,3.6vw,3.4rem);font-weight:700;letter-spacing:-.03em;line-height:1.05;color:var(--ink);max-width:22ch;text-wrap:balance}
.sec .lead{font-size:1.15rem;max-width:58ch;margin-top:1.1rem}

/* Bento: 3 cells, 3x2, dense */
.bento{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,minmax(230px,auto));grid-auto-flow:dense;gap:14px;margin-top:3rem}
.cell{position:relative;border-radius:18px;background:var(--bg2);border:1px solid var(--line);overflow:hidden;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
.cell.a{grid-column:span 2;grid-row:span 2}
.cell img{width:100%;height:100%;object-fit:cover;display:block;transition:transform 1.2s var(--ease)}
.cell:hover img{transform:scale(1.04)}
.cell .cap{position:absolute;left:0;right:0;bottom:0;padding:1.4rem 1.6rem;background:linear-gradient(to top,rgba(7,9,15,.9),transparent)}
.cell .cap h3{font-size:1.35rem;font-weight:600;color:var(--ink)}
.cell .cap p{font-size:.95rem;margin-top:.3rem}
.cell.b,.cell.c{padding:1.6rem}
.cell .big{font-size:clamp(2.6rem,4vw,3.6rem);font-weight:500;color:var(--ink);line-height:1;margin:.2rem 0 .5rem}
.cell .big small{font-size:1.1rem;color:var(--acc);margin-left:.3rem}
.cell h3{font-size:1.15rem;font-weight:600;color:var(--ink)}
.cell p{font-size:.95rem}
.cell.c{background:linear-gradient(160deg,rgba(98,211,154,.14),rgba(14,18,27,0) 60%),var(--bg2)}

/* Pinned chapter with stacking cards */
.chap{display:grid;grid-template-columns:1fr 1fr;gap:4rem;align-items:start}
.chap .pin{position:sticky;top:110px}
.chap .story{font-size:clamp(1.15rem,1.6vw,1.45rem);line-height:1.5;color:var(--ink);margin-top:1.4rem;max-width:34ch}
.chap .story .w{opacity:.18;transition:opacity .2s}
.stack{display:grid;gap:1.2rem}
.card{position:sticky;background:var(--bg2);border:1px solid var(--line);border-radius:18px;padding:1.8rem;box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 30px 60px -30px rgba(0,0,0,.9)}
.card:nth-child(1){top:110px}.card:nth-child(2){top:134px}.card:nth-child(3){top:158px}
.card h3{font-size:1.5rem;font-weight:600;color:var(--ink);letter-spacing:-.02em}
.card p{margin-top:.5rem;font-size:1rem}
.card .q{margin-top:1rem;padding:.9rem 1rem;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid var(--line);font-size:.92rem;color:#C9D0DD}
.card .who{color:var(--acc);font-family:'IBM Plex Mono',monospace;font-size:.82rem;display:block;margin-bottom:.35rem}
.card img{width:100%;border-radius:10px;margin-top:1.1rem;display:block}
.spacer{height:38vh}

/* Action */
.act{text-align:center;padding:10rem 0 6rem}
.act h2{max-width:none;margin:0 auto}
.act .ctas{margin-top:2.2rem}
.foot{border-top:1px solid var(--line);padding:2rem 0 1rem;display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;color:var(--muted);font-family:'Outfit',sans-serif;font-size:.92rem}
.foot a{color:var(--muted);text-decoration:none}
.foot a:hover{color:var(--ink)}

/* Scroll-driven motion (Chromium); everything renders static elsewhere */
@supports (animation-timeline: view()){
  .rv{animation:rv linear both;animation-timeline:view();animation-range:entry 0% entry 45%}
  .grow{animation:grow linear both,dim linear both;animation-timeline:view(),view();animation-range:entry 0% cover 35%,exit 10% exit 100%}
  .chap{timeline-scope:--story}
  .chap .story{view-timeline-name:--story}
  .chap .story .w{animation:lit linear both;animation-timeline:--story}
  .chap .story .w.k0{animation-range:entry 55% cover 42%}.chap .story .w.k1{animation-range:entry 60% cover 46%}.chap .story .w.k2{animation-range:entry 65% cover 50%}.chap .story .w.k3{animation-range:entry 70% cover 54%}.chap .story .w.k4{animation-range:entry 75% cover 58%}.chap .story .w.k5{animation-range:entry 80% cover 62%}.chap .story .w.k6{animation-range:entry 85% cover 66%}.chap .story .w.k7{animation-range:entry 90% cover 70%}
}
@keyframes rv{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scale(.86);opacity:.35}to{transform:none;opacity:1}}
@keyframes dim{to{opacity:.25}}
@keyframes lit{to{opacity:1}}
@media (prefers-reduced-motion: reduce){.hero .in,.hero .bg,.rv,.grow,.marq .track,.chap .story .w{animation:none!important;opacity:1!important;transform:none!important}}
@media (max-width:1100px){[data-testid="stHorizontalBlock"]{flex-wrap:wrap}[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{min-width:100%;flex:1 1 100%}}
@media (max-width:900px){.bento{grid-template-columns:1fr}.cell.a{grid-column:span 1;grid-row:span 1;min-height:320px}.chap{grid-template-columns:1fr}.chap .pin{position:static}.card{position:static}.spacer{display:none}.sec{padding:5rem 0}.nav a:not(.go){display:none}.hero .bg{top:76%}}

/* Tool + results (dark) */
.tool{padding:5rem 0 2rem}
.tool h2{font-family:'Outfit',sans-serif;font-size:clamp(1.8rem,3vw,2.6rem);font-weight:700;letter-spacing:-.03em;color:var(--ink);margin:0 0 .4rem}
.lede{color:var(--muted);font-size:.95rem;margin:0 0 1rem;max-width:60ch}
h3.nn-h{font-family:'Outfit',sans-serif;font-size:1.1rem;font-weight:600;margin:1.2rem 0 .5rem;color:var(--ink)}
.shell{background:rgba(255,255,255,.04);border-radius:18px;padding:5px;border:1px solid var(--line)}
.form{background:var(--bg2);border-radius:14px;padding:1.6rem 1.8rem 1.4rem;box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}
.form h2{font-family:'Outfit',sans-serif;font-size:1.5rem;font-weight:700;margin:0 0 .15rem;color:var(--ink);letter-spacing:-.02em}
.form .sub{font-size:.9rem;color:var(--muted);margin:0 0 1rem}
.form .stamp{float:right;border:1.5px solid var(--danger);color:var(--danger);font-weight:600;font-size:.74rem;padding:.2rem .55rem;border-radius:4px;transform:rotate(-3deg);margin-top:.2rem;font-family:'Outfit',sans-serif}
table.ledger{width:100%;border-collapse:collapse;font-size:.96rem;border:none}
table.ledger td{padding:.42rem .25rem;border:none;border-bottom:1px dotted #2B3446;vertical-align:baseline;color:var(--ink)}
table.ledger td.n{width:3.4rem;font-family:'IBM Plex Mono',monospace;color:var(--muted)}
table.ledger td.amt{width:9rem;text-align:right;font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums}
table.ledger td.cnt{width:6.5rem;text-align:right;font-size:.8rem;color:var(--muted)}
table.ledger tr.part td{border-bottom:1.5px solid var(--muted);padding-top:1rem;font-weight:600}
table.ledger tr.total td{border-bottom:none;padding-top:.55rem;font-weight:600}
table.ledger tr.total td.amt{border-top:1px solid var(--muted);border-bottom:3px double var(--acc);color:var(--acc)}
table.ledger tr.empty td{color:var(--muted)}
.note{border-left:2px solid var(--acc);padding:.45rem 0 .45rem .9rem;margin:0 0 .9rem;font-size:.93rem;line-height:1.5;color:var(--ink)}
.note.bad{border-left-color:var(--danger)}
.note .who{color:var(--muted)}
.note .pick{font-family:'IBM Plex Mono',monospace;color:var(--acc)}
.skel .bar{height:14px;border-radius:4px;margin:.75rem 0;background:linear-gradient(90deg,var(--line) 0%,#243047 45%,var(--line) 90%);background-size:220% 100%;animation:shimmer 1.6s var(--ease) infinite}
@keyframes shimmer{to{background-position:-120% 0}}
.graph{overflow-x:auto}
.graph svg{width:100%;max-width:520px;min-width:420px;height:auto;display:block}
.graph .node{fill:var(--bg2);stroke:var(--line)}
.graph .node.hot{stroke:var(--acc)}
.graph .lbl{font-family:'Outfit',sans-serif;font-size:14px;font-weight:600;fill:var(--ink)}
.graph .ms{font-family:'IBM Plex Mono',monospace;font-size:12px;fill:var(--muted)}
.graph .edge{stroke:var(--muted);stroke-width:1.5;fill:none}
.graph .edge.hot{stroke:var(--acc)}
.graph .edge.cond{stroke-dasharray:5 5}
div.stButton>button[kind="primary"]{background:var(--acc);border:none;color:var(--acc-ink);font-weight:600;padding:.7rem 1.5rem;border-radius:999px;transition:transform .5s var(--ease),background .3s var(--ease)}
div.stButton>button[kind="primary"]:hover,div.stButton>button[kind="primary"]:focus{background:#7BE3AE;color:var(--acc-ink);transform:translateY(-2px)}
div.stButton>button[kind="primary"]:focus-visible{outline:2px solid var(--acc);outline-offset:3px}

/* Phone: the fixed columns above leave the line label 109px */
@media (max-width:600px){table.ledger td.cnt{display:none}table.ledger td.amt{width:6.2rem}table.ledger td.n{width:2.4rem}table.ledger{font-size:.9rem}.form{padding:1.2rem 1rem 1rem}.tool h2{font-size:2rem}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

report = None
report_path = BASE / "results" / "validation.json"
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))


def story_words(text: str) -> str:
    return " ".join(f'<span class="w k{i % 8}">{esc(w)}</span>' for i, w in enumerate(text.split()))


def front() -> str:
    returns = f"{report['checked']['line9']:,}" if report else "3,632"  # returns with a checkable Part I
    l9 = report["rates"]["line9"] if report else "100.0"
    l18 = report["rates"]["line18"] if report else "99.94"
    return f"""
<div class="nn">
<nav class="nav"><span class="mark">NinetyNinety</span><a href="#proof">Proof</a><a href="#how">How it works</a><a class="go" href="#draft-a-return">Draft a return</a></nav>

<section class="hero">
  <img class="bg" src="{asset('draft-page1.jpg')}" alt="">
  <div class="wash"></div>
  <div class="c">
    <h1 class="in">Bank rows in.<br>A drafted <span class="pill" style="background-image:url({asset('draft-partI.jpg')})"></span> 990-EZ out.</h1>
    <p class="in d1">Two Strands agents read every transaction independently. A referee settles their disputes from the IRS instructions. Every line on the form cites the rows and the rule behind it.</p>
    <div class="ctas in d2"><a class="btn p" href="#draft-a-return">Draft a return</a><a class="btn g" href="#how">See how it works</a></div>
  </div>
</section>

<div class="marq"><div class="track">
<span>Built with Strands Agents</span><span>Form 990-EZ, Part I</span><span>{returns} real IRS returns re-computed</span><span>Preparer, Reviewer, Referee</span><span>Every line cites its rows</span><span>Draft, never a filing</span>
<span>Built with Strands Agents</span><span>Form 990-EZ, Part I</span><span>{returns} real IRS returns re-computed</span><span>Preparer, Reviewer, Referee</span><span>Every line cites its rows</span><span>Draft, never a filing</span>
</div></div>

<section class="sec" id="proof"><div class="wrap">
  <h2 class="rv">The arithmetic was checked against the IRS, not against itself.</h2>
  <p class="lead rv">The same code that fills your form rebuilt the totals of {returns} real Form 990-EZ filings from their own line items. The few misses are returns whose stated totals disagree with their own lines.</p>
  <div class="bento">
    <div class="cell a grow"><img src="{asset('draft-page1.jpg')}" style="object-position:50% 22%" alt="The drafted Form 990-EZ, Part I filled from the demo ledger"><div class="cap"><h3>The output is the real IRS form</h3><p>Filled field by field on the official f990ez.pdf, marked DRAFT on every page.</p></div></div>
    <div class="cell b rv"><h3>Line 9, total revenue</h3><div class="big mono">{l9}<small>%</small></div><p>{report['matched']['line9'] if report else '3,632'} of {report['checked']['line9'] if report else '3,632'} filed returns rebuilt exactly.</p></div>
    <div class="cell c rv"><h3>Line 18, excess or deficit</h3><div class="big mono">{l18}<small>%</small></div><p>The model never does arithmetic. Totals are computed in Python from the classified lines.</p></div>
  </div>
</div></section>

<section class="sec" id="how"><div class="wrap chap">
  <div class="pin">
    <h2>Three agents. One graph. No hidden opinions.</h2>
    <p class="story">{story_words("Preparer and Reviewer are parallel entry nodes of one Strands graph. They read the same batch and never see each other. Each is asked to quote the IRS instruction it relied on, and Python checks the quote. When their lines differ, a conditional edge sends the row to the Referee, who decides from the IRS text and shows its reasoning on the form.")}</p>
  </div>
  <div class="stack">
    <div class="card"><span class="who">preparer</span><h3>Reads the ledger like a bookkeeper</h3><p>Every row gets a line, a confidence, and the deciding sentence copied from the IRS instructions through a real tool call.</p><div class="q">"Voluntary transfers where the donor receives nothing of comparable value in return: donations, grants from foundations or government."</div></div>
    <div class="card"><span class="who">reviewer</span><h3>Audits blind</h3><p>Same batch, same tool, zero visibility into the Preparer. Two independent readings of every transaction.</p><img src="{asset('draft-totals.jpg')}" alt="Lines 17 and 18 of the drafted form, total expenses and excess or deficit"></div>
    <div class="card"><span class="who">referee</span><h3>Runs only when they disagree</h3><p>A conditional edge in the graph. The Referee may pick only one of the two disputed lines; its quoted reason is word-checked against the IRS text like every other rule.</p><div class="q">"Line 3 includes membership dues and assessments paid to belong to the organization."</div></div>
    <div class="spacer"></div>
  </div>
</div></section>

<section class="act"><div class="wrap">
  <h2 class="rv">Upload a year of bank rows. Get the form back.</h2>
  <div class="ctas rv"><a class="btn p" href="#draft-a-return">Draft a return</a></div>
</div></section>
<div class="wrap"><div class="foot"><span>Built with Strands Agents for the AWS Agents for Humans hackathon.</span><span><a href="https://github.com/ishal1410/ninetyninety">GitHub, MIT license</a></span></div></div>
</div>
"""


st.markdown(front(), unsafe_allow_html=True)


def graph_svg(trace: list[dict] | None) -> str:
    runs = [t for t in (trace or []) if not t.get("error")]

    def mean_ms(node):
        vals = [t["node_ms"].get(node) for t in runs if t.get("node_ms", {}).get(node) is not None]
        return round(sum(vals) / len(vals)) if vals else None

    referee_runs = sum(1 for t in runs if t.get("referee_ran"))
    tools = sum(t.get("tool_calls", 0) for t in runs)
    model_calls = sum(sum(t.get("model_calls", {}).values()) for t in runs)
    hot = bool(runs) and referee_runs > 0

    def box(name, x, y, sub, is_hot=True):
        return (f'<rect class="node{" hot" if is_hot else ""}" x="{x}" y="{y}" width="160" height="50" rx="8"/>'
                f'<text class="lbl" x="{x + 12}" y="{y + 21}">{name}</text>'
                f'<text class="ms" x="{x + 12}" y="{y + 39}">{sub}</text>')

    if runs:
        task = [f'{len(runs)} batches', f'{tools} tool calls']
        if model_calls:
            task.append(f'{model_calls} model calls, counted by Strands hooks')
        prep = f"{mean_ms('preparer'):,} ms mean" if mean_ms("preparer") else "did not run"
        rev = f"{mean_ms('reviewer'):,} ms mean" if mean_ms("reviewer") else "did not run"
        ref = f"ran {referee_runs} of {len(runs)} batches"
    else:
        task = ["12 rows per batch", "same task to both"]
        prep, rev, ref = "quotes an IRS rule", "never sees Preparer", "quotes the IRS text"
    svg = ['<svg viewBox="0 0 520 230" role="img" aria-label="Strands agent graph">',
           '<text class="lbl" x="6" y="112">Batch task</text>',
           f'<text class="ms" x="6" y="132">{task[0]}</text>',
           f'<text class="ms" x="6" y="150">{task[1]}</text>',
           f'<text class="ms" x="6" y="168">{task[2]}</text>' if len(task) > 2 else '',
           '<path class="edge hot" d="M112 120 C 130 120, 130 70, 150 70"/>',
           '<path class="edge hot" d="M112 120 C 130 120, 130 170, 150 170"/>',
           f'<path class="edge cond{" hot" if hot else ""}" d="M310 70 C 330 70, 330 120, 348 120"/>',
           f'<path class="edge cond{" hot" if hot else ""}" d="M310 170 C 330 170, 330 120, 348 120"/>',
           box("Preparer", 150, 45, prep), box("Reviewer", 150, 145, rev), box("Referee", 348, 95, ref, is_hot=hot),
           '<text class="ms" x="150" y="218">Dashed edges: only when they disagree.</text>',
           '</svg>']
    return '<div class="graph">' + "".join(svg) + "</div>"


pad_l, body, pad_r = st.columns([1, 12, 1])
with body:
    st.markdown('<div class="tool"><h2 id="draft-a-return">Draft a return</h2><p class="lede">Upload a CSV with date, description, amount, '
                'or use the synthetic demo ledger. The agents run live; a 54-row ledger takes a few minutes on the free tier.</p></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        uploaded = st.file_uploader("Transaction ledger as CSV with date, description, amount", type="csv")
        use_demo = st.checkbox("Use the synthetic demo ledger instead", value=uploaded is None)
    with c2:
        org_name = st.text_input("Organization name for the PDF", "DEMO COMMUNITY ORG")
        ein = st.text_input("EIN for the PDF", "00-0000000")
    b1, b2 = st.columns([1, 2])
    go = b1.button("Draft a return", type="primary")
    replay = b2.button("Replay the recorded run (no model calls)",
                       help="Shows the draft recorded on 2026-09-08 from the demo ledger through Google Gemini. "
                            "Same code path, no quota used. Use it if the free tier for the day is spent.")

    MAX_ROWS = 60  # the hosted demo shares one free-tier Gemini project

    def start_job(transactions, skipped):
        """Run the graph on a worker thread so a widget rerun (Enter in a text
        box, a click) cannot kill the run; the next script run resumes it."""
        job = {"done": (0, 1), "form": None, "error": None,
               "loaded": len(transactions), "skipped": skipped}

        def work():
            try:
                job["form"] = prepare_ledger(
                    transactions, max_rows=MAX_ROWS, exclusive=True,
                    progress=lambda done, total: job.__setitem__("done", (done, total)))
            except Exception as error:  # noqa: BLE001 - shown to the user below
                job["error"] = error
        job["thread"] = threading.Thread(target=work, daemon=True)
        job["thread"].start()
        st.session_state["job"] = job
        return job

    job = st.session_state.get("job")
    form, recorded, loaded, skipped = None, False, 0, []
    if (go or replay) and job is None:
        st.session_state.pop("draft", None)  # never show a stale draft under a new run
        with tempfile.TemporaryDirectory(prefix="ninetyninety-") as tmp:
            path = BASE / "fixtures" / "demo_ledger.csv"
            if go and uploaded is not None and not use_demo:
                path = Path(tmp) / "ledger.csv"
                path.write_bytes(uploaded.getvalue())
            try:
                transactions = load_ledger(path, skipped)
            except ValueError as error:
                st.error(f"Could not read the ledger: {error}")
                st.stop()
        if not transactions:
            st.error("No readable rows in the ledger: every row needs a description and an amount.")
            st.stop()
        if replay:
            form, recorded, loaded = load_recorded_run(BASE / "results" / "demo_run.json"), True, len(transactions)
        else:
            job = start_job(transactions, skipped)
    if job is not None:
        bar = st.progress(0.0, text="Preparer and Reviewer are reading the ledger in parallel")
        skeleton = st.empty()
        skeleton.markdown('<div class="shell"><div class="form skel">'
                          + "".join(f'<div class="bar" style="width:{w}%"></div>' for w in (38, 82, 74, 88, 61, 79, 45, 84, 70))
                          + '</div></div>', unsafe_allow_html=True)
        while job["thread"].is_alive():
            done, total = job["done"]
            if done:
                bar.progress(done / total, text=f"Batch {done} of {total} through the Strands graph")
            job["thread"].join(0.5)
        st.session_state.pop("job", None)
        skeleton.empty()
        bar.empty()
        if job["error"] is not None:
            st.error(f"Could not complete the draft: {job['error']}")
            st.stop()
        form, loaded, skipped = job["form"], job["loaded"], job["skipped"]
        exhausted = sum(t.get("rows", 0) for t in form.trace if "exhausted" in str(t.get("error", "")))
        if exhausted:
            st.warning(f"{exhausted} rows were not classified: the free-tier quota for today is spent. "
                       "Use the replay button above to see the recorded run.")
    if form is not None:
        pdf_bytes, pdf_error = None, None
        try:
            with tempfile.TemporaryDirectory(prefix="ninetyninety-") as tmp:
                pdf = fill_form(form, download_form(BASE / "data" / "f990ez.pdf"),
                                Path(tmp) / "draft.pdf", org_name, ein)
                pdf_bytes = pdf.read_bytes()
        except Exception as error:  # noqa: BLE001
            pdf_error = str(error)
        # Kept across reruns: the download button reruns the script and st.button
        # is False on that rerun, so without this the whole draft would vanish.
        st.session_state["draft"] = {"form": form, "skipped": skipped, "loaded": loaded,
                                     "pdf": pdf_bytes, "pdf_error": pdf_error, "recorded": recorded}

    draft = st.session_state.get("draft")
    if draft:
        form, skipped = draft["form"], draft["skipped"]
        if draft.get("recorded"):
            st.caption("Recorded on 2026-09-08 through Google Gemini; live runs use the same code.")
        st.markdown(
            f'<p class="lede" style="margin-top:.6rem">Read {draft["loaded"]} transactions'
            + (f", skipped {len(skipped)} with unreadable amounts." if skipped else ".") + "</p>",
            unsafe_allow_html=True)
        left, right = st.columns([3, 2], gap="large")

        with left:
            rows = ['<table class="ledger">']
            for part, lines, total_key, total_label in (
                    ("Revenue", REVENUE_LINES, "line9", "Total revenue"),
                    ("Expenses", EXPENSE_LINES, "line17", "Total expenses")):
                rows.append(f'<tr class="part"><td class="n"></td><td>{part}</td>'
                            f'<td class="cnt"></td><td class="amt"></td></tr>')
                for line in lines:
                    result = form.lines.get(line.number)
                    if result is None:
                        rows.append(f'<tr class="empty"><td class="n">{line.number}</td><td>{esc(line.label)}</td>'
                                    f'<td class="cnt"></td><td class="amt"></td></tr>')
                    else:
                        n = len(result.transactions)
                        rows.append(f'<tr><td class="n">{line.number}</td><td>{esc(line.label)}</td>'
                                    f'<td class="cnt">{n} row{"s" if n != 1 else ""}</td>'
                                    f'<td class="amt">{money(result.amount)}</td></tr>')
                rows.append(f'<tr class="total"><td class="n">{total_key[4:]}</td><td>{total_label}</td>'
                            f'<td class="cnt"></td><td class="amt">{money(form.totals[total_key])}</td></tr>')
            rows.append(f'<tr class="total"><td class="n">18</td><td>Excess or (deficit) for the year</td>'
                        f'<td class="cnt"></td><td class="amt">{money(form.totals["line18"])}</td></tr>')
            rows.append("</table>")
            st.markdown(
                '<div class="shell"><div class="form"><span class="stamp">DRAFT, NOT A FILING</span>'
                '<h2>Form 990-EZ, Part I</h2>'
                '<p class="sub">Totals are computed in Python from the classified lines. '
                'The model never does arithmetic.</p>'
                + "".join(rows) + "</div></div>",
                unsafe_allow_html=True)

            if draft["pdf"] is not None:
                st.download_button("Download the PDF, marked DRAFT",
                                   draft["pdf"], file_name="990-EZ-DRAFT.pdf",
                                   mime="application/pdf")
            else:
                st.info(f"PDF not produced: {draft['pdf_error']}")

            st.markdown('<h3 class="nn-h">Where each line came from</h3>', unsafe_allow_html=True)
            for number in sorted(form.lines, key=form_order):
                result = form.lines[number]
                with st.expander(f"Line {number}, {line_by_number(number).label}: "
                                 f"{money(result.amount)} from {len(result.transactions)} rows"):
                    for c in result.transactions:
                        st.markdown(
                            f'<div class="note"><span class="who">row {c["source_row"]}, {esc(c["date"])}</span>'
                            f' &nbsp;{esc(c["description"])} &nbsp;<span class="pick">{money(c["amount"])}</span>'
                            f'<br><span class="who">Rule:</span> {esc(c["rule"])}</div>',
                            unsafe_allow_html=True)

        with right:
            st.markdown('<h3 class="nn-h">The graph that ran</h3>', unsafe_allow_html=True)
            st.markdown(graph_svg(form.trace), unsafe_allow_html=True)

            st.markdown(f'<h3 class="nn-h">Agent disagreements, {len(form.disagreements)}</h3>'
                        '<p class="lede">The Reviewer never sees the Preparer, so these are two '
                        'independent readings. The Referee runs only when they differ; its reason is '
                        'checked against the IRS text.</p>', unsafe_allow_html=True)
            for item in form.disagreements:
                referee = (f'<span class="who">Referee</span> <span class="pick">line {esc(item["referee"])}</span>: '
                           f'{esc(item["referee_reason"])}' if item["referee"]
                           else '<span class="who">Referee did not rule; the Preparer&rsquo;s line is used.</span>')
                st.markdown(
                    f'<div class="note"><b>row {item["source_row"]}</b> {esc(item["description"])}<br>'
                    f'<span class="who">Preparer</span> <span class="pick">line {esc(item["preparer"])}</span>: {esc(item["preparer_rule"])}<br>'
                    f'<span class="who">Reviewer</span> <span class="pick">line {esc(item["reviewer"])}</span>: {esc(item["reviewer_rule"])}<br>'
                    f'{referee}<br><span class="who">On the form:</span> <span class="pick">line {esc(item["used"])}</span></div>',
                    unsafe_allow_html=True)
            if not form.disagreements:
                st.markdown('<div class="note">Preparer and Reviewer agreed on every row.</div>',
                            unsafe_allow_html=True)

            st.markdown(f'<h3 class="nn-h">Low confidence, {len(form.low_confidence)}</h3>',
                        unsafe_allow_html=True)
            for item in form.low_confidence:
                st.markdown(f'<div class="note"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                            f'<span class="pick">line {item["line"]}</span><br><span class="who">{esc(item["note"])}</span></div>',
                            unsafe_allow_html=True)
            if form.ungrounded:
                st.markdown(f'<h3 class="nn-h">Rule not found in the IRS guidance, {len(form.ungrounded)}</h3>',
                            unsafe_allow_html=True)
                for item in form.ungrounded:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> <span class="pick">line {item["line"]}</span>'
                                f'<br><span class="who">Quoted rule:</span> {esc(item["rule"][:160])}</div>',
                                unsafe_allow_html=True)
            if form.unreviewed:
                st.markdown(f'<h3 class="nn-h">Single opinion only, {len(form.unreviewed)}</h3>',
                            unsafe_allow_html=True)
                for item in form.unreviewed:
                    st.markdown(f'<div class="note"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                                f'<span class="pick">line {item["line"]}</span><br><span class="who">{esc(item["note"])}</span></div>',
                                unsafe_allow_html=True)
            if form.unclassified:
                st.markdown(f'<h3 class="nn-h">Not classified, {len(form.unclassified)}</h3>',
                            unsafe_allow_html=True)
                for item in form.unclassified:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                                f'<span class="pick">{money(item["amount"])}</span><br><span class="who">{esc(item["error"])}</span></div>',
                                unsafe_allow_html=True)
            if skipped:
                st.markdown(f'<h3 class="nn-h">Rows with unreadable amounts, {len(skipped)}</h3>',
                            unsafe_allow_html=True)
                for item in skipped:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> {esc(item["description"])}'
                                f'<br><span class="who">Amount as written:</span> {esc(item["amount_raw"])}</div>',
                                unsafe_allow_html=True)

            with st.expander(f"Full Strands trace, {len(form.trace)} graph runs"):
                st.dataframe(trace_rows(form.trace), width="stretch", hide_index=True)
