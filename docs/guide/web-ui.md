# Using the Web UI

The PhdScout web interface is built with [Gradio](https://gradio.app) and is split into four tabs that follow the natural workflow of an academic job search. This page describes each tab in detail.

---

## Tab 1 — Setup & Search

This is the starting point. All inputs for the search are collected here.

### CV Upload

Click the upload box and select your CV. Supported formats:

- **PDF** — most common; text is extracted with `pdfplumber`. Multi-column PDFs are supported.
- **DOCX** — paragraphs and table cells are extracted with `python-docx`.
- **TXT** — plain text, read as-is.

!!! tip "CV quality matters"
    The LLM extracts your profile directly from the text. A well-structured CV with clear section headers (Education, Publications, Research Interests) will produce a more accurate profile, which in turn improves match scoring.

### Research Field

Type the primary area of research you are looking for. Examples:

- `machine learning` — broad, returns many results
- `computational neuroscience` — specific, returns focused results
- `NLP, natural language processing` — comma-separated terms work; the scraper tries each

!!! tip "Specificity"
    Specific queries produce better-matched results. `protein structure prediction` will return more relevant positions than `biology`.

### Location Preference

Choose from the dropdown or type a custom value. The dropdown includes:

- `Worldwide` — no location filter applied
- `Europe (all)` — no country filter for Euraxess; includes EU results from mlscientist
- Individual countries: all EU member states, UK, US, Canada, Australia, Japan, and more

!!! note "Location support varies by source"
    Euraxess has server-side country filters for most European countries. mlscientist.com has country slugs for about a dozen countries. jobs.ac.uk is UK-only. See [Job Sources](sources.md) for details.

### Position Type

| Value | What it matches |
|---|---|
| `predoctoral` | Pre-doctoral, early-stage researcher, master's student positions |
| `phd` | PhD studentships, doctoral positions, graduate student roles (default) |
| `postdoc` | Postdoctoral positions, research associates, research fellows |
| `fellowship` | Fellowships, Marie Curie, ERC grants, scholarships |
| `research_staff` | Research scientists, PIs, lecturers, professors |

Position types are detected from the title and description using a keyword list in `BaseScraper._detect_type`.

### Minimum Match Score

The slider (30–90, default 60) controls which positions are highlighted as qualifying after scoring. Positions below this threshold are still shown in the Results table — they are just not recommended for the review queue.

!!! tip "When to lower the threshold"
    If you are getting zero qualifying positions, try lowering to 50 or 45. This is common in very specific or niche fields where job descriptions are brief and the LLM scores conservatively.

### LLM Model

Select the Groq model to use for this session. The model affects CV parsing, scoring, cover letter generation, and tailoring hints.

| Model | Best for |
|---|---|
| `llama-3.3-70b-versatile` | Best quality — cover letters and scoring (default) |
| `llama-3.1-8b-instant` | Fast iteration, lower latency |

### Starting the Search

Click **Parse CV & Search Positions**. A progress bar shows three stages:

1. `Parsing CV...` — LLM extracts your profile
2. `Searching job boards (~60s)...` — four scrapers run in sequence
3. `Scoring positions...` — LLM scores each job against your profile

The status line shows the final count when complete, e.g. `Found 31 positions — 14 above score 60`.

---

## Tab 2 — Results

### CV Profile Panel (left)

Displays the structured profile extracted from your CV. Review this carefully:

- **Name and contact** — should be extracted correctly from the CV header
- **Research interests** — the most important section for scoring; make sure these are complete
- **Education** — degrees with institutions and years; thesis topics improve matching
- **Publications** — titles, venues, and years
- **Technical skills** — programming languages, frameworks, lab techniques

If something important is missing (e.g. a key research interest), it is likely absent from your CV text. Adding it to the CV and re-running will improve match accuracy.

### Scored Positions Table (right)

Columns:

| Column | Description |
|---|---|
| `#` | Rank by score |
| `Score` | Match score 0–100 |
| `Title` | Position title |
| `Institution` | University or research institute |
| `Type` | Detected position type |
| `Rec.` | Recommendation: `apply`, `consider`, or `skip` |
| `Why good fit` | First 60 characters of the LLM's explanation |

Click **Go to Review** to proceed to the next tab.

---

## Tab 3 — Review & Edit

This is where you read each position in detail, edit the cover letter, and decide whether to approve.

### Selecting a Position

The dropdown lists all scored positions sorted by match score (highest first), prefixed with the score in brackets, e.g. `[87] TU Munich — PhD Position in Deep Learning`.

Click **Load Position** to generate the tailoring hints and cover letter. This triggers two LLM calls and takes 10–30 seconds.

### Position Details Panel (left)

Shows:
- Title, institution, location
- Type and deadline
- URL link
- Full match analysis: score bar, recommendation, why it's a good fit, concerns
- Matching areas and missing requirements as bullet lists
- Expandable full description

### CV Tailoring Hints Panel (right)

Shows position-specific, actionable advice:

- **Profile summary tweak** — one sentence suggestion for your opening paragraph
- **Research alignment** — how to frame your research interests for this specific group
- **Skills to highlight** — specific skills from your CV with rationale
- **Experience to highlight** — which roles or projects to mention
- **Keywords to add** — terms from the job description not currently in your CV
- **Suggested section order** — recommended ordering of CV sections for this position

### Cover Letter Draft

The generated letter is shown in an editable text box. The `DRAFT` header at the top is a reminder — remove it before sending.

The letter follows a four-paragraph structure:
1. Specific interest in the research group and position title
2. Research background alignment with the group's work
3. Most relevant publications, projects, or technical skills
4. Why this institution, availability, enthusiasm

!!! warning "Review before sending"
    The LLM may hallucinate PI names, mis-attribute publications, or use slightly wrong institutional details. Always read the full letter and correct any errors.

#### Regenerate Letter

Click **Regenerate Letter** to produce an alternative version with a different opening, different projects highlighted, and adjusted framing. Useful if the first draft doesn't fit the tone you want.

#### Download .txt

Click **Download .txt** to save the current letter text as a `.txt` file without approving the application.

### Notes Field

Add private notes about the application — deadline reminders, contacts, application portal URLs. These are saved in the ZIP export under `my_notes.txt`.

### Approving

Click **Approve & Save** to add the position to your approved list. The same position cannot be approved twice.

---

## Tab 4 — Export

### Approved Applications

Shows a table of all approved positions with the approval timestamp.

### Download as ZIP

Click **Download as ZIP** to export all approved applications. The ZIP structure:

```
applications.zip
├── summary.json                    ← list of all approved positions
└── applications/
    ├── MIT_PhD_Machine_Learning/
    │   ├── cover_letter_draft.txt  ← edited cover letter
    │   ├── my_notes.txt            ← your notes (if any)
    │   └── position_details.json   ← full position + match data
    └── ...
```

`summary.json` at the root contains a flat list for quick reference:

```json
[
  {
    "title": "PhD Position in Machine Learning",
    "institution": "MIT",
    "match_score": 87,
    "url": "https://...",
    "approved_at": "2024-03-15T14:30:00"
  }
]
```
