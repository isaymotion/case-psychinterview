# dev-tools: case presentation tools

Generic helpers used with the `case-presentation-prep` Claude skill. **Never commit patient data here** (this repo is public): case.json, notes, Q&A and handouts stay in the chat workspace or the private claude.ai project.

| File | Purpose | Run from |
|---|---|---|
| gen_deck.mjs | Calls `CaseSlides.generate` in the PsychInterview page via Playwright (Unicorn template, textScale 1.3, extra sections from sections.json) | a work folder; needs `python3 -m http.server 8770` running in the folder that contains the `case-psychinterview` checkout |
| remap_notes.py | Writes presenter notes (time per slide + running total) onto a re-paginated deck by slide group; optional `notes_overrides.json` (extra notes, new groups, MSE title, genogram image) | work folder |
| build_rehearsal.py | Builds the Rehearsal app JSON (schema v1) for isaymotion/102526 | work folder |
| render_pdf.mjs | HTML → A4 PDF with confidential footer + page numbers | work folder |
| para_replace.py | Builds Google Docs batchUpdate requests that replace whole paragraphs by prefix (style reset to black, optional bold/italic prefix) | work folder |

Setup in a fresh workspace:
```
git clone https://github.com/isaymotion/case-psychinterview && cd case-psychinterview && git checkout large-text   # until PR #12 is merged
git worktree add ../dt origin/dev-tools
cd .. && python3 -m http.server 8770 &      # serves /case-psychinterview/
pip install python-pptx --break-system-packages
```
gen_deck.mjs loads `http://localhost:8770/case-psychinterview/`; usage: `node dt/tools/gen_deck.mjs case.json sections.json deck_raw.pptx "Ma. Isabella P. Navarro, MD" 2026-10-26T09:00:00+08:00`.
sections.json example: `[{"id":"sczA","title":"Schizophrenia, Criterion A: the HD-SB Network","fields":[{"id":"sczA","t":"table","label":"","c":["","Symptom","How Mark meets it","Status"]}]}]` (inserted after Discussion).
Render check: `soffice --headless --convert-to pdf deck.pptx && pdftoppm -r 28 -png deck.pdf s` then view contact sheets.
