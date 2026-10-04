"""Run with:  python test_app.py   (no AI keys needed; the model calls are faked)."""
import agents
import tools


def test_tiles_cover_every_state():
    assert set(tools.TILES) == set(tools.STATES)
    cells = [(r, c) for r, c, _ in tools.TILES.values()]
    assert len(cells) == len(set(cells))


def test_known_answers():
    top = tools.run({"tool": "rank", "args": {"year": 2024, "n": 1}})["rows"][0]
    assert (top["state"], top["crime_rate"]) == ("Delhi", 1258.5)
    assert tools.run({"tool": "movers", "args": {}})["rows"][0]["state"] == "Telangana"
    assert tools.run({"tool": "heads", "args": {"n": 1}})["rows"][0]["crime_head"] == "Theft"
    assert "error" in tools.run({"tool": "rank", "args": {"year": 2023, "metric": "chargesheet_rate"}})


def test_verifier_catches_a_wrong_number():
    res = tools.run({"tool": "rank", "args": {"n": 3}})
    assert tools.check(res) == []
    assert tools.ungrounded("Delhi leads at 1,258.5 per lakh.", res) == []
    assert tools.ungrounded("Delhi leads at 1,300 per lakh.", res) == ["1,300"]
    res["rows"][0]["crime_rate"] = 999.0  # corrupt the data
    assert tools.check(res)


def fake_llm(draft_first, draft_second=None, approve=True):
    drafts = [draft_first, draft_second or draft_first]

    def f(system, user, order=("gemini", "groq")):
        if system is agents.ORCH:
            return {"in_scope": True, "tasks": ["Which state has the highest crime rate?"]}, "gemini"
        if system.startswith("You are the Crime Analysis Agent. Choose"):
            return {"tool": "rank", "args": {"year": 2024, "n": 1}}, "gemini"
        if system is agents.WRITE:
            return {"insight": drafts.pop(0) if len(drafts) > 1 else drafts[0]}, "gemini"
        return {"approved": approve, "issues": [] if approve else ["claim not supported"]}, "groq"
    return f


def test_pipeline_verified():
    agents.llm = fake_llm("Delhi has the highest rate, 1,258.5 per lakh.")
    out = agents.answer("q")
    assert out["status"] == "verified" and out["highlight"] == ["Delhi"]


def test_pipeline_fixes_bad_draft_then_verifies():
    agents.llm = fake_llm("Delhi has 1,999.0 per lakh.", "Delhi has 1,258.5 per lakh.")
    assert agents.answer("q")["status"] == "verified"


def test_pipeline_flags_when_it_cannot_be_fixed():
    agents.llm = fake_llm("Delhi has 1,999.0 per lakh.")
    assert agents.answer("q")["status"] == "flagged"


def test_pipeline_flags_when_verifier_disapproves():
    agents.llm = fake_llm("Delhi has 1,258.5 per lakh.", approve=False)
    assert agents.answer("q")["status"] == "flagged"


def test_test_mode_plants_error_and_it_gets_corrected():
    agents.llm = fake_llm("Delhi has 1,258.5 per lakh.")
    out = agents.answer("q", plant=True)
    assert out["status"] == "verified"
    assert any("Number check FAILED" in s["text"] for s in out["steps"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok  ", name)
