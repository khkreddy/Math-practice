# Vendored TikZ libraries

| Path | What it is |
|---|---|
| `mathfig/` | Original school-maths TikZ library, plus its harvest README and OPTIONS |
| `physfig/` | Original physics TikZ library, plus its harvest README and OPTIONS |
| `NOTICE.md` | Apache 2.0 credit and what was left out |

`scripts/build_figures.sh` puts `vendor/mathfig` on `TEXINPUTS` and compiles `figures/sources/*.tex` to `web/figures/*.svg`.

The harvest READMEs also describe example galleries (svg, pdf, repro). Those binary galleries are not in this repository. The `.sty` and `.code.tex` sources are.
