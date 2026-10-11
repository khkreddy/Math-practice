# mathfig — option reference

`mathfig.sty` is a parameterised TikZ library written for Hari's teaching use. Its option set follows the
user-facing controls and URL parameters of the generators on **mathfigures.com** (teacher.dev). The site served
only as a feature list. No JavaScript or rendering code from the site was copied or transliterated.

```latex
\usepackage{mathfig}          % loads tikz, amsmath, xfp
\mathfigset{labels=medium}    % large | medium | small  (the site's "Large/Medium/Small labels" buttons)
```

Every macro takes one optional argument of `key=value` pairs (pgfkeys) and draws one `tikzpicture`.
Values that contain commas, `=` or brackets must be braced: `data={1,2,3}`.

## Label convention (all macros)

| value | meaning |
|---|---|
| `auto` | show the measure if that quantity was given, otherwise no label (default for most measure labels) |
| `measure` | always show the computed measure (rounded to `round` decimals, plus `unit`) |
| `none` or `{}` | no label |
| `?` | a blank line for students to fill in |
| anything else | typeset as math, e.g. `x`, `2x+3`, `h`, `65^\circ` |

Numbers are rounded to `round` decimals (default 1; site: whole/tenths/hundredths = 0/1/2), and trailing zeros are dropped.
`unit` is appended with a space (site: None/cm/m/mm/in/ft/yd/units/Other → `unit={}`, `cm`, …, any text).

---

## Polygons — `\mfTriangle`, `\mfRectangle`, `\mfParallelogram`, `\mfTrapezoid`, `\mfKite`

All polygons are drawn to scale from the given measures, then rotated/flipped and fitted into `width`×`height`.

### Keys per corner `X` ∈ {A, B, C, D}
| key | default | values | site control |
|---|---|---|---|
| `X` | (macro default) | angle in degrees; empty = not given | angle input |
| `X label` | `auto` | label convention | angle label Measure/Text/None |
| `X arcs` | `0` | 0–3 arc marks (congruent angles) | click angle → arcs |
| `X name` | `X` | corner name (math), `{}` hides | corner names |
| `hX` | `false` | draw the height from X | "Heights from A/B/C" |
| `hX label` | `auto` | label convention (`measure` = computed height) | height label Measure/Text/None |
| `hX foot` | empty | name of the foot point | foot name |
| `hX style` | `dashed` | `solid`, `dashed`, `dotted` or TikZ options | height line style |

### Keys per side `S` ∈ {AB, BC, CA, CD, DA}
| key | default | values | site control |
|---|---|---|---|
| `S` | (macro default) | length (fp expression: `3*sqrt(2)`, `12/5`) | side input |
| `S label` | `auto` | label convention | side label Measure/Text/None |
| `S ticks` | `0` | 0–3 tick marks | congruence ticks |
| `S arrows` | `0` | 0–3 parallel arrows | parallel marks |

### Shared keys
| key | default | values | site control |
|---|---|---|---|
| `unit` | empty | any text | Unit |
| `round` | `1` | decimals | Round to whole/tenths/hundredths |
| `right angle squares` | `true` | bool | Right-angle squares |
| `bottom` | empty | side key (`AB`, `BC`, …) placed horizontally at the bottom | "Side at the bottom" |
| `flip` | `false` | mirror | Flip |
| `turn` | `0` | degrees (−180…180) | Turn slider |
| `width`, `height` | `9`, `5.5` | fit box in cm | (figure size) |
| `scale` | `1` | extra TikZ scale | — |
| `dAC`, `dBD` | `false` | draw a diagonal (quadrilaterals) | Diagonals AC/BD |
| `dAC label`, `dBD label` | `none` | label convention | diagonal label |
| `dAC style`, `dBD style` | `solid` | solid/dashed/dotted | diagonal style |
| `cross` | empty | name of the diagonal intersection (`E`) | crossing point name |
| `kind` | per macro | see below | Kind |

### Macro specifics
* `\mfTriangle`: defaults `A=24, B=90, AB=12, BC label=x, C label=none`. The solver handles SSS, SAS, ASA/AAS and SSA (acute
  solution); missing data falls back to sensible values. Clear a default by passing it empty: `A={}`.
* `\mfRectangle`: `kind=rectangle|square`; defaults `AB=10, BC=6`; with `square`, `BC=AB` and the BC label is off.
* `\mfParallelogram`: `kind=parallelogram|rhombus`; defaults `AB=10, DA=6, A=60` with parallel arrows (1 on AB/CD, 2 on BC/DA).
  Heights `hD`/`hC` go to AB.
* `\mfTrapezoid`: `kind=right|isosceles|trapezoid` (default `right`); defaults `AB=12, CD=7` with arrows on the bases. `h` is the height
  (right: `DA`). For `isosceles` and `trapezoid`, the default is `CD=6` plus a measured height from D (`hD=false` removes it); `trapezoid` uses angle `A` (default 60).
* `\mfKite`: `AB = BC`, `CD = DA`, angle `B` at the top (standing upright). Defaults `AB=5, DA=9, B=100` with ticks.

## `\mfRegularPolygon`
| key | default | values | site control |
|---|---|---|---|
| `n` | `6` | 3–20 | Number of sides |
| `size` | `8` | number | Size |
| `size by` | `side` | `side`, `radius`, `apothem` | Size from side/radius/apothem |
| `side label` | `auto` | label convention | Side label |
| `side ticks` | `0` | 0–3 | Side marks |
| `angle label` | `none` | label convention (`measure` = interior angle) | Interior angle |
| `angle arcs` | `0` | 0–3 | Angle marks |
| `central angle` | `none` | (reserved) | Central angle |
| `center dot` | `true` | bool | Center dot |
| `center name` | empty | text | Center name |
| `apothem` | `true` | bool | Apothem |
| `apothem label` | `a` | label convention | Apothem label |
| `apothem style` | `dashed` | solid/dashed/dotted | Apothem line style |
| `radius` | `false` | bool | Radius |
| `radius label` | `measure` | label convention | Radius label |
| `radius style` | `dashed` | style | Radius line style |
| `radii` | `false` | draw all radii | All radii |
| `letters` | `false` | name the corners A, B, C, … | Letter corners |
| `unit`, `round`, `right angle squares`, `turn`, `width`, `height`, `scale` | | as above | |

## Lines — `\mfAngles`, `\mfParallelLines`
### `\mfAngles`
| key | default | values | site control |
|---|---|---|---|
| `rays` | `{0,60}` | directions in degrees (first = baseline) | rays / add ray |
| `lines` | `{}` | per ray `true` = continue through the vertex as a line | "run through vertex as a line" |
| `styles` | `{}` | per ray `solid`/`dashed`/`dotted` | ray style |
| `angle labels` | `{auto}` | per gap (counter-clockwise from the baseline), label convention | click angle → label |
| `angle arcs` | `{}` | per gap, number of arcs | click angle → marks |
| `vertex` | empty | vertex name | points |
| `points` | `{}` | per ray, the name of a point on it | click to add points |
| `length`, `radius` | `5`, `0.6` | ray length, arc radius (cm) | — |
| `arrows` | `true` | arrowheads on rays | — |
| `reflex` | `false` | also mark gaps ≥ 180° | — |
| `turn`, `round`, `scale`, `right angle squares` | | | Turn, Round |

### `\mfParallelLines`
| key | default | values | site control |
|---|---|---|---|
| `lines` | `{m,n}` | names of the parallel lines (top to bottom) | parallel lines / add |
| `gap` | `2.2` | distance between lines (cm) | — |
| `transversals` | `{t/65}` | `name/angle[/x]` items | transversals (angle) |
| `marks` | `1` | number of ">" parallel marks | — |
| `angles` | `{}` | `transversal/line/position/label`; position 1–4 = above-right, above-left, below-left, below-right | click angle → label ("Each angle is above m, to the right of the transversal") |
| `points` | `{}` | `transversal/line/name` intersection points | click to add points |
| `length`, `arrows`, `turn`, `round`, `scale` | `10`, `true`, `0`, `1`, `1` | | Turn, Round |

## Solids — `\mfPrism`, `\mfPyramid`, `\mfCylinder`, `\mfCone`, `\mfSphere`
Polyhedra use a cabinet (oblique) projection: x right, y up, z back, `depth scale`=0.5, `depth angle`=40°.
Hidden edges come from face visibility (outward normals) and are drawn dashed (`hidden=false` omits them).

| key | default | values | used by | site control |
|---|---|---|---|---|
| `base` | `rectangle` | `rectangle`, `right`, `isosceles`, `regular` | prism, pyramid (`rectangle`/`regular`) | Base |
| `n` | `6` | 3–8 sides of a regular base | prism, pyramid | Sides |
| `length`, `width`, `height` | 5, 3, 4 (prism); 6, 6, 4 (pyramid) | numbers | prism, pyramid, cylinder, cone | Length/Width/Height |
| `slant` | empty | slant height (pyramid: to the middle of the front edge; height is computed if empty) | pyramid, cone | Slant height |
| `tri base`, `tri height`, `hyp` | 6, 8, — | triangle base | prism | Base / triangle height / hypotenuse |
| `sits` | `side` | `side` (triangle faces you) or `base` (stands on the triangle) | prism | Sits standing on base / lying on its side |
| `side`, `apothem` | 4, — | regular base | prism, pyramid | Side / Apothem |
| `radius` | 3 | number (with `diameter=true` it is the diameter, as on the site) | cylinder, cone, sphere | Radius |
| `diameter` | `false` | show the diameter instead of the radius | cylinder, cone, sphere | Diameter instead |
| `oblique`, `lean` | `false`, — | leaning solid; `lean` = horizontal offset of the top | all but sphere | Right/Oblique, Lean |
| `shape`, `bowl` | `whole`, `false` | `hemisphere`; `bowl=true` opens upward | sphere | Whole/Hemisphere, Dome/Bowl |
| `hidden` | `true` | dashed hidden edges | all | Hidden edges |
| `show height` | `true` | dashed height with right-angle mark | pyramid, cone, oblique cylinder | Height shown |
| `right angle squares` | `true` | bool | all | Right-angle squares |
| `names` | `false` | letter the vertices A, B, C, … | prism, pyramid | Name the corners |
| `depth` | `right` | `right` / `left` | prism, pyramid | Depth goes back left/right |
| `<q> label` | `auto` | label convention for q ∈ length, width, height, slant, tri base, tri height, hyp, side, apothem, radius, lean | | per-measure label |
| `unit`, `round` | `cm`, `1` | | | Unit, Round |
| `center dot` | `true` | dot at the centre of the radius | cylinder, cone, sphere | — |
| `fig width`, `fig height`, `scale` | 7, 6, 1 | fit box | | — |
| `depth scale`, `depth angle` | 0.5, 40 | projection | prism, pyramid | — |

## Graphs
### `\mfNumberLine`
| key | default | values | site control |
|---|---|---|---|
| `from`, `to`, `step` | −10, 10, 1 | fp expressions (`1/4`, `0.1`) | From / To / Count by |
| `every` | `1` | number every n-th tick; 0 = none | Numbers every tick/2nd/4th/5th/10th/none |
| `fractions` | `false` | write tick numbers as fractions | (fraction steps) |
| `graph` | empty | intervals separated by `;` in interval notation: `[-2,inf)`, `(-3,4]`, `(-inf,-1); [3,inf)`; `(`/`)` gives an open dot | inequalities incl. compound and "or" |
| `points` | empty | `name=value` list, e.g. `P=3/4, Q=3/2` | named points P(3/4) |
| `sequence`, `terms` | empty, 5 | expression in `n` (`1/n`), number of terms | sequence a_n = … |
| `sequence label` | `auto` | `auto` (fraction label at points off the ticks), `none`, or a template using `\mfn` | — |
| `color`, `length`, `arrows`, `scale` | mfink, 12, true, 1 | | end arrows |

### `\mfGrid` (coordinate grid)
| key | default | values | site control |
|---|---|---|---|
| `x from`, `x to`, `x step` (same for y) | 0, 15, 1 | fp expressions, `pi` allowed (`-2pi`, `pi/2`) | From / To / Count by |
| `x every`, `y every` | `1` | number every n-th line; 0 = none | Numbers every line/2nd/5th/10th/none |
| `x pi`, `y pi` | `false` | label as multiples of π | (π axes) |
| `trig` | `radians` | `radians` / `degrees` | Trig in radians/degrees |
| `minor` | `0` | 2, 4 or 5 minor lines per cell | Minor gridlines |
| `x label`, `y label` | `x`, `y` | axis-end labels (`{}` hides) | Axis label |
| `title`, `x title`, `y title` | empty | text (`?` = blank) | Titles Text/Blank/None |
| `arrows` | `true` | end arrows | End arrows |
| `plot` (repeatable) | — | `[colour]expression in x`, e.g. `plot={[mfblue]x^2-2x-3}`; a leading `y=` is allowed | equations y = … ( \|color=…) |
| `points` | empty | `name/x/y` list | points A(2,4) |
| `samples`, `numbers`, `width`, `height`, `scale` | 241, true, 9, 9, 1 | | — |

### `\mfBoxPlot`
| key | default | values | site control |
|---|---|---|---|
| `data` | empty | comma list; exactly 5 values = five-number summary | Data |
| `sets` | empty | `name=values | name=values` (several box plots) | data sets (name + data) |
| `outliers` | `false` | 1.5·IQR rule, outliers as dots | Show outliers |
| `whisker ends` | `true` | end caps | Whisker end lines |
| `min label`, `q1 label`, `median label`, `q3 label`, `max label` | `none` | label convention (`measure` = value) | labels None/Value/Text |
| `from`, `to`, `step`, `every` | fitted | axis; empty = fit with a 1-2-5 step | number line from/to/count by, numbers every |
| `title`, `axis title` | empty | text | Titles |
| `arrows`, `length`, `box height`, `round`, `scale` | true, 12, 0.8, 2, 1 | | End arrows |

Quartiles use the exclusive (Tukey) method, which gives the same numbers as the site.

### `\mfMapping`
| key | default | values | site control |
|---|---|---|---|
| `inputs`, `outputs` | empty | comma lists (numbers are set in math) | Inputs / Outputs |
| `arrows` | empty | `input/output` pairs, e.g. `{1/3, 2/5}`; an input can have several | arrows per input / ordered pairs |
| `input title`, `output title`, `title` | Input, Output, — | text | Titles |
| `shape` | `oval` | `oval`, `box`, `none` | Sides Ovals/Boxes/None |
| `gap`, `row`, `scale` | 5, 0.85, 1 | spacing | — |

## `\mfRuler` (length reading)
| key | default | values | site control |
|---|---|---|---|
| `system` | `metric` | `metric` / `imperial` | Units |
| `ruler` | 15 (cm) / 6 (in) | ruler length | Ruler length 15/20/30/50/100 cm, 6/8/12/20 in |
| `marks` | `mm` / 16 | metric: `mm`, `0.5`, `cm`/`1`, `5`, `10`; imperial: 1, 2, 4, 8, 16 | Smallest marks |
| `length`, `start` | 4.37, 0 | object length and left end | Object length, Left end at |
| `object` | `cylinder` | `cylinder` (metal), `cube`, `rock`, `marbles` | Object |
| `marbles` | `4` | 1–5 | Marbles |
| `guides` | `false` | dotted guide lines at the ends | Dashed guide lines |
| `view` | `magnifier` | `magnifier` / `whole` | Show ruler + magnifiers / ruler only |
| `zoom` | `auto` | magnification (`auto` fits the zoomed window into the magnifier, min 1.2) | — |
| `magnifier numbers` | `1` | *reserved — accepted but not yet used* | Numbered marks in the magnifier 1–6 |
| `read` | `estimate` | `estimate` / `mark` (rounding of the answer) | Read to |
| `answer` | `false` | print the answer under the ruler | Answer key |
| `title` | empty | text | Title |
| `width`, `scale` | 12, 1 | drawing size | — |

## Coverage per generator

"Covered" = the site control has a key with the same effect. "Missing/partial" lists what the macro cannot do (or does differently).
Site URL parameters were mapped by `tools/repro_map.py`; all 86 captured examples are rebuilt with the macros.

| generator | macro | site controls covered | missing / partial |
|---|---|---|---|
| coordinate-grid | `\mfGrid` | equations (repeatable `plot`, colour), chart/x/y titles (text, `?` blank line, none), x/y from/to/count-by, numbers every 1/2/5/10/none, axis labels text/none, end arrows, minor gridlines 2/4/5, points, π-axes | per-end arrow choice is all-or-nothing (`arrows`); implicit equations / inequalities (shading) are not supported; only `y = f(x)` |
| number-line | `\mfNumberLine` | from/to/step, numbers every 1/2/4/5/10/none, fractions, inequality graphs (simple, compound, "or"), lettered points, sequences | inequality must be given in interval notation (`graph={[-2,inf)}`), not as typed text `x >= -2` (the repro script converts) |
| triangle | `\mfTriangle` | corner names, angles A/B/C, lengths AB/BC/CA (any 3 consistent givens, SSS/SAS/ASA/AAS solved to scale), label Measure/Text/None/`?`, heights from A/B/C, unit incl. Other, rounding, right-angle squares, side at the bottom, turn, ticks/arcs | ambiguous SSA case picks the acute solution only |
| rectangle | `\mfRectangle` | rectangle/square, AB/BC, corner names, diagonals (+labels/style, crossing point), unit, rounding, position (side at bottom), turn | — |
| parallelogram | `\mfParallelogram` | parallelogram/rhombus, AB/DA, angle A, corner names, heights, diagonals, unit, rounding, position, turn, ticks/parallel arrows | — |
| trapezoid | `\mfTrapezoid` | trapezoid/isosceles/right, AB/CD/DA, corner names, heights, diagonals, unit, rounding, position, parallel arrows | site defaults reproduced via `kind`-specific defaults |
| kite | `\mfKite` | AB/DA, angle B, corner names, heights, diagonals, unit, rounding, position (upright or side at bottom) | — |
| regular-polygon | `\mfRegularPolygon` | 3–12 sides, given side/radius/apothem, center name, center dot, apothem/radius lines with Measure/Text/None labels, unit, rounding, position | `central angle` key reserved but not drawn |
| angles | `\mfAngles` | rays/lines, labels per angle (click-labels → list keys), arcs, vertex & point names, reflex, turn, rounding | interactive point-and-click editing replaced by list keys |
| parallel-lines | `\mfParallelLines` | lines, transversals (angle, position), parallel marks, angle labels per position 1–4, points, turn, rounding | as for angles (list keys instead of clicks) |
| prism | `\mfPrism` | base rectangle/right triangle/isosceles/regular polygon, right/oblique, length/width/height, side/apothem, labels, hidden edges dashed, right-angle squares, unit, rounding, depth left/right | — |
| cylinder | `\mfCylinder` | right/oblique, radius (or diameter), height, labels, hidden edges, unit, rounding | viewpoint fixed ("seen from a little above") |
| pyramid | `\mfPyramid` | base rectangle/regular, right/oblique, length/width/height/slant, show height/slant line, labels, unit, rounding, depth left/right | proportions approximate vs the site |
| cone | `\mfCone` | right/oblique, radius/diameter, height, slant, show height, labels, unit, rounding | viewpoint fixed |
| sphere | `\mfSphere` | whole/hemisphere, radius/diameter, labels, unit, rounding | viewpoint fixed |
| box-plot | `\mfBoxPlot` | several named data sets (raw data or five-number summary), stat labels None/Value/Text, whiskers to min/max or 1.5·IQR outliers, chart/axis titles (text/blank/none), from/to/step, numbers every n | quartile method fixed (Tukey, exclusive median) |
| mapping-diagram | `\mfMapping` | inputs/outputs, arrows / ordered pairs, input/output/diagram titles (text/blank/none), sides ovals/boxes/none | ordered-pair text must be given as `in/out` list |
| length-reading | `\mfRuler` | metric/imperial, ruler length, smallest marks, read to estimate/mark, object length & left end, object (marbles/rock/cube/metal cylinder), view ruler+magnifiers/ruler only, title, answer key | `magnifier numbers` (1–6 numbered marks in the magnifier) reserved, not implemented; rock outline is generic |
