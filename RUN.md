# Run it on your laptop, then deploy

## 1. Run locally (about 10 minutes)
1. Unzip the folder and open it in VS Code (File > Open Folder).
2. Open a terminal in VS Code (Terminal > New Terminal).
3. Install the libraries:
   `pip install -r requirements.txt`
   (If "pip" is not found, use `python -m pip install -r requirements.txt`, or on Windows `py -m pip install -r requirements.txt`.)
4. Make your keys file: copy `.env.example` to a new file named exactly `.env`, then replace the two placeholder words with your real keys. No quotes, no spaces around `=`.
5. Run the checks (no keys needed): `python test_app.py`
   You should see 8 lines starting with `ok`.
6. Start the app: `python -m uvicorn main:app --reload`
7. Open http://127.0.0.1:8000 in your browser. Click the example questions.
   Every question you ask is saved in `cache.json`, so the demo answers load instantly later.

If anything shows an error, copy the whole error text from the terminal and send it to me.

## 2. Put it on GitHub
1. On github.com click New repository, name it `ncrb-agent`, leave "Add a README" unticked, and create it.
2. In the VS Code terminal, run these one at a time (replace the URL with yours):
   `git init`
   `git add .`
   `git commit -m "first version"`
   `git branch -M main`
   `git remote add origin https://github.com/YOUR-NAME/ncrb-agent.git`
   `git push -u origin main`
3. Refresh the GitHub page. Check that `.env` is NOT in the file list. If it is, tell me right away and replace your keys.

## 3. Deploy on Render (one service, no Vercel needed)
1. On render.com click New + > Web Service, and pick your `ncrb-agent` repo.
2. Settings: Runtime Python 3, Build Command `pip install -r requirements.txt`, Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT`, Instance Type Free.
3. Under Environment Variables add `GEMINI_API_KEY` and `GROQ_API_KEY` with your keys.
4. Click Deploy. When it says Live, open the URL shown at the top. The first load can take about a minute.
5. Free services sleep after 15 idle minutes, so open the URL a few minutes before your demo.

## Optional settings
- `GROQ_MODEL`: the second model's name on Groq (default `openai/gpt-oss-120b`). Change it here if Groq retires that model.
