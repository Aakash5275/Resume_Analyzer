# FitRank

FitRank is an NLP web app that screens a resume against a job description and builds a tailored resume for that job.

It extracts skills, experience, and education from unstructured text, scores how well a candidate matches a role, and can draft a formatted resume (with or without a photo) that you can preview, edit, and download as a PDF.

## Features

- **Screen** — paste or upload a resume and a job description (TXT, PDF, or DOCX). Get a match score, required-skill coverage, and a gap report (matched vs missing skills).
- **Resume builder** — paste a job description (and optionally your current resume). Choose a **with photo** or **without photo** layout, edit the preview, and download a PDF.
- The builder uses skills from the job description. It keeps your real experience when you provide a resume. It does not invent jobs.

Match score weights:

```
0.55 skill coverage + 0.15 TF-IDF + 0.15 experience + 0.10 education + 0.05 preferred
```

## Requirements

- Python 3.10 or newer
- pip

On Windows, if `pip.exe` or `streamlit.exe` is blocked, use `python -m pip` and `python -m streamlit`.

## Setup and run (local)

1. Open a terminal in this project folder.

2. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

4. (Optional) Download the Kaggle resume corpus. The Screen and Resume builder pages do **not** need this:

```bash
python load_kaggle.py
```

5. Start the app:

```bash
python -m streamlit run app.py
```

6. Open the URL Streamlit prints, usually [http://localhost:8501](http://localhost:8501).

### CLI (optional)

```bash
python cli.py --resume your_resume.txt --jd job.txt
```

## Deploy on Streamlit Community Cloud

Streamlit Community Cloud hosts this app for free and gives you a public URL like `https://your-app.streamlit.app`.

You need:

- A [GitHub](https://github.com) account
- This project pushed to a GitHub repository (commands are at the bottom of this file)
- A [Streamlit Community Cloud](https://share.streamlit.io) account (sign in with the same GitHub account)

### Steps

1. Confirm the repo contains at least:
   - `app.py` (the Streamlit entry file)
   - `requirements.txt`
   - the `src/` folder
   - `.streamlit/config.toml` (theme)

   Do **not** upload `.venv`. Users paste or upload text in the browser, so you do **not** need `load_kaggle.py` on the server.

2. Open [https://share.streamlit.io](https://share.streamlit.io).

3. Click **Sign in** and choose **Continue with GitHub**. Approve access to the repository if GitHub asks.

4. Click **Create app** (or **New app**).

5. Fill in the form:
   - **Repository** — your GitHub user/org and repo name (for example `YourName/NLP`)
   - **Branch** — `main`
   - **Main file path** — `app.py`
   - **App URL** — optional short name (this becomes `https://that-name.streamlit.app`)

6. Open **Advanced settings** only if you need them:
   - **Python version** — pick **3.12** (or the newest version Streamlit offers that is 3.10+)
   - Secrets — leave empty. This app does not need API keys for Screen or Resume builder.

7. Click **Deploy**.

8. Wait for the build log to finish (`Installing dependencies`, then the app starts). The first deploy can take a few minutes.

9. When the status is running, open the Streamlit URL. Use **Screen** and **Resume builder** the same way as on localhost.

### After the first deploy

Every time you push to the same branch on GitHub, Streamlit Cloud rebuilds the app.

If the first page load fails on NLTK (tokenizer or stopwords), refresh once. The app downloads that data on first use. If it still fails, open the app **Manage app** → **Reboot**.

### If deploy fails

- Main file must be exactly `app.py` at the repo root (not `NLP/app.py` unless that is how the repo is structured).
- `requirements.txt` must be at the repo root.
- Check the Streamlit build log for a missing package and add it to `requirements.txt`, then push again.

## Project layout

```
app.py                 Streamlit UI (Screen + Resume builder)
cli.py                 score a resume file from the terminal
load_kaggle.py         optional Kaggle corpus download
requirements.txt       Python packages
.streamlit/config.toml light theme
src/preprocess.py      clean and tokenize text
src/extract.py         skills, experience, education
src/match.py           hybrid match score
src/builder.py         JD-tailored resume draft
src/resume_format.py   HTML preview and PDF export
```

## Push this project to GitHub

Do this **before** Streamlit Cloud deploy. Run the commands from the project folder (`NLP`).

### 1. Install Git and sign in to GitHub

Install Git from [https://git-scm.com](https://git-scm.com) if it is not installed. Create a GitHub account if you do not have one.

### 2. Create an empty repository on GitHub

1. Go to [https://github.com/new](https://github.com/new).
2. Repository name: for example `FitRank` or `NLP`.
3. Leave it **empty** (do not add a README, `.gitignore`, or license on GitHub — this project already has them).
4. Click **Create repository**.
5. Copy the repo URL, for example `https://github.com/YOUR_USERNAME/NLP.git`.

### 3. Commit and push (commands)

In PowerShell or Terminal, from this project folder:

```bash
git init
git add .
git status
```

Check that `.venv` is **not** in the staged files. Then:

```bash
git commit -m "Add FitRank resume screener and builder"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/NLP.git
git push -u origin main
```

Replace `YOUR_USERNAME/NLP.git` with your real GitHub URL.

If Git asks you to set a name and email (first time only):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

If `origin` already exists, skip `git remote add` and run:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/NLP.git
git push -u origin main
```

### 4. Later updates

After you change code:

```bash
git add .
git commit -m "Describe the change"
git push
```

Streamlit Cloud will redeploy from `main` automatically.
