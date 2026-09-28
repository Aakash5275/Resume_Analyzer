# FitRank — NLP design

FitRank treats a resume and a job description as unstructured text. The NLP work is to clean that text, pull out skills and education, measure how well the two documents overlap, explain the gaps, and (in the builder) rewrite a resume so it uses the job’s language.

Two different NLP jobs live in the app:

| Task | Kind of NLP | Where |
|---|---|---|
| Screen a resume against a job | Information extraction + lexical similarity + a weighted score | `src/preprocess.py`, `src/extract.py`, `src/tfidf.py`, `src/match.py`, `src/gap.py` |
| Build a tailored resume | Natural language generation | `src/gemini_resume.py` (Gemini), with a rule-based fallback in `src/builder.py` |

Screening does **not** call a large language model. The match score is computed locally from a skill gazetteer, regular expressions, and TF-IDF. Gemini is used only when the user clicks **Build tailored resume**.

## End-to-end pipeline

```
Upload or paste (TXT / PDF / DOCX)
        |
        v
Text load  (pdfplumber, python-docx)
        |
        v
Normalize  (Unicode, lowercase, strip email / phone / URL)
        |
        +---------------------------+
        |                           |
        v                           v
Skill gazetteer              Tokenize + stopwords
(longest alias match)        (for TF-IDF only)
        |                           |
        v                           v
Regex IE                     Unigrams + bigrams
education, section split     TF-IDF vectors
        |                           |
        +------------+--------------+
                     v
            Hybrid match score
                     |
                     v
         Gap report (matched / missing skills, verdict)
```

Entry point: `screen()` in `src/pipeline.py` calls `match_resume_to_jd()` and then `build_gap_report()`.

## 1. Document loading

`src/io_utils.py` turns a file into plain text:

- `.txt` / `.md` — read as UTF-8
- `.pdf` — `pdfplumber` page text
- `.docx` — paragraph text from `python-docx`

Everything after this step is a string. Layout, fonts, and images are not used for scoring. A profile photo is used only in the resume PDF layout, not in the NLP score.

## 2. Preprocessing

File: `src/preprocess.py`

Order:

1. **Unicode normalize** (`NFKC`) so look-alike characters collapse to one form.
2. **Noise removal** — emails, URLs, and phone numbers are blanked so they are not treated as words.
3. **Lowercase**.
4. **Symbol keep** — letters, digits, `+`, `#`, `.`, and `-` stay. That preserves tokens such as `c++`, `c#`, and `node.js`. Slashes become spaces, so `CI/CD` can match `ci cd`.
5. **Tokenization** — NLTK `word_tokenize` (Punkt) when the data is installed; otherwise a regex tokenizer.
6. **Stopword removal** — a built-in English list, plus NLTK’s English stopword list when it is available.
7. **Lemmatization** — NLTK WordNet lemmatizer when WordNet is installed. TF-IDF turns lemmatization **off** so skill phrases stay closer to the original wording.

NLTK resources downloaded on first use: `punkt`, `punkt_tab`, `stopwords`, `wordnet`, `omw-1.4`, and the averaged perceptron tagger. If a download fails, the built-in stopword list and regex tokenizer still run.

This stage is classic **text normalization**. It is shared by similarity. Skill extraction uses its own lighter normalize so line breaks and list structure are not destroyed.

## 3. Information extraction

File: `src/extract.py`  
Taxonomy: `src/skills_taxonomy.py`

This is **rule-based information extraction**, not a trained named-entity model.

### 3.1 Skill gazetteer (dictionary match)

Each canonical skill has aliases. Examples:

- `javascript` ← `js`, `java script`
- `react` ← `reactjs`, `react js`
- `natural language processing` ← `nlp`
- `machine learning` ← `ml` (only in a skill-list line; see below)

`build_alias_map()` sorts aliases **longest first**. The extractor scans the lowercased text and takes the longest alias that fits, then marks those characters as used so a shorter alias cannot match inside a longer one (`machine learning` wins over a stray `learning`).

A match must be a whole token (the character before and after cannot be a letter or digit).

### 3.2 Negation

A window of about 48 characters before a hit is checked for `no`, `not`, `without`, `lacking`, `don't`, and similar cues. `no Python experience` does not count as the skill Python.

### 3.3 Ambiguous aliases

Short aliases that are also ordinary English words (`go`, `rest`, `spring`, `node`, `c`, `r`, `ml`, `js`, …) are accepted only on list-like lines: bullets, commas, or a line that already names a technology (`python`, `sql`, `developer`, and so on).

So “we go to the office and handle the rest” does **not** become Go and REST API. “Skills: Go, Python, SQL” does.

### 3.4 Fuzzy alias backup

If a multi-word alias of length 8 or more was not found exactly, RapidFuzz `extractOne` compares it to word bigrams and trigrams. The cutoff is **92 / 100**. This catches small spelling differences (`scikit learn` vs `scikit-learn`) without matching unrelated phrases.

### 3.5 Alias check at score time

Exact set intersection is not enough, because the resume may say `React JS` and the job may say `React`. `text_has_skill()` searches the raw resume again for every alias of a job skill. A skill counts as matched if it is in the extracted resume set **or** any alias appears in the resume text.

### 3.6 Job-description sections

Headings split the job into required vs preferred blocks:

- Required cues: `requirements`, `must have`, `technical skills`, `qualifications`, …
- Preferred cues: `preferred`, `nice to have`, `bonus`, …
- Body cues such as `responsibilities` end a requirements block so a long duties paragraph is not forced into one bucket.

All skills found anywhere in the job are in scope. Skills that appear only under a preferred heading stay preferred. Everything else is treated as required for coverage.

### 3.7 Education (regular expressions)

Degree patterns map text to a label and a level:

| Pattern examples | Label | Level |
|---|---|---|
| PhD, doctorate | PhD | 4 |
| M.Tech, M.S., MBA, MCA | master’s | 3 |
| B.Tech, B.S., B.A., BCA | bachelor’s | 2 |

A second pattern captures a field such as Computer Science. Another pattern captures an institution word (`university`, `college`, `iit`, …).

### 3.8 Experience years (extracted, not scored)

The code can still read “N years of experience” and date ranges such as `2020–2024`. An **Education** section, and lines that mention a degree, GPA, school, or graduation, are removed before that count. School years are not job years.

**Experience fit weight is 0**, so those years do not change the match score shown in the app. The Screen page does not display an experience metric.

## 4. Lexical similarity — TF-IDF cosine

File: `src/tfidf.py`

This is a **bag-of-words** model implemented with NumPy (no scikit-learn).

1. Preprocess both documents **without** lemmatization.
2. Build **unigrams and bigrams** (`python fastapi`, not only `python` and `fastapi`).
3. Append the extracted skill names onto each side so canonical skills participate in the vector even if the surface wording differed.
4. Build a vocabulary from the two documents only (a 2-document corpus).
5. **TF** — `1 + log(count)` (sublinear term frequency).
6. **IDF** — smoothed inverse document frequency: `log((1 + N) / (1 + df)) + 1` with `N = 2`.
7. L2-normalize each vector.
8. **Cosine similarity** is the dot product of the two unit vectors, clipped to `[0, 1]`.

Cosine is high when the resume and the job share the same content words, and low when they talk about different topics. It is a complement to the gazetteer: the gazetteer is precise about known skills; TF-IDF still rewards shared wording the taxonomy does not list.

## 5. Hybrid match score

File: `src/match.py`

Each part is a number from 0 to 1. The displayed score is a weighted sum, scaled to 0–100.

| Component | Weight | How it is computed |
|---|---|---|
| Skill coverage | **0.65** | (required job skills found on the resume) / (required job skills) |
| TF-IDF similarity | **0.18** | cosine above |
| Education fit | **0.12** | resume degree level vs job degree level |
| Preferred skills | **0.05** | share of preferred skills present on the resume; 0.5 if the job lists none |
| Experience fit | **0.00** | implemented, but weight is zero so it does not move the score |

If the weights do not sum to 1, they are normalized by their total before scaling to 100.

**Education fit**

- Job states no degree: a small default (about 0.45–0.55), so education neither saves nor sinks the score.
- Resume level ≥ job level: 1.0
- Resume one step below: 0.7
- Further below: 0.4
- Resume has no detected degree while the job asks for one: 0.3

**Verdict** (`src/gap.py`)

| Score | Label |
|---|---|
| ≥ 80 | Strong fit |
| ≥ 65 | Good fit |
| ≥ 45 | Partial fit |
| below 45 | Weak fit |

### Why a hybrid score

A pure keyword count misses paraphrases (`js` vs `javascript`) unless aliases exist. A pure TF-IDF score can look “similar” because both texts say “team”, “responsible”, and “experience”. Putting **most of the weight on canonical skill coverage** makes the score follow the actual tools in the job, while TF-IDF and education add a smaller signal.

## 6. Gap report (explainability)

File: `src/gap.py`

The report is not a second model. It restates the match sets in recruiter language:

- matched required skills
- missing required skills
- missing preferred skills
- extra skills that are on the resume but not in the job
- short suggestions (name the missing skills; mention education only if the degree level is below the job)

Each matched skill can point at the surface form that triggered it (`react js` → `react`). That is the “why this matched” evidence.

## 7. Resume builder — generation

### Gemini (primary)

File: `src/gemini_resume.py`

The job text, optional current resume, name, and target title are sent to the Gemini API (`google-genai`). The model is asked to return **JSON** only: summary, skills, experience lines, education, projects, certifications.

Generation models, in order, so a busy model does not fail the request:

1. `gemini-2.5-flash-lite`
2. `gemini-2.0-flash-lite`
3. `gemini-2.0-flash`
4. `gemini-2.5-flash`
5. `gemini-flash-latest`

A **503 / 429** (model overloaded) is retried with a short wait, then the next model is tried.

Instructions to the model:

- Mirror the job title and required tools.
- If a current resume is provided, rewrite only facts that are already in it.
- If no resume is provided, still emit a complete draft and mark unknown employers as “Previous Employer” so the user can edit them.
- Experience lines use `Role | Company | Dates` plus bullets, which the HTML/PDF templates render as job headings.

This step is **controlled natural language generation**. The API key stays in `.streamlit/secrets.toml` and is not part of the scoring code.

### Local fallback

File: `src/builder.py`

If Gemini is down, the same extracted skills, degree, and section text are assembled into a draft with string templates. No new employers are invented. The UI labels this writer as “Local draft”.

## 8. What this project is, in NLP terms

Used:

- Text normalization and tokenization
- Stopword filtering and lemmatization
- Gazetteer / dictionary entity extraction
- Longest-match alias resolution (a simple form of **term normalization**)
- Negation scoping (a small rule, not a full dependency parser)
- Section segmentation by headings
- Regular-expression information extraction for degrees
- Character n-gram style **fuzzy string matching** (RapidFuzz) as a backup
- TF, IDF, and cosine similarity on unigrams and bigrams
- Set overlap as skill coverage (precision-style hit rate against the job’s required list)
- Weighted linear combination of those signals
- Template filling and LLM JSON generation for the resume draft

Not used for the score:

- No transformer embedding model (no BERT, Sentence-BERT, or spaCy NER)
- No classifier trained on labeled resume–job pairs
- No part-of-speech features in the score (the tagger may be downloaded for NLTK, but matching does not read POS tags)
- Experience years are parsed and then given weight 0

## 9. Code map

```
src/preprocess.py      clean, tokenize, stopwords, lemmatize
src/skills_taxonomy.py canonical skills, aliases, section heading cues
src/extract.py         gazetteer, fuzzy backup, education regex, JD sections
src/tfidf.py           TF-IDF cosine
src/match.py           coverage, education fit, weighted score
src/gap.py             matched / missing skills and verdict
src/pipeline.py        screen() used by the Streamlit Screen page
src/builder.py         rule-based resume draft
src/gemini_resume.py   Gemini resume JSON
src/resume_format.py   HTML preview and PDF (layout, not NLP)
app.py                 Screen and Resume builder UI
```

## 10. Worked example

Job requires Python, SQL, React, and Docker, and prefers AWS.  
Resume lists “Python, SQL, React JS, Node.js, Docker, AWS”.

1. Gazetteer canonicalizes `React JS` → `react` and `Node.js` → `node.js`.
2. Required set: python, sql, react, docker. Preferred: aws.
3. Alias check finds every required skill on the resume. Coverage = 4/4 = 1.0.
4. Preferred bonus = 1.0 because AWS is present.
5. TF-IDF is moderately high because both texts share those tool names and less of the surrounding prose.
6. Education adds a small amount if a degree is detected and the job does not demand a higher one.
7. Weighted score lands in the Good or Strong band, and the gap report lists no missing required skills. Node.js shows up as an extra skill.
