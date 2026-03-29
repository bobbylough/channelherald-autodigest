# News Digest Rebuild Spec

A design document for rebuilding `channelherald-automation` with a focus on
high-quality article selection, scoring, and summarization.

---

## Goals

The digest has one job: surface 5–7 stories per day per category that are genuinely worth
reading — surprising, intellectually stimulating, or consequential to someone
who thinks about technology and business for a living.

**"High quality" means:**

1. Every story in the digest would be worth bringing up at dinner. Not just
   topically relevant — actually interesting, with a non-obvious angle.
2. Recycled AI hype, press releases, and product announcements are filtered
   out before they reach the summarizer.
3. Summaries give you enough to decide whether to click. They don't spoil the
   article, don't sound like a bot, and don't start with "This article explains."
4. Long-form pieces get longer teasers. Quick news items get one sentence.
   The length signal comes from the article itself, not a fixed rule.
5. When scraping fails (paywall, JS wall, thin content), the digest says so
   clearly rather than pretending to summarize from a title alone.
6. The same story does not appear twice even if two newsletters link to it.

**Non-goals:** The digest is not a research tool, a reading list, or a
comprehensive news feed. It is a daily briefing for one person. Five great
stories beat fifteen mediocre ones.

---

## Pipeline

```
Cron job (7am daily)
  → AOL IMAP fetch
      pull newsletters from inbox (configurable lookback window)
      tag each email as preferred_sender or regular_sender

  → Scored link extraction
      parse HTML emails, build candidate URL list per email
      score each URL: position in email + link text length + preferred_domain bonus
      sample top-N per email (preferred_senders get 2x cap)

  → Domain filter
      drop ignored_domains
      sort preferred_domains to front

  → Article scraper
      fetch article text, estimate read time, strip UTM params
      compute content_depth = min(word_count / 100, 5)

  → Article cap
      keep up to max_articles full-content articles (title_only excluded)

  → Article rater (optional Ollama or cloud)
      rate each article: dinner_score (1–5), novelty_score (1–3),
      engagers list, category, rating_explanation (1 sentence)
      apply per-tier score threshold:
        preferred_sender articles: min_dinner_score_preferred (default 3)
        regular articles: min_dinner_score (default 4)
      drop articles where dinner_score AND novelty_score are both low

  → LLM summarizer
      batch articles (5 per call for cloud models, 3 for local)
      pass word_count as depth signal
      handle title_only articles with explicit paywall copy

  → Summary quality gate
      re-rate each summary on "would I forward this?" (1–3)
      drop or flag summaries scoring below summary_min_score

  → Digest builder
      deduplicate by topic (Jaccard similarity on title tokens, threshold 0.5)
      group by category (AI → Business → Technology)
      surface engagers badges per story
      render HTML with inline CSS only

  → SMTP send
```

---

## Quality Design

### Summary Quality

#### Body truncation

Raise `_MAX_BODY_WORDS` from **600 to 1200** for full-content articles.

The current 600-word cap was set to reduce token costs on local models. For
cloud providers (Anthropic, Groq, OpenAI) it loses too much context on
long-form pieces. The fix is to use 1200 words for cloud providers and keep
600 for Ollama — the caller already knows the provider.

```python
_MAX_BODY_WORDS_CLOUD = 1200
_MAX_BODY_WORDS_LOCAL = 600

def _max_body_words(provider: str) -> int:
    return _MAX_BODY_WORDS_LOCAL if provider == "ollama" else _MAX_BODY_WORDS_CLOUD
```

#### Depth signal in the prompt

Pass the original word count to the LLM so it can calibrate teaser length:

```json
{
  "id": 1,
  "title": "...",
  "body": "...",
  "word_count": 2400,
  "read_time": 12,
  "title_only": false
}
```

The system prompt should say: articles with `word_count > 1500` deserve 3–4
sentences; articles under 600 words warrant 1–2. The LLM should not pick
lengths arbitrarily.

#### title_only handling

When `title_only=True`, the current prompt says "base the summary on the title
alone and end it with (may require subscription)." This produces vague,
unhelpful summaries like "A piece about X, which may require subscription."

Replace with explicit copy:

> If `title_only=true`, write: "**[Paywall]** {title} — full content requires
> a subscription or was unavailable at scrape time." Do not attempt to summarize
> or expand on the title. One sentence only.

This sets correct expectations for the reader and stops the model from
hallucinating content it does not have.

#### Summary validation pass

After summarization, re-rate each summary using the same rater model with a
simpler prompt: "Would you forward this summary to a smart friend? 1 = no,
2 = maybe, 3 = yes." Summaries scoring 1 are replaced with a "short take"
fallback format:

> **Short take:** {title} — {one-sentence factual description of what the
> article covers, drawn from the summary or title}.

This is the `summary_min_score` gate (default 2). It catches summaries that
are generic, that repeat the title verbatim, or that used filler phrases
("this article explains") despite instructions not to.

Do not re-run the LLM summarizer on failed summaries — use the short take
fallback. A second summarization call on a bad article is unlikely to be
better and doubles token cost.

#### Prompt file split

Split the current monolithic `system.txt` into two files:

- `summary_system.txt` — the writing guidelines (voice, tone, angles, strong/weak
  examples). This is the part that changes most often.
- `summary_schema.txt` — the JSON schema enforcement instructions (field
  names, required fields, no preamble, no fences). This rarely changes.

`llm.py` loads both and concatenates them, schema first, guidelines second.
Keeping them separate makes it easy to tune the voice without accidentally
breaking the schema rules.

#### Deduplication

Two newsletters frequently link to the same story under different URLs (e.g.,
a Reuters article shared by three Substack authors). Before building the
digest, check for topic overlap across summaries:

1. Tokenize each article title (lowercase, strip stopwords).
2. Compute pairwise Jaccard similarity on title token sets.
3. If similarity > 0.5, keep the article with the higher `dinner_score`; drop
   the other.

This is a 10-line function in `digest_builder.py`. No external libraries
needed. Do not use embeddings or semantic similarity — title-level dedup is
sufficient.

---

### Rating Quality

#### Schema additions

Add two fields to the rating schema:

```json
{
  "id": 1,
  "category": "AI",
  "dinner_score": 4,
  "novelty_score": 2,
  "engagers": ["software engineer", "entrepreneur"],
  "rating_explanation": "Covers a real deployment case with surprising failure modes, not just another benchmark announcement."
}
```

- `novelty_score` (1–3): Is this a new perspective, or recycled coverage?
  1 = seen this take 10 times this week, 3 = genuinely fresh angle.
- `rating_explanation` (string): One sentence explaining the score. Used only
  in debug log output — never shown in the digest. Invaluable for diagnosing
  why good articles are being dropped.

#### Drop rule

Current: drop if `dinner_score < min_dinner_score`.

New: drop if `dinner_score < threshold` **OR** if `dinner_score <= 2 AND
novelty_score == 1`. The second condition catches the "AI hype recycling"
problem: a story can be mildly interesting (score 3) but be the fifteenth
article this week about the same announcement. If both scores are low, it goes.

#### Per-tier thresholds

Add `min_dinner_score_preferred` (default 3) for articles from
`preferred_senders`. Regular sender articles use `min_dinner_score` (default 4).

This means: if you trust a sender enough to put them in `preferred_senders`,
you accept slightly lower-scoring articles from them because their selection
signal is already better than random.

#### Engagers badge in digest

The `engagers` field is currently generated and discarded — it is merged into
summaries in `digest.py` but `digest_builder.py` ignores it. Render it as a
small badge below each story headline:

```
For: software engineers, entrepreneurs
```

Use a muted style (gray, small font) so it does not compete with the summary.
This gives readers a fast relevance signal without requiring them to read the
full teaser.

#### Stronger model for rating

The rating prompt runs on `mistral-nemo` or `qwen2.5:7b` locally, which
produces unreliable structured output and scores that drift toward the middle
(3s everywhere). Two options:

1. Use a cloud model for rating when `enable_rating = true` and
   `rating_provider` is not `ollama`. The rater already supports Groq/Anthropic/
   OpenAI — just set `rating_provider = groq` in config.
2. When using Ollama, prefer `qwen2.5:14b` over 7b — the 14b model has
   meaningfully more reliable structured output on the rating schema.

Document both options in the README. Do not hardcode a model preference in
the code.

---

### Article Selection Quality

#### Scored sampling

Replace `random.sample(candidates, N)` in `link_extractor.py` with scored
sampling. Score each candidate URL before selecting:

```python
def _score_url(tag: Tag, url: str, preferred_domains: list[str]) -> float:
    score = 0.0
    # Position signal: earlier links in the email are usually more featured
    # (caller passes 0-based index of this tag among all <a> tags)
    score += max(0.0, 1.0 - (tag_index / 50))  # decays to 0 after 50 links

    # Link text quality: longer, more descriptive anchor text = better article link
    text = tag.get_text(strip=True)
    score += min(len(text) / 80, 1.0)  # caps at 1.0 for 80+ char anchor text

    # Preferred domain bonus
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    if any(domain == d or domain.endswith("." + d) for d in preferred_domains):
        score += 1.5

    return score
```

Sort candidates by score descending, take the top N. The random element is
gone — this is deterministic and reproducible given the same email content.

The `preferred_domains` list must be threaded into `extract_links()`. The
`Config` object is already available in `digest.py` at call time.

#### Source tier concept

Add `preferred_senders` to `Config` (comma-separated, same `@domain.com`
syntax as `newsletter_senders`). These are senders whose emails get 2x the
`max_articles_per_email` cap. Regular senders get the base cap.

`imap_fetch.py` already tags emails by sender — extend the return value to
include a `is_preferred` flag, and pass it to `extract_links()` so it can
apply the correct cap per email.

#### Content depth signal

After scraping, compute `content_depth = min(article["word_count"] // 100, 5)`
and store it on the article dict. When the rater scores two articles close in
`dinner_score` (within 1 point), prefer the deeper one. This is enforced at
the cap step in `digest.py`:

```python
# Sort by dinner_score desc, then content_depth desc as tiebreaker
articles.sort(key=lambda a: (-(a.get("dinner_score") or 0), -(a.get("content_depth") or 0)))
articles = articles[:config.max_articles]
```

This does not require a new config key — it is baked into the sort.

---

## Architecture / Config Changes

### New `Config` fields

```python
preferred_senders: list[str] = field(default_factory=list)
min_dinner_score_preferred: int = 3
summary_min_score: int = 2
enable_summary_validation: bool = False  # opt-in; adds one LLM call per summary
```

### Pipeline module changes

| Module              | Change                                                                                                   |
| ------------------- | -------------------------------------------------------------------------------------------------------- |
| `config.py`         | Add `preferred_senders`, `min_dinner_score_preferred`, `summary_min_score`, `enable_summary_validation`  |
| `imap_fetch.py`     | Return `list[dict]` with `body` and `is_preferred` instead of `list[str]`                                |
| `link_extractor.py` | Accept `list[dict]` emails; use scored sampling; apply per-tier cap                                      |
| `scraper.py`        | Add `content_depth` field to article dict                                                                |
| `article_rater.py`  | Add `novelty_score` and `rating_explanation` to schema and merge logic                                   |
| `llm.py`            | Raise body truncation limit for cloud providers; pass `word_count` in prompt; split system prompt files  |
| `digest.py`         | Apply per-tier score thresholds; run summary validation pass if enabled; run dedup before digest builder |
| `digest_builder.py` | Render engagers badge; accept pre-deduped story list                                                     |

No new top-level modules. No new external dependencies beyond what is already
in `requirements.txt`.

---

## Config Reference

All keys live in `digest/config.properties`. New keys introduced in this spec
are marked **new**.

### Required

| Key                       | Description                                                |
| ------------------------- | ---------------------------------------------------------- |
| `imap_host`               | IMAP server hostname                                       |
| `imap_port`               | IMAP port (993 for AOL SSL)                                |
| `imap_user` / `smtp_user` | Email address                                              |
| `imap_pass` / `smtp_pass` | AOL app password                                           |
| `smtp_host`               | SMTP server hostname                                       |
| `smtp_port`               | SMTP port (587 for AOL STARTTLS)                           |
| `newsletter_senders`      | Comma-separated sender addresses or `@domain.com` patterns |
| `email_to`                | Digest recipient address                                   |
| `llm_provider`            | `groq`, `anthropic`, `openai`, or `ollama`                 |
| `api_key`                 | API key for the selected provider                          |
| `preferred_domains`       | Comma-separated domains to boost in scored sampling        |

### Optional — pipeline tuning

| Key                      | Default   | Description                                                                                                                         |
| ------------------------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `email_lookback_days`    | `1`       | How many days back to fetch emails                                                                                                  |
| `max_articles_per_email` | `5`       | Max articles sampled per regular sender email                                                                                       |
| `max_articles`           | `0`       | Cap on full-content articles per run (`0` = unlimited)                                                                              |
| `max_digest_stories`     | `7`       | Max stories per category in the digest                                                                                              |
| `debug`                  | `false`   | Write scrape log and verbose LLM prompt logs each run                                                                               |
| **`preferred_senders`**  | _(empty)_ | **New.** Comma-separated senders or `@domain.com` patterns that get 2x the `max_articles_per_email` cap and a lower score threshold |

### Optional — rating

| Key                              | Default          | Description                                                      |
| -------------------------------- | ---------------- | ---------------------------------------------------------------- |
| `enable_rating`                  | `false`          | Rate articles before summarizing; drops low scorers              |
| `rating_provider`                | _(llm_provider)_ | Provider for rating calls; set to `ollama` to rate locally       |
| `ollama_model`                   | _(none)_         | Local Ollama model name (e.g. `qwen2.5:14b`)                     |
| `min_dinner_score`               | `4`              | Drop regular-sender articles scoring below this (1–5)            |
| **`min_dinner_score_preferred`** | `3`              | **New.** Drop preferred-sender articles scoring below this (1–5) |

### Optional — summary quality

| Key                             | Default | Description                                                                                                                                |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **`enable_summary_validation`** | `false` | **New.** After summarization, re-rate each summary on "would I forward this?" and replace low-scoring summaries with a short-take fallback |
| **`summary_min_score`**         | `2`     | **New.** Summaries scoring below this (1–3) are replaced with the short-take format. Only used when `enable_summary_validation = true`     |

---

## Prompt Design

### Summary system prompt

The revised prompt is split across two files. Load both; concatenate with a
blank line between them. Schema enforcement goes first so the model sees the
output contract before reading the style guidelines.

**`digest/prompts/summary_schema.txt`**

```
You are writing teaser-style summaries for a curated newsletter. You will
receive a JSON array of articles, each with a numeric "id".

Return a JSON object with a "summaries" array containing EXACTLY one entry
per input article — no more, no fewer. Do not add, invent, or look up any
articles beyond those provided.

Each entry must contain:
  - "id": the same integer from the input article — do not change it
  - "category": one of "AI", "Business", or "Technology"
  - "summary": a teaser summary following the guidelines below
  - "read_time": the read time in minutes (unchanged from input)

If an article has title_only=true, write exactly:
  "[Paywall] {title} — full content requires a subscription or was
  unavailable at scrape time."
  One sentence only. Do not expand or speculate.

Return valid JSON only — no preamble, no markdown fences, no commentary.
Format: {"summaries": [{"id": 1, ...}, {"id": 2, ...}]}
```

**`digest/prompts/summary_system.txt`**

```
SUMMARY GUIDELINES

Length: calibrate to article depth.
  - word_count > 1500: 3–4 sentences.
  - word_count 600–1500: 2–3 sentences.
  - word_count < 600: 1–2 sentences.
Vary lengths across summaries in the same batch.

Voice and tone:
  - Human, thoughtful, and slightly provocative — like a smart friend
    tipping you off, not a press release summarizer.
  - Do NOT start with the same word or phrase as the article title.
  - Do NOT mention the author, publication, or use phrases like "this
    article explains", "the piece covers", or "according to".
  - Do NOT use dashes.
  - Focus on why the idea is interesting, surprising, or important.
  - Leave one question unresolved in the reader's head — do not literally
    ask a question, but create the feeling that there is more to find out.
  - Never repeat the same sentence structure or opening word across
    summaries in the same batch.

What makes a summary work — use exactly one of these angles per summary:
  1. Flip an assumption: the obvious take is wrong, here is why.
  2. Reveal a hidden shift: something subtle but important is changing.
  3. Show real-world consequence: not what it is, but why it matters today.
  4. Introduce tension: opportunity vs. risk, speed vs. quality,
     power vs. control.
  5. Leave a glimpse: this feels like an early preview of something larger.

STRONG vs. WEAK

Weak: This article discusses how AI is changing software development.
Strong: Engineers are not being replaced, but their role is quietly shifting
  from writing code to supervising systems that do. Whether that makes them
  more powerful or less relevant depends on who owns the systems.

Weak: The article explains how companies are using AI agents in workflows.
Strong: Software that does not just assist but takes action is showing up
  inside real businesses. Once agents can negotiate, schedule, and decide,
  the line between tool and employee starts to blur.

Weak: This article looks at problems with text generation in AI images.
Strong: AI can paint photorealistic scenes but still cannot spell. That odd
  mismatch reveals something deeper about how these models see the world,
  and why language remains stubbornly hard.
```

### Rating prompt concept

The rating prompt must ask for four outputs: `dinner_score`, `novelty_score`,
`engagers`, and `rating_explanation`. The key principle is to make the
scoring criteria concrete and mutually exclusive — vague criteria produce
middle-of-the-distribution scores.

**What to ask and why:**

`dinner_score (1–5)` — "If you heard this story mentioned at dinner by a smart,
curious person, how likely are you to want to hear more?" Score 5 means you
would interrupt your own story to hear it. Score 1 means you would politely
nod and change the subject. The scale is anchored to conversation interest,
not importance or accuracy. This works because the use case is a personal
digest for entertainment and intellectual stimulation, not a research feed.

`novelty_score (1–3)` — "How many times have you seen this exact take in the
past two weeks?" 1 = this is the 10th article making the same point about
the same announcement. 2 = familiar topic, meaningfully new angle. 3 = this
is a perspective or finding I have not seen before. This is the filter against
AI hype recycling — a story can be interesting in isolation (dinner_score 3)
but still be recycled noise (novelty_score 1).

`engagers` — "Which of these five personas would actively want to continue
this conversation: software engineer, entrepreneur, surgeon, CEO, business
analyst?" List all that apply. This is not about who the article is written
for — it is about who would bring it up again at the next meeting. Use an
enum to keep the field consistent.

`rating_explanation` — "In one sentence, explain the dinner_score." This goes
to the debug log only. The value is diagnostic: it tells you whether the model
is scoring on the right criteria or making a category error (e.g., rating a
speculative op-ed as a score 5 because the topic is hot).

**What the rating prompt should NOT do:**

- Ask the model to predict click-through rate or "engagement" — these metrics
  reward sensationalism.
- Ask for a confidence score — it adds noise without value.
- Ask the model to evaluate writing quality — the summaries are not written
  yet at rating time; only the scraped body is available.

---

## What Not to Build

These are tempting improvements that are explicitly out of scope. Follow the
KISS principle.

**No vector database or semantic search.** Title-level Jaccard dedup (10 lines)
is sufficient for same-story detection across 5–7 newsletters. Embeddings add
a new service dependency, a new failure mode, and latency for a problem that
does not need them at this scale.

**No web UI or reading history.** The digest is an email. The delivery
mechanism (SMTP) is already as simple as possible. A web UI requires a server,
a domain, auth, and maintenance. The goal is zero infrastructure beyond a cron
job.

**No feedback loop requiring user interaction.** Do not build a "thumbs up /
thumbs down" system, a rating interface, or any mechanism that requires the
user to take action to improve future digests. The user's time is what the
system is saving. Implicit signals (which articles they click) require a
tracking server. Skip it.

**No per-article model selection.** Do not build routing logic that sends
"complex" articles to one model and "simple" articles to another. It adds
configuration surface area and makes behavior unpredictable. Pick one
summarization model and tune the prompt.

**No caching layer.** Articles are scraped once per run. The `seen_urls.db`
prevents re-scraping across runs. Do not add Redis, a file-based cache, or
HTTP cache headers logic. The scraper is already fast enough for 10–20
articles.

**No multi-user support.** The config has one `email_to` address. Do not
generalize to multiple recipients, multiple config files loaded in parallel,
or per-user preferences. The system is explicitly for one person.

**No scheduled retry.** If the pipeline fails (LLM call fails twice, SMTP
fails), it exits with an error and saves the HTML fallback. Do not add a retry
queue, a delay-and-rerun mechanism, or a watchdog process. A daily cron job
that fails once in a while is acceptable. A persistent background service that
can get into a broken state is not.
