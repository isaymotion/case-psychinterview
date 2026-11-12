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
- **Import:** `DocxImport.fileToData(file)` → `{kind, data, filled, missed, edited}`.
- **Genogram:** `genogramLayout(d)` → `genogramSVG(G)`; slides draw it as editable shapes.
- **Slides:** `CASE_FORMAT` in slides.js sets order; `NOT_SLIDES = ['enc','pres']`.
- **Google export:** `GOOGLE_CLIENT_ID` in index.html (set). Redirect sign-in (no pop-up), scope `drive.file`, uploads to Drive folder "PsychInterview", converts to Google Docs/Slides. Google Cloud project is in "Testing" mode: only test users she lists can sign in.

## 4. Per-unit recipe (a feature or change)
1. `git checkout main && git pull` in the clone; branch `git checkout -b <topic>`.
2. Edit index.html / slides.js / pdf.js with small exact replacements (Python `str.replace` with `assert old in s`).
3. If adding a field type: update `isFilled`, `fieldHTML`, input/click handlers, Word export (`valueParas` or a table), import (`parseValue`/table detection), `extText` (plain text for notes/slides), and slides `sectionBlocks`.
4. Bump `CACHE` in sw.js and `VERSION` date.
5. Run tests (§5); look at rendered output images for any visual change.
6. Commit with attribution lines, push, open PR and merge with gh REST API (§8).

## 5. Commands
```
git clone https://github.com/isaymotion/case-psychinterview && cd case-psychinterview
git fetch origin dev-tools && git worktree add ../dt origin/dev-tools
pip install python-docx --break-system-packages      # playwright + Chromium are preinstalled
bash ../dt/tools/tests/run_all.sh "$PWD"               # runs against the clone
```
Passing: every `errors []`, no Traceback; "screens visited: 85 across 7 records"; slides 5 designs generated (~41–42 slides for the fixture); Google test shows sign-in with the real client id; linked-documents lines print differential, admitDx with "Rule out:", labs with (L) flags.
- Docx validation: `python3 /mnt/skills/public/docx/scripts/office/validate.py file.docx`. Render: `soffice --headless --convert-to pdf file.docx && pdftoppm -jpeg -r 50 file.pdf p`.
- Other tests in `tools/tests/`: `t_roundtrip.py scripts work live fx` (needs an older app copy as `live`), `t_oldfields.py`, `t_portrait.py`, `t_ui1.py`, `t_geno.js`, `t_name.py`. Each takes the tests folder as argv[1].

## 6. Status
| Area | State |
|---|---|
| Case form in hospital protocol order, 29 sections + MSE 18A–G | Done, live |
| Hospital-protocol Word export with letterhead, genogram, lab table, ddx, formulation grid | Done |
| Progress note, discharge summary, medical certificate, clinical abstract, handover (+ morning notes), safety plan (English/Filipino) | Done |
| Slides: 5 designs, pptx/pdf/Keynote, Google Slides, timeline slide, large text, formulation builder | Done (later sessions) |
| Google Docs/Slides export | Live; **not yet confirmed by the user on a real iPad + Gmail** |
| Rename to PsychInterview | Done |
| Filipino safety-plan wording | Awaiting review by a Filipino-speaking clinician |

## 7. Next steps
- Ask whether the real Google export worked on her iPad. If error `redirect_uri_mismatch`: the Google Cloud client must list redirect URI `https://isaymotion.github.io/case-psychinterview/` exactly and JS origin `https://isaymotion.github.io`. If `access_denied`: add the Gmail to Audience → Test users.
- Check Google Docs conversion of the protocol export (floating logos, genogram) and Google Slides fonts; adjust if they convert badly.
- Next release: cache `v24`, VERSION = release date.

## 8. Pitfalls learned
- `gh pr create` fails (GraphQL blocked). Use REST: `gh api repos/isaymotion/case-psychinterview/pulls -f base=main -f head=<branch> -f title=… -f body=…` then `gh api -X PUT repos/…/pulls/<n>/merge -f merge_method=merge`.
- Push with `git push -u origin <branch>`; the stop hook complains about branches without upstream. Clone is shallow with a single-branch refspec: run `git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'` once.
- Pages build status API is blocked; just tell the user to wait 1–2 min and reopen the app.
- docx schema order: `<w:jc>` must come last in `<w:pPr>`; validate after any docx change.
- Hidden rail in portrait: test scripts must use `textContent`, not `innerText`.
- Playwright: start the local server inside the test (`serve.py`), not with `&` in bash (gets killed).
- Lab cards need `minmax(400px,…)` or names truncate in portrait.
- Working diagnosis is excluded from "Rule out" lists (`caseDifferential`).
- The official Stanley-Brown safety plan wording is copyrighted: keep original six-step wording with the credit line; don't reproduce the official form.
- Other sessions edit main too: always `git pull` first.

## 9. Files to re-attach
- None needed for app work. The hospital's `Case_Presentation_Protocol_Format.docx` is only needed if the protocol layout must be re-matched (logos are already embedded in index.html). The case-presentation skill's tools README in `tools/README.md` describes separate deck/rehearsal helpers.
