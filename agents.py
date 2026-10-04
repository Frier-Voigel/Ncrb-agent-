"""Three agents. Gemini does the planning and writing, Python does the maths, Groq double-checks."""
import json
import os
import re
from pathlib import Path

import tools

_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8-sig").splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

NAMES = {"gemini": "Gemini 2.5 Flash", "groq": "Groq"}

ORCH = """You are the Orchestrator of an assistant that answers questions about India's NCRB crime statistics.
Data available: state/UT-wise total IPC/BNS cognizable cases for 2022, 2023, 2024; population (2024); crime rate per lakh population (published for 2024, estimated for 2022/2023); chargesheet rate (2024 only); and NATIONAL crime-head totals (not split by state).
NOT available: districts or cities, crime type by state, special and local laws, years outside 2022-2024, causes or opinions.
Reply with JSON only: {"in_scope": true or false, "tasks": ["self-contained sub-question", ...], "reply": "..."}
- in_scope is true when the question can be answered from the available data.
- tasks has 1 item, or 2 only when the question has two truly independent parts.
- reply is used only when in_scope is false: one friendly sentence saying what you can answer instead."""

PLAN = """You are the Crime Analysis Agent. Choose exactly ONE tool to answer the task.
Tools:
- compare(states: list of 1-6 state names, metric: "crime_rate"|"total_cases"|"chargesheet_rate", years: optional list) -> each year with % change vs previous year
- rank(year: 2022-2024, metric, n: 1-10, order: "desc"|"asc", state_type: optional "State" or "UT", state: optional state name)
  Give state to get ONE state's rank among all of them (use it for "what is X's rank / position"). Without state it lists the top n.
- movers(year_from, year_to, n, order) -> states with the biggest % change in total cases
- heads(year, n, order, contains: optional text) -> NATIONAL crime-head counts (theft, hurt, fraud ...)
Notes: chargesheet_rate exists only for 2024. Default year is 2024. "Highest" means order "desc".
State names must be exactly from: {STATES}
Reply with JSON only: {"tool": "...", "args": {...}}. If no tool can answer: {"tool": null, "reason": "one sentence"}."""

WRITE = """You are the Crime Analysis Agent. Using ONLY the result you are given, answer the task in 2-4 plain sentences.
Rules: every number you write must appear in the result rows or notes, copied exactly (commas allowed, no rounding up to 'lakh' or 'thousand'); mention a caveat from the notes when it matters; no causes, no speculation, no advice.
Reply with JSON only: {"insight": "..."}"""

VERIFY = """You are the Verification Agent. You get a question, the data rows retrieved, notes, and a draft answer.
Check ONLY whether every claim in the draft is supported by the rows: numbers, rankings, comparisons, and directions such as rose or fell.
Reply with JSON only: {"approved": true or false, "issues": ["each unsupported or wrong claim"]}
Approve when every claim is supported. Do not judge style."""


def _json(text):
    text = re.sub(r"```(?:json)?", "", text)
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def _gemini(system, user):
    import requests
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                                   "thinkingConfig": {"thinkingBudget": 0}}},
        timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(system, user):
    import requests
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
        json={"model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"), "temperature": 0,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


_CALL = {"gemini": _gemini, "groq": _groq}


def llm(system, user, order=("gemini", "groq")):
    """Try each provider in turn. Returns (parsed JSON, provider name)."""
    errs = []
    for p in order:
        try:
            return _json(_CALL[p](system, user)), p
        except Exception as e:  # missing key, rate limit, bad JSON ... fall through to the next provider
            errs.append(f"{p}: {type(e).__name__}: {e}")
    raise RuntimeError("; ".join(errs))


def _step(agent, text):
    return {"agent": agent, "text": text}


def _plant(text):
    """Test mode only: swap the first real number in the draft for a wrong one."""
    for m in re.finditer(tools._NUM, text):
        x = float(m.group().replace(",", ""))
        if not (x == int(x) and (x <= 10 or 2000 <= x <= 2100)):
            return text[:m.start()] + f"{x * 1.37:,.1f}" + text[m.end():], m.group()
    return text, None


def analyse(task, plant=False):
    steps = []
    plan_prompt = PLAN.replace("{STATES}", ", ".join(tools.STATES))
    plan, who = llm(plan_prompt, task)
    res = tools.run(plan) if plan.get("tool") else {"error": plan.get("reason") or "no tool fits"}
    if "error" in res:
        steps.append(_step("Analyst", f"First plan did not work ({res['error']}); trying once more"))
        plan, who = llm(plan_prompt, f"{task}\nYour previous plan {json.dumps(plan)} failed: {res['error']}. "
                                      "If the data cannot answer this, return tool null.")
        res = tools.run(plan) if plan.get("tool") else {"error": plan.get("reason") or "no tool fits"}
    if "error" in res:
        return {"task": task, "status": "out_of_scope", "steps": steps, "rows": [], "highlight": [],
                "answer": "The available NCRB data cannot answer that: " + res["error"].rstrip(".") + "."}

    steps.append(_step(f"Analyst ({NAMES[who]})", f"Chose {plan['tool']} with {json.dumps(res['args'])}"))
    steps.append(_step("Python", f"Ran it on the NCRB files: {len(res['rows'])} rows"))
    problems = tools.check(res)
    if problems:
        steps.append(_step("Verifier", "Recompute from the raw files FAILED: " + "; ".join(problems)))
        return {"task": task, "status": "flagged", "steps": steps, "rows": res["rows"], "highlight": [],
                "issues": problems, "answer": "The data check failed, so no answer is shown."}
    steps.append(_step("Verifier", "Recomputed from the raw files: values and ranking match"))

    issues, text = [], ""
    for attempt in range(2):
        hint = f"\nA reviewer found these problems; fix them: {issues}" if issues else ""
        w, who = llm(WRITE, json.dumps({"task": task, "result": res}) + hint)
        text = str(w.get("insight", ""))
        steps.append(_step(f"Analyst ({NAMES[who]})", "Revised the draft" if issues else "Drafted the answer"))
        if plant and attempt == 0:
            text, old = _plant(text)
            if old:
                steps.append(_step("Test mode", f"Injected a wrong number into the draft (replaced {old})"))
        issues = []
        loose = tools.ungrounded(text, res)
        if loose:
            issues.append(f"Numbers not found in the data: {', '.join(loose)}")
            steps.append(_step("Verifier", f"Number check FAILED: {', '.join(loose)}"))
        else:
            steps.append(_step("Verifier", "Number check: every quoted number is in the data"))
        v, who = llm(VERIFY, json.dumps({"question": task, "rows": res["rows"], "notes": res["notes"], "draft": text}),
                     order=("groq", "gemini"))
        if v.get("approved") is True:
            steps.append(_step(f"Verifier ({NAMES[who]})", "Claim check: approved"))
        else:
            issues += [str(i) for i in v.get("issues", [])] or ["Verifier did not approve the draft"]
            steps.append(_step(f"Verifier ({NAMES[who]})", "Claim check: " + "; ".join(issues)))
        if not issues:
            break
    status = "flagged" if issues else "verified"
    highlight = sorted({r["state"] for r in res["rows"] if "state" in r})
    return {"task": task, "status": status, "steps": steps, "rows": res["rows"], "highlight": highlight,
            "issues": issues, "notes": res["notes"], "answer": text}


def answer(question, plant=False):
    plan, who = llm(ORCH, question)
    tasks = [str(t) for t in plan.get("tasks") or []][:2] or [question]
    steps = [_step(f"Orchestrator ({NAMES[who]})",
                   f"Split into {len(tasks)} task(s)" if plan.get("in_scope") else "Question is outside the data")]
    if not plan.get("in_scope"):
        return {"status": "out_of_scope", "steps": steps, "tables": [], "highlight": [], "issues": [],
                "answer": plan.get("reply") or "I can answer questions about state-wise crime counts and rates "
                                               "for 2022-2024 and national crime types."}
    parts = [analyse(t, plant) for t in tasks]
    for p in parts:
        steps += p["steps"]
    statuses = {p["status"] for p in parts}
    status = "flagged" if "flagged" in statuses else "verified" if "verified" in statuses else "out_of_scope"
    steps.append(_step("Orchestrator", "Combined the checked answers"))
    return {"status": status, "steps": steps,
            "answer": "\n".join(p["answer"] for p in parts),
            "tables": [{"title": p["task"], "rows": p["rows"]} for p in parts if p["rows"]],
            "highlight": sorted({s for p in parts for s in p["highlight"]}),
            "issues": [i for p in parts for i in p.get("issues", [])]}
