"""Adds crime_type to the NCRB Crime Explorer.
Run from the project folder (the one with main.py):   python apply_crime_type.py
Edits tools.py, main.py, index.html, test_app.py in place. Originals are saved as *.bak.
Safe to run twice: it stops if a file is already patched or doesn't match."""
import json
import shutil
import sys
from pathlib import Path

D = Path(__file__).parent
FILES = ["tools.py", "main.py", "index.html", "test_app.py"]


def load(p):
    raw = (D / p).read_bytes().decode("utf-8")
    return raw.replace("\r\n", "\n"), "\r\n" in raw


def save(p, text, crlf):
    (D / p).write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def patch(name, pairs):
    s, crlf = load(name)
    for old, new in pairs:
        if s.count(old) != 1:
            sys.exit(f"STOP: {name}: expected one match, found {s.count(old)} for:\n{old[:120]}\n"
                     "(already patched, or the file differs from the original). Nothing was changed.")
        s = s.replace(old, new)
    return name, s, crlf


# ------------------------------------------------------------------ tools.py
tools = [
('YEARS = (2022, 2023, 2024)\n',
 'YEARS = (2022, 2023, 2024)\nALL_CRIMES = "All crimes (IPC/BNS total)"  # state files hold totals only, so this is their crime_type\n'),
('''    cols = ["state", "year", metric, "pct_change_vs_prev_year"]
    return _out("compare"''',
 '''    d["crime_type"] = ALL_CRIMES
    cols = ["state", "crime_type", "year", metric, "pct_change_vs_prev_year"]
    return _out("compare"'''),
('''    d = d.sort_values(metric, ascending=order == "asc", kind="stable").reset_index(drop=True)
    args =''',
 '''    d = d.sort_values(metric, ascending=order == "asc", kind="stable").reset_index(drop=True)
    d["crime_type"] = ALL_CRIMES
    args ='''),
('rows = _py(d.loc[hit, ["state", "state_type", "year", metric]])',
 'rows = _py(d.loc[hit, ["state", "state_type", "crime_type", "year", metric]])'),
('rows = _py(d[["state", "state_type", "year", metric]])',
 'rows = _py(d[["state", "state_type", "crime_type", "year", metric]])'),
('''    d["pct_change"] = ((d.cases_to / d.cases_from - 1) * 100).round(1)
    d = d.sort_values("pct_change"''',
 '''    d["pct_change"] = ((d.cases_to / d.cases_from - 1) * 100).round(1)
    d.insert(1, "crime_type", ALL_CRIMES)
    d = d.sort_values("pct_change"'''),
('''    d = d.rename(columns={c: "cases", r: "rate_per_lakh"})[["sl", "crime_head", "level", "cases", "rate_per_lakh"]]''',
 '''    d = d.rename(columns={c: "cases", r: "rate_per_lakh", "crime_head": "crime_type"})[["sl", "crime_type", "level", "cases", "rate_per_lakh"]]'''),
("TOOLS = {", '''def crime_type_list():
    """Main crime types (heads) in the national file, for the filter dropdown."""
    d = H[(H.level == "head") & ~H.crime_head.str.startswith("Other BNS/IPC")]
    return sorted(d.crime_head.unique())


def crime_breakdown(year=2024, types=None, n=15, order="desc"):
    """National counts and rates per crime_type, for the breakdown chart/table. `types` filters to chosen crime types."""
    year, n = _year(year), max(1, min(int(n), 70))
    if order not in ("asc", "desc"):
        raise ValueError("order is asc|desc")
    c, r = f"cases_{year}", f"rate_{year}"
    d = H[(H.level == "head") & ~H.crime_head.str.startswith("Other BNS/IPC")].dropna(subset=[c])
    if types:
        known = set(crime_type_list())
        bad = [t for t in types if t not in known]
        if bad:
            raise ValueError(f"unknown crime type(s): {bad}")
        d = d[d.crime_head.isin(types)]
    d = d.sort_values(c, ascending=order == "asc", kind="stable").head(n)
    d = d.rename(columns={c: "cases", r: "rate_per_lakh", "crime_head": "crime_type"})[["crime_type", "cases", "rate_per_lakh"]]
    d["cases"] = d.cases.astype(int)
    notes = ["National totals only: NCRB crime types are not split by state in our files.",
             "2022/2023 use IPC heads and 2024 uses BNS heads, so some types have no value for earlier years."]
    return {"year": year, "scope": "India (national)", "rows": _py(d), "notes": notes}


TOOLS = {'''),
('''    for r in rows:
        r["row"], r["col"], r["abbr"] = TILES[r["state"]]''',
 '''    for r in rows:
        r["crime_type"] = ALL_CRIMES
        r["row"], r["col"], r["abbr"] = TILES[r["state"]]'''),
('return {"year": year, "estimated": year != 2024, "breaks": breaks, "states": rows}',
 'return {"year": year, "crime_type": ALL_CRIMES, "estimated": year != 2024, "breaks": breaks, "states": rows}'),
('by = {(x["sl"], x["crime_head"]): x for x in src}',
 'by = {(x["sl"], x["crime_head"]): x for x in src}  # source file still uses crime_head'),
('x = by.get((r["sl"], r["crime_head"]))', 'x = by.get((r["sl"], r["crime_type"]))'),
('''bad.append(f"{r['crime_head']}: result''', '''bad.append(f"{r['crime_type']}: result'''),
('if [x["crime_head"] for x in pool[:len(rows)]] != [r["crime_head"] for r in rows]:',
 'if [x["crime_head"] for x in pool[:len(rows)]] != [r["crime_type"] for r in rows]:'),
]

# ------------------------------------------------------------------ main.py
main = [
("from fastapi import FastAPI\n", "from fastapi import FastAPI, HTTPException\n"),
("class Names(BaseModel):", '''@app.get("/crime_types")
def crime_types(year: int = 2024, types: str = "", n: int = 15):
    """National breakdown by crime_type. types = '|'-separated crime types (empty = top n of all)."""
    chosen = [t.strip() for t in types.split("|") if t.strip()]
    try:
        out = tools.crime_breakdown(year, chosen or None, n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    out["available"] = tools.crime_type_list()
    return out


class Names(BaseModel):'''),
]

# ------------------------------------------------------------------ test_app.py
tests = [
('["rows"][0]["crime_head"] == "Theft"', '["rows"][0]["crime_type"] == "Theft"'),
("def test_rank_of_one_state():", '''def test_every_stat_row_has_crime_type():
    for plan in ({"tool": "rank", "args": {"n": 2}}, {"tool": "compare", "args": {"states": ["Kerala"]}},
                 {"tool": "movers", "args": {}}, {"tool": "heads", "args": {"n": 2}}):
        res = tools.run(plan)
        assert all(r["crime_type"] for r in res["rows"]), plan
        assert tools.check(res) == []
    assert all(s["crime_type"] == tools.ALL_CRIMES for s in tools.map_data(2024)["states"])


def test_crime_breakdown_and_filter():
    top = tools.crime_breakdown(2024, None, 3)["rows"]
    assert top[0]["crime_type"] == "Theft" and len(top) == 3
    one = tools.crime_breakdown(2024, ["Rape", "Theft"])["rows"]
    assert {r["crime_type"] for r in one} == {"Rape", "Theft"}
    try:
        tools.crime_breakdown(2024, ["Nope"])
        assert False
    except ValueError:
        pass


def test_rank_of_one_state():'''),
]

# ------------------------------------------------------------------ index.html
html = [
("  footer { padding-bottom:32px;", """  .wide { grid-column:1 / -1; }
  .ctl { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-start; margin-bottom:12px; }
  .ctl label { font-size:.85rem; color:var(--muted); display:flex; flex-direction:column; gap:4px; }
  select { font:inherit; border:1px solid var(--line); border-radius:8px; padding:6px 8px; background:#fff; max-width:100%; }
  select[multiple] { min-width:260px; height:120px; }
  .ctl button { font:inherit; border:1px solid var(--line); background:#fff; border-radius:8px; padding:6px 12px; cursor:pointer; align-self:flex-end; }
  .bars { display:grid; gap:4px; margin:8px 0 12px; }
  .bar { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(0,2fr) 70px; gap:8px; align-items:center; font-size:.85rem; }
  .bar .lab { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .bar .track { background:var(--bg); border-radius:4px; height:14px; }
  .bar .fill { background:var(--accent); height:100%; border-radius:4px; }
  .bar .val { text-align:right; font-variant-numeric:tabular-nums; }
  .tag { display:inline-block; padding:1px 8px; border-radius:999px; border:1px solid var(--line); font-size:.8rem; color:var(--muted); }
  footer { padding-bottom:32px;"""),
('    <div class="legend" id="legend"></div>',
 '    <p class="small">Crime type shown: <span class="tag" id="maptype">All crimes (IPC/BNS total)</span></p>\n    <div class="legend" id="legend"></div>'),
('''  </section>
</main>''', '''  </section>

  <section class="wide" aria-labelledby="typehead">
    <h2 id="typehead">Crime types in India</h2>
    <p class="small">National counts for each crime type. The state map above uses all crimes together because NCRB crime types are not split by state in our data.</p>
    <div class="ctl">
      <label>Crime type (hold Ctrl or Cmd to pick several)
        <select id="typesel" multiple aria-label="Filter by crime type"></select>
      </label>
      <button id="typeclear" type="button">Show top 15</button>
    </div>
    <div class="bars" id="typebars" aria-label="Cases by crime type"></div>
    <div id="typetable"></div>
    <p class="small" id="typenote"></p>
  </section>
</main>'''),
("Crime types are available nationally only, not by state.",
 'Crime types are available nationally only, not by state; state rows are labelled "All crimes".'),
("let mapData = null, byState = {}, hl = new Set(), selected = null;",
 "let mapData = null, byState = {}, hl = new Set(), selected = null, curYear = 2024, typesLoaded = false;"),
('''l.bindTooltip(() => { const s = stateOf(f); return el("span", s ? `${s.state}: ${fmt(s.crime_rate)} per lakh` : `${nameOf(f)}: no data`); });''',
 '''l.bindTooltip(() => { const s = stateOf(f); return el("span", s ? `${s.state} (${s.crime_type}): ${fmt(s.crime_rate)} per lakh` : `${nameOf(f)}: no data`); });'''),
('''  const r = await fetch("/map?year=" + year);
  mapData = await r.json();''', '''  curYear = +year;
  const r = await fetch("/map?year=" + year);
  mapData = await r.json();'''),
('''  drawMap();
}

function restyle()''', '''  drawMap();
  loadTypes();
}

function restyle()'''),
('b.setAttribute("aria-label", `${s.state}, ${fmt(s.crime_rate)} per lakh`);',
 'b.setAttribute("aria-label", `${s.state}, ${s.crime_type}, ${fmt(s.crime_rate)} per lakh`);'),
('  $("#mapnote").textContent = mapData.estimated ? "Estimated rates: cases divided by 2024 population." : "";',
 '  $("#maptype").textContent = mapData.crime_type;\n  mapNote();'),
('let t = `${s.state} (${s.state_type}): ${fmt(s.total_cases)} cases,',
 'let t = `${s.state} (${s.state_type}) [${s.crime_type}]: ${fmt(s.total_cases)} cases,'),
("const BADGE = {", '''function mapNote() {
  const t = [];
  if (mapData && mapData.estimated) t.push("Estimated rates: cases divided by 2024 population.");
  if (chosenTypes().length) t.push("The map still shows all crimes together; crime types are national only.");
  $("#mapnote").textContent = t.join(" ");
}

function chosenTypes() { return [...$("#typesel").selectedOptions].map(o => o.value); }

async function loadTypes() {
  const types = chosenTypes();
  try {
    const r = await fetch(`/crime_types?year=${curYear}&n=${types.length ? 70 : 15}&types=${encodeURIComponent(types.join("|"))}`);
    if (!r.ok) throw new Error("bad response");
    const d = await r.json();
    if (!typesLoaded) {   // fill the dropdown once
      d.available.forEach(t => { const o = el("option", t); o.value = t; $("#typesel").append(o); });
      typesLoaded = true;
    }
    drawTypes(d);
  } catch (e) {
    $("#typebars").replaceChildren(el("p", "Could not load crime types.", "small"));
    $("#typetable").replaceChildren();
  }
}

function drawTypes(d) {
  const max = Math.max(...d.rows.map(r => r.cases), 1), bars = $("#typebars");
  bars.replaceChildren();
  d.rows.forEach(r => {
    const row = el("div", null, "bar"), track = el("div", null, "track"), fill = el("div", null, "fill");
    fill.style.width = (r.cases / max * 100) + "%";
    track.append(fill);
    const lab = el("span", r.crime_type, "lab"); lab.title = r.crime_type;
    row.append(lab, track, el("span", fmt(r.cases), "val"));
    bars.append(row);
  });
  $("#typetable").replaceChildren(table(d.rows));
  $("#typenote").textContent = `${d.year}, ${d.scope}. ` + d.notes.join(" ");
  mapNote();
}

$("#typesel").onchange = loadTypes;
$("#typeclear").onclick = () => { [...$("#typesel").options].forEach(o => o.selected = false); loadTypes(); };

const BADGE = {'''),
]

if __name__ == "__main__":
    for f in FILES:
        if not (D / f).exists():
            sys.exit(f"STOP: {f} not found. Run this script from the project folder.")
    done = [patch("tools.py", tools), patch("main.py", main), patch("index.html", html), patch("test_app.py", tests)]
    for name, text, crlf in done:          # everything matched, so now write
        shutil.copy(D / name, D / (name + ".bak"))
        save(name, text, crlf)
        print("patched", name)
    cf = D / "cache.json"                  # old saved answers have no crime_type column
    if cf.exists():
        try:
            c = json.loads(cf.read_text(encoding="utf-8"))
            keep = {k: v for k, v in c.items() if "crime_type" in json.dumps(v)}
            if len(keep) != len(c):
                shutil.copy(cf, D / "cache.json.bak")
                cf.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
                print(f"cache.json: dropped {len(c) - len(keep)} old answer(s) so they regenerate with crime_type")
        except (OSError, ValueError):
            pass
    print("\nDone. Next: python test_app.py   then restart:  python -m uvicorn main:app --reload")
