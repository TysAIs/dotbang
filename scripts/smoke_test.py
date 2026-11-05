import http.server, os, threading, urllib.request, functools, pathlib
PORT = int(os.environ.get("PORT", "8765"))
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pathlib.Path.cwd()))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
for p in ["/", "/pages/learn.html", "/pages/affiliates.html", "/pages/giveaways.html", "/pages/merch.html", "/assets/style.css", "/robots.txt", "/assets/favicon.svg"]:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{p}") as r:
        body = r.read().decode("utf-8", "replace")
        print(p, r.status, len(body), "B")
        if p == "/":
            assert "<title>dotBANG" in body
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
