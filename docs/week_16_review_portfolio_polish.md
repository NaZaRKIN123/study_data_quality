# Week 16 — Review, Gaps & Portfolio Polish | Training Materials

> **Companion to:** Week 16 of the *Data Automation Testing* study plan
> **Time budget:** 6–10 hours across 5 days
> **Goal:** Turn 15 weeks of work into something you can confidently *talk about* in interviews and *share publicly*. By Friday you have: a self-assessed gaps list, one targeted gap closed, a published portfolio write-up, a working interview-question bank you've practiced answering, and live mock-interview feedback from Claude.
>
> **This is the last week of the curriculum.** What gets you a job offer isn't the final 5% of technical depth — it's the ability to articulate what you've built, acknowledge what you don't know, and converse fluently about trade-offs. This week trains that skill.

---

## How to use this file

- Like Week 15, this week is deliverable-focused, not theory-heavy
- Each day has a **concrete output** and a "Done when..." checklist
- Friday brings back the AI workflow — mock interviews with Claude, which deserves real time investment
- The interview-question bank in Day 4 is the most reusable artifact of the week — bookmark it
- A "What's next?" section at the end of the file looks beyond Week 16

---

## Day 1 (Mon) — Review Your Own Code

### Goal

Read everything you wrote across 15 weeks with fresh eyes. Identify patterns — both the good (your strengths to talk about) and the cringeworthy (your gaps to fill). End the day with a written self-assessment.

### Why this matters

You will absolutely be asked to walk through your code in interviews. The candidates who do this poorly are the ones who haven't read their own code in months and are surprised by what they find. **Re-reading is preparation.** It also makes you a better engineer; "I'd do this differently now" is a senior thinking pattern that matters more than knowing more libraries.

### What to do

**Step 1 — Take a 24-hour break first if you can.**

Cold eyes catch things hot eyes miss. If you finished the capstone Friday, today is Monday — you've had the weekend. Good. If not, take an hour walk before starting.

**Step 2 — Re-read the code in chronological order.**

Start with Week 1 SQL exercises. Move forward. For each substantive piece of code, ask:

| Question | What it tells you |
|---|---|
| What was I trying to do? | If it's not obvious, your future self has nothing to read |
| Would I write this the same way today? | Catches genuine improvement — "I now know `groupby` exists" |
| What test would I add now? | Reveals testing maturity — usually you wanted more tests early on |
| What's the actual purpose vs the stated purpose? | Catches over-engineering — code doing more than the comment says |
| Could a stranger run this without help? | Catches missing setup, hardcoded paths, undocumented assumptions |

This isn't a code review of your past self for the purpose of feeling bad. It's an inventory.

**Step 3 — Categorize each piece into K/I/R**

For each file or major code chunk, mark:

- **K — Keep.** Clean, recent, working, you'd write similar today
- **I — Improve.** Works but has rough edges (no docstrings, magic numbers, unused imports, copy-paste from tutorial without adaptation)
- **R — Regret.** Things you wouldn't do today — wrong approach, fragile pattern, anti-pattern you've since learned to avoid

A typical 15-week curriculum produces ~60% K, ~30% I, ~10% R. If you have far less K, your work is rougher than it should be — Week 15 polish was incomplete. If you have far more K, you're either very good or not being honest about gaps.

**Step 4 — Note three patterns**

Across the whole codebase, write down (in `notes.md`):

- **Three things you got better at over time.** ("I started with `iterrows`; by Week 8 I was writing vectorized pandas.")
- **Three patterns you adopted consistently.** ("I always pin random seeds in tests after Week 8.")
- **Three things you'd do differently if you started today.** ("I'd use Polars instead of pandas for the whole project; Polars wasn't on my radar in Week 2.")

This 9-item list is **interview gold**. Senior engineers love hearing "I'd do X differently because Y." It signals self-awareness, growth, and engineering judgment all at once.

**Step 5 — Note one piece of code you're particularly proud of**

Pick one function, test, design decision, or workflow that you genuinely think is good work. Why is it good? What constraints did you balance? Have a 60-second answer ready — you'll use it Wednesday and Friday.

### Common discoveries

Patterns most learners find on re-read:

- **Inconsistent error handling** — some functions raise specific errors, others swallow exceptions silently
- **Test assertions that don't actually test** — `assert df is not None` after loading; passes vacuously
- **Magic numbers** — thresholds like `0.05`, `1000`, `0.95` scattered without explanation
- **Tutorial leakage** — code structure that mirrors a tutorial you followed without adapting to your problem
- **Documentation drift** — comments and docstrings that no longer match the code
- **Duplicate logic** — the same reconciliation rule expressed differently in 3 places (despite Week 13's lecture on this)

If you find any of these, you're normal. If you find none, look harder.

### Done when...

- [ ] Every substantive file has a K/I/R categorization
- [ ] You have a written list of 3+3+3 patterns/improvements
- [ ] You've identified one piece of work you're proud of, with a 60-second story
- [ ] You have a candidate list of "things to fix this week" if time allows
- [ ] You've drafted your gap list for Day 2

---

## Day 2 (Tue) — Fill the One Gap That Matters Most

### Goal

Pick the **single** most important gap from Day 1 (or from your honest self-assessment of the curriculum) and spend a full session closing it. Resist the temptation to fill many gaps shallowly.

### Why one gap, not many

Skill acquisition is non-linear. Spending 6 hours on one weak topic moves it from "I know nothing" to "I can talk about this." Spending 6 hours on six topics, 1 hour each, moves none of them anywhere meaningful. **One gap deeply > six gaps shallowly.**

Especially before interviews. A specific topic you can discuss confidently outweighs a long shallow list.

### Choosing the gap

Ask yourself, honestly: which of these would you most fear being asked about in an interview tomorrow?

A short candidate list, in rough priority order for a Data QA / Data Engineering role:

1. **SQL fluency** — joins, window functions, CTEs, plan reading. Foundational; if shaky, fix this first.
2. **dbt mental model** — what's a model, what's a source, how `ref()` and `source()` work, when to use seeds vs sources, what `dbt build` actually does.
3. **CI/CD basics** — what triggers what, how secrets work, what branch protection means, what a workflow file looks like.
4. **Data quality dimensions** — the six (completeness, uniqueness, validity, consistency, timeliness, accuracy). Be able to give an example of each.
5. **Bronze/Silver/Gold pattern** — what each layer holds, what's tested at each, why it exists.
6. **ML testing distinct from data testing** — drift, leakage, performance regression. Why "predict(x) == y" doesn't work as a test.
7. **Tool choice trade-offs** — Soda vs Great Expectations vs dbt tests; pandas vs DuckDB vs Spark.
8. **Production observability vs CI testing** — what runs where, why both, alerting tiers.

Other candidates:
- A specific tool you skimmed but didn't deeply use (Iceberg, Hudi, Spark, Airflow)
- A concept you recognize but couldn't explain (idempotency, schema evolution semantics, JSON vs JSONL)
- A common interview question you don't have a fluent answer for

**Pick exactly one.** If you can't pick, default to SQL fluency — it's the most universally tested topic and good SQL never goes out of style.

### Filling the gap — a structured 6-hour approach

If you've picked, say, "dbt mental model," spend the day like this:

**Hour 1 — Re-read foundation material.** Open the [dbt Learn](https://courses.getdbt.com/) course or your Week 6 notes. Skim quickly; flag anything you can't explain.

**Hour 2 — Pick three things you flagged. Build small examples.** Don't read about them; *use* them. A 20-line dbt project that exercises the concept is worth more than 2 hours of reading.

**Hour 3 — Ask 5 hard questions, write the answers.** Below for the topic of dbt as an example. Adapt the format to your gap topic:

> 1. What's the difference between `ref()` and `source()`? When use each?
> 2. What does `dbt build` do in dependency order — exactly, including tests?
> 3. When would you choose a seed vs a source?
> 4. What's an incremental model, and how does it determine which rows to update?
> 5. What's the difference between a generic test and a singular test? When do you write each?

Write paragraph-length answers. If you can't, you found a real gap — go back to the docs.

**Hour 4 — Find a real-world failure case.** Search GitHub issues, Stack Overflow, dbt Slack archives for "I don't understand X" posts. Read the answers. Real-world confusion patterns are interview-question patterns.

**Hour 5 — Update your capstone if applicable.** Could anything you just learned be applied to improve your Week 15 work? Even a small improvement (rename a confusingly-named model, add an explanatory comment) cements the learning.

**Hour 6 — Self-quiz.** Ask Claude (or a friend) to quiz you on the topic. 5 questions, escalating difficulty. Note where you stumble.

### What "filling the gap" looks like

Before: "dbt? I used it. Models, sources, tests... yeah." (vague)

After: "dbt is a framework for SQL transformations. Models compile to SQL, run in dependency order via `dbt build`, with tests interleaved between models. Sources represent raw external tables; seeds are CSV files dbt manages. Generic tests live in `schema.yml` and are reusable; singular tests live as `.sql` files in the `tests/` directory and are queries that should return zero rows. Incremental models use `unique_key` and a `where` clause to merge new data instead of full rewrites. Common gotcha: forgetting that `dbt run` skips tests — `dbt build` runs both."

The latter answer takes 30 seconds and signals "I've used this." The former takes 5 seconds and signals "I followed a tutorial."

### Done when...

- [ ] You've picked one gap and committed to it for the day
- [ ] You can answer 5 hard questions on the topic, in writing
- [ ] You have a small worked example demonstrating the concept
- [ ] You've drafted a 30-second verbal explanation of the topic
- [ ] You've documented the gap-fill in your `notes.md` so you remember what you covered

---

## Day 3 (Wed) — Portfolio Write-Up

### Goal

Publish (or be ready to publish) a written piece about your capstone — either a blog post, a LinkedIn article, or a polished GitHub README that doubles as both. **Public** is the operative word. Private documentation isn't a portfolio piece; it's just notes.

### Why bother

Three reasons:

1. **Recruiters and hiring managers Google you.** A published piece on data quality testing puts your name in the right search results.
2. **Writing forces clarity.** If you can write about a project, you can talk about it. Conversion of vague feelings into concrete sentences is the work.
3. **Network effect.** Sharing on LinkedIn / Twitter / Mastodon brings the project to the attention of others working in the field. People who like your work refer it.

### Format options

| Format | Length | Best for | Effort |
|---|---|---|---|
| **LinkedIn post** | 200–400 words | Quick, professional, drives connections | 1–2 hours |
| **Medium / dev.to / personal blog post** | 800–1500 words | Longer story, more SEO permanence | 3–5 hours |
| **GitHub README only** | n/a | If you're not into self-promotion | Already done in Week 15 |
| **Twitter / Mastodon thread** | 5–8 tweets | Reaches data community quickly | 1 hour |

**Recommendation for most learners**: a single blog post (Medium / dev.to / personal site) PLUS a LinkedIn announcement linking to it. The blog post is the artifact; the LinkedIn post is the distribution.

### Blog post structure that works

The "problem → approach → outcome → lessons" arc is durable. Specifically:

```markdown
# Title that's specific, not vague
e.g. "I built a 25-test data quality pipeline. Here's what I learned about
which tests matter."

## The problem (1–2 paragraphs)
What was the question? Why does it matter? Who has it?

## What I built (architecture diagram + 1 paragraph per layer)
Walk through Bronze → Silver → Gold. Embed the diagram from your README.

## Three design decisions and what I'd do differently
Pick three trade-offs you made. For each: what I chose, why, what changed
my mind in the end. This section is what makes the post worth reading.

## What surprised me
Honest. "I assumed X; the data showed Y." Or "I expected dbt to feel heavyweight;
it didn't."

## What's next
Be honest about gaps. "I'd add Iceberg for time travel; I'd test on real production
data instead of synthetic; I'd run this against a real Snowflake instead of DuckDB."

## Code
Link to the repo. One sentence about what's in it.
```

This structure is ~1000 words. It takes 3–4 hours to write well.

### What works in this kind of writing

- **Specifics over generalities.** "I tested 25 assertions across 8 categories" beats "I tested thoroughly."
- **Honest constraints.** "Synthetic data limited what I could exercise" beats "production-ready."
- **Numbers when you have them.** "Pipeline runs in 38 seconds; peak memory 180MB" beats "fast and lean."
- **Real screenshots.** Of dashboards, of CI runs, of the drift report. Visual proof > text claims.
- **Trade-offs you considered, not just the one you picked.** "I considered Spark but chose DuckDB because..." is much stronger than just announcing the choice.

### What doesn't work

- **Tutorial-tone content.** "Today we'll learn about dbt!" — you're not teaching dbt, you're showing what you built.
- **Buzzword soup.** "Cutting-edge production-grade enterprise data observability platform." Real engineers see this for what it is.
- **Hidden weakness inflation.** "Working knowledge of Snowflake" if you've never logged into Snowflake. Hiring managers ask follow-up questions that expose gaps.
- **No code, no diagrams.** A wall of text on technical topics signals "I don't have the actual artifacts to show."
- **Promoted as "ultimate guide" / "everything you need to know."** Be calibrated; you have 16 weeks of experience, not 16 years.

### LinkedIn post template

If you also want to do the LinkedIn announcement (recommended), a short template that performs well:

```
After 16 weeks focused on data quality testing, I built an end-to-end project
covering everything from SQL test patterns to production drift detection.

The repo: [link]
The write-up: [link to blog post]

A few things that surprised me along the way:

→ Most "ML failures" are data engineering failures
→ Plan-shape SQL tests beat timing tests every time
→ Pick one place per concern; testing the same thing in 3 tools is just maintenance debt

Curious to hear from anyone who's tackled similar problems. What's the most
underrated test pattern you've adopted in production?

#DataEngineering #DataQuality #Testing
```

200 words. ~1 hour to draft + polish. Posts in the morning of a weekday for best engagement.

### Done when...

- [ ] You have a published blog post (or one ready to publish — final review pending)
- [ ] You have a LinkedIn / social post ready (or published)
- [ ] The post links to the GitHub repo
- [ ] You've shared with at least one person for feedback before going public
- [ ] You've added the blog link to your GitHub profile and resume

---

## Day 4 (Thu) — Interview Question Bank

### Goal

Build a comprehensive bank of interview questions (organized by topic) and **practice answering them out loud**. By end of day you can give fluent 60–90 second answers to ~20 common questions in the data quality / testing space.

### Why this works

You've seen most of these questions before — every week's "Interview Prep" section had 5. Today you compile them, fill gaps, and *practice them aloud*. Reading an answer is not preparing; speaking it is.

The "out loud" part is non-negotiable. Most candidates *think* they have a good answer until they hear themselves try to say it. Awkward word choices, unclear structure, dead-end sentences — all surface only when speaking.

### How to prepare

**Step 1 — Compile the bank from prior weeks (~30 min)**

Go back through the "Interview Prep" sections of each week's training file. Pull out the 5 questions per week (75 total across Weeks 2–14, give or take). Group them into categories:

| Category | Sample questions from prior weeks |
|---|---|
| **Data quality fundamentals** | 6 dimensions; how to handle PII; dimension trade-offs |
| **SQL** | Reconciliation patterns; window functions; plan reading |
| **Python testing** | pandas vs DuckDB; mock vs fake; pytest fixtures |
| **ETL / pipelines** | Idempotency; medallion architecture; reconciliation |
| **dbt** | Tests vs sources; build order; freshness |
| **Great Expectations** | When to use it; checkpoint design; CI integration |
| **CI/CD** | Branch protection; Slim CI for dbt; secrets handling |
| **Mocking & test data** | Faker vs sampled prod; factory fixtures; AI for synthetic |
| **Non-relational data** | JSON Schema; XML XPath; schema-on-read vs write |
| **Big data** | Spark vs DuckDB choice; sampling strategies; lazy evaluation |
| **Lakehouse** | Delta vs Iceberg; vacuum policies; time travel |
| **Performance** | EXPLAIN; pytest-benchmark; volume tests |
| **Observability** | Testing vs observability; alert fatigue; SLOs |
| **ML testing** | Drift kinds; train-test leakage; fairness when |

That's a reusable index. Put it in `interview_prep.md` in your project for ongoing practice.

**Step 2 — Self-assess (~30 min)**

For each question, rate yourself:

- 🟢 **Fluent** — I could answer in an interview right now, with examples
- 🟡 **Solid concept, needs polish** — I know the answer; my delivery is shaky
- 🔴 **Have to look it up** — I'd struggle to answer cold

Aim for ≥ 70% green by end of week. Yellow questions need practice; red questions need re-study + practice.

**Step 3 — Practice the green and yellow ones (~2 hours)**

Read each question aloud. Answer aloud, with a timer set to 90 seconds. Record yourself if you can — playback reveals more than you think.

For each question, the answer should follow this loose structure:

1. **Direct answer** (1 sentence) — show you understood the question
2. **The "why" or trade-off** (1–2 sentences) — show you understand context
3. **A concrete example or anecdote** (1–2 sentences) — show you've done it
4. **Caveats or "depends on..."** (1 sentence) — show senior thinking

Example, for the question "How do you handle data quality at scale?":

> [Direct answer] I tier checks by where they run and what they catch. [Trade-off] In CI, fast pre-deploy checks — schema validation, basic invariants — to catch obvious bugs before they ship. In production, observability checks on real data — drift, freshness, distribution — that catch what tests can't see. [Example] In my e-commerce capstone, dbt tests run on every PR, Soda Core runs nightly against production data, Evidently checks drift on a feature column. [Caveat] The right checks depend on the data and consumers — for a regulated dataset I'd add audit trails; for a consumer-facing one I'd add SLO-based alerting.

Four sentences, ~80 words, ~30 seconds. Hits the structure naturally.

**Step 4 — Drill the hard ones (~1 hour)**

Take your 5 weakest answers. Practice each 5 times until smooth. Speaking is muscle memory; repetition matters.

### The behavioral side

Technical questions are 60–70% of the interview. The rest is behavioral / situational:

- "Tell me about yourself."
- "Walk me through your background."
- "Tell me about a time you disagreed with a teammate."
- "What's the most challenging bug you've debugged?"
- "Why are you interested in this role?"

These have **less of a wrong answer than candidates think.** The mistake is to wing them. Prepare:

- A 60-second "tell me about yourself" that ties your experience to data quality / testing — even if your background isn't directly that
- Two specific stories from work or projects: one where you fixed something hard, one where you made a wrong call and learned from it
- A 30-second "why this role" answer that's specific, not generic

### Behavioral storytelling — the STAR pattern

Most behavioral questions want a story. STAR keeps you concise:

- **S — Situation.** What was the context? (1 sentence)
- **T — Task.** What were you responsible for? (1 sentence)
- **A — Action.** What did you do? (2–3 sentences — the meat)
- **R — Result.** What happened? Quantify if possible. (1 sentence)

A story for "tell me about a bug you debugged":

> [S] In my capstone project I had a reconciliation test that started failing intermittently — only on some PR runs, not all. [T] I needed to figure out if it was a real bug or test flakiness. [A] I added structured logging to the test, ran it 20 times, and noticed the failures correlated with a fixture that wasn't seeded — Faker was producing different data each run. I pinned the seed, the failures stopped. [R] The test went from ~80% pass rate to 100%, and I made "always seed Faker" a `.cursorrules` convention I now apply by default.

40 seconds. Real. Concrete. Shows debugging, root-cause thinking, and learning. **This is exactly what interviewers want.**

### Done when...

- [ ] You have an `interview_prep.md` with 75+ questions categorized
- [ ] You've self-rated each as 🟢 / 🟡 / 🔴
- [ ] You can answer 70%+ at the green level
- [ ] You've practiced the top 20 questions out loud, on a timer
- [ ] You have 2 prepared behavioral stories (STAR format)
- [ ] You have a polished 60-second "tell me about yourself"

---

## Day 5 (Fri 🤖) — Mock Interview with Claude

### What you're learning today

The most useful AI workflow you've encountered. Real interviewers are expensive (their time, your nervousness). Claude is free and infinitely patient. The mock-interview pattern lets you practice at high volume with feedback you can iterate on within minutes.

### Setup

Use Claude (claude.ai), preferably with the Projects feature so you can attach your repo. Mock interviews work in regular chat too — just paste relevant context.

### Exercise 1 — Technical screen (45–60 min)

The first mock interview should approximate a 30–45 minute technical screen — the early-stage interview most data engineering candidates face.

**Prompt to Claude:**

> *"Act as a senior data engineer interviewing me for a Data Quality Automation Engineer role. The interview is a 45-minute technical screen. Ask me 8–10 questions covering: SQL fundamentals, data quality concepts, testing approaches, CI/CD for data, and one curveball based on my answers.*
>
> *Rules:*
> *- Ask one question at a time. Wait for my answer.*
> *- After each answer, give brief feedback (1–2 sentences): what was strong, what could be sharper.*
> *- If my answer reveals a follow-up worth pursuing, pursue it.*
> *- Maintain interviewer energy — neutral, professional, slightly probing.*
> *- At the end, give an overall assessment: where I'd likely pass, where I'd struggle, what to practice.*
>
> *I'll attach my capstone repo for context. Start with question 1 when ready."*

Then *answer the questions out loud or in writing*. Don't look up answers. The point is to simulate cold conditions.

After the interview ends, ask:

> *"Now give me a more critical assessment. What were my three weakest answers and why? What would have been a stronger version of each?"*

This is the gold. The first feedback round is encouraging; the second-round critical pass reveals real gaps.

### Exercise 2 — Hiring manager / behavioral (30–45 min)

A different kind of interview, focusing on judgment and communication.

**Prompt:**

> *"Act as a hiring manager (not a senior engineer — focus is on judgment, ownership, and communication, not technical depth) interviewing me for a Data Quality Automation Engineer role. The interview is 30 minutes.*
>
> *Ask me 5–6 questions covering:*
> *- Tell me about yourself*
> *- A challenging project and what you learned*
> *- A time you disagreed with a teammate*
> *- How you'd approach a vague problem (e.g., 'our data quality is bad — fix it')*
> *- Why this role / why this company (I'll fill in the company)*
>
> *Rules:*
> *- Probe with follow-ups. Don't accept vague answers.*
> *- After the full interview, give feedback on: structure, specificity, where I sounded vague, what came across well.*
> *- Be honest, not encouraging.*
>
> *Ready when you are."*

Behavioral interviews are where many technical candidates underperform. This practice is unusually high-leverage.

### Exercise 3 — Take-home / case study (1 hour)

Some companies replace technical screens with take-homes. Practice once:

**Prompt:**

> *"Generate a realistic 60-minute take-home assignment for a Data Quality Automation Engineer role. Include: a problem statement, a small synthetic dataset (or describe one), expected deliverables, and evaluation criteria. Make it realistic — what an actual hiring team would send.*
>
> *After I submit, evaluate my work as the hiring panel would: what's strong, what's missing, where it would land in the hire/no-hire conversation."*

Spend 60 minutes on the assignment. Submit your work. Read the feedback. Note the judgment criteria — those are what hiring panels actually use.

### Exercise 4 — Walk-me-through-the-repo (15–20 min)

Specific to portfolio-based interviews:

**Prompt:**

> *"I'll attach my capstone repo. Act as a senior engineer who has 10 minutes to evaluate it before our interview. After your review, ask me 4 questions about specific design decisions in the repo. Probe my reasoning. If I'm vague, ask follow-ups until you understand the actual decision I made.*
>
> *The goal is to find weak points in my ability to articulate my own work. Be skeptical."*

The point isn't to defend everything; it's to practice articulating decisions, including the ones you'd reverse today.

### What good Claude interviewer feedback looks like

The best AI feedback is *specific*, not encouraging. Push for it:

- "That was good." → not useful
- "That answer would have been stronger if you'd named a specific tool you'd choose and why" → useful
- "Your answer to question 4 was technically correct but generic — a hiring manager would notice you're describing the textbook, not your experience" → very useful

If Claude defaults to soft feedback, prompt: *"Be more critical. Imagine you're trying to find reasons to NOT hire me. What weaknesses showed up?"*

### Acting on feedback

After each mock interview:

1. **Note the 3 weakest answers** in `notes.md`
2. **Write a stronger version of each.** Often you knew a better answer; under simulated pressure you didn't reach it. Practice the version that includes the better answer.
3. **Re-run with the same questions** later in the day or the next day. You should be visibly better the second time.

### Iteration cadence

For real interview prep, this is the rhythm that works:

- **Days 1–3 of week**: 1 mock interview per day. 2 hours each (interview + reflection).
- **Days 4–5**: deep on weakest answers. Drill specific questions.
- **Repeat for 1–2 weeks** before real interviews.

This week — do the 4 exercises, even if abbreviated. Build the muscle.

### Done when...

- [ ] You've completed at least one technical mock interview with Claude
- [ ] You've completed at least one behavioral mock interview with Claude
- [ ] You've gotten critical (not encouraging) feedback on each
- [ ] You've identified and rewritten 3+ weak answers
- [ ] You've added a "weak spots" section to `notes.md` for ongoing practice

---

## Final Self-Assessment — The 16-Week Curriculum Test

If you've engaged seriously across all 16 weeks, you should be able to answer most of these without hesitation. Treat this as a final calibration.

### SQL & Data Quality (Weeks 1–4)
1. Three reasons to use `LEFT JOIN ... WHERE x IS NULL` over `NOT IN`?
2. The 6 data quality dimensions, and an example of each?
3. Why does `SELECT count(*)` differ from `SELECT count(column)`?
4. What's the medallion architecture, and what's tested at each layer?

### Tooling (Weeks 5–8)
5. When does Great Expectations win over pandera or vice versa?
6. The difference between dbt's generic tests and singular tests?
7. What does `actions/checkout@v5` do, and why is it always step 1?
8. Faker vs sampled production data vs AI-generated synthetic — when each?

### Advanced Data (Weeks 9–11)
9. Why is JSON Schema's `additionalProperties: false` a trade-off?
10. When is DuckDB the right tool, and when does Spark win?
11. How does Delta Lake achieve ACID over immutable Parquet files?

### Performance & Production (Weeks 12–13)
12. Why are plan-shape SQL tests more robust than timing tests?
13. The three deployment models for Soda checks and when each fits?
14. SLI vs SLO vs SLA — definitions in your own words?

### ML & Capstone (Weeks 14–16)
15. Three kinds of drift, with concrete examples?
16. Why are most production ML failures actually data engineering failures?
17. Walk through your capstone in 5 minutes — out loud.

If you stumbled on more than 3, those are your continued-practice targets.

---

## What's Next? — Beyond Week 16

The curriculum ends here, but the work doesn't. A few directions worth considering:

### Land the role you trained for

The capstone + the polished portfolio + practiced answers + LinkedIn presence = you have an active candidacy. Apply. The first 5 applications teach you what's missing in your materials; iterate.

### Production exposure

Synthetic data is sufficient for the curriculum; real production data has texture you can't simulate. If you have access to real data at work, start using these patterns there. If you don't yet, the capstone is your bridge.

### Pick a depth

The curriculum touched many tools shallowly. To go senior, pick one and go deep. A few high-leverage choices for data quality / testing:

- **dbt and dbt Cloud** — the analytics engineering skill that compounds
- **Apache Iceberg** — the table format winning the lakehouse war; deep knowledge here is in demand
- **Soda or Monte Carlo or another observability platform** — running these at scale is its own discipline
- **A specific cloud's data stack** — Snowflake, BigQuery, Databricks; pick one your local market values

Six months of depth in one of these from this foundation puts you well ahead of most "I know all the tools" candidates.

### Contribute back

The libraries you use have open issues. Some are documentation-only ("how do you do X?"). Answering one or two as you encounter them is the easiest way into open-source contribution. dbt, Great Expectations, Evidently — all welcome answers from competent users, not just maintainers.

### Stay calibrated

The data engineering / data quality landscape shifts every 6–12 months. New tools displace old ones; APIs change; opinions evolve. Re-read your curriculum once a year; see what aged well and what didn't. The aging itself is a useful signal about which patterns are durable.

---

## Final closing note

Sixteen weeks ago you started Week 1 with SQL. You now have a portfolio piece, a tested vocabulary, and the ability to converse fluently with senior engineers about real engineering trade-offs.

The hardest part of the work was the discipline of showing up week after week. That muscle — the ability to commit to a learning plan and finish it — is more valuable than any specific tool you've learned. Companies hire for it. Promotions follow it. Use it.

Good luck out there.

---

## Done when... (the whole curriculum)

- [ ] You finished Week 16
- [ ] Your capstone is on GitHub, with green CI badge
- [ ] Your portfolio write-up is published
- [ ] You can walk through your work in 5 minutes, fluently
- [ ] You've drilled the top 20 interview questions out loud
- [ ] You've done at least one full mock interview with Claude
- [ ] You've identified your top 3 ongoing-practice targets
- [ ] You've applied to at least one role using the new materials (or scheduled to do so)

---

*That's the curriculum. 16 weeks done. Now go use it.*
