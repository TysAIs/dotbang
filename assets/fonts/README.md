# Web fonts — self-hosted, no third-party font requests at runtime

Four files, all latin-subset woff2, all OFL. Fetched 2026-11-04 from
`fonts.googleapis.com/css2` (the woff2 URLs it serves live on `fonts.gstatic.com`);
licence texts are the OFL copies published in `github.com/google/fonts`.

| File | Family | Weights | Source |
|---|---|---|---|
| `inter-latin-var.woff2` | Inter | 400-700 variable | `github.com/google/fonts` → `ofl/inter` |
| `jetbrains-mono-latin-var.woff2` | JetBrains Mono | 400-700 variable | `github.com/google/fonts` → `ofl/jetbrainsmono` |
| `silkscreen-400-latin.woff2` | Silkscreen | 400 | `github.com/google/fonts` → `ofl/silkscreen` |
| `silkscreen-700-latin.woff2` | Silkscreen | 700 | `github.com/google/fonts` → `ofl/silkscreen` |

sha256 (as committed):

```
3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62  inter-latin-var.woff2
83c005d49d8a6a50474c73a5a36ac0468076e9c4a29da7bdb14995d80560a5be  jetbrains-mono-latin-var.woff2
e6c72ea4702249202bcdd79d3343057e4e25ef1f04e3fcffd8602ab53b40b4cc  silkscreen-400-latin.woff2
5741b7f01a127f40ed70281fa2f686e8fc2cfe241930a120e4d1a1cebe78f995  silkscreen-700-latin.woff2
```

Departure Mono (MIT) is specified for the wordmark display face but is **not**
committed yet: the design brief leaves "wordmark in Departure Mono vs drawn as
custom letterforms" open, so shipping the file now would be a decision made by
default. Add it when that call is made.

Licences: `OFL-Inter.txt`, `OFL-JetBrainsMono.txt`, `OFL-Silkscreen.txt`.
