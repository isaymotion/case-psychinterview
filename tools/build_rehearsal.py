"""Build the Rehearsal app JSON (schema v1) from presenter notes and a Q&A file.
usage: python3 build_rehearsal.py notes.json groups.json slide_map.json qa.json numbers.json meta.json OUT.json
  notes.json      {"<baseline slide #>": [seconds, "note text"], ...}
  groups.json     [["Section title", [baseline slide #s]], ...]
  slide_map.json  {"<baseline slide #>": [final slide numbers]}  (written by remap_notes.py)
  qa.json         [{"cat":..., "q":..., "a":[...], "tip":opt, "ref":opt}, ...]
  numbers.json    [{"group":..., "items":[{"label":..., "value":..., "note":opt}]}]
  meta.json       {"title":..., "presenter":..., "date":...}
"""
import json, re, sys
notes, groups, smap, qa, numbers, meta = [json.load(open(p)) for p in sys.argv[1:7]]
ABBR = r'(?<!\bDr\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bMrs\.)(?<!\bvs\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bSt\.)'
def sentences(t):
    return [x.strip() for x in re.split(ABBR + r'(?<=[.!?])\s+(?=[A-Z0-9“\'(])', t) if x.strip()]
sections = []
for i, (title, ids) in enumerate(groups, 1):
    secs = sum(notes[str(k)][0] for k in ids)
    body = [s for k in ids for s in sentences(notes[str(k)][1])]
    nums = sorted({n for k in ids for n in smap.get(str(k), [])})
    label = f"{title} (slides {nums[0]}–{nums[-1]})" if len(nums) > 1 else (f"{title} (slide {nums[0]})" if nums else title)
    sections.append({"id": f"s{i}", "title": label, "minutes": round(secs / 60, 2), "notes": body})
Q = [dict(id=f"q{i}", **q) for i, q in enumerate(qa, 1)]
out = {"v": 1, **meta, "sections": sections, "qa": Q, "numbers": numbers}
json.dump(out, open(sys.argv[7], 'w'), ensure_ascii=False, indent=1)
print(len(sections), 'sections', round(sum(s['minutes'] for s in sections), 1), 'min;', len(Q), 'questions')
