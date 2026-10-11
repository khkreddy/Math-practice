# Notice

This directory vendors two TikZ libraries used to draw practice-sheet figures.

## mathfig

`vendor/mathfig/` is the original `mathfig` library (`mathfig.sty` and `mathfig-*.code.tex`) together with that harvest's `README.md` and `OPTIONS.md`.

Example figures described in the README as coming from Math Figures (mathfigures.com, a teacher.dev project) are free to use, copy, change, and share under the Apache License 2.0, © Math Figures (mathfigures.com). The full licence is at https://www.apache.org/licenses/LICENSE-2.0.

`mathfig/` itself is original code. The mathfigures.com site was used only as a feature list. None of its JavaScript or rendering code was copied.

Credit line for handouts: Figures based on mathfigures.com (teacher.dev), Apache License 2.0.

The captured example SVG/PDF galleries from that harvest are not included here. The library sources are what this project compiles against.

## physfig

`vendor/physfig/` is the original `physfig` library together with that harvest's `README.md` and `OPTIONS.md`.

Example figures described there as coming from physicsfigures.com (teacher.dev) are under the Apache License 2.0. `physfig/` itself is original code written from a feature list; no site code was copied.

This first practice sheet does not draw a physics figure. The library is vendored so a later sheet can.

## This question's figure

`figures/sources/q24.tikz` is drawn for this paper. It uses mathfig's line, arrow, and thin styles. It is not a mathfigures.com example.
