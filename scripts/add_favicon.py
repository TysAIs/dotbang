import pathlib
for p in [pathlib.Path("index.html"), *pathlib.Path("pages").glob("*.html")]:
    t = p.read_text()
    href = "assets/favicon.svg" if p.name == "index.html" else "../assets/favicon.svg"
    if "favicon" not in t:
        t = t.replace('<link rel="stylesheet"', f'<link rel="icon" type="image/svg+xml" href="{href}">\n<link rel="stylesheet"')
        p.write_text(t)
        print("patched", p)
