#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pdflatex -interaction=nonstopmode skill_f2p_causal.tex
pdflatex -interaction=nonstopmode skill_f2p_causal.tex
echo "PDF: $(pwd)/skill_f2p_causal.pdf"
