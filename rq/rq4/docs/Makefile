# Render progress.md → progress.pdf (advisor-facing).
# Requires pandoc (brew install pandoc) and a LaTeX engine (xelatex on macOS).
#
#   make            # rebuild PDF
#   make clean      # remove generated PDF
#
.PHONY: pdf clean
SRC := progress.md
OUT := progress.pdf

pdf:
	@command -v pandoc >/dev/null || { echo "pandoc not found: brew install pandoc"; exit 1; }
	pandoc $(SRC) \
	  --resource-path=.:.. \
	  --from markdown \
	  --pdf-engine=xelatex \
	  --toc --toc-depth=2 \
	  --metadata title="RQ4 Progress Report" \
	  --metadata author="Eamin C." \
	  --metadata date="$(shell date +%Y-%m-%d)" \
	  -V geometry:margin=1in \
	  -V mainfont="Helvetica" \
	  -V monofont="Menlo" \
	  -V mathfont="STIX Two Math" \
	  -V colorlinks=true \
	  -o $(OUT)

clean:
	rm -f $(OUT)
