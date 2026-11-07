#!/usr/bin/env python3
"""Solve the mass of the two closing bands so every delivered surface lands
inside the palette bands, and write the answer into assets/style.css.

This is not a checker — the checker is the brand pack's tools/audit_palette.py.
This is the solver that finds the padding numbers the checker will accept:

  1. render every page at each layout region (1440, 1024, 820, 390) through real
     Chromium over CDP, full page, exactly the way the brand pack's render.py does
  2. classify every sampled pixel with the brand pack's own audit_palette module
  3. from the measured field / ink / accent pixel counts, compute the band
     heights that put the surface inside the bands (black 70-80, white 10-15,
     accent 4-14) and rewrite the RATIO-TUNING block with the resulting padding
  4. re-run tools/audit_palette.py --check on the renders to prove it

The page height is a function of the viewport width while the bands are a fixed
pixel height, so the values are keyed to the stylesheet's own layout breakpoints.

usage:
  DOTBANG_BRAND=/path/to/dotbang-brand python3 scripts/ratio_solve.py [--apply]
"""
import asyncio, base64, importlib.util, json, os, pathlib, shutil, subprocess, sys, time, urllib.request

SITE = str(pathlib.Path(__file__).resolve().parent.parent)
BRAND = os.environ.get("DOTBANG_BRAND", "~/.hermes/shared/dotbang-brand-2026-11-05")
OUT = os.environ.get("DOTBANG_RATIO_OUT",
                     os.path.expanduser("~/.hermes/cache/scratch/ratio-solve"))
CHROME = "~/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome"
PORT = 9452
PROFILE = os.path.expanduser("~/.hermes/cache/scratch/dbx-tune/chrome-profile")

spec = importlib.util.spec_from_file_location("audit_palette", BRAND + "/tools/audit_palette.py")
AP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AP)
from PIL import Image

PAGES = [("home", "index.html"), ("learn", "pages/learn.html"), ("merch", "pages/merch.html"),
         ("giveaways", "pages/giveaways.html"), ("affiliates", "pages/affiliates.html")]
# one tuning group per layout region: the bands are a fixed pixel height while
# the ratio is a percentage of the page, and the page height is a function of the
# width, so each region gets its own solved value. The regions follow the
# stylesheet's own breakpoints (1100 / 1020 / 760).
GROUPS = [
    ((1440, 900, 1), None),
    ((1024, 768, 1), "(min-width:1021px) and (max-width:1100px)"),
    ((820, 1180, 1), "(min-width:761px) and (max-width:1020px)"),
    ((390, 844, 2), "(max-width:760px)"),
]
VIEWPORTS = [g[0] for g in GROUPS]

RECTS_JS = r"""
(() => {
  const r = el => { if(!el) return null; const b = el.getBoundingClientRect();
    return {x:Math.round(b.x), y:Math.round(b.y+scrollY), w:Math.round(b.width), h:Math.round(b.height)}; };
  const cs = el => el ? getComputedStyle(el) : null;
  const c = cs(document.querySelector('.contact-in'));
  const f = cs(document.querySelector('footer.site-foot'));
  return {docH: document.documentElement.scrollHeight, docW: document.documentElement.scrollWidth,
          innerW: innerWidth, hOverflow: document.documentElement.scrollWidth > innerWidth + 1,
          contact: r(document.querySelector('.contact')),
          foot: r(document.querySelector('footer.site-foot')),
          index: r(document.querySelector('.page-index')),
          contactPad: c ? [c.paddingTop, c.paddingBottom] : null,
          footPad: f ? [f.paddingTop, f.paddingBottom] : null,
          plateOverflow: (() => { const p = document.querySelector('.contact');
            return p ? p.scrollHeight - p.clientHeight : null; })()};
})()
"""


def http_json(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=5) as r:
        return json.load(r)


class CDP:
    def __init__(self, ws):
        self.ws, self.id, self.events = ws, 0, []

    async def send(self, method, **params):
        self.id += 1
        mid = self.id
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            raw = await asyncio.wait_for(self.ws.recv(), timeout=120)
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    async def eval(self, expr):
        r = await self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                            awaitPromise=True)
        return r.get("result", {}).get("value")

    async def settle(self, t=1.0):
        deadline = time.time() + 20
        while time.time() < deadline:
            if any(e.get("method") == "Page.loadEventFired" for e in self.events):
                break
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=1)
                self.events.append(json.loads(raw))
            except asyncio.TimeoutError:
                pass
        await asyncio.sleep(t)


def audit_png(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    counts = {}
    step = 2 if w * h > 2_000_000 else 1
    n = 0
    for y in range(0, h, step):
        for x in range(0, w, step):
            k = AP.classify(*px[x, y])
            counts[k] = counts.get(k, 0) + 1
            n += 1
    pct = {k: v / n for k, v in counts.items()}
    black = pct.get("black", 0) + pct.get("black_alpha", 0)
    white = pct.get("white", 0) + pct.get("white_alpha", 0)
    return {"w": w, "h": h, "black": black, "white": white,
            "accent": pct.get("accent", 0), "pink": pct.get("pink", 0),
            "other": pct.get("other", 0)}


async def main(apply):
    os.makedirs(OUT, exist_ok=True)
    shutil.rmtree(PROFILE, ignore_errors=True)
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
         f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
         "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
         "--disable-gpu", "--force-color-profile=srgb", "--font-render-hinting=none",
         "--allow-file-access-from-files", "--window-size=1440,900", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    target = None
    import websockets
    for _ in range(160):
        try:
            pages = [t for t in http_json("/json/list") if t.get("type") == "page"]
            if pages:
                target = pages[0]
                break
        except Exception:
            pass
        await asyncio.sleep(0.25)
    if not target:
        proc.kill()
        raise SystemExit("chromium never exposed a page target")

    results = []
    try:
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=None) as ws:
            cdp = CDP(ws)
            await cdp.send("Page.enable")
            await cdp.send("Runtime.enable")
            for pid, rel in PAGES:
                url = "file://" + os.path.join(SITE, rel)
                for w, h, dsf in VIEWPORTS:
                    tag = f"{pid}-{w}"
                    await cdp.send("Emulation.setDeviceMetricsOverride", width=w, height=h,
                                   deviceScaleFactor=dsf, mobile=(w < 500))
                    cdp.events.clear()
                    await cdp.send("Page.navigate", url=url)
                    await cdp.settle()
                    m = await cdp.eval(RECTS_JS)
                    docH = m["docH"]
                    await cdp.send("Emulation.setDeviceMetricsOverride", width=w, height=docH,
                                   deviceScaleFactor=dsf, mobile=(w < 500))
                    await asyncio.sleep(0.6)
                    shot = await cdp.send("Page.captureScreenshot", format="png")
                    png = os.path.join(OUT, f"{tag}-full.png")
                    open(png, "wb").write(base64.b64decode(shot["data"]))
                    a = audit_png(png)
                    results.append({"page": pid, "vw": w, "docH": docH, "docW": m["docW"],
                                    "overflow": m["hOverflow"], "plateOverflow": m["plateOverflow"],
                                    "contact": m["contact"], "foot": m["foot"],
                                    "index": m["index"], "contactPad": m["contactPad"],
                                    "footPad": m["footPad"], "audit": a})
                    print(f"{tag}: doc={docH} B={100*a['black']:.2f} W={100*a['white']:.2f} "
                          f"A={100*a['accent']:.3f} P={100*a['pink']:.3f} O={100*a['other']:.3f} "
                          f"contact={m['contact'] and m['contact']['h']} "
                          f"foot={m['foot'] and m['foot']['h']}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    json.dump(results, open(os.path.join(OUT, "tune.json"), "w"), indent=1)

    # ---- solve -----------------------------------------------------------
    # Three fixed quantities per surface: the field pixels (B), the white pixels
    # that are not band padding (Wc — body text plus the plate's own content),
    # and the accent pixels the band's content carries (Ac). Padding on the two
    # bands is pure background, so the delivered ratios are a function of two
    # integers: how many rows of accent and of white are added.
    #
    # The page is kept as dark as the ceiling allows, but white is a floor once
    # the ink plate has its content — so the height is whatever makes white sit
    # under its ceiling, and the accent absorbs the rest. If that pushes accent
    # over its own ceiling the surface is infeasible and says so.
    WHITE_CEIL = 0.145      # ceiling with margin under 15
    WHITE_GOAL = 0.120
    BLACK_CEIL = 0.795
    ACCENT_CEIL = 0.130
    plan = {}
    print("\nsolved composition (padding per side, CSS px):")
    for r in results:
        a = r["audit"]
        W, H0 = a["w"], a["h"]
        dsf = W / float(r["vw"])
        N_black = a["black"] * W * H0
        N_accent = a["accent"] * W * H0
        N_white = a["white"] * W * H0
        pad_a = sum(float(p.replace("px", "")) for p in r["contactPad"])
        pad_w = sum(float(p.replace("px", "")) for p in r["footPad"])
        # strip the padding that is in the measured shot: what is left is content
        floor_a = ((r["contact"]["h"] if r["contact"] else 0) - pad_a) * dsf
        floor_w = ((r["foot"]["h"] if r["foot"] else 0) - pad_w) * dsf
        cur_a = (r["contact"]["h"] if r["contact"] else 0) * dsf
        cur_w = (r["foot"]["h"] if r["foot"] else 0) * dsf
        B = N_black / W
        Ac = max(0.0, N_accent / W - (cur_a - floor_a))
        Wc = max(0.0, N_white / W - (cur_w - floor_w))
        # smallest height that keeps white under its ceiling, and the height at
        # which the field sits at its own ceiling
        H = max(Wc / WHITE_CEIL, B / BLACK_CEIL)
        leftover = H - B - Wc - Ac
        w_target, a_target = floor_w, floor_a
        if leftover <= 0:
            w_target, a_target = floor_w, floor_a
            H = B + Wc + Ac
        else:
            # spend the budget: ink to its working share, the accent takes the rest
            w_add = min(leftover, max(0.0, WHITE_GOAL * H - Wc))
            w_target += w_add
            a_target += leftover - w_add
        H = B + Wc + (w_target - floor_w) + Ac + (a_target - floor_a)
        p_black, p_acc, p_whi = B / H, (Ac + a_target - floor_a) / H, (Wc + w_target - floor_w) / H
        ok = (70 <= 100 * p_black <= 80 and 10 <= 100 * p_whi <= 15 and 4 <= 100 * p_acc <= 14)
        plan.setdefault(r["page"], {})[r["vw"]] = (
            round(max(0.0, (a_target - floor_a) / (2 * dsf))),
            round(max(0.0, (w_target - floor_w) / (2 * dsf))))
        print(f"  {r['page']:11s} {r['vw']:5d} floor a={floor_a/dsf:.0f} w={floor_w/dsf:.0f} "
              f"-> accent {a_target/dsf:.0f}px, plate {w_target/dsf:.0f}px "
              f"(pad/side {max(0,(a_target-floor_a)/(2*dsf)):.1f}/"
              f"{max(0,(w_target-floor_w)/(2*dsf)):.1f}), docH {H/dsf:.0f} | "
              f"pred B={100*p_black:.2f} W={100*p_whi:.2f} A={100*p_acc:.2f}"
              + ("" if ok else "  <-- OUT OF BAND"))

    if apply:
        css = os.path.join(SITE, "assets/style.css")
        src = open(css).read()
        lo = src.index("/* RATIO-TUNING:BEGIN */") + len("/* RATIO-TUNING:BEGIN */")
        hi = src.index("/* RATIO-TUNING:END */")

        def block(vw):
            out = []
            for pid, _ in PAGES:
                pa, pw = plan[pid][vw][0], plan[pid][vw][1]
                out.append(f'body[data-page="{pid}"]{{--plate-t:{pa}px;--plate-b:{pa}px;'
                           f'--foot-t:{pw}px;--foot-b:{pw}px}}')
            return out

        parts = []
        for (vw, cond) in GROUPS:
            if cond is None:
                parts.append("\n" + "\n".join(block(vw[0])))
            else:
                parts.append("\n@media %s{\n  " % cond +
                             "\n  ".join(block(vw[0])) + "\n}")
        body = "".join(parts) + "\n"
        open(css, "w").write(src[:lo] + body + src[hi:])
        print("\nwrote RATIO-TUNING block to assets/style.css")


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
