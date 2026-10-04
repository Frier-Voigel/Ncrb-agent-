# NCRB Agent: Checklist (19 of 31 done)

Hackathon: 4 Oct 2026. Map: crime rate only. Models: Gemini 2.5 Flash plus Groq. [x] = done.

## A. Data (5/5)
- [x] State-wise totals file (crime_data.csv, cleaned into states.csv)
- [x] National crime-head file (crime_heads_india.csv)
- [x] Cleaned states.csv: notes column, 2022/23 rates estimated and flagged, totals cross-checked
- [x] Scope decided: state/UT level, IPC/BNS cognizable crimes, map by crime rate
- [x] Map approach: tile map built into the page (no boundary file needed)

## B. Accounts and keys (5/5)
- [x] Gemini API key
- [x] Groq API key
- [x] GitHub account
- [x] Render account (hosts everything; Vercel is not needed)
- [x] Vercel account (optional, unused)

## C. Software (4/4)
- [x] Python
- [x] Node.js
- [x] Git
- [x] VS Code

## D. Build (5/7)
- [x] tools.py: compare, rank, movers, crime heads, plus the independent recompute check
- [x] agents.py: Orchestrator, Analyst, Verifier and their prompts
- [x] main.py: the web server
- [x] index.html: tile map, chat, verified badge, "how this was checked" steps
- [x] test_app.py: 8 checks pass with faked model answers
- [ ] YOU: create .env with your two keys (steps in RUN.md)
- [ ] YOU: run with real keys, ask 10 questions, send me any error text

## E. Deploy (0/5)
- [ ] Code pushed to GitHub (.env must not be on GitHub)
- [ ] Render web service created
- [ ] Both keys added as Render environment variables
- [ ] Live URL tested on your phone
- [ ] Live URL opened a few minutes before the demo (free hosting sleeps)

## F. Demo (0/5)
- [ ] 5 demo questions run once locally so they are saved in cache.json, then committed to GitHub
- [ ] Test mode shown once: tick the checkbox and watch the verifier catch the wrong number
- [ ] Short screen recording as a backup
- [ ] Limits ready to say out loud: no crime type by state, 2022/23 rates are estimates
- [ ] 2-minute pitch rehearsed once

## Data cautions for the pitch
- Manipur fell 76% in 2024 after its 2023 spike; Kerala and Andhra Pradesh fell 29% and 25%. Could be real or reporting changes.
- Delhi's rate (1,258.5) is far above everyone else, so the map uses quantile colour bins.
- 2022/23 use IPC heads and 2024 uses BNS heads, so compare crime types across years only where both exist.
