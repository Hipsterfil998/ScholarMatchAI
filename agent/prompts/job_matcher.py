"""Job matcher prompts.

This prompt is sent once per job listing, so its fixed overhead is multiplied
by the number of results. On Groq's free tier the pipeline is bound by tokens
per minute, not by latency, so keeping it compact is what decides whether a
large result set gets scored at all. The eligibility rule is restated here
only as a hint — ``JobMatcher.score`` enforces it as a hard cap regardless.
"""

JOB_MATCHER_SYSTEM = (
    "You are an expert academic recruiter for PhD and postdoc placements. "
    "Score how well a candidate fits a position. JSON only, no commentary."
)

JOB_MATCHER_PROMPT = """Score this candidate against the position.

CANDIDATE:
{profile}

POSITION:
{title} | {institution} | {location} | type: {pos_type}
{description}

Return exactly these keys:
{{"match_score": <integer 0-100>, "recommendation": "apply"|"consider"|"skip",
"matching_areas": [...], "missing_requirements": [...],
"why_good_fit": "<2-3 sentences>", "concerns": "<1-2 sentences, empty if none>"}}

Bands: 85+ excellent, 70-84 good, 55-69 partial, 35-54 weak, 0-34 poor.
Eligibility: postdoc and fellowship posts need a completed or in-progress PhD —
if the profile shows none, score <= 30 and recommend skip; a PhD still in
progress caps the score at 65. PhD posts have no such cap.

Judge meaning, not keywords ("NLP" = "natural language processing", "deep
learning" = "neural networks"); adjacent or complementary fields count as
partial overlap (>= 55). Descriptions are often short excerpts — infer the
research area from the title and institution instead of penalising brevity.
List every matching area you find, including transferable methods, tools and
publications. Weigh research alignment, thesis relevance, methodology,
publication record, skills and career stage; be generous when evidence is
ambiguous."""
