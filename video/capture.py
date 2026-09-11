"""Record each shot of the demo from the REAL hosted app and the real pages.

One shot = one browser context = one webm in clips/. Durations come from
durations.json (the narration), so picture and voice line up without trimming.

  python capture.py            # every shot
  python capture.py s04 s05    # only those
"""
import json, pathlib, shutil, sys, time

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
REPO = HERE.parent
CLIPS = HERE / "clips"
APP = "https://ninetyninety.streamlit.app/?embed=true"
PAGES = "https://ishal1410.github.io/ninetyninety"
DUR = json.loads((HERE / "durations.json").read_text(encoding="utf-8"))
PAD = 0.6          # tail so the picture never ends before the sentence does
FRAME = "iframe[src*='/~/+/']"

# a real pointer: playwright's mouse moves fire events but draw nothing
CURSOR = """
(() => {
  if (window.__cur) return;
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;'
    + 'margin:-11px 0 0 -11px;border-radius:50%;pointer-events:none;left:-99px;top:-99px;'
    + 'background:rgba(30,107,78,.28);border:2px solid #1E6B4E;'
    + 'box-shadow:0 0 0 4px rgba(30,107,78,.12);transition:transform .12s ease-out';
  document.documentElement.appendChild(d);
  window.__cur = d;
  addEventListener('mousemove', e => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', () => d.style.transform = 'scale(.7)', true);
  addEventListener('mouseup', () => d.style.transform = 'scale(1)', true);
})();
"""
# hide the embed footer and any host chrome; zoom so the app fills a 1080p frame
CHROME_OFF = """
(() => {
  const s = document.createElement('style');
  s.textContent = `footer, [class*="viewerBadge"], [data-testid="stStatusWidget"],
    [data-testid="stToolbar"], .stAppEmbeddingFooter, [data-testid="stBottomBlockContainer"]
    { display:none !important; }
    html { zoom: 1.5; }`;
  document.head.appendChild(s);
})();
"""


T0 = {}


OUTER_OFF = """
(() => {
  const s = document.createElement('style');
  s.textContent = `footer, [class*="viewerBadge"], a[href*="streamlit.io"],
    [class*="_hostedName_"] { display:none !important; }
    html, body { background:#F7F8FA !important; overflow:hidden !important; }
    iframe { border:0 !important; }`;
  document.head.appendChild(s);
})();
"""


def context(pw, name):
    b = pw.chromium.launch(headless=True, args=["--force-color-profile=srgb",
                                                "--font-render-hinting=none"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1,
                        record_video_dir=str(CLIPS / "raw"),
                        record_video_size={"width": 1920, "height": 1080},
                        accept_downloads=True)
    ctx.add_init_script(CURSOR)
    T0[name] = time.time()
    T0["name"] = name
    T0.pop("mark", None)
    return b, ctx


def mark(page):
    """Everything before this is page load; build.sh trims it off."""
    T0["mark"] = round(time.time() - T0[T0["name"]], 2)


def finish(b, ctx, page, name):
    """Close the context so playwright flushes the webm, then rename it."""
    src = page.video.path()
    ctx.close()
    b.close()
    dest = CLIPS / f"{name}.webm"
    dest.unlink(missing_ok=True)
    shutil.move(src, dest)
    (CLIPS / f"{name}.json").write_text(json.dumps({"trim": T0.get("mark", 0.0)}), encoding="utf-8")
    print(f"  saved {dest.name} ({dest.stat().st_size // 1024} KB)")


def fill_to(page, name):
    """Keep recording live until the shot covers its whole narration line."""
    target = DUR[name] + PAD
    while True:
        elapsed = (time.time() - T0[name]) - T0.get("mark", 0.0)
        if elapsed >= target:
            break
        page.wait_for_timeout(min(500, int((target - elapsed) * 1000) + 50))
    print(f"   covered {elapsed:.1f}s of {target:.1f}s")


def hold(page, seconds):
    page.wait_for_timeout(int(seconds * 1000))


def glide(page, x, y, steps=26):
    """Move the pointer the way a hand does, not in one jump."""
    page.mouse.move(x, y, steps=steps)


def open_app(page, wait=18):
    page.goto(APP, wait_until="load", timeout=180000)
    fr = page.frame_locator(FRAME)
    fr.locator("[data-testid='stAppViewContainer']").wait_for(state="attached", timeout=180000)
    page.wait_for_timeout(int(wait * 1000))
    page.frame(url=lambda u: "/~/+/" in u).evaluate(CHROME_OFF)
    page.frame(url=lambda u: "/~/+/" in u).evaluate(CURSOR)
    page.evaluate(OUTER_OFF)
    page.wait_for_timeout(900)
    mark(page)
    return fr


def app_frame(page):
    return page.frame(url=lambda u: "/~/+/" in u)


def scroll(page, dy, steps=30, pause=0.035):
    """Smooth wheel scroll inside the streamlit main container."""
    step = dy / steps
    for _ in range(steps):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(int(pause * 1000))


# --------------------------------------------------------------- shot 1 ----
def s01(pw):
    """The problem. Landing hero, held, then the first line of the argument."""
    b, ctx = context(pw, "s01")
    page = ctx.new_page()
    page.goto(PAGES + "/", wait_until="load", timeout=120000)
    page.evaluate(CURSOR)
    page.wait_for_timeout(1500)
    mark(page)
    hold(page, 2.0)
    glide(page, 960, 620)
    hold(page, DUR["s01"] * 0.62)
    scroll(page, 520, steps=44, pause=0.05)
    fill_to(page, "s01")
    finish(b, ctx, page, "s01")


# --------------------------------------------------------------- shot 2 ----
def s02(pw):
    """Who it is for. Land on 'How it works', step 1 visible."""
    b, ctx = context(pw, "s02")
    page = ctx.new_page()
    page.goto(PAGES + "/", wait_until="load", timeout=120000)
    page.evaluate(CURSOR)
    page.evaluate("window.scrollTo(0, 520)")
    page.wait_for_timeout(1200)
    mark(page)
    hold(page, 1.2)
    scroll(page, 900, steps=50, pause=0.05)
    glide(page, 700, 500)
    fill_to(page, "s02")
    finish(b, ctx, page, "s02")


SHOTS = {}

def fscroll(page, to_px, seconds=1.6):
    """Smoothly scroll streamlit's main container to an absolute offset."""
    fr = app_frame(page)
    fr.evaluate("""([to, ms]) => {
        const el = document.querySelector('section[data-testid="stMain"]') || document.scrollingElement;
        const from = el.scrollTop, dt = ms, t0 = performance.now();
        return new Promise(res => {
            function step(t) {
                const k = Math.min(1, (t - t0) / dt);
                const e = k < .5 ? 4*k*k*k : 1 - Math.pow(-2*k + 2, 3) / 2;   // easeInOutCubic
                el.scrollTop = from + (to - from) * e;
                k < 1 ? requestAnimationFrame(step) : res();
            }
            requestAnimationFrame(step);
        });
    }""", [to_px, int(seconds * 1000)])


def to_text(page, needle, seconds=1.6, offset=-160):
    """Scroll until the element containing `needle` sits near the top."""
    fr = app_frame(page)
    y = fr.evaluate("""(needle) => {
        const el = document.querySelector('section[data-testid="stMain"]') || document.scrollingElement;
        const hit = [...document.querySelectorAll('h2,h3,p,summary,div,span,label')]
            .find(n => n.textContent.trim().startsWith(needle));
        if (!hit) return null;
        const r = hit.getBoundingClientRect();
        return el.scrollTop + r.top;
    }""", needle)
    if y is None:
        print(f"   !! text not found: {needle!r}")
        return False
    fscroll(page, max(0, y + offset), seconds)
    return True


def point_at(page, fr_locator, dwell=1.1):
    box = fr_locator.bounding_box()
    if not box:
        return
    glide(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    hold(page, dwell)


def replay(page, fr):
    btn = fr.locator("button:has-text('Replay'):visible").first
    point_at(page, btn, 0.5)
    btn.click()
    page.wait_for_timeout(9000)


# --------------------------------------------------------------- shot 4 ----
def s04(pw):
    """The Strands graph that ran: the trace, five runs, referee on batch five."""
    b, ctx = context(pw, "s04")
    page = ctx.new_page()
    fr = open_app(page)
    replay(page, fr)
    to_text(page, "The graph that ran", 1.8)
    hold(page, 4.0)
    exp = fr.locator("summary:has-text('Full Strands trace')").first
    point_at(page, exp, 0.8)
    exp.click()
    hold(page, 2.5)
    to_text(page, "Full Strands trace", 1.2, offset=-90)
    hold(page, 6.0)
    rows = fr.locator("[data-testid='stDataFrame'] [role='row'], table tr")
    n = rows.count()
    if n:
        point_at(page, rows.nth(min(n - 1, 5)), 3.0)
    fill_to(page, "s04")
    finish(b, ctx, page, "s04")



# --------------------------------------------------------------- shot 3 ----
def s03(pw):
    """The real upload and the real click: a live run actually starts here."""
    b, ctx = context(pw, "s03")
    page = ctx.new_page()
    fr = open_app(page)
    to_text(page, "Draft a return", 1.4)
    hold(page, 1.2)
    drop = fr.get_by_test_id("stFileUploaderDropzone")
    point_at(page, drop, 0.5)
    fr.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(
        str(REPO / "fixtures" / "demo_ledger.csv"))
    page.wait_for_timeout(2500)
    name = fr.locator("text=demo_ledger.csv").first
    print("   upload shows filename:", name.count() > 0)
    hold(page, 1.6)
    box = fr.locator("label:has-text('Use the synthetic demo ledger instead')").first
    if box.count():
        checked = fr.locator("input[type='checkbox']").first.is_checked()
        print("   demo box still ticked:", checked)
        if checked:
            point_at(page, box, 0.4)
            box.click()
            page.wait_for_timeout(1200)
    go = fr.locator("button:has-text('Draft a return'):visible").first
    point_at(page, go, 1.0)
    go.click()                      # a real run starts: this is not a mock
    page.wait_for_timeout(1500)
    bar = fr.locator("[data-testid='stProgress']").count()
    said = fr.get_by_text("Preparer and Reviewer").count()
    busy = fr.get_by_text("another draft is running").count()
    print(f"   progress bar={bar} caption={said} locked_out={busy}")
    hold(page, 6.0)
    fill_to(page, "s03")
    finish(b, ctx, page, "s03")


# --------------------------------------------------------------- shot 5 ----
def s05(pw):
    """One disagreement, opened: preparer, reviewer, referee, and what shipped."""
    b, ctx = context(pw, "s05")
    page = ctx.new_page()
    fr = open_app(page)
    replay(page, fr)
    to_text(page, "Adjudication record", 1.8)
    hold(page, 3.0)
    for needle, dwell in (("PREPARER", 3.4), ("REVIEWER", 3.4), ("REFEREE", 3.4)):
        col = fr.locator(f"text={needle}").first
        point_at(page, col, dwell)
    onform = fr.locator("text=ON THE FORM").first
    point_at(page, onform, 3.0)
    to_text(page, "Where each line came from", 1.6)
    hold(page, 1.6)
    exp = fr.locator("summary:has-text('Line 1, Contributions')").first
    point_at(page, exp, 0.8)
    exp.click()
    hold(page, 2.0)
    to_text(page, "Line 1, Contributions", 1.0, offset=-120)
    fill_to(page, "s05")
    finish(b, ctx, page, "s05")


# --------------------------------------------------------------- shot 6 ----
def s06(pw):
    """The filled IRS form itself: lines 9, 17, 18, and the DRAFT notice."""
    b, ctx = context(pw, "s06")
    page = ctx.new_page()
    page.goto((HERE / "scenes" / "pdf.html").as_uri(), wait_until="load", timeout=60000)
    page.evaluate(CURSOR)
    page.wait_for_timeout(1200)
    mark(page)
    hold(page, 1.4)
    page.evaluate("setView(.62, -240, 1800)")          # into Part I
    hold(page, 2.6)
    for fy, dwell in ((0.674, 3.0), (0.815, 2.6), (0.840, 2.6)):   # lines 9, 17, 18
        pt = page.evaluate("([fx, fy]) => ptAt(fx, fy)", [0.90, fy])
        glide(page, pt["x"], pt["y"]); hold(page, dwell)
    page.evaluate("setView(.49, 0, 1500)")             # back out to the whole page
    hold(page, 2.2)
    page.evaluate("setView(.85, -20, 1400)")           # up to the red DRAFT notice
    hold(page, 1.2)
    pt = page.evaluate("([fx, fy]) => ptAt(fx, fy)", [0.45, 0.020])
    glide(page, pt["x"], pt["y"]); hold(page, 2.6)
    page.evaluate("showPage(2); setView(.49, 0, 1200)")
    fill_to(page, "s06")
    finish(b, ctx, page, "s06")


# --------------------------------------------------------------- shot 7 ----
def s07(pw):
    """Footing checked against real filed returns."""
    b, ctx = context(pw, "s07")
    page = ctx.new_page()
    page.goto(PAGES + "/technical.html", wait_until="load", timeout=120000)
    page.evaluate(CURSOR)
    page.wait_for_timeout(1200)
    mark(page)
    found = page.evaluate("""() => {
        const h = [...document.querySelectorAll('h2,h3')]
            .find(n => /checked against filed returns/i.test(n.textContent));
        if (!h) return null;
        return h.getBoundingClientRect().top + scrollY - 120;
    }""")
    if found is None:
        print("   !! accuracy section not found on technical.html")
        found = 1200
    page.evaluate("([y]) => window.scrollTo({top: y, behavior: 'smooth'})", [found])
    hold(page, 3.0)
    for y in (430, 520, 600):
        glide(page, 900, y); hold(page, 3.2)
    page.evaluate("window.scrollBy({top: 420, behavior: 'smooth'})")
    fill_to(page, "s07")
    finish(b, ctx, page, "s07")


# --------------------------------------------------------------- shot 8 ----
def s08(pw):
    """The architecture diagram."""
    b, ctx = context(pw, "s08")
    page = ctx.new_page()
    page.goto((HERE / "scenes" / "architecture.html").as_uri(), wait_until="load", timeout=60000)
    page.evaluate(CURSOR)
    page.wait_for_timeout(1000)
    mark(page)
    hold(page, 2.0)
    page.evaluate("setView(1.5, 120, 180, 1800)")   # the graph half
    hold(page, 6.0)
    page.evaluate("setView(1.5, 60, -220, 1600)")   # the python layer
    hold(page, 5.0)
    page.evaluate("setView(1, 0, 0, 1400)")
    fill_to(page, "s08")
    finish(b, ctx, page, "s08")


# --------------------------------------------------------------- shot 9 ----
def s09(pw):
    """Close on the public repo."""
    b, ctx = context(pw, "s09")
    page = ctx.new_page()
    page.goto("https://github.com/ishal1410/ninetyninety", wait_until="load", timeout=120000)
    page.evaluate(CURSOR)
    page.wait_for_timeout(2000)
    mark(page)
    hold(page, 2.5)
    glide(page, 1500, 330); hold(page, 3.0)          # the About sidebar, MIT licence
    page.evaluate("window.scrollTo({top: 700, behavior: 'smooth'})")
    hold(page, 4.0)
    glide(page, 700, 420); hold(page, 3.5)
    page.evaluate("window.scrollTo({top: 1150, behavior: 'smooth'})")
    fill_to(page, "s09")
    finish(b, ctx, page, "s09")


SHOTS = {"s01": s01, "s02": s02, "s03": s03, "s04": s04, "s05": s05,
         "s06": s06, "s07": s07, "s08": s08, "s09": s09}


if __name__ == "__main__":
    CLIPS.mkdir(exist_ok=True)
    (CLIPS / "raw").mkdir(exist_ok=True)
    want = sys.argv[1:] or list(SHOTS)
    with sync_playwright() as pw:
        for name in want:
            if name not in SHOTS:
                print(f"  skip {name}: not defined yet"); continue
            t = time.time()
            print(f"== {name} (target {DUR[name] + PAD:.1f}s)")
            SHOTS[name](pw)
            print(f"   took {time.time() - t:.1f}s")
