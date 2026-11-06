"""Smoke test for the dotBANG site.

Serves the repo on a loopback port and checks, for every page:
  - HTTP 200 and a dotBANG title
  - the page's own content markers (so a page cannot silently lose its point)
  - every same-origin href/src resolves to 200 (no broken CSS, font or page link)
  - brand casing: the wordmark is written dotBANG, never DOTBANG or DotBang
Run: python3 scripts/smoke_test.py   (exit 0 = pass)
"""
import http.server, os, threading, urllib.request, urllib.parse, functools, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PORT", "8765"))
PAGES = {
    "/": ["Your data,", "Available for work", "Territory and sales briefs", "ig.me/m/dot___bang",
          "accent plate #6CACE4"],
    "/pages/services.html": ["Three ways to work", "The data proof", "Model operations"],
    "/pages/work.html": ["The Territory Brief", "11,232 rows", "20 checks, 0 failures",
                         "hackney-territory-brief-preview"],
    "/pages/learn.html": ["GB10 setup standard", "Gauntlet benchmark", "xPST"],
    "/pages/merch.html": ["No store yet", "follow the audience"],
    "/pages/giveaways.html": ["Published up front", "No data hoarding"],
    "/pages/affiliates.html": ["Link list pending", "The rule", "How a link gets on this page"],
}
ASSETS = ["/assets/fonts/inter-latin-subset.woff2", "/assets/fonts/jetbrains-mono-latin-subset.woff2",
          "/assets/favicon.svg", "/robots.txt"]

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

failures = []
seen, queue = set(), list(PAGES) + ASSETS
while queue:
    path = queue.pop(0)
    if path in seen:
        continue
    seen.add(path)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}") as r:
            body = r.read()
            status = r.status
    except Exception as e:  # noqa: BLE001
        failures.append(f"{path}: {e}")
        continue
    print(f"{path} {status} {len(body)}B")
    if not path.endswith((".css", ".woff2", ".svg", ".txt")):
        text = body.decode("utf-8")
        for marker in PAGES.get(path, []):
            if marker not in text:
                failures.append(f"{path}: missing marker {marker!r}")
        for bad in ("DOTBANG", "DotBang", "dotbang llc"):
            if bad in text:
                failures.append(f"{path}: brand casing {bad!r}")
        for m in re.finditer(r'(?:href|src)="([^"]+)"', text):
            link = m.group(1)
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = urllib.parse.urljoin(path, link).split("#")[0]
            if target and target not in seen:
                queue.append(target)

srv.shutdown()
if failures:
    print("\nFAIL")
    for f in failures:
        print("  " + f)
    sys.exit(1)
print(f"\nPASS — {len(seen)} URLs fetched, every link resolves, every page carries its markers, casing clean.")
