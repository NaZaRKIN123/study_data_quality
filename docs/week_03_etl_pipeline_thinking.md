# Week 3 — ETL Concepts & Pipeline Thinking | Training Materials

> **Companion to:** Week 3 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Understand what you're actually testing — the shape, stages, and failure modes of data pipelines. By Friday you'll have built a tiny three-layer pipeline and know what tests live at each layer.

---

## How to use this file

- This week is more conceptual than Week 1 or Week 2 — but every concept is grounded in a small running pipeline you'll build
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday is **hands-on AI workflow practice** — risk analysis with Claude
- Answers to all self-checks are at the bottom of the file

---

## One-time setup (~10 minutes)

You'll reuse the project from Week 2 — same `customers.csv`, `orders.csv`, etc. If you skipped Week 2, run the `seed_data.py` script from Week 2's setup section now.

Add a new folder for this week's pipeline code:

```bash
cd week2-python-testing      # your Week 2 folder
mkdir pipeline tests/pipeline
```

You'll build the pipeline in `pipeline/` and tests in `tests/pipeline/`.

No new dependencies needed — pandas + pytest is enough.

---

## Day 1 (Mon) — ETL vs ELT

### Theory

**ETL** = Extract → Transform → Load. Data is reshaped *before* it lands in the warehouse. Old-school, born in an era when storage was expensive and warehouse compute was a constrained resource.

**ELT** = Extract → Load → Transform. Data lands raw in the warehouse first; transformation happens *inside* the warehouse using SQL. Modern. Won the day once cloud warehouses (Snowflake, BigQuery, Redshift) made storage near-free and compute elastic.

| | ETL | ELT |
|---|---|---|
| Where does T happen? | A separate compute layer (Spark, Informatica, custom Python) before loading | Inside the warehouse, usually as SQL (often via dbt) |
| Where does raw data live? | Often nowhere persistent — it's transformed in flight | In the warehouse, in a "raw" or "bronze" schema |
| Re-running with new logic | Re-extract from source (often slow, sometimes impossible) | Re-run transformations against existing raw data (fast) |
| Storage cost | Lower (only transformed data is stored) | Higher (raw + transformed both stored) |
| Schema flexibility | Rigid — schema decided up front | Loose — load first, decide structure later |
| Where do you test? | Mostly the T stage, before load | Both: ingestion correctness *and* SQL transformation correctness |

### The modern data stack (you'll meet all of these)

A typical ELT pipeline today:

```
[Source DBs / SaaS APIs / Files]
        ↓
[E+L tools]   Fivetran / Airbyte / custom Python
        ↓
[Warehouse]   Snowflake / BigQuery / Redshift / Databricks
        ↓
[T tool]      dbt (most common) / SQLMesh
        ↓
[Serving]     Looker / Tableau / Mode / reverse ETL (Hightouch, Census)
```

You'll touch **dbt** in Week 6 and Snowflake/Databricks-style platforms later. For now, just understand the *shape* — and which layer each test type belongs at.

### Why this matters for QA

In ETL, transformation is a separate Python/Spark job — you test it in isolation with pytest, before any database is involved. (That's exactly what you did in Week 2.)

In ELT, transformation is SQL run inside the warehouse — so you test it *there*, with tools like dbt tests or Great Expectations pointing at the warehouse. The tests look different (declarative SQL assertions instead of pytest functions) but the principles are identical.

### Gotchas

1. **"ETL" is used as shorthand for "any data pipeline"** in conversation, even when the pipeline is technically ELT. Don't get hung up on the label — focus on *where transformation happens*, because that's where your tests need to be.
2. **ELT means raw data sticks around.** That's a feature for replay-ability and a privacy/compliance liability for PII. Many regulated industries can't do pure ELT.
3. **Real pipelines are hybrid.** Lightweight cleanup (dropping bad rows, decoding) often happens *before* load in an "ELT" pipeline. The line is blurry.

### Exercises

No coding today — this is mental-model day. Open a notes file and answer these:

1. For each scenario below, decide: ETL or ELT? Justify in one line.
   - A bank moves transactions from Oracle to a Snowflake warehouse, masking account numbers in flight before they ever land in cloud storage.
   - A startup pulls Stripe + Salesforce + Google Ads via Fivetran into BigQuery, then runs dbt models nightly to build their finance reports.
   - A team uses a Python script to read a CSV from S3, joins it with a small reference table in memory, and writes the result back to S3 as Parquet.
2. Sketch (in plain text or on paper) the pipeline for a hypothetical e-commerce company that needs:
   - Orders from a Postgres OLTP database
   - Web events from a streaming source
   - Loaded daily into a warehouse, with revenue dashboards on top
   - Mark which boxes are E, L, T, and which tools you'd choose at each stage
3. Open the [Airbyte ETL vs ELT post](https://airbyte.com/blog/etl-vs-elt) (or any equivalent — search "ETL vs ELT 2024"). Read it. Did anything in their framing contradict mine? Which is right?
4. **Reflection:** in your Week 2 pytest tests, were you testing transformation logic before it hit any storage? That was an ETL-style test. Could you imagine the same business rules tested *after* load in SQL? That'd be ELT-style.

### External practice

- [Airbyte — ETL vs ELT](https://airbyte.com/blog/etl-vs-elt) — short, accurate
- [Modern Data Stack overview by dbt Labs](https://www.getdbt.com/blog/future-of-the-modern-data-stack) — the canonical "what tools fit where" reference
- *Fundamentals of Data Engineering* by Reis & Housley (O'Reilly, 2022) — chapters 1–3 are the best paid material on this; check your library

### Self-check (Day 1)

> Q1.1 — One sentence: what's the actual difference between ETL and ELT?
> Q1.2 — Why did ELT become dominant in the last ~10 years? Name two reasons.
> Q1.3 — In an ELT pipeline using dbt, is your transformation code SQL or Python?
> Q1.4 — A pipeline does a small Python `cleanup_phone_numbers()` step before loading raw data into Snowflake. Is the overall pattern ETL, ELT, or both?

---

## Day 2 (Tue) — Common Pipeline Patterns

### Theory

Today's vocabulary determines whether you sound like someone who has shipped data pipelines or someone who has only read about them. Five concepts:

#### 1. Batch vs Streaming

- **Batch** processes data in chunks at intervals — every hour, every night, weekly. Simple, well-understood, easy to test. The default for analytical workloads.
- **Streaming** processes events one at a time as they arrive (or in tiny "micro-batches" of seconds). Lower latency, much harder to test and reason about. Tools: Kafka, Flink, Spark Structured Streaming.

90% of the data tested in industry is batch. Streaming gets disproportionate attention in conference talks.

#### 2. Idempotency

A pipeline is **idempotent** if running it twice with the same input produces the same output as running it once. Mathematically: `F(F(x)) = F(x)`.

This is **the** most important property of a production pipeline. Why? Because pipelines fail in the middle, get re-triggered, get re-run by humans debugging. Without idempotency, every retry is a potential data corruption.

The standard pattern: **`MERGE`/`UPSERT` keyed by a deterministic primary key**, never blind `INSERT`. Or: write to a date-partitioned location and overwrite that partition on rerun.

#### 3. Late-arriving data

Events with timestamps from the past, arriving now. Causes:
- Mobile apps queuing events offline, syncing days later
- Upstream system was down, replayed
- Clock skew across machines

Pipelines have to choose: **wait** (delay processing until "everything has arrived") or **process and revise** (compute now, restate later when laggards arrive).

A **watermark** is the explicit decision: "I won't accept data older than X." Anything later than the watermark is dropped or routed to a side channel.

#### 4. Partitioning

Data is physically split into chunks by some key — usually date (`partition_date=2024-05-01/`). Two reasons:
- **Query performance** — only read partitions you need
- **Idempotency / replayability** — rerun a single day without rebuilding the whole dataset

A common bug class: confusing **event date** (when did it happen?) with **ingestion date** (when did we receive it?). Late-arriving data turns this from "small annoyance" to "wrong answer in the dashboard".

#### 5. Delivery semantics

Three flavors when reading from a queue or stream:

| Semantic | Meaning | Risk |
|---|---|---|
| At-most-once | Each event processed 0 or 1 times | Data loss |
| At-least-once | Each event processed 1+ times | Duplicates (must dedupe) |
| Exactly-once | Each event processed exactly once | Sounds great. Hard to actually achieve. |

In practice, **most production pipelines are at-least-once + idempotent processing**, which gives you "effectively exactly-once" without the mythology.

### Gotchas

1. **"Idempotent" and "deterministic" aren't the same.** A function can be idempotent (`F(F(x))=F(x)`) without being deterministic (`F(x)` doesn't always equal `F(x)`) — and vice versa. For data pipelines you usually want both.
2. **`INSERT` is almost never the right operation.** Use `MERGE`, `INSERT ... ON CONFLICT`, or full-partition overwrites. If your code says `INSERT INTO target VALUES ...` — that's a bug waiting for the first retry.
3. **Watermark thresholds are business decisions, not technical ones.** "Drop events more than 7 days late" has accounting implications. Always confirm with the data owner.
4. **Partitioning by `ingestion_date` makes reprocessing easy but skews historical analytics.** Partitioning by `event_date` is correct for analytics but harder to operate. Many pipelines do both (one as the partition key, the other as a column).
5. **"Exactly-once" claims usually have an asterisk.** Kafka and Flink advertise it within their own boundaries — but the moment you write to an external sink (a database, an API), the guarantee weakens. Read the fine print.

### Exercises

Now we start coding. Create `pipeline/ingest.py`:

1. Write `ingest_orders(input_path, output_path) -> int`. It should:
   - Read `orders.csv` with explicit dtypes (use what you learned in Week 2)
   - Drop any rows where `order_id` is NULL
   - Write the result as Parquet to `output_path` (use `df.to_parquet`; pip install `pyarrow` if needed)
   - Return the number of rows written
2. **Make it idempotent.** Calling `ingest_orders(...)` twice with the same input should result in the same output file with the same row count — no duplication. Test this: run it twice, check the row count is identical.
3. Now add `customer_id == 999` to your `orders.csv` for one row. Re-run. Confirm idempotency still holds (the bad row didn't double).
4. Identify the natural **partition key** for orders. (Hint: it's `order_date`.) Modify `ingest_orders` to write each date's data to its own subfolder: `output_path/order_date=2024-05-01/orders.parquet`. This is the file layout used by every modern data lake (Hive partitioning).
5. **Late-arriving exercise:** add a row with `order_date = '2024-04-01'` to `orders.csv`. Re-run the partitioned ingestion. What happens to the existing `2024-04-01` partition (if any)? What *should* happen for idempotency?
6. **Trap exercise:** what if your ingestion function appends rows instead of overwriting? Modify it to `df.to_parquet(..., mode="append")` (this isn't a real pandas option — what's the equivalent? what would happen if it were?). Then revert.

### External practice

- *Designing Data-Intensive Applications* by Martin Kleppmann — chapter 11 covers stream processing and exactly-once. Probably the single best technical book in this space.
- [DataEngineering.wiki — Idempotency](https://dataengineering.wiki/) — short, practical
- [Confluent — exactly-once semantics in Kafka](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/) — for when you want to know what the "exactly-once" claim actually means

### Self-check (Day 2)

> Q2.1 — Define idempotency in one sentence. Then give one concrete example of a non-idempotent operation in a data pipeline.
> Q2.2 — A streaming pipeline accepts events. An event arrives with a timestamp 14 days in the past. The watermark is set to "drop events older than 7 days". What happens?
> Q2.3 — What's the difference between partitioning by `event_date` and `ingestion_date`? Which is "more correct"? Why might you use the other?
> Q2.4 — A pipeline reads from Kafka with at-least-once semantics. Without any other defenses, what data quality issue will appear in the destination?

---

## Day 3 (Wed) — What Can Go Wrong

### Theory — the failure mode catalog

Below are the failure modes that account for the vast majority of data quality incidents you'll diagnose. Memorize the names; you'll see all of them in production within a year.

| Failure mode | What happens | How tests catch it |
|---|---|---|
| **Schema drift** | Upstream renames/adds/removes a column | Pin expected schema; assert columns + dtypes match |
| **Type mismatch** | Same column, different type than yesterday (`"123"` → `123`) | dtype assertion; range checks may also flag |
| **Pipeline failure mid-load** | Job crashed at 80% — partial data is in the destination | Row count check vs source; "did the run end successfully?" assertion |
| **Duplicate loads** | Non-idempotent rerun produced 2× rows | Uniqueness assertion on primary key |
| **Late-arriving data** | Events from yesterday land today, pollute today's stats | Compare grouping by event_date vs ingestion_date |
| **Time zone bugs** | Mixed UTC and local times → off-by-hours errors | Standardize at ingestion; assert timestamps are UTC |
| **Silent value corruption** | Encoding, truncation, or float precision loss | Hash-based reconciliation against source |
| **Cardinality explosion** | A bad JOIN multiplied rows | Row count before/after JOIN equals expected |
| **Source row vanishes** | Upstream hard-deletes a row; pipeline doesn't notice | Soft-delete handling; row-count drift alerts |
| **Referential break** | A foreign key points to a parent that no longer exists | Anti-join check (you wrote this in Week 1, Day 4) |
| **Stale data** | Pipeline ran but with old input | Freshness check on source timestamps |
| **Encoding chaos** | UTF-8 read as latin-1, mojibake everywhere | Explicit encoding on read; sample-based string checks |

### The most dangerous category: silent corruption

The above table sorts roughly by **how loud the failure is**. Schema drift is loud — your pipeline crashes. Silent corruption is the dangerous one: pipeline succeeds, dashboards update, and the numbers are wrong. By the time anyone notices, decisions have been made on bad data.

The defense is **reconciliation tests**: independently recompute a metric two ways and assert they match. Total revenue from `orders.total_amount` vs `SUM(quantity * unit_price)` from `order_items` is exactly this pattern (you wrote it in Week 1 Day 4 and Week 2 Day 3).

### Gotchas

1. **"It worked yesterday" is the most common bug report**, and it's almost always either schema drift or a non-idempotent rerun. Train yourself to check those two first.
2. **Tests that only fail when the data is *very* wrong are useless.** A range check that allows `0 <= revenue <= 1_000_000_000` will pass on a 10× error. Tighten ranges to plausible business limits.
3. **Time zone bugs hide for months.** `datetime` without timezone info is the original sin. Standardize everything to UTC at ingestion; convert only at the display layer.
4. **`NaN` propagation through aggregations** can silently zero-out a metric. `SUM` ignores NaN, but `mean` over `[NaN, NaN, NaN]` is `NaN`, which then breaks downstream comparisons.
5. **"The data is missing" and "the data is zero" are different.** A test that checks `revenue > 0` won't catch the case where a missing day shows up as `revenue = 0` (because `SUM` of zero rows = 0 in pandas, NULL in SQL — see Week 2 Day 2).

### Exercises

Today is "introduce bugs and catch them." For each scenario, modify `orders.csv` (or your ingestion code) to reproduce the failure, then write a pytest that catches it. Restore the file between exercises.

1. **Schema drift:** rename `total_amount` to `amount` in `orders.csv`. Run your Week 2 tests. Observe the failure. Now write a test that catches it specifically: `assert "total_amount" in df.columns`.
2. **Type drift:** change one `total_amount` value to `"one hundred"` (a string). Read the file. What dtype does the column end up as? Write a test that asserts `df["total_amount"].dtype` is numeric.
3. **Duplicate load:** simulate a non-idempotent rerun by appending the contents of `orders.csv` to itself (`cat orders.csv >> orders.csv`). Write a test that catches it via primary key uniqueness.
4. **Stale data:** add a `loaded_at` column to your ingestion output. Write a freshness test: `loaded_at` must be within the last 24 hours. Test what happens if you re-run with a stale value.
5. **Reconciliation:** write the cross-table reconciliation test from Week 1 / Week 2 again, but make it parametrized — run it for orders 1001 through 1007. Which orders fail, and why? (You should see 1004 and 1006 fail, for two different reasons.)
6. **Time zone trap:** add a column `order_timestamp` with strings like `'2024-05-01 09:00:00'` (naive — no timezone). Convert to datetime, then to UTC, then back to "America/New_York". What's the displayed value? What was the original "intent" — was the string already in UTC, or in some local time? **There's no way to know without a contract.** Write that observation as a comment in your test file.

### External practice

- [Locally Optimistic — Testing data pipelines](https://locallyoptimistic.com/post/data-testing/) — opinionated, accurate, short
- [The Data Engineering Subreddit — "what's the worst data bug you've ever seen"](https://www.reddit.com/r/dataengineering/) (search the term) — sobering and educational
- [Monte Carlo — Data observability concepts](https://www.montecarlodata.com/blog-what-is-data-observability/) — preview of Week 13

### Self-check (Day 3)

> Q3.1 — A data pipeline that succeeded yesterday produces incorrect output today. What are the two most common causes?
> Q3.2 — Why is silent corruption more dangerous than a hard pipeline failure?
> Q3.3 — Name three independent properties of a single column that you'd assert in a quality test.
> Q3.4 — `df["amount"].sum()` returns `0`. Without seeing the data, name two distinct scenarios that produce that result.

---

## Day 4 (Thu) — Testing at Each Stage

### Theory — the layered testing model

A data pipeline has stages. Different bugs are visible at different stages. **Testing only at the end means bad data in early stages cascades silently.**

The medallion pattern (Bronze / Silver / Gold) is the most common naming — same idea, different layers:

| Layer | What lives here | What you test |
|---|---|---|
| **Bronze (raw / ingestion)** | Source data, minimally processed, schema preserved | Schema match, row count vs source, freshness, encoding |
| **Silver (cleaned / conformed)** | Deduped, type-cast, joined to reference data, business keys assigned | Uniqueness on PK, no nulls in required columns, referential integrity, value ranges |
| **Gold (serving / marts)** | Aggregated, business-ready, dashboard-shaped | Reconciliation against silver, expected row counts per dimension, business rule assertions |

You don't test the same thing at every layer — that wastes CI time. **Each layer catches its own bugs.**

### What test belongs where (rules of thumb)

- **At the source / pre-load:** "Is the file there? Right name? Right size? Right encoding?"
- **At Bronze:** "Did all rows from source land here? Does the schema match what we expected from the supplier?"
- **At Silver:** "Are PK assumptions valid? Do FKs resolve? Are values in expected ranges? Is each row unique on the business key?"
- **At Gold:** "Do my aggregates reconcile to silver? Does today's revenue look plausible given last 30 days? Are all expected dimensions present?"

### Gotchas

1. **Don't duplicate tests across layers.** If you're checking `customer_id IS NOT NULL` at Bronze, Silver, *and* Gold, you've added 2× CI cost for one check. Pick one layer (usually Silver, where the column is "guaranteed" by contract) and trust it.
2. **Source-side tests are often forgotten.** Reconciling row counts with the upstream system is often the only way to catch "we missed half the file" bugs. Yet many teams skip it because the upstream system is "someone else's problem."
3. **Smoke tests vs deep checks** run on different cadences. Smoke tests (does the pipeline succeed, are tables non-empty) every run. Deep checks (full reconciliation, full distribution profile) maybe daily or on demand — too expensive every run.
4. **Gold tests need business context.** "Revenue should be ≥ 0" is too loose. "Revenue should be within 30% of last week's" is closer. The tightness of Gold tests is a measure of how well you understand the business.

### Exercises — build a 3-layer pipeline

Create the file `pipeline/build.py` and implement the three functions below. Then write tests in `tests/pipeline/test_pipeline.py`.

```python
# pipeline/build.py
import pandas as pd
from pathlib import Path

DATA = Path(__file__).parent.parent

def bronze_orders() -> pd.DataFrame:
    """Bronze: load orders.csv with explicit schema. No transformation."""
    return pd.read_csv(
        DATA / "orders.csv",
        dtype={
            "order_id":     "Int64",
            "customer_id":  "Int64",
            "total_amount": "Float64",
            "status":       "string",
        },
        parse_dates=["order_date"],
    )

def silver_orders(bronze: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Silver: drop cancelled, drop orphan customers, dedupe by order_id."""
    df = bronze[bronze["status"] == "completed"].copy()
    valid_customers = set(customers["customer_id"].dropna())
    df = df[df["customer_id"].isin(valid_customers)]
    df = df.drop_duplicates(subset=["order_id"])
    return df.reset_index(drop=True)

def gold_daily_revenue(silver: pd.DataFrame) -> pd.DataFrame:
    """Gold: revenue per day, ready for the dashboard."""
    return (
        silver
        .groupby("order_date", as_index=False)["total_amount"]
        .sum()
        .rename(columns={"total_amount": "revenue"})
        .sort_values("order_date")
        .reset_index(drop=True)
    )
```

Now write the tests. **Write at least two assertions per layer**, scoped to that layer's responsibility.

1. **Bronze tests** (in `tests/pipeline/test_bronze.py`):
   - Schema: required columns present, dtypes match expected
   - Row count: matches the line count of the source CSV (minus the header)
2. **Silver tests** (in `tests/pipeline/test_silver.py`):
   - `order_id` is unique
   - `customer_id` has no nulls and every value exists in `customers`
   - No row has `status == "cancelled"`
   - No row has the orphan customer (id = 999)
3. **Gold tests** (in `tests/pipeline/test_gold.py`):
   - Reconciliation: `gold["revenue"].sum()` equals `silver["total_amount"].sum()` (treating NULLs the same way)
   - Every date in silver appears in gold (no dropped days)
   - All revenue values are non-negative
4. **Run the whole suite:** `pytest -v tests/pipeline/`. How many tests? How long does it take?
5. **Stretch:** add a "cross-layer reconciliation" test: count of distinct customers in gold (after grouping by date) should equal count of distinct customers in silver. If you didn't keep customer_id in gold, why not? Should you?
6. **Trap exercise:** introduce a bug in `silver_orders` that changes `drop_duplicates(subset=["order_id"])` to `drop_duplicates()`. Re-run the suite. Which test catches it? Why didn't the others?

### External practice

- [dbt Labs — Best practices for data testing](https://docs.getdbt.com/best-practices/materializations/3-configuring-materializations) (and adjacent articles) — opinionated, well-written
- [Locally Optimistic — Testing data pipelines](https://locallyoptimistic.com/post/data-testing/) — re-read with this layered lens; it'll click harder
- [Databricks — Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) — the Bronze/Silver/Gold framing, named

### Self-check (Day 4)

> Q4.1 — At which layer do you test referential integrity? Why not the others?
> Q4.2 — A test asserts "yesterday's revenue is within 30% of the 30-day average." At which layer does this belong?
> Q4.3 — You're tempted to put the same `not_null(customer_id)` check at Bronze, Silver, and Gold. What's a good reason to, and a good reason not to?
> Q4.4 — A bug in the `bronze_orders` function silently converts `customer_id` to a float (Int64 → float64). Which test in this exercise would have caught it?

---

## Day 5 (Fri 🤖) — AI Workflow: Pipeline Risk Analysis

### What you're learning today

Two skills: (1) using AI as a **risk-analysis brainstorming partner** to surface failure modes you didn't think of, and (2) converting that risk list into a runnable test plan. By the end of this session, you'll have an AI-augmented version of yesterday's three-layer pipeline.

### Setup (~5 min)

- Open Claude or your AI tool of choice
- Have your `pipeline/build.py` from Day 4 ready

### Exercise 1 — Failure mode brainstorming

Paste your `build.py` source code into Claude with this prompt:

> *"Act as a senior data engineer reviewing this pipeline. List every realistic failure mode you can think of, organized by layer (bronze / silver / gold) and by category (schema, value, performance, operational). For each failure mode, suggest one concrete pytest assertion that would catch it. Be specific to the columns and joins in this code, not generic."*

Read the output critically. The AI will likely:
- Suggest some failure modes you missed (good — add them)
- Suggest some that don't apply to your specific code (filter them out)
- Phrase tests vaguely ("check data quality") — push back: *"Be specific. What column? What threshold? What predicate?"*

### Exercise 2 — Convert risks to runnable test stubs

Pick five failure modes from Exercise 1 that you didn't already test for. In Cursor (or with Claude + manual paste), prompt:

> *"For each of these five failure modes, write a pytest function in the style of my existing tests in `tests/pipeline/`. Use the validators from `validators.py` where they apply. Include a clear assertion message."*

Run the new tests. For each:
- If it fails — was it a real bug, or a false alarm from a too-strict assertion?
- If it passes — did the AI write something that *would* catch the bug, or just `assert True`?

### Exercise 3 — The "what if" prompt

This is one of the most useful AI workflow patterns for risk analysis. Prompt:

> *"Imagine each of these six things happens to my pipeline tomorrow. For each, walk me through which of my current tests would catch it, which would silently pass, and what new test I'd need:*
> *1. The source CSV adds a new column called 'discount'.*
> *2. The 'order_date' column starts arriving in MM/DD/YYYY format instead of ISO.*
> *3. A row appears with order_id = NULL.*
> *4. Two rows appear with the same order_id but different total_amounts.*
> *5. A customer_id that exists in orders no longer exists in customers (upstream deleted them).*
> *6. The CSV file is empty (zero data rows, header only)."*

This forces the AI (and you) into adversarial thinking. Capture the gaps in a `gaps.md` file — these are your candidates for next week's tests.

### Update your `.cursorrules`

Add a section about pipeline conventions:

```
Pipeline conventions:
- Bronze functions take a path, return a DataFrame with explicit dtypes.
- Silver functions take Bronze DataFrame(s) as input, return a transformed DataFrame.
- Gold functions take Silver DataFrame(s) as input, return aggregated DataFrame.
- All transformation functions are pure: same input → same output, no side effects.
- All transformations preserve a primary key trail; no row-level "ghost rows" appear.
- Tests are organized in tests/pipeline/test_{layer}.py (one file per layer).
- Tests at each layer assert only that layer's responsibilities — no cross-layer duplication.
```

### Quality bar — when is an AI-generated test plan "good"?

- [ ] Every failure mode is *specific to the schema and joins of this pipeline*, not generic
- [ ] Every suggested test names a column and a predicate, not "check data quality"
- [ ] No suggestion contradicts a test you already have (or if it does, it's flagged as a stricter version)
- [ ] At least one suggestion surprised you — if not, the AI is just paraphrasing, not adding value
- [ ] Each test stub is runnable as-is and produces a useful failure message

### Reflection (write 3–5 sentences in `notes.md`)

- Which failure modes did the AI catch that you missed?
- Which categories did it over-emphasize? (Often: performance and security, even when not relevant.)
- How does Friday week 3 differ from Friday week 2? (Hint: today was about *risk surfacing*, not test scaffolding. Different prompt patterns.)

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 4. 5–7 = re-review the weak day. <5 = redo exercises.

1. In one sentence each: ETL vs ELT — what's the difference?
2. Why did ELT become dominant after ~2015?
3. Define idempotency. Give an example of a non-idempotent SQL statement and how to make it idempotent.
4. A streaming pipeline accepts events with timestamps. What's a watermark, and what trade-off does it embody?
5. Name three failure modes that produce *silent* corruption (no exception, but wrong output).
6. What's the difference between partitioning by event_date and ingestion_date? Which would you choose for analytics?
7. In the Bronze/Silver/Gold model, where do you put a referential integrity check, and why?
8. Reconciliation tests compare two independent computations of the same metric. Why is this different from a "value range" test, and when do you need it?
9. A pipeline test passes for 30 days, then starts failing. Without seeing the failure message, what are the three most likely causes?
10. You ask Claude for a pipeline risk analysis. The output is a list of 15 generic risks ("data quality issues", "performance problems"). What do you do?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about pipeline thinking. Try to answer aloud (or in writing) before peeking at "what a good answer covers".

### IQ1. "What's the difference between ETL and ELT? Which is more common today, and why?"

*What a good answer covers:*
- ETL transforms data *before* loading; ELT loads raw data first and transforms in the warehouse
- ELT became dominant once cloud warehouses (Snowflake, BigQuery) made compute and storage elastic and cheap, so storing raw data and re-transforming on demand became economical
- The "T" in ELT typically lives in dbt or similar — SQL-based, version-controlled, testable
- ELT also enables replay-ability: if business logic changes, you re-transform without re-extracting
- Caveat: regulated industries sometimes can't store raw PII, so they fall back to ETL

*Likely follow-up:* "What's a downside of ELT?" (Answer: storage cost; raw-data sprawl; harder PII / GDPR compliance because raw data sticks around.)

### IQ2. "Explain idempotency. Why does it matter for data pipelines?"

*What a good answer covers:*
- A pipeline is idempotent if running it N times produces the same result as running it once
- Pipelines fail mid-flight, get retried, get re-run by humans debugging — without idempotency every retry is a corruption risk
- Standard pattern: use deterministic primary keys + UPSERT/MERGE instead of INSERT, or partition + overwrite-partition
- Idempotency is often confused with determinism — they're related but distinct (you can be idempotent and non-deterministic, e.g. logging only the latest result)

*Likely follow-up:* "Walk me through how you'd make a `INSERT INTO daily_revenue ...` SQL statement idempotent." (Answer: replace with `MERGE` keyed on `(date, dimension)`, or `DELETE FROM daily_revenue WHERE date = :d` followed by `INSERT`, or write to a date-partitioned table and overwrite the partition.)

### IQ3. "What kinds of tests would you write for a data pipeline that loads orders from a Postgres source into a Snowflake warehouse?"

*What a good answer covers:*
- **At the source / pre-load:** can we connect? is data available? freshness check.
- **At the bronze layer:** schema matches contract; row count from Postgres reconciles with row count loaded; encoding is correct
- **At the silver layer:** primary key uniqueness; no nulls in required columns; referential integrity (every customer_id resolves); value ranges (no negative amounts)
- **At the gold/serving layer:** business reconciliation (revenue from orders = sum of order_items × unit_price); aggregate plausibility (today within X% of recent average); all expected dimensions present
- **Operational:** pipeline ran successfully (job status); pipeline ran *recently* (freshness); duration within SLA

*Likely follow-up:* "Which of those would you run on every pipeline execution, and which only daily?" (Answer: schema, row count, PK uniqueness, NULLs every run; full reconciliation + distribution profiling daily because it's expensive.)

### IQ4. "What's schema drift, and how do you detect it before it breaks downstream?"

*What a good answer covers:*
- Schema drift = upstream changes the shape of data: adds a column, removes one, renames one, changes a type
- Symptoms vary: from loud (pipeline crashes on a missing column) to silent (new column is ignored downstream, data quietly stops appearing in dashboards)
- Detection: pin an expected schema (column names + dtypes) and assert match at the bronze layer. Tools like Great Expectations, dbt source freshness, and Soda all support this declaratively.
- Mitigation strategy: contract testing with upstream — agree on a schema, alert when it changes, fail loudly rather than silently

*Likely follow-up:* "Upstream wants to add a column. How does your pipeline handle it gracefully?" (Answer: schema test should fail / warn; you update the contract and the bronze layer's expected schema; downstream layers stay untouched until you decide to use the new column.)

### IQ5. "Walk me through the Bronze / Silver / Gold layered architecture and what testing belongs at each layer."

*What a good answer covers:*
- **Bronze:** raw ingested data, schema preserved, minimal transformation. Tests: schema match, row count vs source, encoding, freshness.
- **Silver:** cleaned, deduped, type-cast, joined to reference data, business keys assigned. Tests: PK uniqueness, no NULLs in required columns, referential integrity, value ranges, no orphans.
- **Gold:** aggregated, business-ready, dashboard-shaped. Tests: reconciliation against silver totals, expected dimensions present, plausibility against historical baselines.
- The layered model means each test fails at the right altitude: a bronze schema bug doesn't cascade to gold reconciliation failures masking the root cause
- Avoid duplicating the same check across all three layers — pick the layer where it's the contract, not all of them

*Likely follow-up:* "Where would you put a check that 'every customer in orders also exists in customers'?" (Answer: silver — that's where business keys are conformed and FKs are guaranteed by contract. Earlier is too soon; later is too late.)

---

## If you have extra time this week (stretch)

- Read the first three chapters of *Designing Data-Intensive Applications* by Martin Kleppmann — the "data systems" mental model is foundational
- Try [DuckDB](https://duckdb.org/) for the first time — read a Parquet file, run SQL on it. You'll use it heavily in Week 10.
- Skim [the Airflow concepts page](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/index.html) — DAGs, tasks, scheduling. You'll meet it in Week 13.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — In ETL, transformation happens *before* loading into the warehouse (in a separate compute layer). In ELT, raw data is loaded first and transformation runs *inside* the warehouse, usually as SQL.
- **Q1.2** — (1) Cloud warehouses made storage and compute cheap and elastic, so storing raw data became economical. (2) The rise of dbt made SQL-based transformations versioned, testable, and team-friendly.
- **Q1.3** — SQL. dbt is a SQL-first transformation tool with templating (Jinja) and testing built around it.
- **Q1.4** — Strictly, hybrid — there's a small T before the L. In casual conversation, most people would still call this "ELT" because the *bulk* of transformation logic is in the warehouse, not in the cleanup step.

### Day 2 answers

- **Q2.1** — A pipeline is idempotent if running it twice produces the same output as running it once. Example of non-idempotent: `INSERT INTO daily_summary VALUES (...)` — every rerun adds duplicate rows. Make it idempotent with MERGE / UPSERT keyed on a deterministic primary key, or by writing to a date-partitioned location and overwriting the partition.
- **Q2.2** — The event is dropped (or routed to a side channel for late-data handling). Watermarks make a deliberate trade-off: you accept some data loss in exchange for being able to "close the books" on a time period.
- **Q2.3** — Event date = when the event happened. Ingestion date = when the pipeline saw it. Event date is more correct for analytics (revenue on the day the order was placed, not the day we ingested it). But ingestion date is easier for operations (each daily partition contains exactly what arrived that day, regardless of late events). Many pipelines partition by ingestion date and keep event date as a column.
- **Q2.4** — Duplicates. At-least-once means some events will be delivered more than once. Without idempotent processing or explicit deduplication downstream, you'll have duplicate rows.

### Day 3 answers

- **Q3.1** — Schema drift in the source, or a non-idempotent rerun. Both are quiet, frequent, and visible only if you have explicit tests.
- **Q3.2** — Hard failures alert you immediately. Silent corruption produces wrong results that pass tests, update dashboards, and inform decisions — by the time you notice, real damage is done.
- **Q3.3** — Many valid answers. Examples: not-null, uniqueness, value-in-set, value-in-range, dtype, regex match, distribution stability, distinct-count threshold.
- **Q3.4** — (a) The column is genuinely all zeros in the data. (b) The column is all NULL — pandas' `sum` returns 0 over NULL-only Series (in fact, `sum()` of an empty Series is also 0). They're indistinguishable from `.sum()` alone — you need `.isna().sum()` or `len(df)` to tell them apart.

### Day 4 answers

- **Q4.1** — Silver, because that's where business keys are conformed and foreign keys are part of the layer's contract. Bronze is too early — raw data may legitimately have orphans. Gold is too late — by then orphans have already been aggregated into wrong totals.
- **Q4.2** — Gold. The check requires comparing a metric to its historical pattern, which only makes sense once data is aggregated to a business-meaningful grain.
- **Q4.3** — Pro: defense in depth — if the Silver check is wrong, Gold catches it. Con: 3× the CI cost for the same logical assertion, and a test failure at Gold doesn't tell you which layer is at fault. Usually: pick the layer where it's the contract, not all of them.
- **Q4.4** — The Bronze schema test (`assert df.dtypes["customer_id"] == "Int64"`). The other tests would still pass; floats compare and sum just fine. Schema drift is exactly the kind of thing the Bronze layer is responsible for catching.

### End-of-week answers

**A1.** ETL transforms data before loading into the warehouse; ELT loads raw data first and transforms inside the warehouse using SQL.

**A2.** Cloud warehouses made compute + storage cheap and elastic, so the cost of storing raw data and re-transforming on demand became negligible. Combined with the rise of dbt, ELT became operationally easier than ETL.

**A3.** A pipeline is idempotent if running it N times produces the same result as running it once. Non-idempotent example: `INSERT INTO target VALUES (...)`. Make it idempotent: `MERGE INTO target USING source ON target.pk = source.pk WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT ...`.

**A4.** A watermark is the threshold past which late-arriving data is rejected (or sidelined). The trade-off: lower watermark = faster results but more dropped data; higher watermark = more correct results but higher latency and harder to "close" a time window.

**A5.** Many valid: type drift that happens to coerce cleanly, encoding errors that don't crash, time zone mishandling, NULL propagation through aggregations zeroing out metrics, partial joins that drop rows silently, duplicate loads when downstream queries average, late-arriving data shifting historical metrics.

**A6.** Event date = when the event happened (correct for analytics). Ingestion date = when the pipeline saw it (easier for operations). For analytics, partition by event date — but expect to handle restating historical partitions when late data arrives.

**A7.** Silver layer. That's where business keys are conformed and foreign-key relationships are part of the contract. Earlier (Bronze) is too raw; later (Gold) is too aggregated to localize the failure.

**A8.** A range check verifies a single column against fixed bounds. A reconciliation test independently computes the same metric two ways and asserts they match — catching silent corruption that range checks miss because both numbers are individually plausible. Use reconciliation when a metric matters enough that a wrong-but-plausible value would cause real harm.

**A9.** (1) Schema drift in the source. (2) An upstream non-idempotent rerun. (3) A change in source data that shifted a column's distribution past a previously-loose test threshold (sometimes from infrastructure changes — new region, new tenant — sometimes from real business change).

**A10.** Push back. *"Be specific to the columns and joins in this pipeline. Drop generic items."* Generic risk lists are a sign the AI didn't actually engage with the code. You want the answer to feel hand-crafted to your schema, not boilerplate.

---

*Done with Week 3? You should be able to look at any pipeline (yours or someone else's) and articulate which layer each test belongs at, why idempotency matters, and which failure modes are most likely. If yes — onward to Week 4 (Data Quality Concepts), where we'll formalize this with the six dimensions of data quality. If not — focus on the day that felt weakest, especially Day 2 (idempotency) and Day 4 (layered testing), because the rest of the plan compounds on these.*
