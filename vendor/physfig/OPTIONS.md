# physfig — options reference

`physfig.sty` is an original, parameterised TikZ library written for Hari's teaching use. It does not contain any code from physicsfigures.com; the site was used only as a *feature reference* (the list of user-facing controls and URL parameters). Figure ideas based on physicsfigures.com (teacher.dev).

## Setup

```latex
\usepackage{physfig}          % loads tikz, circuitikz, xfp, amsmath, bm
% \usepackage[nocircuits]{physfig}  % skip circuitikz if you do not need \pfCircuit
\usepackage{mathptmx}         % optional: Times-like fonts close to the site
\usepackage[scaled=0.92]{helvet} % optional: sans font for graph labels (avoids bitmap fonts)
```

Copy the folder `physfig/` (physfig.sty + physfig-*.code.tex) next to your worksheet or into your local texmf tree. Requires a TeX Live from 2020 or later (uses `\fpeval`, expl3).

## Conventions used by every macro

* Labels are typeset in math mode: `label=F_N`, `label=5\,\mathrm{kg}`, `angle label=35^\circ`.
* `?` as a label value draws a **blank line** for students to fill in (site: *Blank line*).
* An empty value `{}` means **no label** (site: *None*).
* Boolean keys can be given bare (`gravity` = `gravity=true`).
* `mirror` flips the figure left to right; `color` switches to the colour scheme for slides; `scale` scales the whole picture.
* Saving presets (site: *Save preset*): define your own command, e.g. `\newcommand\myramp[1][]{\pfIncline[surface=rough, gravity, normal, #1]}`.


## `\pfFBD[keys]` — Free Body Diagram Generator (/free-body-diagram)

| key | default | allowed values | generator control |
|---|---|---|---|
| `body` | dot | dot, block, ball, cart | Body: Dot / Block / Ball / Cart |
| `force={...}` | — | repeatable; sub-keys below | Forces → Force n |
| `dir` (sub-key) | 90 | 0–359 (deg, counter-clockwise from +x) | Force n Direction slider / quick directions Up=90, Down=270, Left=180, Right=0 |
| `length` (sub-key) | 1 | 0.25–2 | Force n Length (×) |
| `label` (sub-key) | F | math text, `?` = blank line, `{}` = none | Force n Label: Text / Blank line / None |
| `angle mark` (sub-key) | false | true/false (bare key = true) | angle marker shown on the site when a force has the angle flag (URL 4th field) |
| `angle label` (sub-key) | \theta | math text / ? / {} | label of that angle marker |
| `color` (sub-key) | (auto) | any xcolor name | —(extra) |
| `forces={d/l/label,...}` | — | shorthand list of dir/length/label | Add a force (Gravity, Normal, Friction, Tension, Applied, Spring, Air resistance, Force) → just give the label you want, e.g. 270/1/F_g |
| `notation` | none | none, arrow, bold | Vector notation: None / Arrow / Bold (per label: type \vec{F} or \mathbf{F} yourself) |
| `velocity / velocity dir / velocity label` | false / 0 / v | bool / deg / math | Motion: Velocity (drawn dashed beside the body) |
| `acceleration / acceleration dir / acceleration label` | false / 0 / a | bool / deg / math | Motion: Acceleration |
| `unit` | 2.3 | cm drawn for length 1 | —(extra) |
| `mirror` | false | bool | Figure: Mirror (flip left to right) |
| `color` | false | bool (colours each force) | Figure: Color (for slides) |
| `scale` | 1 | number | —(extra) |

## `\pfVectors[keys]` — Vector Diagram Generator (/vector-diagram)

| key | default | allowed values | generator control |
|---|---|---|---|
| `vector={...}` | — | repeatable, drawn head to tail in order | Vectors → Vector n / Add a vector |
| `mag` (sub-key) | 1 | 0.5–12 (grid squares) | Magnitude |
| `dir` (sub-key) | 0 | 0–359 | Direction / quick directions |
| `style` (sub-key) | drawn | drawn, dashed, off | Arrow: Drawn / Dashed / Left off |
| `label` (sub-key) | (empty) | math / ? / {} | Label: Text / Blank line / None |
| `components, x label, y label` (sub-key) | false, auto (=A_x), auto (=A_y) | bool / math | (URL vector fields) components of one vector |
| `angle mark, angle label` (sub-key) | false, \theta | bool / math | (URL vector fields) angle of one vector |
| `vectors={m/d/label,...}` | — | shorthand | — |
| `resultant` | dashed | drawn, dashed, off, none | Resultant → Arrow: Drawn / Dashed / Left off (none = no resultant at all, URL resultant=none) |
| `resultant label` | R | math / ? / {} | Resultant → Label |
| `resultant angle, resultant angle label` | false, \theta | bool / math | Mark its angle |
| `resultant components` | false | bool | Show its components |
| `grid` | true | bool | Grid and axes → Grid |
| `axes` | false | bool | x and y axes, from the first tail |
| `unit` | 0.5 | cm per grid square | —(extra) |
| `mirror, color, scale` | false, false, 1 |  | Figure: Mirror / Color |

## `\pfIncline[keys]` — Inclined Plane Generator (/inclined-plane)

| key | default | allowed values | generator control |
|---|---|---|---|
| `object` | block | block, ball, cart | Object |
| `label` | m | math / ? / {} | Object label: Text / Blank line / None |
| `size` | 1 | 0.5–2 | Size (%) |
| `position` | 0.55 | 0.2–0.85 (fraction up the ramp) | Where on the ramp |
| `objects, label 1, label 2, object 2` | 1, m_1, m_2, block | 1 or 2 | Add an object above (two objects tied by a string) |
| `angle` | 30 | 5–60 | Ramp → Angle |
| `angle label` | \theta | math / ? / {} | Angle label |
| `surface` | smooth | smooth, rough | Surface |
| `gravity / gravity label` | false / F_g | bool / math | Gravity (+ its label) |
| `normal / normal label` | false / F_N | bool / math | Normal force |
| `friction / friction label` | none / F_f | none, up, down | Friction: None / Up the ramp / Down the ramp |
| `applied / applied label` | none / F_A | none, up, down | Applied force |
| `tension / tension label` | false / T | bool (2 objects) | tension in the string (URL tension=1) |
| `velocity / velocity label` | none / v | none, up, down | Velocity |
| `acceleration / acceleration label` | none / a | none, up, down | Acceleration |
| `length mark / length label` | false / L | bool / math | Marks → Length of the ramp |
| `height mark / height label` | false / h | bool / math | Marks → Height of the ramp |
| `ramp length` | 9 | cm | —(extra) |
| `mirror, color, scale` | false, false, 1 |  | Figure |

## `\pfPulley[keys]` — Pulley Generator (/pulley)

| key | default | allowed values | generator control |
|---|---|---|---|
| `setup` | atwood | atwood, table, ramp, tackle | Setup: Atwood / Table / Ramp / Block & tackle |
| `left label, right label` | m_1, m_2 | math / ? / {} | Left/Right object label |
| `size` | 1 | number | Size |
| `hangs lower` | neither | neither, left, right | Hangs lower |
| `third, third label` | none, m_3 | none, left, right | Hang a third object below / The third hangs below |
| `table object, table label, hanging label` | block, m_1, m_2 | block/cart; math | On the table object / labels |
| `ramp object, ramp label, angle, angle label` | block, m_1, 35, \theta |  | On the ramp object / Ramp angle & label |
| `surface` | smooth | smooth, rough (table) | Table → Surface |
| `strands, load label` | 3, m | integer ≥1 | Strands holding up the load / Load label |
| `tension / tension label` | false / T | bool / math | Tension (+ label); with a third mass T_1, T_2 are used |
| `gravity` | false | bool | Gravity |
| `gravity label left/right/third` | auto (= <mass label> g) | math / ? / {} | Gravity label on each object |
| `normal / normal label` | false / F_N | bool | Normal force (table, ramp) |
| `friction / friction label` | none / F_f | none, toward, away | Friction: None / Toward the pulley / Away from it |
| `acceleration / acceleration label` | none / a | atwood: right falls, left falls; table & ramp: falls, rises; tackle: rises, falls | Acceleration |
| `mirror, color, scale` |  |  | Figure |

## `\pfProjectile[keys]` — Projectile Motion Generator (/projectile-motion)

| key | default | allowed values | generator control |
|---|---|---|---|
| `launch` | ground | ground, cliff | Launched from: Level ground / A cliff |
| `cliff height` | 3 | cm (≈ small 2 / medium 3 / tall 4.5) | Cliff height |
| `angle` | 45 | −60…85 (0 = horizontal) | Angle |
| `angle mark / angle label` | true / \theta | bool / math | Mark the angle / Angle label |
| `object, size` | ball, 0.6 | ball, dot; number | Object / Size |
| `path` | true | bool | Show the path (dashed) |
| `positions` | 0 | integer (n time steps → n+1 balls) | Ball at equal time steps |
| `letters` | false | bool | Letter them A, B, C… |
| `velocity / velocity label` | true / v_0 | bool / math | Launch velocity |
| `components / x label / y label` | false / v_{0x} / v_{0y} | bool / math | Its components (+ labels) |
| `gravity / gravity label` | false / g | bool / math | Acceleration due to gravity |
| `height mark / height label` | false / H |  | Marks → Maximum height |
| `range mark / range label` | false / R |  | Marks → Range |
| `cliff mark / cliff label` | false / h |  | Marks → Height of the cliff |
| `width, max height` | 11, 5.5 | cm | —(extra) drawing size |
| `mirror, color, scale` |  |  | Figure |

## `\pfMotionGraph[keys]` — Motion Graph Generator (/motion-graphs)

| key | default | allowed values | generator control |
|---|---|---|---|
| `segments={type/v/t/dir,...}` | faster/4/2, forward, slower/0/2, rest | type ∈ rest, forward, back, faster, slower; v = speed to reach (m/s); t = duration (s); dir = forward/back. Empty fields take defaults (rest 2 s; forward/back keep current speed or 2 m/s, 3 s; faster +2 m/s in 2 s; slower to 0 in 2 s) | Motion: segment list (At rest / Constant velocity forward / back / Speeding up / Slowing down, Speeds up to, Lasts, direction, move earlier/later = reorder the list) |
| `segment={type=..,v=..,t=..,dir=..}` | — | key=value form of one segment | same |
| `start` | 0 | m | Starting position (m) |
| `graphs` | pt | pt, vt, at, all | Graphs: Position–time / Velocity–time / Acceleration–time / All three, stacked |
| `letters` | false | bool | Letter the segment ends A, B, C… |
| `styles` | false | bool | Each segment in its own line style |
| `tangent at` | (empty) | time in s | Tangent to the position–time graph / At |
| `title, time title, position title, velocity title, acceleration title` | {}, Time (s), Position (m), Velocity (m/s), Acceleration (m/s²) | text / ? (blank line) / {} (none) | Titles: Chart title, axis titles |
| `numbers` | true | bool | Numbers on the axes |
| `gridlines` | true | bool | Gridlines |
| `tmax, ymin, ymax, ystep` | auto | numbers | Set the ranges myself (ymin/ymax apply to the position graph; ystep to all) |
| `width, height, stacked height` | 8.5, 4.2, 3.2 | cm | —(extra) |
| `label font, number font` | \small\sffamily, \footnotesize\sffamily | font commands | —(extra) |
| `color, scale` |  |  | Figure: Color |

## `\pfSpringScale[keys]` — Spring Scale Generator (/spring-scale)

| key | default | allowed values | generator control |
|---|---|---|---|
| `capacity` | 10 | 1, 2.5, 5, 10, 20, 30, 50 (N) | Capacity |
| `units` | newtons | newtons, grams, both | Printed in: Newtons / Grams / Both (100 g per N) |
| `colored` | true | bool | Color-coded by capacity |
| `reading` | 3.47 | 0…capacity (N) | Reading: Force on the hook |
| `zero` | 0 | −capacity/10…+capacity/10 (N) | Zero offset (pointer rests at reading+zero) |
| `hook` | block | nothing, block, masses | On the hook: Nothing / Block / Slotted masses |
| `block label` | (empty) | math | Label on the block |
| `masses` | 4 | 1–5 | Masses |
| `show` | both | both, instrument, magnifier | Magnifier → Show |
| `magnifier marks` | 2 | 1–6 | Numbered marks in the magnifier |
| `title` | (empty) | text | Chart title |
| `answer key` | false | bool | Answer key |
| `unloaded` | false | bool | Also show it with nothing hanging |
| `length, scale` | 7, 1 | cm / number | —(extra) |

## `\pfWave[keys]` — Wave Generator (/waves)

| key | default | allowed values | generator control |
|---|---|---|---|
| `type` | transverse | transverse, longitudinal, both | Wave: Transverse / Longitudinal / Both |
| `against` | distance | distance, time | Displacement against: Distance / Time |
| `amplitude, wavelength, period, cycles` | 3, 4, 1, 2 | numbers | Amplitude / Wavelength / Period / Cycles |
| `wavelength mark / wavelength label` | true / \lambda | bool / math / ? / {} | Mark the wavelength |
| `amplitude mark / amplitude label` | true / A |  | Mark the amplitude |
| `period mark / period label` | false / T |  | Mark the period (time axis) |
| `crest label, trough label` | {} | text / ? / {} | Crest label / Trough label |
| `compression label, rarefaction label` | {} | text / ? / {} | Compression / Rarefaction label |
| `numbered` | true | bool | Numbered axes, to measure on |
| `gridlines` | true | bool (false = tick marks only) | Gridlines (tick marks without) |
| `axes` | true | bool (false = wave only, dashed centre line) | no-axes worksheet style |
| `title, x title, y title` | {}, auto, Displacement (cm) | text / ? / {} | Titles |
| `xmax, xstep, number every` | auto, auto, 2 | numbers; number every 0 = no numbers | x-axis range, step, numbering (Every line / 2nd / 5th / 10th / No numbers) |
| `ymax, ystep` | auto | numbers (axis runs −ymax…ymax) | y-axis range and step |
| `minor` | 0 | 0, 2, 4, 5 | Grid: minor gridlines per block |
| `width, height, label font, number font` | 11, 6.4, … |  | —(extra) |
| `color, scale` |  |  | Color (for slides) |

## `\pfCircuit[keys]` — Circuit Diagram Generator (/circuit-diagram)

| key | default | allowed values | generator control |
|---|---|---|---|
| `arrangement` | series | series, parallel | Arrangement: In series / In parallel |
| `part={type=..,name=..,value=..}` | 3 resistors R_1…R_3, 2/4/6 Ω | type: resistor, bulb; name/value: math / ? / {} | Part n: Resistor / Bulb, name, value / Add a resistor or bulb |
| `parts={type/name/value,...}` | — | shorthand | same |
| `source` | battery | cell, battery | Cell or battery: One cell / Battery of two cells |
| `source name, source value` | {}, 12\,\mathrm{V} | math / ? / {} | Battery name / value |
| `polarity` | false | bool | + and − beside it |
| `switch` | none | none, closed, open | Switch |
| `ammeter / ammeter reading` | false / {} | bool / math / ? | Ammeter in the main line / Ammeter reading |
| `voltmeter / voltmeter reading` | none / {} | none, source, 1, 2, … (part number) | Voltmeter: Across the battery / Across R_n |
| `symbols` | us | us, iec | Symbol style: US (zigzag) / IEC, UK GCSE (box) |
| `title` | {} | text / ? | Chart title |
| `height, width` | 3.6, auto | cm | —(extra) |
| `mirror, color, scale` |  | mirror is experimental for circuits | Figure |

## Coverage of the generators' option space

| generator | supported | not (yet) supported / approximated |
|---|---|---|
| Free body diagram | body (4), any number of forces with direction, length, label text/blank/none, angle marker, vector notation none/arrow/bold, velocity & acceleration with direction and label, mirror, colour | forces pointing the same way are offset to one side instead of symmetrically; "Add a force" buttons are not separate keys (just type the label) |
| Vector diagram | any number of vectors (magnitude, direction, drawn/dashed/left off, label), resultant drawn/dashed/off/none + label, resultant angle, resultant components, per-vector components & angle, grid, axes, mirror, colour | label placement is heuristic (opposite side of the polygon centroid) |
| Inclined plane | block/ball/cart, label, size, position, 1 or 2 objects tied by a string, angle 5–60 + label, smooth/rough, gravity, normal, friction up/down, applied up/down, tension, velocity, acceleration, length & height marks, all force labels, mirror, colour | more than two stacked objects; separate per-object forces for the 2-object case use subscripts 1/2 automatically |
| Pulley | Atwood (hangs lower, third mass left/right, T₁/T₂), table (block/cart, rough, normal, friction toward/away, acceleration), ramp (block/cart, angle, normal, acceleration), block & tackle (any number of strands, acceleration), tension/gravity labels, mirror, colour | "Add an object on the table / ramp" (several objects in a row); friction on the ramp setup; exact site geometry |
| Projectile motion | ground/cliff, cliff height, angle, angle mark & label, ball/dot & size, path on/off, equal time steps, lettering, launch velocity & components with labels, gravity, max height, range, cliff height marks, mirror, colour | the cliff height is a length in cm rather than the site's slider steps |
| Motion graphs | 5 segment types with speed, duration, direction, any order, start position; x-t / v-t / a-t / all three stacked; letters; per-segment line styles; tangent at a time; chart & axis titles text/blank/none; numbers; gridlines; manual ranges; colour | the site's exact default speeds/durations for segments without numbers are not known — defaults are documented above; manual y-range applies to the x-t graph only |
| Spring scale | 7 capacities, newtons/grams/both, colour-coding, reading, zero offset, nothing/block/slotted masses (1–5), block label, instrument/magnifier/both, numbered marks in magnifier (zoom), title, answer key, "also show with nothing hanging" | "Random" reading button (use `\pgfmathsetmacro` / `\pgfmathrandom` yourself); exact tick pattern for 2.5/20/30 N scales may differ |
| Waves | transverse/longitudinal/both, against distance/time, amplitude, wavelength, period, cycles, wavelength/amplitude/period marks + labels, crest/trough/compression/rarefaction labels, numbered axes, gridlines or ticks, minor gridlines, no-axes mode, titles, x range/step/number-every, y range/step, colour | x-/y-axis end labels ("x-axis label: Text"), arrow-headed axis ends ("plain ends" alternative), asymmetric y range |
| Circuit diagram | series/parallel, any number of resistors/bulbs with name/value text/blank/none, cell/battery with name/value, polarity signs, switch none/closed/open, ammeter + reading, voltmeter across source or any part + reading, US/IEC symbols, title, colour | mirror is experimental for circuits; label sides follow circuitikz conventions, so a few labels sit on the other side compared with the site |

