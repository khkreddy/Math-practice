#!/usr/bin/env bash
# Compile figures/sources/*.tex with latex + dvisvgm into web/figures/*.svg.
# Requires TeX Live (standalone, tikz) and dvisvgm. mathfig is vendored.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/figures/sources"
out="$root/web/figures"
work="$src/build"
mkdir -p "$out" "$work"
export TEXINPUTS="$root/vendor/mathfig//:${TEXINPUTS:-}"
shopt -s nullglob
found=0
for tex in "$src"/*.tex; do
  found=1
  name="$(basename "$tex" .tex)"
  cp "$tex" "$work/$name.tex"
  if [[ -f "$src/$name.tikz" ]]; then
    cp "$src/$name.tikz" "$work/$name.tikz"
  fi
  (
    cd "$work"
    latex -interaction=nonstopmode "$name.tex" >/dev/null
    dvisvgm --no-fonts --exact -o "$out/$name.svg" "$name.dvi"
  )
  echo "wrote web/figures/$name.svg"
done
if [[ "$found" -eq 0 ]]; then
  echo "no figures/sources/*.tex" >&2
  exit 1
fi
rm -f "$work"/*.aux "$work"/*.log "$work"/*.dvi "$work"/*.tex "$work"/*.tikz
