# mathfig — TikZ versions of the mathfigures.com example figures + an original TikZ library

% Figure based on mathfigures.com (teacher.dev), Apache License 2.0

For Hari's own teaching use. Nothing here has been published.

## Contents
| path | what |
|---|---|
| `svg/<generator>/<slug>.svg` | the original figure SVGs, captured from mathfigures.com (each generator's default plus every named sitemap example) |
| `tikz/<generator>/<slug>.tex` (+ `.pdf`) | standalone TikZ conversion of each SVG (converted automatically, then checked) |
| `tikz_snippets/<generator>/<slug>.tikz` | the same as a bare `tikzpicture`, for `\input` |
| `mathfig/` | **mathfig**: our own parameterised TikZ library (`mathfig.sty` plus 5 `*.code.tex` files) |
| `repro/<generator>/<slug>.tex` (+ `.pdf`) | each captured example rebuilt with one `mathfig` macro call |
| `gallery/gallery.pdf` (+ `.tex`) | several variations per macro, with the code under each |
| `all_figures.pdf` (+ `.tex`) | every example: conversion and macro version side by side, with the macro code and the source URL |
| `OPTIONS.md` | every key, its default, allowed values and the matching site control, plus a coverage table per generator |
| `tools/`, `*.py` | the capture/convert/compare scripts |

The contact sheet (original | conversion | macro) is a separate file: `mathfig_contact_sheet.pdf`.

## Figures per generator (86 total)
| generator | n | macro | | generator | n | macro |
|---|---|---|---|---|---|---|
| coordinate-grid | 6 | `\mfGrid` | | prism | 6 | `\mfPrism` |
| number-line | 6 | `\mfNumberLine` | | cylinder | 5 | `\mfCylinder` |
| triangle | 6 | `\mfTriangle` | | pyramid | 4 | `\mfPyramid` |
| rectangle | 5 | `\mfRectangle` | | cone | 5 | `\mfCone` |
| parallelogram | 4 | `\mfParallelogram` | | sphere | 5 | `\mfSphere` |
| trapezoid | 5 | `\mfTrapezoid` | | box-plot | 6 | `\mfBoxPlot` |
| kite | 4 | `\mfKite` | | mapping-diagram | 6 | `\mfMapping` |
| regular-polygon | 5 | `\mfRegularPolygon` | | length-reading | 6 | `\mfRuler` |
| angles | 1 | `\mfAngles` | | parallel-lines | 1 | `\mfParallelLines` |

All 86 conversions and all 86 macro rebuilds compile with pdflatex (TeX Live 2025) and were checked visually against the originals.

## Using the library
Copy the `mathfig/` folder next to your document (or point `TEXINPUTS` at it: `TEXINPUTS=path/to/mathfig//: pdflatex doc.tex`), then:

```latex
\usepackage{mathfig}   % loads tikz; needs a recent LaTeX (expl3, xparse built in)
...
\mfTriangle[A=40, B=90, AB=8, unit=cm, BC label=?]
\mfNumberLine[from=-5, to=5, graph={[-2,inf)}]
\mfBoxPlot[data={12,15,18,21,22,25,30}, labels=value]
\mfRuler[length=4.37, object=rock]
```
Label convention for every measured quantity: `auto` (show the measure if you gave it), `measure`, `none` or `{}` (no label), `?` (blank line for students), anything else (typeset as math).
Figures are drawn to scale, then fitted to the requested size. See `OPTIONS.md` for all keys and `gallery/gallery.pdf` for examples.

## NOTICE / LICENSE
* The example figures in `svg/`, and the derived `tikz/`, `tikz_snippets/`, `repro/` files and the PDFs built from them, are based on
  figures from **Math Figures (mathfigures.com), a teacher.dev project**. Per its /reuse page they are free to use, copy, change
  and share under the **Apache License 2.0**, © Math Figures (mathfigures.com). Changes: converted from SVG to TikZ and rebuilt
  with mathfig macros. Every file carries the header
  `% Figure based on mathfigures.com (teacher.dev), Apache License 2.0`. The full licence text is at
  https://www.apache.org/licenses/LICENSE-2.0.
* `mathfig/` is original code written for this project. The site was used only as a feature list (which figure types and
  options exist); none of its JavaScript or rendering code was copied or transliterated.
* Credit line for handouts: *Figures based on mathfigures.com (teacher.dev), Apache License 2.0.*
* The site was captured politely (about 1 request per second, robots.txt respected).
