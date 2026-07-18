#!/usr/bin/env bash
# Regenerate docs/optimizer-math.pdf — a typeset "research paper" PDF from
# docs/optimizer-math.md (GitHub can't render the LaTeX). Needs `pandoc` and a
# LaTeX engine (`pdflatex`, from TeX Live) with KOMA-Script, scrlayer-scrpage,
# nowidow, fvextra, microtype, mathtools (all in a full texlive install).
# Usage: bash docs/build-math-pdf.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # repo root
SRC=docs/optimizer-math.md
OUT=docs/optimizer-math.pdf
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Each top-level section starts on a fresh page. pandoc applies the Lua filter
# BEFORE --shift-heading-level-by, so the doc's `##` sections are level 2 here.
cat > "$TMP/sectionbreak.lua" <<'LUA'
function Header(el)
  if el.level == 2 then
    return { pandoc.RawBlock('latex', '\\clearpage'), el }
  end
end
LUA

# Clean margins, Latin Modern, running headers (title | section), page-per-toc,
# widow/orphan control, wrapped code. Sections keep their manual numbers.
cat > "$TMP/header.tex" <<'TEX'
\usepackage[a4paper,top=2.6cm,bottom=2.6cm,left=2.7cm,right=2.7cm,headsep=0.9cm,includehead]{geometry}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{mathtools}
\usepackage[all]{nowidow}
\usepackage{fvextra}
\fvset{breaklines=true,breakanywhere=true,fontsize=\small}
\usepackage[headsepline]{scrlayer-scrpage}
\clearpairofpagestyles
\automark[section]{section}
\ihead{\small\itshape Relic Build Optimizer}
\ohead{\small\itshape\headmark}
\cfoot*{\pagemark}
\setcounter{secnumdepth}{-1}
\setlength{\jot}{5pt}
\let\nrtoc\tableofcontents
\renewcommand{\tableofcontents}{\clearpage\nrtoc}
TEX

# Strip the H1 + the GitHub-only PDF note, lift the intro paragraph into the
# abstract, and prepend the paper front-matter.
python3 - "$SRC" "$TMP/paper.md" <<'PY'
import sys
src, out = sys.argv[1], sys.argv[2]
L = open(src, encoding="utf-8").read().splitlines()
i = 1 if (L and L[0].startswith("# ")) else 0
while i < len(L) and L[i].strip() == "": i += 1
if i < len(L) and L[i].lstrip().startswith(">"):           # skip the "get the PDF" note
    while i < len(L) and L[i].strip() != "": i += 1
    while i < len(L) and L[i].strip() == "": i += 1
intro = []
while i < len(L) and L[i].strip() != "": intro.append(L[i]); i += 1
while i < len(L) and L[i].strip() == "": i += 1
body = "\n".join(L[i:])
abstract = " ".join(x.strip() for x in intro)
yaml = ("---\n"
        'title: "Relic Build Optimizer"\n'
        'subtitle: "Mathematical Formulation, Guarantees, and Empirical Validation"\n'
        'author: "zestones · github.com/zestones/Evil-Nightreign"\n'
        'date: "July 2026"\n'
        "abstract: |\n  " + abstract + "\n"
        "---\n\n")
open(out, "w", encoding="utf-8").write(yaml + body)
PY

pandoc "$TMP/paper.md" -o "$OUT" \
  --pdf-engine=pdflatex --shift-heading-level-by=-1 \
  --toc --toc-depth=2 --lua-filter="$TMP/sectionbreak.lua" \
  -V documentclass=scrartcl -V classoption=titlepage -V classoption=parskip=half- \
  -V fontsize=11pt \
  -V colorlinks=true -V linkcolor=black -V 'urlcolor=blue!50!black' -V toccolor=black \
  -H "$TMP/header.tex"

echo "wrote $OUT"
