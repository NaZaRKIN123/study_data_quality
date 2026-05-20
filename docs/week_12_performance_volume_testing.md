# Week 12 — Performance & Volume Testing | Training Materials

> **Companion to:** Week 12 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Shift the question from "is the data correct?" to "is the pipeline fast enough?" By Friday you'll know how to profile Python, read SQL query plans, benchmark code with pytest-benchmark, and design tests that catch performance regressions before they hit production. The honest take: most performance problems in data pipelines come from a small number of patterns — full-table scans, accidental Python loops over big DataFrames, missing aggregation pushdown. Spotting them is more valuable than memorizing optimization tricks.

---

## How to use this file

- This week is more measurement-heavy than coding-heavy — the skill is reading numbers, not writing more code
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday's AI workflow is genuinely useful in real work — pasting a slow query + plan to an AI is a great first move
- Answers to all self-checks are at the bottom

---

## One-time setup (~5 minutes)

```bash
source .venv/bin/activate
pip install pytest-benchmark line_profiler memory_profiler psutil
```

Sanity check:
```bash
python -c "import line_profiler, memory_profiler, psutil; print('ok')"
pytest --version
```

You should see `pytest 8.x` or higher. `pytest-benchmark` 5.2+ is the current line.

---

## Day 1 (Mon) — Performance Fundamentals & Profiling

### Theory

A performance test asserts that something completes within an expected resource budget — time, memory, CPU, network. For data pipelines, the budgets you actually care about:

- **Wall-clock time** — does the daily ETL finish in its window?
- **Peak memory** — does the job fit in the available RAM (laptop or container)?
- **Throughput** — rows processed per second; bytes read per second from storage
- **P95 / P99 latency** — for interactive queries, the slowest 1–5% of responses

Performance work follows a strict order: **measure → identify the bottleneck → fix → measure again**. Skipping the first measurement is the biggest mistake. "I think the join is slow" is a guess; `EXPLAIN ANALYZE` is data.

### The two profilers you actually need

**`cProfile`** (stdlib) — function-level profiler, low overhead, great for "which function ate 80% of the time?"

```python
import cProfile
import pstats

def slow_aggregation(df):
    result = {}
    for _, row in df.iterrows():           # <-- the disaster
        country = row["country"]
        result[country] = result.get(country, 0) + row["total"]
    return result


# Profile it
cProfile.run("slow_aggregation(df)", "profile.out")
pstats.Stats("profile.out").sort_stats("cumulative").print_stats(15)
```

The output sorts functions by cumulative time. Top of the list = your bottleneck.

**`line_profiler`** — line-by-line within a single function. Higher overhead, but pinpoints the slow line.

```python
# install: pip install line_profiler
# Decorate the function you want to profile with @profile (no import needed — kernprof injects it)

@profile   # noqa
def transform(df):
    df["price_squared"] = df["price"] ** 2          # 5%
    df = df[df["price"] > 0]                         # 8%
    df = df.groupby("category").agg({"price": "mean"})  # 87% — there's the bottleneck
    return df


# Run with: kernprof -lv your_script.py
```

Then read the per-line numbers. If 87% of time is on the `groupby`, that's where to focus — not the `**2` operation, however suspicious it looks.

### Memory profiling

`memory_profiler` shows memory use line-by-line:

```python
# pip install memory_profiler
# Decorate with @profile, run with: python -m memory_profiler your_script.py
```

For peak-memory tracking in tests, `psutil` is enough:

```python
import psutil
import os


def peak_memory_mb():
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def test_load_orders_uses_under_500_mb():
    before = peak_memory_mb()
    df = load_orders()    # the function under test
    used = peak_memory_mb() - before
    assert used < 500, f"load_orders used {used:.0f} MB (budget 500 MB)"
```

### The performance triangle

You can almost always trade off between three things:

```
   Speed
    /\
   /  \
  /    \
 /      \
/________\
Memory   Cost
```

Faster code often uses more memory (precompute + cache). Lower memory often costs latency (process in chunks). Cheaper queries often pay in either time or memory. Pick two; the third gives.

### Common Python data-engineering performance bugs

1. **`df.iterrows()`** — Python-level loop over rows. ~1000× slower than vectorized operations on the same data.
2. **`df.apply(func)`** with a Python function — also row-by-row. Sometimes fine for small DataFrames; usually bad for big ones.
3. **String operations in loops** — `result = result + row["x"]` allocates a new string every iteration. Use a list and `"".join()`.
4. **Re-reading the same file inside a loop** — opening, parsing, closing, repeat. Open once, parse once, reuse.
5. **Accidental quadratic algorithms** — nested `for` loops over a DataFrame; `if x in big_list` inside a loop (use a set).
6. **Using pandas where DuckDB or numpy is faster** — pandas excels at small-to-medium ad-hoc work. For aggregations on >1M rows, DuckDB or polars is often 10–100× faster.
7. **Loading the whole DataFrame into memory when streaming would work** — `pd.read_csv(..., chunksize=100_000)` returns an iterator instead of a single DataFrame.

### Gotchas

1. **First-run vs warm-run.** Code runs slower on first invocation (compilation, cache misses). Benchmark with multiple iterations and discard or carefully analyze the first.
2. **Profiler overhead distorts the result.** `line_profiler` slows code 5–10×; `memory_profiler` even more. Compare *between* profiled runs, not profiled vs unprofiled.
3. **Wall time depends on the machine.** A test that asserts "<1 second" passes on your laptop, fails on a slow CI runner. Either set generous budgets or assert *relative* performance ("v2 is at least 2× faster than v1").
4. **System noise.** Background tasks (Spotlight on macOS, Windows Update, antivirus) skew measurements. Run benchmarks multiple times; trust the median.
5. **"Slow" is relative.** A 3-second query that runs once a day is fine. A 300ms query hit 1000× per second is a problem. Rate matters as much as duration.

### Exercises

Create `perf/` directory in your project.

1. Write a deliberately slow function `slow_aggregate(df)` using `df.iterrows()` for grouping. Then write a fast version `fast_aggregate(df)` using `df.groupby(...).agg(...)`. Profile both with `cProfile`. Confirm the `iterrows` version dominates the slow function's time.
2. **Line-level profiling:** take the Week 4 `validate_orders` function. Decorate with `@profile`, run with `kernprof -lv`. Identify the slowest line. Is it where you'd expect?
3. **Memory test:** write a function `load_in_chunks(path, chunksize)` using `pd.read_csv(..., chunksize=...)`. Compare peak memory between `chunksize=None` (load all) and `chunksize=10_000` on a 100 MB CSV. The chunked version should use ~10× less peak memory.
4. **Anti-pattern hunt:** review your Week 2–4 code. Find at least one place where you used `iterrows`, `apply`, or string concatenation in a loop. Replace with vectorized code. Time the difference.
5. **Stretch:** install `py-spy` (`pip install py-spy`) and run `py-spy top -- python your_script.py` — a sampling profiler that doesn't require code modification. It's the standard tool for profiling production processes.

### External practice

- [Python's cProfile docs](https://docs.python.org/3/library/profile.html) — stdlib reference
- [line_profiler GitHub](https://github.com/pyutils/line_profiler) — README has good examples
- [py-spy](https://github.com/benfred/py-spy) — sampling profiler; works on running processes
- [Brendan Gregg — Systems Performance (free chapters online)](https://www.brendangregg.com/systems-performance-2nd-edition-book.html) — the canonical reference, dense but worth it

### Self-check (Day 1)

> Q1.1 — A function takes 10 seconds. Where do you start the optimization process — by guessing, or by measuring? With which tool?
> Q1.2 — Why is `df.iterrows()` slow even though it looks like a normal Python loop?
> Q1.3 — Your benchmark runs in 200ms locally and 800ms in CI. What's the most likely cause, and how do you write a robust assertion?
> Q1.4 — `line_profiler` slows your code 5×. Should you mistrust the relative ordering of slow lines? Why or why not?

---

## Day 2 (Tue) — SQL Query Plans

### Theory

For database-bound work, the bottleneck is almost never Python — it's how the database executes SQL. **`EXPLAIN`** shows you what the database *plans* to do; **`EXPLAIN ANALYZE`** runs the query and shows what it *actually* did with timing. These two commands are the most useful diagnostic tools in data engineering.

### Reading a query plan

Plans are tree-shaped, read bottom-up. Each node is an operation: scan, filter, join, sort, aggregate. Each node has a cost and (in `ANALYZE` form) a real measured time.

Example in DuckDB:

```sql
-- The query
EXPLAIN ANALYZE
SELECT c.country, sum(o.total_amount) AS revenue
FROM 'orders.parquet' o
JOIN 'customers.parquet' c ON o.customer_id = c.customer_id
WHERE c.country IN ('US', 'PL', 'UK')
GROUP BY c.country;
```

The output (abbreviated):
```
┌─────────────────────────────┐
│           ORDER_BY          │  total: 0.001s
└─────────────────────────────┘
┌─────────────────────────────┐
│      HASH_GROUP_BY          │  total: 0.045s, rows: 3
│      country, sum(total)    │
└─────────────────────────────┘
┌─────────────────────────────┐
│          HASH_JOIN          │  total: 0.182s, rows: 487,231
│      o.customer_id =        │
│      c.customer_id          │
└──────────┬─────────┬────────┘
           │         │
┌──────────┴─┐  ┌────┴──────────┐
│ PARQUET    │  │ PARQUET       │
│   SCAN     │  │   SCAN        │
│ orders     │  │ customers     │
│ rows: 1M   │  │ filter:       │
│            │  │ country IN    │
│ total:     │  │   ('US','PL', │
│ 0.350s     │  │   'UK')       │
│            │  │ rows: 12,840  │
│            │  │ total: 0.045s │
└────────────┘  └───────────────┘
```

What this tells you:
- The orders scan reads 1M rows (no filter pushdown) — 350ms
- The customers scan filters down to 12,840 rows — 45ms (filter pushed into the scan, good)
- The join is 182ms — the dominant cost
- The aggregate is 45ms
- Total ≈ 600ms

If the query is slow, you now know *why*. Possible improvements: pre-filter orders by date if applicable, partition by country, ensure customers is the build side of the hash join (smaller table).

### The four common bottleneck patterns

**1. Full table scan when a filter could prune**

```sql
-- Slow: scans all 1B rows even though you only need recent ones
SELECT count(*) FROM events WHERE created_at > '2026-05-01';

-- Plan symptom: SEQ_SCAN with no filter pushdown indicator
```

Fix: ensure the table is partitioned/clustered on the filter column, or that the file format supports min/max pruning (Parquet does).

**2. Wrong join order**

```sql
-- Bad: join two huge tables first, then filter
SELECT a.x, b.y
FROM big_table a JOIN huge_table b ON a.k = b.k
WHERE a.region = 'EU';

-- Better: filter first
SELECT a.x, b.y
FROM (SELECT * FROM big_table WHERE region = 'EU') a
JOIN huge_table b ON a.k = b.k;
```

Modern query planners often fix this automatically. But for cross-engine queries, complex CTEs, or when you spot a problem — manual hints help.

**3. Missing aggregation pushdown**

```sql
-- If the data layer (Parquet, columnar warehouse) supports pre-aggregated stats,
-- COUNT(*) and SUM should be answered from metadata, not by reading data.
-- A plan that shows "SCAN, then AGGREGATE" on a 100GB table for COUNT(*)
-- is a missed opportunity.
```

**4. Cardinality estimate wildly wrong**

The planner estimated 1000 rows; the operation actually returned 1,000,000. Plans optimized for tiny intermediate results blow up. In `EXPLAIN ANALYZE`, look for `estimated_rows` vs `actual_rows`:

```
HASH_JOIN
estimated_rows: 1000     <-- planner thought tiny
actual_rows: 487,231     <-- reality much bigger
```

When estimates are off by >10×, the plan was wrong. Update statistics (`ANALYZE` or equivalent), or rewrite the query to give the planner better hints.

### EXPLAIN syntax across engines

The keyword is universal; details vary:

| Engine | Plan only | With actual timing |
|---|---|---|
| DuckDB | `EXPLAIN ...` | `EXPLAIN ANALYZE ...` |
| Postgres | `EXPLAIN ...` | `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) ...` |
| Snowflake | `EXPLAIN USING TEXT ...` | (Use Query Profile UI for actual; no native `ANALYZE`) |
| BigQuery | "Execution details" tab in console | "Execution details" tab |
| Spark | `df.explain()` or `df.explain("formatted")` | Spark UI's "SQL/DataFrame" tab |

**For testing**, parse `EXPLAIN` output and assert structural properties — "does the plan include a SEQ_SCAN over `huge_table`?" — without relying on absolute time.

### A test that catches plan regressions

```python
import duckdb
import pytest
import re


@pytest.fixture
def con():
    c = duckdb.connect()
    yield c
    c.close()


def test_query_pushes_down_country_filter(con):
    """If the country filter doesn't push down, the scan reads way too much."""
    plan = con.sql("""
        EXPLAIN
        SELECT count(*) FROM 'customers.parquet' WHERE country = 'US'
    """).fetchall()
    plan_text = "\n".join(row[1] for row in plan)

    # The plan should mention a filter at the scan level, not after
    assert "Filters: country" in plan_text, f"Filter didn't push down. Plan:\n{plan_text}"


def test_query_does_not_have_cartesian_product(con):
    plan = con.sql("""
        EXPLAIN
        SELECT * FROM 'orders.parquet' o
        JOIN 'customers.parquet' c ON o.customer_id = c.customer_id
    """).fetchall()
    plan_text = "\n".join(row[1] for row in plan)

    assert "CROSS_PRODUCT" not in plan_text and "NESTED_LOOP_JOIN" not in plan_text, \
        f"Found a cross product or nested-loop join — likely a missing JOIN condition. Plan:\n{plan_text}"
```

These tests don't measure time. They assert that the *plan itself* has good properties. Robust against machine noise; catches the kind of regressions that matter.

### Gotchas

1. **`EXPLAIN` plans are estimates, not guarantees.** The planner may pick differently in production based on table statistics, available memory, etc.
2. **Plan-format changes between versions.** A regex that matches "HASH_JOIN" today may break when DuckDB renames it. Update your tests when the engine updates.
3. **Caching distorts ANALYZE.** Run a query twice — second time is much faster (data in OS file cache). For repeatable timing, drop caches between runs (`sync; echo 3 > /proc/sys/vm/drop_caches` on Linux) or expect first-run vs warm-run differences.
4. **`EXPLAIN ANALYZE` actually runs the query.** Don't `EXPLAIN ANALYZE` an `INSERT INTO production` statement. It will insert.
5. **The plan you get isn't the plan you'll get.** Identical query against identical data can produce different plans tomorrow if statistics change. Plan-stability tests are flakier than they look.

### Exercises

Use your e-commerce Parquet files from Week 10.

1. Run `EXPLAIN` on a simple `SELECT * FROM 'orders.parquet' WHERE total_amount > 100`. Read the plan top-to-bottom. Identify: scan source, filter location, projection.
2. Run `EXPLAIN ANALYZE` on the same query. Compare the plan to the un-`ANALYZE`d version. What's the time of each node?
3. **Plan-shape test:** write a pytest that runs `EXPLAIN` on a query joining orders and customers, and asserts the plan contains `HASH_JOIN` (not `NESTED_LOOP_JOIN`).
4. **Filter pushdown test:** write a query with a filter on the partition column. Verify the plan shows the filter being applied at scan time (Parquet partition pruning).
5. **Cardinality reality check:** for one of your queries, compare `estimated_rows` to `actual_rows` in `EXPLAIN ANALYZE`. Are they close? If not by a factor of 10+, what does that suggest about your statistics?
6. **Stretch:** in Postgres or DuckDB, run the same query twice in a row. Time both. Ask why the second is faster.

### External practice

- [Use The Index, Luke](https://use-the-index-luke.com/) — free book on SQL performance; opinionated and clear
- [DuckDB EXPLAIN docs](https://duckdb.org/docs/guides/meta/explain.html)
- [Postgres EXPLAIN docs](https://www.postgresql.org/docs/current/sql-explain.html) — the canonical reference
- [Snowflake Query Profile UI](https://docs.snowflake.com/en/user-guide/ui-query-profile) — different style; visual

### Self-check (Day 2)

> Q2.1 — Difference between `EXPLAIN` and `EXPLAIN ANALYZE`?
> Q2.2 — A plan shows `estimated_rows: 100, actual_rows: 1,000,000`. What does this mean and what would you investigate?
> Q2.3 — Why is "the plan contains a HASH_JOIN" a more robust test than "the query runs in <500ms"?
> Q2.4 — A query is fast on the first run, slower on the second, fast on the third. What's likely happening?

---

## Day 3 (Wed) — `pytest-benchmark`

### Theory

`pytest-benchmark` is a pytest plugin that measures function-call timing with statistical rigor. It runs your function many times, discards outliers, reports min/max/mean/median/IQR/standard-deviation, and can fail tests that exceed a threshold or regress against a saved baseline.

### The minimal test

```python
def add(a, b):
    return a + b


def test_addition_speed(benchmark):
    result = benchmark(add, 1, 2)
    assert result == 3
```

Run: `pytest tests/test_perf.py --benchmark-only`

Output:
```
------------------------------- benchmark: 1 tests -------------------------------
Name (time in ns)   Min    Max    Mean    StdDev    Median    IQR    Outliers   OPS    Rounds  Iterations
test_addition...    25.0   85.0   28.4    4.2       27.0      2.0    132;28     35M    1500    400
----------------------------------------------------------------------------------
```

Notable columns:
- **Min** — fastest run (often the most reliable measure of the function's "real" cost)
- **Median** — typical runtime (more robust than mean against outliers)
- **IQR** — interquartile range; tight IQR = consistent timing
- **OPS** — operations per second (1 / mean)
- **Rounds × Iterations** — how many calls the plugin made (auto-calibrated to the chosen timer)

### Comparing two implementations

```python
import pandas as pd


def slow_aggregate(df):
    result = {}
    for _, row in df.iterrows():
        result[row["country"]] = result.get(row["country"], 0) + row["total"]
    return result


def fast_aggregate(df):
    return df.groupby("country")["total"].sum().to_dict()


@pytest.fixture
def df_1k():
    return pd.DataFrame({
        "country": ["US"] * 500 + ["PL"] * 500,
        "total":   [10.0] * 1000,
    })


def test_slow_aggregate(df_1k, benchmark):
    benchmark(slow_aggregate, df_1k)


def test_fast_aggregate(df_1k, benchmark):
    benchmark(fast_aggregate, df_1k)
```

Run with `pytest --benchmark-only --benchmark-group-by=name`. The output groups the two tests; you'll see something like fast is 100–1000× faster.

### Asserting performance budgets

You can fail a test if it's too slow:

```python
@pytest.mark.benchmark(min_time=0.001, max_time=0.1, min_rounds=10)
def test_aggregate_is_fast(df_1k, benchmark):
    benchmark(fast_aggregate, df_1k)
    # Will be auto-checked against min/max times
```

For more direct assertions, use `--benchmark-fail` flags:

```bash
# Fail if median is over 1ms
pytest --benchmark-only --benchmark-fail-if='median:1e-3'
```

### Comparing against a saved baseline

This is the killer feature for catching regressions:

```bash
# First run: save the baseline
pytest --benchmark-only --benchmark-save=baseline

# Make changes, run again, compare:
pytest --benchmark-only --benchmark-compare=baseline
```

The output highlights tests that got significantly slower vs the saved baseline. Critical for CI: gate merges on "no benchmark regressed by more than 10%."

### Setup that you don't want measured

By default, anything inside `benchmark(...)` is measured. To set up state once and only measure the function call:

```python
def test_fast_with_setup(benchmark):
    # Setup once
    df = pd.read_parquet("orders.parquet")    # not measured

    # Measured
    result = benchmark(fast_aggregate, df)

    # Assertions
    assert "US" in result
```

For more control (e.g., reset state before each round), use **pedantic mode**:

```python
def test_aggregate_pedantic(benchmark):
    benchmark.pedantic(
        fast_aggregate,
        args=(df,),
        rounds=20,
        iterations=5,
        warmup_rounds=2,
    )
```

### Statistical noise — what to trust

Benchmarks are noisy. A "1ms" function may sometimes take 0.8ms, sometimes 3ms — depends on what else the OS is doing. Robust practices:

1. **Look at the min, not the mean** when your goal is "the inherent speed of the code." Outliers are usually system noise, not function behavior.
2. **Look at the median** when comparing typical user experience.
3. **Look at the IQR** to gauge consistency. Tight IQR = stable; wide IQR = unreliable benchmark.
4. **Run benchmarks on a quiet machine** — close your browser, pause Spotify, suspend `cron`.
5. **Disable garbage collection** for very fast functions (microseconds): `@pytest.mark.benchmark(disable_gc=True)`.
6. **Don't trust differences smaller than ~10%** unless you've controlled the environment carefully.

### When `pytest-benchmark` doesn't fit

- **External services** — `pytest-benchmark` measures the function call. Network calls, DB queries, file I/O are dominated by external timing; the plugin still measures them, but the result reflects the external system, not your code.
- **Long-running operations** (>1 second per call) — the plugin auto-calibrates rounds; very slow functions get fewer rounds and noisier statistics. Sometimes a simple `time.perf_counter()` wrapper is more honest.
- **Multi-process / async** — measuring `await some_func()` works, but the result is dominated by I/O, not Python execution.

### Gotchas

1. **`benchmark()` returns the result of the call** — but only from the first round. Don't rely on it for assertions about per-round behavior.
2. **`pytest-benchmark` interacts oddly with `pytest-xdist`** (parallel test execution). Benchmarks running in parallel compete for CPU and timing becomes unreliable. Run benchmarks separately: `pytest -m benchmark` (after marking them).
3. **Saved baselines depend on hardware.** A baseline saved on your laptop is meaningless on CI. Save and compare on the same machine type.
4. **Default rounds may be too few for fast functions.** A function taking nanoseconds gets thousands of iterations; a function taking 100ms gets only a handful. For statistical confidence, use pedantic mode.
5. **Don't benchmark in CI on every PR.** Performance tests are slow and flaky. Run them on a schedule (nightly), or on a separate runner with controlled hardware.

### Exercises

Create `tests/test_perf.py`.

1. Write `test_fast_aggregate` and `test_slow_aggregate` from the example above. Run with `--benchmark-only`. Confirm fast is much faster (probably 100×+).
2. Run again with `--benchmark-group-by=group`. Add `@pytest.mark.benchmark(group="aggregate")` to both tests. Confirm they appear together.
3. **Save and compare:** run `pytest --benchmark-only --benchmark-save=v1`. Make a small "improvement" to one function (or a regression). Run again with `--benchmark-compare=v1`. Read the comparison output.
4. **Parametrize over data sizes:** write a single test that benchmarks `fast_aggregate` across `n=100`, `1_000`, `10_000`, `100_000`. Run and observe how time scales — is it roughly linear, sublinear, or worse?
5. **Performance budget:** add `--benchmark-fail-if='median:5e-3'` (fail if median > 5ms). Deliberately slow down `fast_aggregate` by adding a `time.sleep(0.01)`. Confirm the test fails.
6. **Stretch:** add benchmarks to your CI workflow from Week 7, but on a separate job that runs only on a schedule (not every PR). Save baselines as workflow artifacts; compare against the previous successful main build.

### External practice

- [pytest-benchmark docs](https://pytest-benchmark.readthedocs.io/) — current
- [Anthony Sottile — pytest-benchmark walkthrough](https://www.youtube.com/results?search_query=pytest+benchmark+anthony+sottile) — concise video intro
- [hyperfine](https://github.com/sharkdp/hyperfine) — alternative tool for benchmarking *commands* (not just functions); great for end-to-end timing

### Self-check (Day 3)

> Q3.1 — Why is `min` often more meaningful than `mean` in benchmark output?
> Q3.2 — Difference between `benchmark(func, *args)` and `benchmark.pedantic(func, args=..., rounds=..., iterations=...)`?
> Q3.3 — A baseline saved on your laptop is compared against a CI run and the CI is "30% slower." Is this a regression?
> Q3.4 — Why shouldn't you run benchmarks in parallel via `pytest-xdist`?

---

## Day 4 (Thu) — Volume Testing

### Theory

A "volume test" answers: does this code still work — and still meet performance budgets — when the input is 10× or 100× larger than typical? Failures at scale fall into a few categories:

1. **Time complexity that wasn't apparent at small scale** — a function is fine on 1k rows, terrible on 10M because it's secretly O(N²)
2. **Memory pressure** — fits in RAM at 1M rows; OOMs at 100M
3. **Buffer / batch size assumptions** — pipelines that work with 1k events/min break at 100k events/min
4. **External service rate limits** — APIs that worked in dev hit throttling in production
5. **Cardinality blowups** — `GROUP BY` over a column that has 10 unique values in dev and 10 million in prod

The goal of volume testing is *not* to test in production; it's to discover scale-related failures *before* production.

### Generating volume

You met Faker in Week 8. For volume testing you generate millions of rows. Memory matters.

**Naive approach** (works up to a few million rows, then OOMs):

```python
from faker import Faker
fake = Faker()
Faker.seed(42)

rows = [
    {"customer_id": i, "email": fake.email(), "country": fake.country_code()}
    for i in range(10_000_000)   # 10M rows
]
df = pd.DataFrame(rows)
```

**Better — vectorized generation with numpy** (scales to 100M+):

```python
import numpy as np
import pandas as pd

n = 10_000_000
rng = np.random.default_rng(42)

# Generate columns directly with numpy
df = pd.DataFrame({
    "customer_id": np.arange(1, n + 1),
    "country":     rng.choice(["US", "PL", "UK", "DE", "FR"], size=n),
    "total":       rng.uniform(10, 1000, size=n).round(2),
    "status":      rng.choice(["pending", "completed", "cancelled"], size=n, p=[0.05, 0.93, 0.02]),
})
```

Faker is great for *realism* (plausible names, emails, addresses); numpy is great for *volume* (billions of rows of synthetic categorical/numeric data). Mix them: small Faker pool, then sample with replacement via numpy:

```python
fake = Faker()
Faker.seed(42)

# Generate 10k unique emails once
email_pool = [fake.email() for _ in range(10_000)]

# Sample 10M rows from the pool
df["email"] = rng.choice(email_pool, size=n)
```

10× faster than calling `fake.email()` 10M times, and the data is still realistic.

### Streaming generation for tests that must not load everything

When even 10M rows don't fit in memory, write directly to disk in chunks:

```python
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def generate_orders_to_parquet(path, n=100_000_000, chunk_size=1_000_000, seed=42):
    rng = np.random.default_rng(seed)

    writer = None
    try:
        for chunk_start in range(0, n, chunk_size):
            this_chunk = min(chunk_size, n - chunk_start)
            tbl = pa.table({
                "order_id":   pa.array(np.arange(chunk_start + 1, chunk_start + this_chunk + 1)),
                "customer_id": pa.array(rng.integers(1, 1_000_000, size=this_chunk)),
                "total":      pa.array(rng.uniform(10, 1000, size=this_chunk).round(2)),
            })
            if writer is None:
                writer = pq.ParquetWriter(path, tbl.schema)
            writer.write_table(tbl)
    finally:
        if writer:
            writer.close()
```

100M rows of Parquet, written to disk, never more than 1M in memory at any point.

### Volume tests — what to assert

```python
import pytest
import time
import psutil
import os


@pytest.fixture(scope="session")
def big_orders_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "orders_10m.parquet"
    generate_orders_to_parquet(str(path), n=10_000_000)
    return str(path)


def test_aggregate_scales_to_10m(big_orders_path, con):
    """The aggregation should complete in reasonable time and not OOM."""
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1e6

    start = time.perf_counter()
    result = con.sql(f"""
        SELECT count(*), sum(total) FROM '{big_orders_path}'
    """).fetchone()
    elapsed = time.perf_counter() - start

    mem_used = process.memory_info().rss / 1e6 - mem_before

    assert result[0] == 10_000_000
    assert elapsed < 5.0,    f"Aggregate took {elapsed:.2f}s (budget 5s)"
    assert mem_used < 500,   f"Aggregate used {mem_used:.0f} MB (budget 500 MB)"


def test_aggregate_does_not_load_full_dataset(big_orders_path, con):
    """Specifically: peak memory shouldn't approach the dataset's on-disk size."""
    file_size_mb = os.path.getsize(big_orders_path) / 1e6

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1e6

    con.sql(f"SELECT count(*) FROM '{big_orders_path}'").fetchone()

    mem_used = process.memory_info().rss / 1e6 - mem_before

    # Reading 100MB of Parquet to count rows shouldn't blow up memory
    assert mem_used < file_size_mb * 0.5, \
        f"Used {mem_used:.0f}MB to count rows in {file_size_mb:.0f}MB file"
```

### Where volume tests live

Not on every PR. Volume tests are slow (minutes), expensive (compute), and flaky (timing-sensitive). The pattern that works:

1. **Unit tests** on every PR — small data, fast, deterministic
2. **Volume tests on a schedule** — nightly or weekly; full data; alert on regressions
3. **Volume tests on demand** — manual trigger before a major release or after a perf-related change

In your Week 7 GitHub Actions, this looks like:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'     # 2 AM UTC nightly
  workflow_dispatch:        # manual trigger

jobs:
  volume-tests:
    runs-on: ubuntu-latest-large    # bigger runner with more RAM
    steps:
      - uses: actions/checkout@v5
      - run: pytest -m volume --tb=short
```

Mark slow tests:
```python
@pytest.mark.volume
def test_aggregate_at_100m_rows():
    ...
```

Then exclude them from regular runs: `pytest -m "not volume"` is your default.

### What "volume" reveals that small data hides

Hidden quadratic algorithms. A function with `df.merge(other_df, on="x")` looks innocent. At 1k rows it's fast; at 10M rows, if `other_df` is also 10M and the merge produces an explosive cross-product, you're looking at minutes or OOM.

Cardinality assumptions. Test data with 5 unique countries; production with 200 countries. A `GROUP BY country` partition strategy that worked for 5 may produce 200 small files in production — not wrong, but slow.

Skew. Test data is uniform; production data has 80% of rows belonging to one customer. A naive partitioning strategy creates one giant partition and many tiny ones.

Exhaustion of unique-value pools. `Faker.unique.email()` exhausts after ~10k calls; a test that generates 100k records hits an error that small tests never see.

### Gotchas

1. **Generation can dominate test time.** If generating 10M rows takes 30 seconds and the actual operation takes 2 seconds, you're testing your data generator more than your code. Pre-generate once (`session` scope) and reuse.
2. **`psutil` memory measurement is OS-RSS, not Python heap.** It includes shared libraries, file caches, etc. Differences are more reliable than absolutes.
3. **Garbage collection lurks.** A test that "uses 500 MB" may use 200 MB peak with 300 MB hanging around uncollected. Run `gc.collect()` between measurements for cleaner numbers.
4. **Fixed seeds matter even more at scale.** With 10M random rows, even small distribution differences produce large absolute differences. Pin every random source.
5. **Volume tests fail differently.** A unit test failing usually means a bug; a volume test failing might mean the runner is overloaded. Be patient with one-off failures; alert on patterns.

### Exercises

1. Write `generate_orders_to_parquet(path, n)` from the streaming example. Use it to create a 1M-row Parquet file, then a 10M-row file. Compare file sizes and generation times.
2. **Time-and-memory test:** write a test that asserts your `validate_orders` pipeline (Week 4) runs in <10 seconds and uses <300MB on a 10M-row input. Run it. Tune budgets if needed; *don't* set them so loosely they catch nothing.
3. **Find a hidden quadratic:** in your code, find a place where you do `df.merge(other_df, on="x")` or similar. Test it at 10k, 100k, 1M rows. Plot or print the times. Is it linear or worse?
4. **Cardinality test:** generate orders where `customer_id` has 5 unique values (small test scenario) vs 1M unique values (production scenario). Run your aggregation; compare timing. Anything surprising?
5. **Skew exercise:** generate 1M orders where 90% have `customer_id=1` (heavy skew). Run a `GROUP BY customer_id` aggregation. Is it slower than uniform distribution? Why might that be?
6. **Stretch:** mark your volume tests with `@pytest.mark.volume` and configure CI to skip them on PRs but run them nightly via `cron` (Week 7 patterns).

### External practice

- [Pandas — Scaling to large datasets](https://pandas.pydata.org/docs/user_guide/scale.html) — official guidance on chunking
- [Apache Arrow — Performance](https://arrow.apache.org/docs/python/parquet.html#performance) — internals that matter at scale
- [Aleksey Bilogur — Real-world data is messy](https://www.kaggle.com/learn) — data scaling in practice

### Self-check (Day 4)

> Q4.1 — Why generate 10M rows with numpy instead of Faker?
> Q4.2 — A function works on 1k rows in 10ms. At 1M rows it takes 60 seconds. Is this scaling correctly?
> Q4.3 — Why shouldn't volume tests run on every PR?
> Q4.4 — Your test data is uniformly distributed; production data is heavily skewed. What kind of bugs does this hide?

---

## Day 5 (Fri 🤖) — AI Workflow: Query Plan Analysis

### What you're learning today

Pasting a slow query and its `EXPLAIN ANALYZE` output to an AI is genuinely one of the highest-leverage moves you can make in real data engineering work. The AI is good at:

- Spotting common antipatterns (no filter pushdown, full scan, bad join order)
- Suggesting query rewrites or index/partitioning changes
- Translating obtuse error messages into actionable advice

It's bad at:

- Reasoning about *your specific data distribution* (it can't see your statistics)
- Engine-specific optimizations beyond the most common
- Anything that requires running the query to verify

So: AI proposes; you validate. Standard pattern by now.

### Setup

Reuse the `anthropic` setup from Weeks 8–11.

### Exercise 1 — Plan analysis

Take a real (or contrived) slow query against your e-commerce Parquet files. Run `EXPLAIN ANALYZE` and capture the output. Paste into Claude:

> *"Here is a DuckDB query and its EXPLAIN ANALYZE output. Identify the top bottleneck and propose a rewritten query or schema change to address it. Be specific about which node in the plan is the issue, and explain your reasoning.*
>
> *Query:*
> *```sql*
> *[paste query]*
> *```*
>
> *Plan:*
> *```*
> *[paste plan]*
> *```*
>
> *Don't propose changes the engine handles automatically. If you're unsure whether a rewrite would help, say so."*

The "if you're unsure, say so" instruction is critical. Without it, AI defaults to confident answers. With it, you'll get a more honest analysis (sometimes "this looks fine for the data size, no obvious win").

### Exercise 2 — Generate plan-stability tests

Take a query you care about and the plan you currently get. Ask Claude:

> *"This DuckDB query currently has the plan below. Generate a pytest test that asserts properties of the plan (not the timing) so I can catch regressions if a future query change or engine version produces a worse plan. Focus on:*
> *- Specific operators present (HASH_JOIN, PARQUET_SCAN with filters, etc.)*
> *- Specific operators absent (CROSS_PRODUCT, NESTED_LOOP_JOIN)*
> *- Filter pushdown markers*
>
> *Query:*
> *```sql*
> *[paste]*
> *```*
>
> *Plan:*
> *```*
> *[paste]*
> *```*
>
> *Use string-matching for plan node detection. Do NOT assert specific row counts or timings."*

You get a test scaffold. Verify that:
- The assertions actually fail when the query is broken (test the test)
- The string patterns match the current DuckDB version's output (run and check)
- Plan-shape changes between minor versions don't make the test brittle (consider what's stable)

### Exercise 3 — Performance triage

You have a function that's slow but you don't know why. Run `cProfile`, capture the top-15 output, paste:

> *"This is cProfile output for a function I'm trying to speed up. The top of the list is at the top. What functions deserve the most attention? Are there any obvious wins? Don't suggest profile-guided optimizations that require code I haven't shown.*
>
> *```*
> *[paste cProfile output]*
> *```*
>
> *Then suggest 3 specific things I could investigate, ranked by likelihood of impact."*

The AI is good at noticing patterns ("you spend 60% of time in `iterrows`") and bad at understanding the broader algorithm. Take the suggestions; verify each.

### Exercise 4 — Volume-test design

> *"I have a Python function that processes orders and currently has unit tests at 1000 rows. I want to design a volume test suite. Generate 5 specific volume tests with budgets and rationales:*
>
> *- 1 test that asserts time scales linearly between 10k and 1M rows*
> *- 1 test that asserts peak memory stays under a budget*
> *- 1 test that asserts cardinality scaling (5 vs 1M unique customer_ids)*
> *- 1 test that asserts skew handling (90% rows have one customer_id)*
> *- 1 test that asserts the function still works at 100M rows (correctness, not speed)*
>
> *Use pytest-benchmark or psutil where appropriate. Mark tests with @pytest.mark.volume so they're skippable.*
>
> *Function signature: process_orders(df: pd.DataFrame) -> pd.DataFrame*
>
> *Return only Python code. Include realistic budget values (educated guesses are fine; I'll tune)."*

### Update your `.cursorrules`

```
Performance / volume conventions:
- Always measure before optimizing. cProfile or line_profiler first; intuition second.
- Plan-shape tests > timing tests for catching SQL regressions.
- pytest-benchmark for function-level perf; pytest-bench saves baselines for regression detection.
- Mark volume tests with @pytest.mark.volume; default pytest run skips them.
- Volume tests run on a schedule, not every PR.
- Use numpy for high-volume synthetic data; Faker for realism, sampled into a small pool.
- Fixed seeds for all random sources. Pin everywhere: numpy, Faker, random.
- Memory measurements: psutil RSS for relative comparisons; trust differences, not absolutes.
- Performance budgets: assert relative ("v2 is 2× faster than v1") when possible; absolute values are machine-dependent.
- AI for plan analysis: paste plan + ask "what's the bottleneck"; never run AI suggestions without verifying.
```

### Quality bar — when is a generated perf test "good"?

- [ ] The test actually fails when the function is slow (you verified by deliberately breaking it)
- [ ] Budgets are tight enough to catch real regressions (>10% slower) but not so tight that random noise fails them
- [ ] No assertions on absolute time without acknowledging machine-dependence
- [ ] Volume tests are marked and skippable
- [ ] Generation logic uses fixed seeds
- [ ] Memory assertions distinguish OS-RSS from Python heap (or note the difference)

### Reflection (write 3–5 sentences in `notes.md`)

- Was the AI's plan-analysis advice actionable, or did it hand-wave?
- Did it reach for engine-specific optimizations or stay generic? Which was more useful?
- Comparing this Friday to Week 8 (synth data), 9 (schema inference), 10 (PySpark scaffolds), 11 (schema evolution): which AI workflow gave you the most leverage? Pattern-matching over time is a real skill.

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 13. 5–7 = re-review. <5 = redo exercises.

1. The first step of any performance optimization is what?
2. Why is `df.iterrows()` slow despite looking like a normal Python loop?
3. Difference between `EXPLAIN` and `EXPLAIN ANALYZE`?
4. A query plan shows `estimated_rows: 100, actual_rows: 1,000,000`. What does this hint at?
5. In `pytest-benchmark` output, why is `min` often more meaningful than `mean`?
6. Why do plan-shape tests beat timing tests for SQL regression detection?
7. When would you generate test data with numpy instead of Faker?
8. Why don't volume tests belong on every PR?
9. Two implementations are 30% different in a benchmark. Without controlled hardware, what's the smallest reliable difference?
10. After AI suggests a query rewrite for a slow plan, the first thing you do is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about performance and volume testing.

### IQ1. "How do you decide if a piece of data code is fast enough?"

*What a good answer covers:*
- **Define the budget first**: time, memory, throughput. Tie it to a business constraint ("daily ETL must finish in 4 hours") rather than an absolute number.
- **Measure with the right tool**: `cProfile` for function-level, `line_profiler` for hot lines, SQL `EXPLAIN ANALYZE` for queries, `psutil` for memory.
- **Compare against the budget**: pass / fail.
- **Watch for regressions**: track over time — a 5% degradation week-over-week eats budgets quietly.
- **Don't over-optimize**: code that's fast enough today doesn't need to be faster tomorrow.

*Likely follow-up:* "What's a reasonable budget for a daily ETL on 100GB of data?" (Answer: depends on the SLA, but rules of thumb: a single-machine job on 100GB Parquet should complete in 30–60 minutes if cleanly written. If you're at 4+ hours, something is wrong — likely a row-by-row Python loop or a missing aggregation pushdown.)

### IQ2. "Walk me through reading a SQL query plan."

*What a good answer covers:*
- Plans are tree-shaped, read bottom-up. Each node = an operation.
- For each node, look at: operation type (scan, filter, join, aggregate), estimated vs actual rows, time spent.
- **Watch for**: full table scans where filters could prune; NESTED_LOOP_JOIN on big tables (usually wrong); cardinality estimates off by 10× (statistics are stale or query confuses the planner); aggregations that aren't pushed to the storage layer.
- **EXPLAIN ANALYZE** runs the query — gives actual timings — but be careful in production (don't `EXPLAIN ANALYZE` an INSERT).
- The fix is usually: better filter placement, partition pruning, updating statistics, or rewriting the query to give the planner better hints.

*Likely follow-up:* "What's the difference between a HASH_JOIN and a NESTED_LOOP_JOIN, and when would you want each?" (Answer: hash join builds a hash table on one side, scans the other; O(N+M). Nested loop is O(N×M). Hash is the default and right for almost everything; nested loop only for very small inputs or non-equi joins.)

### IQ3. "How do you test the performance of a function?"

*What a good answer covers:*
- For function-level: `pytest-benchmark`. Measure min/median/IQR, not just mean.
- For comparison: save a baseline (`--benchmark-save`), compare future runs (`--benchmark-compare`).
- For thresholds: `--benchmark-fail-if='median:1e-3'` to fail tests that exceed a budget.
- For SQL: assert *plan shape*, not timing. "The plan must contain HASH_JOIN" is robust; "the query runs in <500ms" is flaky.
- For volume: separate test marker (`@pytest.mark.volume`); run on schedule, not on every PR.
- Pin random seeds. Disable garbage collection for very fast functions. Run on a quiet machine when possible.

*Likely follow-up:* "How do you handle benchmarks in CI where machine performance varies?" (Answer: assert relative performance — "v2 is at least 2× faster than v1" — instead of absolute. Or run benchmarks on dedicated hardware (self-hosted runner). Or compare against a baseline from the same branch on the same runner.)

### IQ4. "What's the difference between unit testing and volume testing?"

*What a good answer covers:*
- **Unit tests**: small data, fast (milliseconds), deterministic, runs on every PR. Goal: prove the function is *correct*.
- **Volume tests**: production-scale data, slow (minutes), more flaky, runs on a schedule. Goal: prove the function is *correct AND meets performance budgets at scale*.
- **What volume reveals that unit tests hide**: hidden quadratic algorithms, memory pressure, cardinality blowups, skew, batch-size assumptions, rate limits.
- **Where volume tests live**: separate marker (`@pytest.mark.volume`), separate workflow (nightly cron, beefier runner), separate alerting (regression noise vs catastrophe).
- **Together**: unit tests catch bugs fast; volume tests catch scale issues before production. Both are necessary.

*Likely follow-up:* "What's a real volume issue you've seen?" (If you can give a specific example, do. Otherwise: "I read about a team whose pipeline was fine on test data but OOM'd in prod because the production data had one customer with 10M orders, while test data was uniform — pretty common pattern.")

### IQ5. "How do you handle skew in a data pipeline?"

*What a good answer covers:*
- **Detect first**: profile the data — `count(*) GROUP BY skew_column` shows the distribution. A few keys with most rows = skew.
- **Common impact**: one partition or one task processes most of the work; total time is bottlenecked on the slowest task.
- **Strategies**: salt the skewed key (add a random suffix to spread to multiple partitions, then aggregate); split skewed keys from non-skewed (process big customers separately); use sorted/clustered storage so skewed keys aren't in the same partition; broadcast small tables to skip the join shuffle.
- **In testing**: explicitly generate skewed test data — don't let uniform synthetic data hide the problem.
- **In monitoring**: alert when partition sizes diverge by >10× from each other; that's the early warning of skew.

*Likely follow-up:* "Have you ever had to fix a skewed query?" (If yes, share the specifics. If no, describe how you would: profile to confirm, then pick the right mitigation based on the data and the engine.)

---

## If you have extra time this week (stretch)

- Try [Polars](https://pola.rs/) for performance comparisons — same task in pandas vs DuckDB vs Polars, on the same machine. The differences can be eye-opening.
- Read [Brendan Gregg — USE Method](https://www.brendangregg.com/usemethod.html) — Utilization, Saturation, Errors. A diagnostic framework that scales beyond data engineering.
- Set up [Grafana + Prometheus](https://prometheus.io/docs/visualization/grafana/) locally to graph performance metrics over time. Overkill for one project, foundational for production.
- Explore [DuckDB's `pragma` for performance tuning](https://duckdb.org/docs/configuration/pragmas) — memory limits, threads, temp directory. Useful for CI runners.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — By measuring. Use `cProfile` for function-level and `line_profiler` if you suspect a single function. Without measurement, you optimize the wrong thing.
- **Q1.2** — `iterrows` creates a Python tuple for each row, with a Python-level function call per iteration. The actual work is fast in C; the tuple creation and Python loop dominate. Vectorized operations (groupby, vector arithmetic) push the loop into C, eliminating the per-row overhead.
- **Q1.3** — CI runners share hardware and have less consistent timing. Either set generous budgets (`< 2s` instead of `< 200ms`), or assert *relative* performance (this version is at least 2× faster than baseline), or use a dedicated benchmark runner with consistent hardware.
- **Q1.4** — Mostly trust the relative ordering. The profiler distorts absolute times but applies similar overhead per call, so the ratio between fast and slow lines is approximately preserved. Don't trust absolute "this line takes Xms" — only "this line is 10× slower than that one."

### Day 2 answers

- **Q2.1** — `EXPLAIN` shows the query plan (the planner's strategy) without running the query. `EXPLAIN ANALYZE` runs the query and adds actual timings and row counts to the plan. ANALYZE is more useful but slower (and never use on INSERTs).
- **Q2.2** — The planner badly underestimated the result set. Possible causes: stale statistics; a complex predicate the planner can't accurately estimate; correlated columns the planner treats as independent. Investigate by running `ANALYZE table_name` (or equivalent) to refresh stats; consider whether the query can be rewritten to give the planner a clearer cardinality.
- **Q2.3** — Plan-shape assertions are robust against machine speed and noise; timing tests are flaky. The plan tells you *why* the query is slow; the timing only tells you *that* it is. Plan-shape is also stable across hardware — a plan generated on your laptop should match the one generated in CI (same engine version, same data).
- **Q2.4** — OS file caching. The first run hits cold disk; subsequent runs hit warm OS file cache (or DB buffer pool). The third run is fast for the same reason. To get repeatable timing, either drop caches between runs or accept first-run vs warm-run framing.

### Day 3 answers

- **Q3.1** — `min` is closer to the function's "inherent speed" because the slowest runs are usually system noise (GC, OS interrupt, page fault), not anything about the function. `mean` is dragged up by outliers; `min` reflects best-case execution.
- **Q3.2** — `benchmark(func, *args)` auto-calibrates rounds and iterations based on the timer resolution. `benchmark.pedantic` gives you explicit control: `rounds`, `iterations`, `warmup_rounds`. Use pedantic when you need consistency or when auto-calibration produces few rounds (e.g., for slow functions).
- **Q3.3** — Probably not — likely just hardware difference. Saved baselines are only meaningful on the same hardware as the comparison run. Either save baselines on the same machine type (CI runner saves baselines for CI), or use relative comparisons within a single run.
- **Q3.4** — Parallel tests compete for CPU and OS resources, making timing noisy and unreliable. Benchmarks need a quiet machine — at minimum, no competing test workloads. Run benchmarks separately from the main test suite (`pytest -m benchmark` after marking).

### Day 4 answers

- **Q4.1** — Faker is row-by-row Python; numpy is vectorized C. For 10M rows of synthetic data, Faker is 10–100× slower. For *realism* in a few hundred values, Faker wins; for *volume* of mostly-categorical or numeric data, numpy wins. Mix them: Faker pool of 10k realistic emails, then numpy `rng.choice(...)` to sample 10M rows from the pool.
- **Q4.2** — No. 1k → 1M is 1000× more data. Linear scaling means 10s. 60s = 6× slower than linear, suggesting superlinear complexity (likely O(N log N) for sort/groupby, possibly O(N²) for nested loops). Worth investigating.
- **Q4.3** — They're slow (minutes), expensive (compute, RAM), and flaky (timing-sensitive on shared CI runners). Running on every PR clogs CI and produces false-positive failures from noise. Run on schedule (nightly) or on demand; alert on persistent regressions.
- **Q4.4** — Skew: one or a few keys hold most of the rows. Uniform synthetic data hides single-partition bottlenecks, OOMs on the largest partition, retry storms in concurrent writers, and the "GROUP BY one_skewed_column produces 99% empty groups + 1 huge group" pattern. Generate skewed test data deliberately.

### End-of-week answers

**A1.** Measure. With `cProfile`, `line_profiler`, `EXPLAIN ANALYZE`, `psutil` — whatever fits the question. Optimization without measurement is gambling.

**A2.** It's a Python-level loop with per-row tuple construction; the actual work is fast in C, but the Python overhead dominates. Vectorized pandas operations push the loop into C, eliminating per-row overhead.

**A3.** `EXPLAIN` shows the planner's intended strategy; `EXPLAIN ANALYZE` runs the query and adds actual timing and row counts. ANALYZE is more useful for diagnosis but more expensive.

**A4.** Stale statistics or a complex predicate the planner can't estimate. Refresh statistics; consider rewriting the query to give clearer cardinality hints.

**A5.** `min` is closer to the function's intrinsic speed; outliers are usually system noise (GC, OS interrupts), not the function being slow.

**A6.** Plan-shape assertions are robust against hardware noise and engine-version timing changes. They identify *why* the query would be slow, not just *that* it is. Timing tests fail unpredictably; plan-shape tests fail meaningfully.

**A7.** When you need volume more than realism. numpy generates millions of rows of categorical/numeric data in seconds; Faker is 10–100× slower for the same. Mix them: Faker for a small pool of realistic values, numpy to sample at scale.

**A8.** They're slow, expensive, and flaky. Running them on every PR adds noise to the signal and slows engineers down. Run on a schedule or on demand; alert on persistent regressions.

**A9.** Roughly 10–15%. Smaller differences are usually system noise. To resolve smaller differences reliably, you need controlled hardware and many runs.

**A10.** Verify it. Run the rewrite, capture the new plan, compare. AI suggestions are starting points, not solutions. The actual fix sometimes works; sometimes the AI proposed a rewrite the planner already does internally; sometimes the suggested change makes things worse on your specific data distribution.

---

*Done with Week 12? You can profile Python, read SQL plans, write benchmarks that catch regressions, and design volume tests that find scale problems before production. Onward to Week 13 — Monitoring & Data Observability — where the question shifts from "is my code fast enough?" to "can I tell when something has gone wrong in production?"*
