import http.server, threading, urllib.request, functools, pathlib
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pathlib.Path.cwd()))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
for p in ["/", "/pages/learn.html", "/pages/affiliates.html", "/pages/giveaways.html", "/pages/merch.html", "/assets/style.css", "/robots.txt", "/assets/favicon.svg", "/assets/brand/mark.svg", "/assets/brand/mark-signal.svg", "/assets/brand/mark-inverse.svg", "/assets/fonts/inter-latin-var.woff2", "/assets/fonts/jetbrains-mono-latin-var.woff2", "/assets/fonts/silkscreen-400-latin.woff2", "/assets/fonts/silkscreen-700-latin.woff2", "/assets/social/dotbang-avatar-400x400-default.png", "/assets/social/dotbang-banner-1500x500-signal.png", "/assets/social/dotbang-cover-1280x720-inverse.png"]:
    with urllib.request.urlopen(f"http://127.0.0.1:8765{p}") as r:
        body = r.read().decode("utf-8", "replace")
        print(p, r.status, len(body), "B")
        if p == "/":
            assert "<title>dotBANG" in body
            assert 'src="assets/brand/mark-signal.svg"' in body, "index must reference the mark asset"
            assert '<span class="mark">' not in body, "no inline typed mark left"
            assert "var(--accent)" not in body, "no legacy accent token left"
        if p.endswith(".woff2"):
            assert len(body) > 1000, "font file looks truncated"
        if "learn" in p:
            assert body.count("github.com/TysAIs") == 3, body.count("github.com/TysAIs")
            print("  learn links ok (3 real repos)")
        if "affiliates" in p:
            assert "Link list pending" in body and "amazon" not in body.lower()
            print("  affiliates: no invented links ok")
        if "merch" in p:
            assert "No store yet" in body
srv.shutdown()
print("ALL PAGES 200 OK")
