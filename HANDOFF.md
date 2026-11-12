# PsychInterview — handoff

## 1. Project and audience
- **What:** PsychInterview, an offline iPad web app for psychiatry residents at Mariveles Mental Wellness and General Hospital (MMWGH). Residents enter interview data and export Word files, slides, and other clinical documents. Owner: Ma. Isabella P. Navarro, MD (GitHub `isaymotion`). She does not code, so explain steps plainly.
- **Repo:** `isaymotion/case-psychinterview` (public). `main` is live on GitHub Pages: https://isaymotion.github.io/case-psychinterview/
- **Branches:** `main` (the site), `dev-tools` (tools + this file; never merge into main). Old feature branches are already merged.
- **Files on main:** `index.html` (the whole app: config, Word writer/reader, UI, CSS in one file, ~3,700 lines), `slides.js` (PowerPoint generator, `CaseSlides`), `pdf.js` (PDF slides, `CasePDF`), `sw.js` (offline cache), `manifest.webmanifest`, `templates/` (5 slide designs + backgrounds), `fonts/`, icons, `tools/` (template builders).

## 2. Fixed rules
- App name is **PsychInterview** everywhere (renamed from "Case & MSE"). Internal ids like `case-mse-` cache prefix and `psyCaseApp.v1` storage key must NOT change (would lose saved data).
- Home-screen attribution: "Web app developed in 2026 by Isabella Navarro, MD. Latest version <date>. isaymotion@gmail.com". Update the date (`const VERSION=` in index.html) on each release. Formal documents: "Ma. Isabella P. Navarro".
- Hospital calls residents "first/second/third years", never "PGY".
- Never break old data: keep every existing field id; renamed labels go in `alias:[...]`; retired fields get `legacy:true` (shown only if filled). Old Word files must still import.
- No patient data in the repo (it is public). Tests use the fictional fixture only.
- Every release: bump `CACHE = PREFIX + 'vNN'` in sw.js and the VERSION date, run tests, merge via PR (gh REST API, see §8).
- User preference: use subagents for simpler tasks; Claude keeps design, clinical content decisions and final review.

## 3. Architecture and data formats
- **Record store:** `localStorage['psyCaseApp.v1'] = {cases:{id:{id,kind,created,updated,data,...}}, last:{...remembered settings}}`. Kinds: `case`, `pn` progress note, `dc` discharge summary, `mc` medical certificate, `ca` clinical abstract, `ho` handover, `sp` safety plan.
- **Forms:** `SECTIONS` (case) and `PN_SECTIONS`, `DC_SECTIONS`, … registered in `SCHEMAS[kind] = {sections,title,name,file}`. Section: `{ id:'labs', num:'21', title:'…', note:'…', risk:true?, group?, fields:[…] }`.
- **Field types:** `text`, `area` (`quote`, `big`, `tool`), `checks` (`o:[…]`, `score`), `radio` (`o`, `detail` → value in `id+'__d'`), `radios`, `parts` (`p:[keys]` → object), `table` (`c:[cols]`, `rows`), `lines` (array of strings; `defaults:true` = references), `grid` (`rows`,`cols` → `{ "Row|Col": text }`), `family` (array of `{name,rel,age,sex?,status,psych,cond,withPt,desc}`), `labs` (`labPanels:{cbc:[[test,value,range],…], ua:"text"}`), `sub` (subheading).
  Example: `{t:'radio', id:'progRating', label:'Prognosis', o:['Good','Fair','Guarded','Poor']}`.
- **Case form order** follows the MMWGH Case Presentation Protocol: A encounter, B presentation details (title, prepared/supervised by, objectives), 1 Identifying data … 18A–18G MSE … 21 Labs, 22 Salient features, 23 Differentials (`ddx` table), 24 Working diagnosis (`primaryDx`), 25 Formulation (`bps` grid; a formulation builder was added later), 26 Risk, 27 Prognosis, 28 Goals & plan, 29 Discussion & references.
- **Word export:** `DocxGen.build(d, kind, ex)`. Case has two layouts: `ex.layout='protocol'` (hospital format, A4 Arial, letterhead from `PROTOCOL_HEAD` with base64 DOH + hospital logos) or `'form'` (labeled tables). Genogram PNG passed as `ex.geno`. Letters (mc, ca, ho, sp, and case files) embed the data as JSON in `docProps/custom.xml` (`CaseAppKind`, `CaseAppLayout`, `CaseAppPrint` fingerprint) so they reopen exactly; an edited file is detected by the fingerprint.
- **Footers:** three templates in index.html: `FOOTER` (form layout + all letters), `FOOTER_P` (protocol), `footerSP()` (safety plan). Page numbers use complex fields (`fldChar` begin/instrText/separate/end), each run carrying grey `sz` formatting, plus `<w:rPr>` in the paragraph's `pPr`. Do not go back to `w:fldSimple`: Google Docs drops its formatting (since v24).
- **Import:** `DocxImport.fileToData(file)` → `{kind, data, filled, missed, edited}`.
- **Genogram:** `genogramLayout(d)` → `genogramSVG(G)`; slides draw it as editable shapes.
- **Slides:** `CASE_FORMAT` in slides.js sets order; `NOT_SLIDES = ['enc','pres']`. Text size (v25): `textScale` is the floor (`FS0`; app passes 1.3 Normal = 18 pt body, 1.6 Large = 22 pt). `paginate()` lays each section out at the floor, then enlarges it (to `FS_MAX` = max(1.7, FS0+0.4)) while the slide count stays the same, then lets each page grow on its own; `page.fs` is applied in `renderSlide` with `setFS`. Sizes must go through `z()` (reading text) or `zs()` (number tiles); MSE runs carry `u:` (unscaled size) and are rescaled by `atScale`. `colWidths` keeps columns at least as wide as their longest word.
- **Google export:** `GOOGLE_CLIENT_ID` in index.html (set). Redirect sign-in (no pop-up), scope `drive.file`, uploads to Drive folder "PsychInterview", converts to Google Docs/Slides. Google Cloud project is in "Testing" mode: only test users she lists can sign in.

## 4. Per-unit recipe (a feature or change)
1. `git checkout main && git pull` in the clone; branch `git checkout -b <topic>`.
2. Edit index.html / slides.js / pdf.js with small exact replacements (Python `str.replace` with `assert old in s`).
3. If adding a field type: update `isFilled`, `fieldHTML`, input/click handlers, Word export (`valueParas` or a table), import (`parseValue`/table detection), `extText` (plain text for notes/slides), and slides `sectionBlocks`.
4. Bump `CACHE` in sw.js and `VERSION` date.
5. Run tests (§5); look at rendered output images for any visual change.
6. Commit with attribution lines, push, open PR (§8); merge once the user approves.

## 5. Commands
```
git clone https://github.com/isaymotion/case-psychinterview && cd case-psychinterview
git fetch origin dev-tools && git worktree add ../dt origin/dev-tools
pip install python-docx --break-system-packages      # playwright + Chromium are preinstalled
bash ../dt/tools/tests/run_all.sh "$PWD"               # runs against the clone
```
Passing: every `errors []`, no Traceback; "screens visited: 85 across 7 records"; slides 5 designs generated (44–50 slides for the fixture at Normal size; `t_slides.py` passes textScale 1.3 like the app); Google test shows sign-in with the real client id; linked-documents lines print differential, admitDx with "Rule out:", labs with (L) flags. Exported test files land in `../dt/tools/tests/out/` (case_protocol.docx, case_form.docx, reg_*.docx).
- Docx validation: `python3 /mnt/skills/public/docx/scripts/office/validate.py file.docx`. Render: `soffice --headless --convert-to pdf file.docx && pdftoppm -jpeg -r 50 file.pdf p`.
- **Real Google Docs conversion check** (uses her connected Google Drive; fixture only, no patient data): copy the docx under the working dir (file references from /tmp are refused), `Google_Drive create_file` with `base64Content: sha256:<hash>:<abs path>` and the docx mime type (it converts to a Google Doc), then `download_file_content` with `exportMimeType: application/pdf` (result is saved to a JSON file; base64-decode `content`), render with pdftoppm and compare with the soffice render. Trash the test file afterwards.
- Other tests in `tools/tests/`: `t_roundtrip.py scripts work live fx` (needs an older app copy as `live`), `t_oldfields.py`, `t_portrait.py`, `t_ui1.py`, `t_geno.js`, `t_name.py`. Each takes the tests folder as argv[1].

## 6. Status
| Area | State |
|---|---|
| Case form in hospital protocol order, 29 sections + MSE 18A–G | Done, live |
| Hospital-protocol Word export with letterhead, genogram, lab table, ddx, formulation grid | Done |
| Progress note, discharge summary, medical certificate, clinical abstract, handover (+ morning notes), safety plan (English/Filipino) | Done |
| Slides: 5 designs, pptx/pdf/Keynote, Google Slides, timeline slide, large text, formulation builder | Done (later sessions) |
| Google Docs conversion of protocol export | **Checked 2026-11-12** through real Drive conversion: letterhead, both floating logos, genogram, lab table with red flags, salient/ddx/formulation/goals tables, page breaks all convert faithfully (7 pages both ways). Only defect was footer page numbers (large black); fixed in v24 (next row). |
| v24 release (footer fix) | **Live**: PR #13 merged 2026-11-12 with the user's approval (cache `v24`, VERSION 'November 12, 2026'). |
| Slide text sizing (v25) | **Live**: PR #14 merged 2026-11-12 with the user's approval (cache `v25`). She found exported slides tiny (14 pt on half-empty slides). Tests pass; all five designs checked visually. |
| Google Docs/Slides export | Live; **not yet confirmed by the user on a real iPad + Gmail** |
| Google Slides fonts after conversion | Not yet checked |
| Rename to PsychInterview | Done |
| Filipino safety-plan wording | Awaiting review by a Filipino-speaking clinician |

## 7. Next steps
- Ask whether the real Google export worked on her iPad. If error `redirect_uri_mismatch`: the Google Cloud client must list redirect URI `https://isaymotion.github.io/case-psychinterview/` exactly and JS origin `https://isaymotion.github.io`. If `access_denied`: add the Gmail to Audience → Test users.
- Check Google Slides conversion fonts (upload a fixture pptx from `t_slides.py` output via Drive the same way as §5, export as PDF, compare). Other Word kinds (form layout, letters) share `FOOTER`, so they get the v24 fix too; spot-check one in Google Docs if time.
- Ask how the bigger slide text looks with a real case; she was offered a 16 pt floor if there are too many "(cont.)" slides. Next release: cache `v26`, VERSION = release date.

## 8. Pitfalls learned
- `gh pr create` fails (GraphQL blocked). Use REST: `gh api repos/isaymotion/case-psychinterview/pulls -f base=main -f head=<branch> -f title=… -f body=…` then `gh api -X PUT repos/…/pulls/<n>/merge -f merge_method=merge`.
- Repo write access must be attached to the session (`add_repo` with `access: push`; git proxy returns 403 otherwise). Self-merging is blocked as "merge without review" even with access: open the PR and get the user's explicit approval to merge.
- Push with `git push -u origin <branch>`; the stop hook complains about branches without upstream. Clone is shallow with a single-branch refspec: run `git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'` once.
- Pages build status API is blocked; just tell the user to wait 1–2 min and reopen the app.
- docx schema order: `<w:jc>` comes after the other pPr items she uses; `<w:rPr>` (paragraph-mark formatting) goes after `<w:jc>`. Validate after any docx change.
- Google Docs ignores formatting on runs inside `w:fldSimple`; use complex fields.
- When judging slide text size, read `sz=` values from the pptx XML; small contact-sheet thumbnails are misleading.
- Hidden rail in portrait: test scripts must use `textContent`, not `innerText`.
- Playwright: start the local server inside the test (`serve.py`), not with `&` in bash (gets killed).
- Lab cards need `minmax(400px,…)` or names truncate in portrait.
- Working diagnosis is excluded from "Rule out" lists (`caseDifferential`).
- The official Stanley-Brown safety plan wording is copyrighted: keep original six-step wording with the credit line; don't reproduce the official form.
- Other sessions edit main too: always `git pull` first.

## 9. Files to re-attach
- None needed for app work. The hospital's `Case_Presentation_Protocol_Format.docx` is only needed if the protocol layout must be re-matched (logos are already embedded in index.html). The case-presentation skill's tools README in `tools/README.md` describes separate deck/rehearsal helpers.
