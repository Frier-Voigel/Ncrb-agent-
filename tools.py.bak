"""Data tools. Python does all the maths; the agents only pick a tool and its arguments."""
import csv
import difflib
import re
from bisect import bisect_right
from pathlib import Path

import pandas as pd

D = Path(__file__).parent
S = pd.read_csv(D / "states.csv")
H = pd.read_csv(D / "crime_heads_india.csv", dtype={"sl": str})
STATES = sorted(S.state.unique())
METRICS = ("crime_rate", "total_cases", "chargesheet_rate")
YEARS = (2022, 2023, 2024)

# name: (row, col, abbreviation) on the tile map, north at the top
TILES = {
    "Ladakh": (0, 3, "LA"),
    "Jammu & Kashmir": (1, 2, "JK"), "Himachal Pradesh": (1, 3, "HP"),
    "Punjab": (2, 2, "PB"), "Chandigarh": (2, 3, "CH"), "Uttarakhand": (2, 4, "UK"),
    "Sikkim": (2, 6, "SK"), "Arunachal Pradesh": (2, 8, "AR"),
    "Rajasthan": (3, 1, "RJ"), "Haryana": (3, 2, "HR"), "Delhi": (3, 3, "DL"),
    "Uttar Pradesh": (3, 4, "UP"), "Bihar": (3, 5, "BR"), "West Bengal": (3, 6, "WB"),
    "Assam": (3, 8, "AS"), "Nagaland": (3, 9, "NL"),
    "Gujarat": (4, 1, "GJ"), "Madhya Pradesh": (4, 3, "MP"), "Chhattisgarh": (4, 4, "CG"),
    "Jharkhand": (4, 5, "JH"), "Meghalaya": (4, 7, "ML"), "Manipur": (4, 9, "MN"),
    "Dadra & Nagar Haveli and Daman & Diu": (5, 1, "DD"), "Maharashtra": (5, 3, "MH"),
    "Odisha": (5, 5, "OD"), "Tripura": (5, 8, "TR"), "Mizoram": (5, 9, "MZ"),
    "Goa": (6, 2, "GA"), "Telangana": (6, 4, "TG"),
    "Karnataka": (7, 3, "KA"), "Andhra Pradesh": (7, 4, "AP"), "A&N Islands": (7, 8, "AN"),
    "Lakshadweep": (8, 1, "LD"), "Kerala": (8, 3, "KL"), "Tamil Nadu": (8, 4, "TN"),
    "Puducherry": (8, 5, "PY"),
}


def _state(name):
    n = str(name).strip()
    low = {s.lower(): s for s in STATES}
    for c in (n.lower(), n.lower().replace(" and ", " & ")):
        if c in low:
            return low[c]
    m = difflib.get_close_matches(n.lower(), list(low), n=1, cutoff=0.6)
    if m:
        return low[m[0]]
    raise ValueError(f"unknown state '{name}'")


def _norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(s).lower().replace("&", " and ")).split())


_KEY = {_norm(s): s for s in STATES}
_KEY.update({  # other spellings found in map files
    "nct of delhi": "Delhi", "orissa": "Odisha", "pondicherry": "Puducherry", "uttaranchal": "Uttarakhand",
    "andaman and nicobar islands": "A&N Islands", "andaman and nicobar": "A&N Islands",
    "andaman nicobar": "A&N Islands", "dadra and nagar haveli": "Dadra & Nagar Haveli and Daman & Diu",
    "daman and diu": "Dadra & Nagar Haveli and Daman & Diu",
})


def resolve(names):
    """Map map-file region names to our state names (None when nothing matches)."""
    out = {}
    for n in names:
        k = _norm(n)
        if k not in _KEY:
            close = difflib.get_close_matches(k, list(_KEY), n=1, cutoff=0.85)
            k = close[0] if close else None
        out[n] = _KEY.get(k)
    return out


def _py(df):
    """DataFrame to plain Python records (NaN becomes None) so it is valid JSON."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _notes(d, metric):
    out = []
    for n in d.notes.dropna():
        out += [p for p in n.split(" | ") if not p.startswith("Rate estimated")]
    if metric == "crime_rate" and d.rate_is_estimated.any():
        out.append("2022/2023 crime rates are estimates: cases divided by 2024 population.")
    return list(dict.fromkeys(out))


def _out(tool, args, rows, notes):
    if not rows:
        raise ValueError("no data for that request")
    return {"tool": tool, "args": args, "rows": rows, "notes": notes}


def _metric(m):
    if m not in METRICS:
        raise ValueError(f"metric must be one of {METRICS}")
    return m


def _year(y):
    y = int(y)
    if y not in YEARS:
        raise ValueError(f"year must be one of {YEARS}")
    return y


def compare(states, metric="crime_rate", years=None):
    metric = _metric(metric)
    sts = list(dict.fromkeys(_state(s) for s in states))[:6]
    d = S[S.state.isin(sts)].sort_values(["state", "year"], kind="stable").copy()
    d["pct_change_vs_prev_year"] = (d.groupby("state")[metric].pct_change(fill_method=None) * 100).round(1)
    if years:
        years = [_year(y) for y in years]
        d = d[d.year.isin(years)]
    cols = ["state", "year", metric, "pct_change_vs_prev_year"]
    return _out("compare", {"states": sts, "metric": metric, "years": years}, _py(d[cols]), _notes(d, metric))


def rank(year=2024, metric="crime_rate", n=5, order="desc", state_type=None, state=None):
    year, metric, n = _year(year), _metric(metric), max(1, min(int(n), 10))
    if order not in ("asc", "desc") or state_type not in (None, "State", "UT"):
        raise ValueError("order is asc|desc, state_type is State|UT")
    d = S[S.year == year]
    if state_type:
        d = d[d.state_type == state_type]
    d = d.dropna(subset=[metric])
    if d.empty:
        raise ValueError(f"{metric} is not available for {year}")
    d = d.sort_values(metric, ascending=order == "asc", kind="stable").reset_index(drop=True)
    args = {"year": year, "metric": metric, "n": n, "order": order, "state_type": state_type, "state": None}
    if state:  # one state's position among all of them
        s = _state(state)
        hit = d.index[d.state == s]
        if len(hit) == 0:
            raise ValueError(f"{s} has no {metric} for {year}" + (f" among the {state_type}s" if state_type else ""))
        rows = _py(d.loc[hit, ["state", "state_type", "year", metric]])
        rows[0]["rank"], rows[0]["out_of"] = int(hit[0]) + 1, len(d)
        return _out("rank", {**args, "state": s}, rows, _notes(d.loc[hit], metric))
    d = d.head(n)
    rows = _py(d[["state", "state_type", "year", metric]])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return _out("rank", args, rows, _notes(d, metric))


def movers(year_from=2023, year_to=2024, n=5, order="desc"):
    yf, yt, n = _year(year_from), _year(year_to), max(1, min(int(n), 10))
    if order not in ("asc", "desc"):
        raise ValueError("order is asc|desc")
    p = S.pivot(index="state", columns="year", values="total_cases")
    d = pd.DataFrame({"state": p.index, "cases_from": p[yf].values, "cases_to": p[yt].values})
    d["pct_change"] = ((d.cases_to / d.cases_from - 1) * 100).round(1)
    d = d.sort_values("pct_change", ascending=order == "asc", kind="stable").head(n)
    sub = S[S.state.isin(d.state) & S.year.isin([yf, yt])]
    notes = _notes(sub, "total_cases") + ["Changes are in total cases, not per-capita rates."]
    args = {"year_from": yf, "year_to": yt, "n": n, "order": order}
    return _out("movers", args, _py(d), notes)


def heads(year=2024, n=10, order="desc", contains=None):
    year, n = _year(year), max(1, min(int(n), 15))
    if order not in ("asc", "desc"):
        raise ValueError("order is asc|desc")
    c, r = f"cases_{year}", f"rate_{year}"
    d = H[H.level.isin(["head", "sub_head"] if contains else ["head"])].dropna(subset=[c])
    d = d[~d.crime_head.str.startswith("Other BNS/IPC")]  # residual bucket, not a crime type
    if contains:
        d = d[d.crime_head.str.contains(str(contains), case=False, regex=False)]
    d = d.sort_values(c, ascending=order == "asc", kind="stable").head(n)
    d = d.rename(columns={c: "cases", r: "rate_per_lakh"})[["sl", "crime_head", "level", "cases", "rate_per_lakh"]]
    d["cases"] = d.cases.astype(int)
    notes = ["National totals only, not available by state.",
             "2022/2023 use IPC heads and 2024 uses BNS heads, so heads new in 2024 have no earlier value.",
             "The residual 'Other BNS/IPC crimes' bucket is left out of rankings."]
    args = {"year": year, "n": n, "order": order, "contains": contains}
    return _out("heads", args, _py(d), notes)


TOOLS = {"compare": compare, "rank": rank, "movers": movers, "heads": heads}


def run(plan):
    """Run {'tool','args'}. Returns a result dict, or {'error': ...} so the Analyst can fix its plan."""
    try:
        f = TOOLS.get(plan.get("tool"))
        if f is None:
            raise ValueError(f"unknown tool {plan.get('tool')!r}; use one of {list(TOOLS)}")
        return f(**(plan.get("args") or {}))
    except (ValueError, TypeError, KeyError) as e:
        return {"error": str(e)}


def map_data(year=2024):
    d = S[S.year == _year(year)].copy()
    breaks = [round(float(b), 1) for b in d.crime_rate.quantile([0.2, 0.4, 0.6, 0.8])]
    rows = _py(d[["state", "state_type", "total_cases", "crime_rate", "chargesheet_rate", "notes"]])
    for r in rows:
        r["row"], r["col"], r["abbr"] = TILES[r["state"]]
        r["bin"] = bisect_right(breaks, r["crime_rate"])
    return {"year": year, "estimated": year != 2024, "breaks": breaks, "states": rows}


# ---------- Verification helpers (independent of the pandas code above) ----------

def check(res):
    """Recompute from the raw CSV files with the stdlib only. Returns a list of problems (empty = all good)."""
    raw = {(r["state"], int(r["year"])): r for r in csv.DictReader(open(D / "states.csv", encoding="utf-8"))}
    num = lambda v: float(v) if v not in ("", None) else None
    t, a, rows, bad = res["tool"], res["args"], res["rows"], []

    if t in ("compare", "rank"):
        m = a["metric"]
        for r in rows:
            src = raw[(r["state"], r["year"])]
            v = num(src[m])
            if (v is None) != (r[m] is None) or (v is not None and abs(v - r[m]) > 0.05):
                bad.append(f"{r['state']} {r['year']} {m}: result {r[m]} but source {v}")
            if m == "crime_rate" and v is not None:
                calc = num(src["total_cases"]) / num(src["population_lakhs"])
                if abs(calc - v) > 2:
                    bad.append(f"{r['state']} {r['year']}: published rate {v} but cases/population gives {calc:.1f}")
    if t == "compare":
        m = a["metric"]
        for r in rows:
            prev = raw.get((r["state"], r["year"] - 1))
            p = num(prev[m]) if prev else None
            c = num(raw[(r["state"], r["year"])][m])
            want = round((c / p - 1) * 100, 1) if p and c is not None else None
            got = r["pct_change_vs_prev_year"]
            if (want is None) != (got is None) or (want is not None and abs(want - got) > 0.11):
                bad.append(f"{r['state']} {r['year']}: % change {got} but source gives {want}")
    elif t == "rank":
        m, y = a["metric"], a["year"]
        pool = [(num(v[m]), k[0]) for k, v in raw.items()
                if k[1] == y and num(v[m]) is not None and (not a["state_type"] or v["state_type"] == a["state_type"])]
        pool.sort(key=lambda x: x[0], reverse=a["order"] == "desc")
        names = [s for _, s in pool]
        if a.get("state"):
            r = rows[0]
            if r["state"] not in names or (r["rank"], r["out_of"]) != (names.index(r["state"]) + 1, len(names)):
                bad.append(f"{r['state']}: rank {r['rank']} of {r['out_of']} differs from recomputed rank")
        elif names[:len(rows)] != [r["state"] for r in rows]:
            bad.append("ranking differs from recomputed ranking")
    elif t == "movers":
        yf, yt = a["year_from"], a["year_to"]
        pool = []
        for s in sorted({k[0] for k in raw}):
            f_, t_ = num(raw[(s, yf)]["total_cases"]), num(raw[(s, yt)]["total_cases"])
            pool.append((round((t_ / f_ - 1) * 100, 1), s, f_, t_))
        for r in rows:
            want = next(x for x in pool if x[1] == r["state"])
            if (want[0], want[2], want[3]) != (r["pct_change"], r["cases_from"], r["cases_to"]):
                bad.append(f"{r['state']}: movers row differs from source")
        pool.sort(key=lambda x: x[0], reverse=a["order"] == "desc")
        if [x[1] for x in pool[:len(rows)]] != [r["state"] for r in rows]:
            bad.append("movers ranking differs from recomputed ranking")
    elif t == "heads":
        y, col = a["year"], f"cases_{a['year']}"
        src = list(csv.DictReader(open(D / "crime_heads_india.csv", encoding="utf-8")))
        by = {(x["sl"], x["crime_head"]): x for x in src}
        for r in rows:
            x = by.get((r["sl"], r["crime_head"]))
            if x is None or num(x[col]) != r["cases"]:
                bad.append(f"{r['crime_head']}: result {r['cases']} but source {x and x[col]}")
        lv = ("head", "sub_head") if a["contains"] else ("head",)
        pool = [x for x in src if x["level"] in lv and num(x[col]) is not None
                and not x["crime_head"].startswith("Other BNS")
                and (not a["contains"] or a["contains"].lower() in x["crime_head"].lower())]
        pool.sort(key=lambda x: num(x[col]), reverse=a["order"] == "desc")
        if [x["crime_head"] for x in pool[:len(rows)]] != [r["crime_head"] for r in rows]:
            bad.append("crime-head ranking differs from recomputed ranking")
    return bad


_NUM = r"\d+(?:,\d{3})*(?:\.\d+)?"


def ungrounded(text, res):
    """Numbers quoted in `text` that appear nowhere in the result rows, notes or arguments."""
    pool = []

    def walk(x):
        if isinstance(x, dict):
            [walk(v) for v in x.values()]
        elif isinstance(x, (list, tuple)):
            [walk(v) for v in x]
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            pool.append(float(x))
        elif isinstance(x, str):
            pool.extend(float(m.replace(",", "")) for m in re.findall(_NUM, x))

    walk([res["rows"], res["notes"], res["args"]])
    bad = []
    for m in re.findall(_NUM, text):
        x = float(m.replace(",", ""))
        if x == int(x) and (x <= 10 or 2000 <= x <= 2100):  # ranks, "top 5", years
            continue
        if not any(abs(x - p) <= 0.051 or x == round(p) for p in pool):
            bad.append(m)
    return bad
