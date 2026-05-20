# Week 10 — Big Data Specifics: PySpark, DuckDB, Parquet & Sampling | Training Materials

> **Companion to:** Week 10 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Test data that doesn't fit in memory. By Friday you'll know when to reach for PySpark vs DuckDB, how Parquet's columnar layout enables fast tests at scale, and how to sample intelligently when full-dataset testing is infeasible. The honest take: many "big data" workloads aren't actually big enough to need Spark, and you'll learn to spot the difference.
>
> **Version note (May 2026):** PySpark 4.1+ ships with `assertDataFrameEqual` and `assertSchemaEqual` built-in (since 3.5). DuckDB is at v1.3.x in the stable v1.x line. Both APIs are stable for the patterns we use this week.

---

## How to use this file

- This week is more conceptual than coding-heavy — the right tool choice matters more than syntax memorization
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday's AI workflow generates PySpark test scaffolds — useful when you inherit a codebase and need fast coverage
- Answers to all self-checks are at the bottom

---

## One-time setup (~15 minutes)

PySpark needs Java. The other tools don't.

```bash
# Verify Java (PySpark 4.x supports Java 17 and 21)
java -version
# If missing on macOS: brew install openjdk@21
# On Ubuntu: sudo apt install openjdk-21-jdk
# On Windows: install from adoptium.net

source .venv/bin/activate
pip install pyspark duckdb pyarrow
```

Sanity check:
```bash
python -c "import pyspark, duckdb, pyarrow; print('pyspark', pyspark.__version__, '| duckdb', duckdb.__version__, '| pyarrow', pyarrow.__version__)"
```

You should see `pyspark 4.x`, `duckdb 1.3+`, `pyarrow 17+` (or higher).

> **First Spark startup is slow** — 10–20 seconds while the JVM initializes. Subsequent calls within the same Python process are fast. If you see "WARNING: An illegal reflective access operation has occurred," that's Java warning Spark about internal API use — annoying but harmless.

---

## Day 1 (Mon) — When Big Data Is Actually Big (and When It Isn't)

### Theory

"Big data" is a loaded term. The literal threshold is "doesn't fit in memory on a single machine." On a modern laptop with 32 GB RAM, that's roughly **>20 GB of working data** after pandas overhead (which is ~5–10× the file size for CSV).

For testing purposes, three regimes:

| Regime | Data size | Tool | Test approach |
|---|---|---|---|
| **Small** | < 1 GB | pandas / SQLite | Test everything, every run |
| **Medium** | 1–500 GB | DuckDB / Polars | Test everything; queries are seconds, not minutes |
| **Large** | 500 GB – 100 TB | Spark / cloud warehouse | Sample for unit tests; full-data checks scheduled |
| **Huge** | > 100 TB | Distributed warehouse | Strict sampling + statistical assertions |

**Most "big data" jobs in real companies sit in the medium regime.** Sales data for a mid-sized retailer, event logs for a SaaS app, ML training data for a recommendation system — usually 10–500 GB. DuckDB handles these on a single machine in seconds. Spark's overhead becomes pure cost.

### When you actually need Spark

- You're processing > 1 TB and a single machine's I/O is the bottleneck
- You're running an existing Spark codebase (don't rewrite for sport)
- You're on Databricks or EMR where Spark *is* the runtime
- You need fault-tolerant distributed processing across many machines

### When DuckDB beats Spark

- Single machine, < 500 GB data
- Embedded analytics (no separate cluster to manage)
- SQL ergonomics matter more than language flexibility
- You want test feedback in seconds, not minutes
- You're paying per Spark cluster minute and don't have to be

### What changes for testing at scale

1. **You can't load the full dataset for every assertion.** A test that runs `df.collect()` on 100 GB will OOM the machine. Aggregate first, collect second.
2. **Lazy evaluation lies about runtime.** A pandas operation runs immediately; a Spark transformation builds a plan and runs when you call an action (`count`, `collect`, `write`). A test that "passes" because no error fired might just have built a plan that never executed.
3. **Statistical tests replace exact equality.** "Every row matches" becomes "1000 sampled rows match" plus "row count is correct" plus "aggregate sum is correct." Most production big-data tests are statistical, not exact.
4. **Partitions and files become testable units.** "Did today's partition land?" "Are all expected files present?" "Does the row count per partition look normal?" These are big-data-specific concerns that don't exist in single-table testing.
5. **Sampling has to be representative.** Random sampling is fine for size-checking; stratified sampling is needed when you care about a rare class (1% fraud detection, 0.01% errors).

### The "test all the data" antipattern

A team I won't name had a Spark test that scanned 4 TB of historical data on every PR — to assert that a regex was applied correctly. The test took 90 minutes per PR, cost real money in cluster time, and engineers learned to bypass CI rather than wait. Then it broke once and nobody fixed it because the cost was too high.

**The fix:** test the regex on a 1000-row sample per PR; run the full-data check nightly on a schedule. Same coverage, 0.001% the cost.

### Gotchas

1. **"Big data" is often a marketing term.** Audit your actual data size before reaching for Spark. If `du -sh data/` says 50 GB, you don't need a cluster.
2. **Pandas DataFrame inflates 5–10× from on-disk size.** A 5 GB CSV becomes 30+ GB pandas. Parquet is much closer to 1:1 in memory.
3. **A single Parquet file can be 100 GB** and DuckDB can still query it in seconds — column pruning and predicate pushdown skip what you don't need. The "fits in memory" rule applies to *what you load*, not what's on disk.
4. **Cluster overhead.** Spinning up a Spark session takes 10–30 seconds. For a 1-second pandas operation, you've added 30× overhead. Spark's overhead amortizes only at scale.
5. **Testing in production-scale data costs money.** $50 in compute for one CI run sounds cheap until 100 PRs/week × $50 = $260,000/year. Sampling matters not just for speed but for budget.

### Exercises (analysis day, no coding)

1. Run `du -sh` on every dataset you have access to. Categorize each as Small / Medium / Large / Huge. How many are actually large?
2. Pick a real PySpark or distributed-data tutorial online. Note how long the example takes to run. Translate the same task to DuckDB syntax. Time both. Spoiler: for most tutorials, DuckDB wins by an order of magnitude.
3. Read [Hannes Mühleisen's "Big Data is Dead"](https://motherduck.com/blog/big-data-is-dead/) (one of DuckDB's authors). Note the argument structure and decide which parts you agree with.
4. **Write a one-page decision tree** in your `notes.md`: given data size, query patterns, team size, cloud budget, which tool do you reach for? Make it concrete enough that you'd send it to a teammate.

### External practice

- [Hannes Mühleisen — Big Data is Dead](https://motherduck.com/blog/big-data-is-dead/) — short, opinionated, well-cited
- [DuckDB vs Spark benchmarks](https://duckdb.org/2024/06/26/benchmarking-tpch-with-duckdb.html) — DuckDB's own benchmarks; biased but data-backed
- [Designing Data-Intensive Applications, Chapter 10](https://dataintensive.net/) — Kleppmann on batch vs stream; foundational

### Self-check (Day 1)

> Q1.1 — Your data is 80 GB on disk in CSV form. Which tools should you consider, and which should you rule out?
> Q1.2 — A test runs `df.filter(...).collect()` in PySpark and prints rows. Why might it pass instantly even on 1 TB of data?
> Q1.3 — Your PR-time CI runs full-data validation on 4 TB. Name three problems with this and a better pattern.
> Q1.4 — When does Spark's overhead start to pay off, in rough terms?

---

## Day 2 (Tue) — PySpark Basics & Testing

### Theory

PySpark gives you the Spark API in Python. You write transformations (filter, join, groupby) on DataFrames; Spark plans and executes them across a cluster (or your laptop, in `local` mode).

### The minimum PySpark you need

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Create a session — local[*] uses all available cores on your machine
spark = (
    SparkSession.builder
    .appName("data-testing")
    .master("local[*]")
    .getOrCreate()
)

# Create a DataFrame from in-memory data (good for tests)
data = [
    ("alice@x.com", "US", 99.50),
    ("bob@x.com",   "PL", 14.00),
    ("carol@x.com", "UK", 250.00),
]
df = spark.createDataFrame(data, schema=["email", "country", "total"])

df.show()
df.printSchema()

# Read from Parquet
df_p = spark.read.parquet("data/orders.parquet")

# Read from CSV
df_c = spark.read.csv("data/customers.csv", header=True, inferSchema=True)

# Filter and aggregate
result = (
    df_p
    .filter(F.col("status") == "completed")
    .groupBy("country")
    .agg(F.sum("total").alias("revenue"))
    .orderBy(F.desc("revenue"))
)

result.show(10)
```

### Lazy evaluation — the most important PySpark concept

In pandas, `df.filter(...)` runs immediately. In Spark:

```python
filtered = df.filter(F.col("status") == "completed")     # nothing happens yet
counted = filtered.count()                                # NOW Spark runs the plan
```

**Transformations** (`filter`, `select`, `groupBy`, `withColumn`) are lazy — they build a plan. **Actions** (`count`, `collect`, `show`, `write`) execute the plan. Until you call an action, no work happens.

This is why a "test" that just calls `df.filter(...)` doesn't prove correctness. The plan builds; nothing runs. You need an action — a count, a collect, a write, or `assertDataFrameEqual` (which calls `collect` internally).

### `assertDataFrameEqual` (PySpark 3.5+)

The built-in test helper:

```python
from pyspark.testing.utils import assertDataFrameEqual

def test_filter_active_orders(spark):
    input_data = [
        ("o1", "completed", 100.0),
        ("o2", "pending",   50.0),
        ("o3", "completed", 200.0),
    ]
    input_df = spark.createDataFrame(input_data, ["order_id", "status", "total"])

    result = input_df.filter(F.col("status") == "completed")

    expected_data = [
        ("o1", "completed", 100.0),
        ("o3", "completed", 200.0),
    ]
    expected_df = spark.createDataFrame(expected_data, ["order_id", "status", "total"])

    assertDataFrameEqual(result, expected_df)
```

Useful options:

| Option | Default | Use case |
|---|---|---|
| `checkRowOrder` | `False` | If you don't care about ordering, default is fine |
| `rtol`, `atol` | `1e-5`, `1e-8` | Float tolerances |
| `ignoreNullable` | `True` | Most tests don't care if nullable bit differs |
| `ignoreColumnOrder` | `False` | Set `True` for "same data, any column order" |
| `showOnlyDiff` | `False` | Set `True` for huge DataFrames — only print diffs |
| `maxErrors` | `None` | Cap error output for big mismatches |

`assertSchemaEqual` does what it says — schema-only comparison without row data.

### A pytest fixture for SparkSession

```python
# conftest.py
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    """One SparkSession for all tests in this session — saves startup cost."""
    s = (
        SparkSession.builder
        .appName("pytest-spark")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "2")    # smaller partitions for tests
        .config("spark.ui.showConsoleProgress", "false") # quieter output
        .getOrCreate()
    )
    yield s
    s.stop()
```

`scope="session"` is critical — without it, every test creates a new SparkSession (10+ seconds each). Session-scoped, you pay it once.

### chispa — a third-party alternative

[chispa](https://github.com/MrPowers/chispa) predates the built-in helpers and offers column-level helpers:

```python
from chispa.column_comparer import assert_column_equality

def test_remove_extra_spaces(spark):
    data = [("hello  world", "hello world"), ("a   b", "a b")]
    df = spark.createDataFrame(data, ["raw", "expected"]).withColumn(
        "actual", F.regexp_replace("raw", r"\s+", " ")
    )
    assert_column_equality(df, "actual", "expected")
```

For new projects, the built-in `assertDataFrameEqual` covers most needs. Reach for chispa when you specifically want column-level helpers or work in a codebase that already uses it.

### Gotchas

1. **`SparkSession.builder.getOrCreate()` returns the existing session if any.** If a test misconfigures and the next test inherits the bad config — confusing. Use a session fixture and don't override it ad-hoc.
2. **`master("local[*]")` works on your laptop; `master("yarn")` and `local[*]` are not interchangeable.** Test code shouldn't hardcode either — read from config.
3. **Float comparison.** `100.0 == 100.000001` is `False`. Use `assertDataFrameEqual(..., rtol=1e-3)` for currency math.
4. **Schema mismatch on simple tests.** `createDataFrame([(1, "a")], ["x", "y"])` infers `x` as `bigint` (long), but a column from CSV might be `int`. Both look like integers; `assertSchemaEqual` flags it. Use `ignoreNullable=True` and explicit `StructType` schemas in tests when this matters.
5. **`show()` is for humans, not tests.** It prints; it doesn't assert. Don't write `df.show()` and call it a test.

### Exercises

Create `tests/test_pyspark.py` (with the `spark` fixture in `conftest.py`).

1. Write a function `mark_high_value_orders(df, threshold)` that adds a column `is_high_value` (`True` if `total > threshold`). Test it with `assertDataFrameEqual` against an expected DataFrame.
2. Write `aggregate_country_revenue(df)` that groups by country and sums total. Test it. (This is the same logic you'd do in dbt or pandas — just the framework changes.)
3. **Lazy evaluation trap:** write a test that calls `df.filter(...)` but never an action. Run it. Why does it pass even if the filter is wrong? Add a `count()` to make the test actually execute and observe the difference.
4. **Schema test:** use `assertSchemaEqual` to verify your Week 4 e-commerce schema (translated to PySpark `StructType`). Confirm an obviously wrong schema fails.
5. Read the e-commerce CSV from Week 2 with `spark.read.csv(... inferSchema=True)`. Compare `df.printSchema()` to what you'd expect — note where Spark's inferences are too loose (e.g., dates inferred as strings).
6. **Stretch:** write a `assertDataFrameEqualNoOrder` wrapper that calls `assertDataFrameEqual(..., checkRowOrder=False)` after sorting both sides. Some teams prefer the explicit name.

### External practice

- [PySpark Testing — official](https://spark.apache.org/docs/latest/api/python/getting_started/testing_pyspark.html) — current, concise
- [PySpark functions reference](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/functions.html) — bookmark this
- [Tomasz Drabas — Learning PySpark](https://www.oreilly.com/library/view/learning-pyspark/9781786463708/) — book, dated but the concepts hold
- [chispa](https://github.com/MrPowers/chispa) — third-party test helpers; column equality, approximate equality

### Self-check (Day 2)

> Q2.1 — Why doesn't `df.filter(F.col("x") > 0)` execute immediately?
> Q2.2 — A test creates a SparkSession and tears it down per-test. What's the performance cost, and how do you fix it?
> Q2.3 — `assertDataFrameEqual(actual, expected, rtol=1e-3)` — when do you need `rtol`?
> Q2.4 — `df.show()` in a test function — why isn't this an assertion?

---

## Day 3 (Wed) — DuckDB at Scale

### Theory

DuckDB is an embedded, in-process analytical database. You met it in Week 6 as the dbt warehouse for local development. Today you'll see why it punches above its weight for testing real (medium-sized) datasets.

### The pitch

- **In-process** — runs inside your Python program, no server, no daemon, no port
- **Columnar** — reads only the columns you query
- **Vectorized** — processes batches of rows in tight loops; very fast
- **Direct file query** — `SELECT * FROM 'orders.parquet'` works without an import step
- **Out-of-core** — spills to disk if data exceeds RAM; doesn't OOM
- **Standard SQL** — Postgres-flavored, widely portable

For testing data: it's the fastest path from "here's a Parquet file" to "is it correct?"

### Querying files directly

```python
import duckdb

# Single file
con = duckdb.connect()
con.sql("SELECT count(*) FROM 'data/orders.parquet'").show()

# Multiple files via glob
con.sql("SELECT count(*) FROM 'data/orders/*.parquet'").show()

# Direct read into pandas
df = con.sql("""
    SELECT country, sum(total) AS revenue
    FROM 'data/orders.parquet'
    WHERE status = 'completed'
    GROUP BY country
    ORDER BY revenue DESC
""").df()
```

The `.df()` method returns a pandas DataFrame; `.arrow()` returns a pyarrow Table; `.fetchall()` returns Python tuples. Pick the format you want at the boundary.

### Schema introspection

```python
# Schema of a Parquet file
con.sql("DESCRIBE SELECT * FROM 'data/orders.parquet'").show()

# Lower-level Parquet metadata
con.sql("SELECT * FROM parquet_metadata('data/orders.parquet')").show()
con.sql("SELECT * FROM parquet_schema('data/orders.parquet')").show()
```

`parquet_metadata` shows row group counts, compressed/uncompressed sizes, min/max statistics per column. **This is gold for testing** — you can assert "row groups have non-trivial size" or "min/max of `total` falls within expected range" *without reading the data itself*. Just metadata.

### Testing patterns with DuckDB

Same testing style as Week 1 (SQL for data testing), now against Parquet files at scale.

```python
import duckdb
import pytest


@pytest.fixture
def con():
    c = duckdb.connect()
    yield c
    c.close()


def test_orders_no_negative_totals(con, parquet_path):
    result = con.sql(f"""
        SELECT count(*) AS bad_rows
        FROM '{parquet_path}'
        WHERE total < 0
    """).fetchone()
    assert result[0] == 0, f"Found {result[0]} orders with negative totals"


def test_orders_country_codes_are_iso(con, parquet_path):
    result = con.sql(f"""
        SELECT count(*) AS bad_rows
        FROM '{parquet_path}'
        WHERE NOT regexp_matches(country, '^[A-Z]{{2}}$')
    """).fetchone()
    assert result[0] == 0


def test_orders_reconciliation(con, parquet_path, items_path):
    """The Week 1 reconciliation rule, now at scale via DuckDB."""
    result = con.sql(f"""
        WITH expected AS (
            SELECT order_id, sum(quantity * unit_price) AS computed_total
            FROM '{items_path}'
            GROUP BY order_id
        )
        SELECT count(*) AS bad_rows
        FROM '{parquet_path}' o
        JOIN expected e USING (order_id)
        WHERE abs(o.total_amount - e.computed_total) > 0.01
    """).fetchone()
    assert result[0] == 0
```

### Reading from cloud storage

DuckDB's `httpfs` extension lets you query S3 or HTTPS directly:

```python
con.sql("INSTALL httpfs; LOAD httpfs;")
con.sql("""
    SELECT count(*)
    FROM 's3://my-bucket/data/orders/*.parquet'
""").show()
```

For tests on cloud data, this lets you skip the download step entirely. Authentication via env vars (`AWS_ACCESS_KEY_ID`, etc.) or a manual `SET s3_access_key_id = ...` config.

### When DuckDB doesn't fit

- **Concurrent writers** — DuckDB is single-writer (one process can write at a time, multiple can read). For high write concurrency, use Postgres or a real warehouse.
- **Multi-machine workloads** — DuckDB is single-machine. If your data genuinely requires distribution, Spark or a cloud warehouse wins.
- **Long-running services** — DuckDB is for analytical batch / interactive use, not OLTP. Don't put it behind a 24/7 API.

### Gotchas

1. **DuckDB is *not* a data warehouse.** It's a local engine. Don't confuse it with Snowflake / BigQuery (which are managed, distributed, multi-user). The query syntax is similar; the operational model is different.
2. **Schema inference can guess wrong.** `read_csv_auto` is helpful but not perfect — strings that look like dates may be treated as dates inconsistently across files. Specify schema explicitly when correctness matters.
3. **In-memory DBs lose state.** `duckdb.connect()` (no path) creates an in-memory DB — gone when the process exits. For persistence: `duckdb.connect("warehouse.duckdb")`.
4. **Quoting paths in SQL.** `SELECT * FROM 'orders.parquet'` works; `SELECT * FROM orders.parquet` (without quotes) is parsed as schema.table — different thing.
5. **Version pinning matters.** DuckDB v0.x → v1.0 was a breaking change. Within v1.x line, the API is stable. Pin major version in production.

### Exercises

1. Take your Week 2 e-commerce CSVs. Convert them to Parquet:
   ```python
   con.sql("COPY (SELECT * FROM read_csv_auto('customers.csv')) TO 'customers.parquet' (FORMAT PARQUET);")
   ```
   Compare file sizes. Parquet should be smaller and queryable directly.
2. Translate three Week 1 SQL tests (the reconciliation rule, NULL email check, status enum check) to query Parquet via DuckDB. Confirm they pass on clean data and fail on the seeded bugs.
3. **Schema test:** write a function `assert_parquet_schema(path, expected: dict)` that uses `parquet_schema(...)` to verify column names and types match a dictionary. Use it as a fixture-loaded test.
4. **Metadata-only test:** without reading any data, use `parquet_metadata(...)` to assert that `total_amount`'s `stats_min` is ≥ 0 and `stats_max` is < 100,000. (This is fast — milliseconds — even on huge files.)
5. **Multi-file glob:** generate 10 small Parquet files in `data/orders/year=2024/month=*/orders.parquet` (Hive partitioning). Query them as one table. Assert row count equals the sum of per-file row counts.
6. **Stretch:** install the `httpfs` extension and query a public S3 Parquet dataset (e.g., NYC taxi data is freely available). Time how long a count takes vs downloading the file first.

### External practice

- [DuckDB documentation](https://duckdb.org/docs/) — comprehensive, well-organized
- [DuckDB Python API reference](https://duckdb.org/docs/clients/python/overview)
- [Parquet Tips](https://duckdb.org/docs/current/data/parquet/tips) — official tips for performance
- [Awesome DuckDB](https://github.com/davidgasquez/awesome-duckdb) — curated list of integrations and tutorials

### Self-check (Day 3)

> Q3.1 — What does "in-process" mean for DuckDB, and why does it matter for testing?
> Q3.2 — Why is querying Parquet metadata (`parquet_metadata(...)`) often enough for a useful test, without reading data?
> Q3.3 — When wouldn't you reach for DuckDB?
> Q3.4 — `SELECT * FROM 'orders.parquet'` vs `SELECT * FROM orders.parquet` — what's the difference and which is the bug?

---

## Day 4 (Thu) — Parquet Internals & Sampling Strategies

### Theory

You've been using Parquet for two days. Today you understand *why* it's the file format of choice for analytical data — and how its structure enables tests that would be impossible on CSV.

### Parquet structure

```
File (orders.parquet)
├── File header (magic bytes "PAR1")
├── Row Group 1
│   ├── Column Chunk 1 (e.g., order_id)
│   │   ├── Page 1 (values 1–100, with min/max stats)
│   │   ├── Page 2 (values 101–200)
│   │   └── ...
│   ├── Column Chunk 2 (e.g., status)
│   ├── Column Chunk 3 (e.g., total)
│   └── ...
├── Row Group 2
├── ...
├── File footer (schema, row group offsets, per-column statistics)
└── File trailer (magic bytes "PAR1")
```

Three things matter for testing:

1. **Columnar layout** — your test queries can read just one column. A "is `total > 0` for all rows" test reads only the `total` column — possibly 1% of the file's bytes.
2. **Per-row-group statistics** — min, max, null count are stored per row group. Many tests can answer from stats alone, without reading data.
3. **Schema in the footer** — the schema travels with the data. No risk of a CSV that "looks like" the expected schema but isn't.

### Schema validation against Parquet

```python
import pyarrow.parquet as pq

table = pq.read_table("data/orders.parquet")
schema = table.schema

print(schema)
# order_id: int64
# customer_email: string
# total_amount: double
# status: string
# order_date: date32[day]

# Programmatic check
expected_fields = {
    "order_id":       "int64",
    "customer_email": "string",
    "total_amount":   "double",
    "status":         "string",
    "order_date":     "date32[day]",
}

for name, dtype_str in expected_fields.items():
    field = schema.field(name)
    assert str(field.type) == dtype_str, f"{name}: expected {dtype_str}, got {field.type}"
```

You don't have to load the whole file. `pq.read_metadata(path)` gives you schema and statistics without reading data:

```python
metadata = pq.read_metadata("data/orders.parquet")
print(metadata.num_rows)              # total row count
print(metadata.num_row_groups)        # how many row groups
print(metadata.row_group(0).column(2).statistics)  # min/max/null_count for col 2
```

### Hive partitioning

A common pattern: `data/orders/year=2024/month=11/orders.parquet`. Each partition is a directory; the directory names encode partition values. Both DuckDB and PySpark auto-recognize this layout.

```python
# DuckDB picks up the partitioning automatically
duckdb.sql("SELECT year, count(*) FROM 'data/orders/**/*.parquet' GROUP BY year").show()

# PySpark
spark.read.parquet("data/orders").show()    # year, month appear as columns
```

**Test assertions specific to partitioned data:**
- All expected partitions exist (the right years/months/days are present)
- No partition is empty (or zero-row partitions are flagged)
- Row counts per partition fall in expected ranges (catches "yesterday's pipeline didn't run")
- Partition column values match directory names (catches "writer wrote year=2024 to year=2025/" bug)

### Sampling strategies

When the data is too big to test exhaustively, you sample. Three common strategies:

**1. Random sampling — uniform**
```python
sampled = duckdb.sql("SELECT * FROM 'orders.parquet' USING SAMPLE 10000").df()
```

Good for: size estimation, quick smoke tests, distribution profiling.
Bad for: rare events. If 0.01% of records are fraud, a 10,000-row sample sees ~1 fraud row — not enough.

**2. Stratified sampling — proportional per group**

```python
sampled = duckdb.sql("""
    WITH numbered AS (
        SELECT *, row_number() OVER (PARTITION BY status ORDER BY random()) AS rn
        FROM 'orders.parquet'
    )
    SELECT * FROM numbered WHERE rn <= 100   -- 100 per status
""").df()
```

Good for: tests that need representation of every category.

**3. Reservoir sampling — for streaming data**

When you can't see all records at once (e.g., processing a stream), reservoir sampling gives you a uniform sample of fixed size with one pass:

```python
import random

def reservoir_sample(stream, k):
    """Return a uniform random sample of k items from an iterable of unknown length."""
    sample = []
    for i, item in enumerate(stream):
        if i < k:
            sample.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                sample[j] = item
    return sample
```

Good for: tests on data that won't fit in memory and can only be iterated once. Used in streaming pipelines for sample-based monitoring.

### When to sample (and when not to)

| Situation | Approach |
|---|---|
| "Are aggregates correct?" | Don't sample — compute the full aggregate. Modern engines do this fast. |
| "Does every row pass a regex?" | Sample if the dataset is huge AND the regex is well-tested elsewhere; otherwise full check. |
| "Are there any nulls?" | Don't sample — `count(*) FILTER (WHERE x IS NULL)` is cheap. |
| "Does the distribution look right?" | Sample — Kolmogorov-Smirnov-style tests don't need full data. |
| "Was the rare class preserved?" | Stratified sample, not random. |
| "Profile for first-time exploration" | Sample — you're looking, not asserting. |

### Gotchas

1. **`USING SAMPLE 10000` in DuckDB samples *roughly* 10000 rows by default**, not exactly. For exact counts, use `USING SAMPLE reservoir(10000 ROWS)` or `USING SAMPLE 10000 ROWS`. Read docs.
2. **Random samples aren't reproducible without a seed.** `SET seed = 0.42` in DuckDB or pass a seed in Spark. Tests that use samples need determinism just like Faker.
3. **Stratified sampling can over-represent rare classes.** If you take 100 per group and one group has only 50, you get all of them — overrepresented in the sample. Document this; don't assume the sample mirrors population proportions.
4. **Parquet schemas can drift across files.** Different writers can produce slightly different types (`int32` vs `int64`). Use `union_by_name=true` (DuckDB) or `mergeSchema=true` (Spark) to handle gracefully — but test that the merge produced what you expected.
5. **Compression interacts with row group size.** Smaller row groups = better random access; larger = better compression. The right size depends on workload. Default (122,880 rows in DuckDB) is fine for most cases.

### Exercises

1. Take your e-commerce orders Parquet. Use `pq.read_metadata` to print: total rows, row group count, per-column min/max/null_count for `total_amount`. Assert min ≥ 0, null_count == 0.
2. Write a function `assert_partition_completeness(base_path, expected_partitions)` that checks every expected `year=2024/month=...` directory exists. Test it with one partition deliberately missing.
3. **Sampling test:** generate a 1M-row DataFrame using Faker. Save to Parquet. Take a 1% random sample with a fixed seed. Assert the sample's mean of `total_amount` is within 5% of the full dataset's mean. (You're testing your sampling, not the data — but it's a useful pattern.)
4. **Stratified sampling:** generate orders where 99% have status `completed` and 1% have status `cancelled`. Take a stratified sample (50 per status). Verify both groups are represented. Compare to a random sample of the same size — does the random sample reliably contain cancelled orders?
5. **Metadata-only test for a 10 GB file (simulated):** instead of the full Parquet, just read metadata. Assert: total_rows > 1M, total_rows < 100M, row group count is reasonable (between 5 and 1000). All in milliseconds.
6. **Stretch:** write a `compare_parquet_schemas(a_path, b_path)` that reports column names added/removed/changed between two Parquet files. Useful for "did upstream change the schema?" tests.

### External practice

- [Apache Parquet — File format](https://parquet.apache.org/docs/file-format/) — official spec; technical
- [Uwe Korn — How fast can we process a Parquet file?](https://uwekorn.com/2019/02/19/how-fast-is-parquet.html) — benchmarks and internals
- [DuckDB sampling syntax](https://duckdb.org/docs/sql/samples.html) — official, concise
- [Vitter's reservoir sampling paper (1985)](https://www.cs.umd.edu/~samir/498/vitter.pdf) — short, accessible classic

### Self-check (Day 4)

> Q4.1 — Why can a "min/max of column X is in range" test on a 100 GB Parquet file run in milliseconds?
> Q4.2 — When is random sampling a bad choice, and what do you use instead?
> Q4.3 — Hive partitioning: how does `data/orders/year=2024/month=11/` differ from a flat directory of files?
> Q4.4 — A Parquet writer produces `int32`; a downstream reader expects `int64`. What's the failure mode, and how do you defend against it?

---

## Day 5 (Fri 🤖) — AI Workflow: Generating PySpark Test Suites

### What you're learning today

Inheriting a Spark pipeline and being told "write tests" is a common assignment. You don't have time to read every transformation by hand. AI shortens that gap — give it the code, get a draft test suite, then review and tighten.

### Setup

Reuse the `anthropic` setup from Weeks 8–9.

### Exercise 1 — Generate tests from a transformation function

Pick one of your Week 6 dbt models (or write a small PySpark transformation). Paste it into Claude:

> *"Here's a PySpark transformation function. Generate a pytest test file using the pytest-spark fixture pattern with `assertDataFrameEqual` from `pyspark.testing.utils`. Cover:*
> *1. The happy path with realistic input.*
> *2. Empty-DataFrame input.*
> *3. NULL handling — what happens when input has nulls in key columns?*
> *4. Edge case where the transformation should change nothing (idempotent input).*
> *5. Schema check using `assertSchemaEqual` against an explicit `StructType`.*
>
> *Include a session-scoped `spark` fixture in conftest.py if needed. Use modern PySpark 4.x APIs.*
>
> *Function:*
> *```python*
> *[paste code]*
> *```*
>
> *Return only Python code; no commentary."*

The AI will produce a draft. **Review carefully** — common mistakes:

- Hardcoded schemas that don't match the function's actual output
- Test data that doesn't exercise the actual logic (e.g., all rows pass the filter, so the filter isn't tested)
- Float comparisons without `rtol`
- Missing `assertDataFrameEqual` import
- Outdated APIs (e.g., importing from `pyspark.sql.testing` — wrong; it's `pyspark.testing.utils`)

### Exercise 2 — Schema-driven test suite

Give Claude a Parquet schema (from `pq.read_metadata(...)`) and ask for validation tests:

> *"Here's the schema of a Parquet file containing customer orders. Generate a pytest test suite using DuckDB to validate: column types match expected, no nulls in primary key, all status values are in {pending, completed, cancelled}, all totals are non-negative, all emails match a basic regex. Use a Parquet path as a pytest fixture parameter.*
>
> *Schema:*
> *```*
> *order_id: int64 not null*
> *customer_email: string*
> *total_amount: double*
> *status: string*
> *order_date: date32[day]*
> *```*
>
> *Return only the Python test file."*

This is faster than writing 5 boilerplate validation tests by hand. The AI is good at the structure; you're good at the domain rules — combine.

### Exercise 3 — Sampling logic

A nuanced one: ask the AI to generate a stratified sampling function plus its tests:

> *"Write a Python function `stratified_sample(con, parquet_path, group_col, n_per_group, seed)` that uses DuckDB to take exactly `n_per_group` rows from each value of `group_col`, deterministically with `seed`. Then write 3 pytest tests:*
> *1. Each group is present in the output.*
> *2. Output has exactly n_per_group * num_groups rows (or fewer if a group has < n_per_group).*
> *3. Same seed produces same output across two calls.*
>
> *Use DuckDB's window functions. Return only Python code."*

Review the SQL. The AI may use `RANDOM()` without `SET seed = ...` (then determinism is broken). It may use `LIMIT` instead of a row-numbering window (then you don't get exactly n per group when ties exist). Both are fixable but worth catching.

### Exercise 4 — Cost vs benefit reflection

Run all three exercises. For each, log:
- Time spent writing the prompt
- Time spent reviewing and fixing the AI's output
- Approximate API cost
- Compare to your estimate of writing the test from scratch by hand

The honest answer: AI saves time on **structure** (boilerplate, imports, fixtures) but doesn't save time on **judgment** (what to test, what assertions matter, what edge cases exist in your domain). For a 5-test file, AI is probably 2–3× faster than hand-writing. For a 1-test file, hand-writing wins.

### Update your `.cursorrules`

```
PySpark / DuckDB testing conventions:
- Use the built-in `pyspark.testing.utils.assertDataFrameEqual` for new code; chispa is acceptable in legacy projects.
- Session-scoped `spark` fixture in conftest.py — never per-test SparkSessions.
- Use `master("local[*]")` for tests; never hardcode cluster URLs.
- Always include an action (count, collect, write, assertDataFrameEqual) in tests; transformations alone don't execute.
- For DuckDB: `con.sql(...).fetchone()` for single values, `.df()` for DataFrames, `.fetchall()` for tuples.
- Quote Parquet paths in SQL: `FROM 'orders.parquet'` not `FROM orders.parquet`.
- Prefer metadata-only tests (`parquet_metadata`) when assertions are about ranges, counts, types — avoid reading data unnecessarily.
- For sampling: deterministic seeds always; stratified for rare classes; document sample size and confidence.
- Float comparisons: rtol=1e-3 for currency, 1e-5 for science, 1e-8 for accounting (audit-grade).
```

### Quality bar — when is a generated big-data test suite "good"?

- [ ] Imports are current — `pyspark.testing.utils.assertDataFrameEqual`, not legacy paths
- [ ] Spark session is session-scoped, not per-test
- [ ] At least one test actually fails when given bad input (you verified)
- [ ] Float tolerances are explicit, not default
- [ ] Schema checks use explicit `StructType`, not duck-typed comparison
- [ ] No hardcoded paths to your machine
- [ ] Sample-based tests have fixed seeds

### Reflection (write 3–5 sentences in `notes.md`)

- Was AI-generated code accurate on PySpark APIs, or did it hallucinate methods that don't exist?
- For test boilerplate, was AI faster than your hand-written version? By how much?
- Compared to Week 8 (synthetic data) and Week 9 (schema inference), is this Friday's AI use the most or least valuable so far? Why?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 11. 5–7 = re-review. <5 = redo exercises.

1. Your data is 50 GB. Should you reach for Spark or DuckDB? Why?
2. PySpark transformations are *lazy*. What does that mean for tests, and what's the practical implication?
3. The function name and exact import path for the built-in PySpark DataFrame equality test.
4. Why is `scope="session"` essential for the `spark` fixture in pytest?
5. What does DuckDB's `parquet_metadata(...)` give you, and why is it useful for testing?
6. The two columnar-storage features that make Parquet tests fast on huge files.
7. When is random sampling a bad choice, and what's the alternative?
8. Hive partitioning — the URL pattern and what it lets you test.
9. A test calls `df.filter(...).collect()` on 1 TB of data. What problem are you about to have?
10. Compared to pandas tests, what's one thing that's *easier* about big-data tests, and one thing that's *harder*?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about big-data testing.

### IQ1. "How do you decide between DuckDB and Spark for a project?"

*What a good answer covers:*
- **Data size** — single-machine threshold (DuckDB) vs requires-distribution threshold (Spark)
- **Existing code** — if there's an existing Spark codebase, don't rewrite it; if greenfield, prefer the simpler tool
- **Operational model** — DuckDB is in-process (zero-ops); Spark is a distributed system with cluster management overhead
- **Latency requirements** — interactive queries: DuckDB wins. Batch jobs over hours of data: either, depending on size
- **Team skills** — Spark expertise is valuable but not free; DuckDB's SQL is portable to anyone who knows SQL
- **Cost** — Spark cluster runtime adds up; DuckDB on a laptop is free

*Likely follow-up:* "Does Spark scale better than DuckDB?" (Answer: yes, because Spark is distributed; DuckDB is single-machine. The question is whether you actually need that scale. Most workloads under 1 TB are solved better by DuckDB.)

### IQ2. "Walk me through testing a PySpark transformation."

*What a good answer covers:*
- Session-scoped SparkSession fixture so you pay startup once
- `assertDataFrameEqual` from `pyspark.testing.utils` for output equality
- `assertSchemaEqual` for schema-only checks (faster, narrower)
- Test data created via `createDataFrame(...)` — small, focused on the case you're testing
- Cover: happy path, empty input, nulls, edge cases (boundary values, single-row, many-row)
- Float comparisons use `rtol`/`atol`
- Lazy evaluation reminder — every test must call an action, not just transformations

*Likely follow-up:* "How do you test a transformation that aggregates billions of rows?" (Answer: don't test it on billions in CI. Test the transformation logic on a small representative sample. Run the full-data version on a schedule against production data, with reconciliation alerts. Trust the unit test for correctness; the production check guards against environmental issues.)

### IQ3. "What's a Parquet file, and why is it the standard for analytical data?"

*What a good answer covers:*
- **Columnar storage** — values from the same column stored together; reading one column doesn't require reading others
- **Compression** — column data is often similar (e.g., status column has few distinct values), so compression is effective
- **Schema embedded** — schema travels with the data; no orphan CSVs with mystery types
- **Per-row-group statistics** — min/max/null_count enable predicate pushdown and metadata-only queries
- **Standard across the ecosystem** — Spark, DuckDB, Polars, Athena, Snowflake, all read Parquet directly
- **Splittable** — parallel readers can each process different row groups

*Likely follow-up:* "When wouldn't you use Parquet?" (Answer: streaming append-only data — Parquet is bad for many small writes; row-format like Avro is better. Or for human-readable interchange — CSV/JSON for that. Or when target tooling doesn't support it; rare but happens.)

### IQ4. "How would you test a partitioned Parquet dataset that gets a new partition daily?"

*What a good answer covers:*
- **Daily freshness check**: assert today's partition exists and has expected row count
- **Schema consistency**: assert today's partition has the same schema as yesterday's (catches upstream schema drift)
- **Volume bounds**: today's row count is within X% of the trailing 7-day average — catches "pipeline ran on empty data" silently
- **Statistical drift**: distribution of key columns (e.g., revenue) hasn't shifted dramatically (Kolmogorov-Smirnov against last week)
- **Partition-internal validation**: same per-row checks as any data file (no nulls, valid ranges, etc.)
- **Cross-partition reconciliation**: if your Bronze and Silver layers are both partitioned, daily counts should reconcile

*Likely follow-up:* "How do you alert when a daily partition is missing?" (Answer: a scheduled check at expected ingest time + N hours; alert if not present. Use freshness SLOs — "partition for date D must exist by D+02:00 UTC" — and treat violation as a paging event.)

### IQ5. "What are the trade-offs of sampling in tests?"

*What a good answer covers:*
- **Pros**: fast, cheap, sufficient for most assertions, scales to any data size
- **Cons**: can miss rare events, sampling bias, requires statistical understanding to interpret confidence
- **When fine**: aggregates, distribution shape, presence checks for common cases, regex coverage
- **When wrong**: rare class detection (use stratified), specific row identification (need full data), audit-grade reconciliation (need exact)
- **Determinism**: tests must be reproducible — use fixed seeds, document sample size
- **Sample size matters**: "1% sample" of 1B rows is 10M — usually enough; "1% sample" of 1000 rows is 10 — usually not

*Likely follow-up:* "How would you test that a fraud-detection model catches the rare fraud cases when fraud is 0.01% of records?" (Answer: stratified sampling — sample all fraud cases plus a random subset of non-fraud — gives you statistical power for the rare class. Or stratify on the prediction itself: confirm precision/recall on a balanced labeled subset rather than a population sample.)

---

## If you have extra time this week (stretch)

- Try [Polars](https://pola.rs/) — a Rust-based DataFrame library with a pandas-like API. Often beats both DuckDB and pandas on single-machine workloads. Worth a 30-minute exploration.
- Read [The Snowflake architecture paper (2016)](https://event.cwi.nl/lsde/papers/p215-dageville-snowflake.pdf) — the canonical "modern data warehouse" paper. Influential beyond Snowflake itself.
- Set up a tiny [Apache Iceberg](https://iceberg.apache.org/) table with DuckDB's Iceberg extension. Iceberg adds time-travel and schema evolution to Parquet — Week 11 territory, sneak preview.
- Compare PySpark, DuckDB, and Polars on the same task: load a 5 GB Parquet, filter, group by, sum. Which wins? Time each.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Both DuckDB and Spark can handle 80 GB. DuckDB is the better default — single machine, embedded, fast. Rule out pandas (would require 400+ GB RAM for a CSV that size); SQLite (not designed for analytical workloads at this scale).
- **Q1.2** — Lazy evaluation. The `filter` is a transformation that builds a plan; `collect` triggers execution. If `collect` returns an empty DataFrame quickly, the plan ran but data was filtered to nothing — could be correct, could be a bug. Either way, *fast* doesn't mean *correct*.
- **Q1.3** — Problems: (a) cost — every PR scans the full data; (b) latency — engineers wait 90 minutes; (c) brittleness — when it breaks, nobody fixes it. Better pattern: small representative sample on PR; full data check on schedule with alerting.
- **Q1.4** — Roughly when single-machine I/O becomes the bottleneck — typically > 1 TB of *frequently scanned* data, or workloads that genuinely need multi-machine parallelism. Below that, Spark's overhead is pure cost.

### Day 2 answers

- **Q2.1** — Lazy evaluation. `filter` is a transformation that adds to the plan; only actions (`count`, `collect`, `show`, `write`) trigger execution. Spark optimizes across the full plan before running anything.
- **Q2.2** — Each SparkSession startup is ~10–20 seconds (JVM boot). With per-test sessions, a 50-test suite spends ~10–15 minutes just starting Spark. Fix: `scope="session"` on the fixture so all tests share one session.
- **Q2.3** — When comparing floats. `100.0 == 100.000001` is `False` in pure equality; `rtol=1e-3` accepts differences up to 0.1%. Currency math, ML model scores, anywhere floats appear.
- **Q2.4** — `show()` prints to stdout. It doesn't raise on mismatch; tests need a real assertion (`assertDataFrameEqual`, etc.) to fail when something's wrong. `show()` in tests means a human had to read the output to know — not automation.

### Day 3 answers

- **Q3.1** — DuckDB runs inside your Python process — no separate server, no daemon, no port. You import a library and call functions. For testing, this means: zero setup, fast startup (milliseconds), no infrastructure to manage. SQLite-style ergonomics with analytical-warehouse query speed.
- **Q3.2** — `parquet_metadata` reads only the file footer (kilobytes), not the data (potentially gigabytes). It includes per-column min/max/null_count statistics per row group. Tests like "no negative totals," "row count is in expected range," "no nulls in primary key" can answer from metadata alone — milliseconds even on 100 GB files.
- **Q3.3** — Concurrent writers (single-writer model); multi-machine workloads requiring true distribution; long-running OLTP services (DuckDB is for analytical batch / interactive, not transactional).
- **Q3.4** — `'orders.parquet'` in quotes is a *file path*; DuckDB reads the file. `orders.parquet` without quotes is a *table name* (`orders` schema, `parquet` table) — DuckDB looks it up in the catalog, doesn't find it, errors. Always quote paths.

### Day 4 answers

- **Q4.1** — Two reasons. (1) Columnar layout — only the queried column is read, not the whole row. (2) Per-row-group statistics (min/max/null_count) live in the file footer. A range query can be answered from stats alone without reading any data pages, regardless of file size.
- **Q4.2** — When the property you're testing depends on rare events. A 1% random sample of 1M rows misses categories with frequency < 0.1% reliably. Use stratified sampling (n per group) instead, or full-data check for the rare-class assertion.
- **Q4.3** — Hive partitioning encodes partition values in directory names: `year=2024/month=11/`. Engines auto-recognize this and treat the values as columns without reading file contents. Tests can assert "all expected partitions exist," "no empty partitions," "partition values match directory names."
- **Q4.4** — At read time, the reader either fails (strict) or auto-promotes (lenient). Lenient mode hides drift; strict mode breaks the pipeline. Defend with a schema check on every file at ingest (or use `union_by_name`/`mergeSchema` and *log* what was merged so drift is visible).

### End-of-week answers

**A1.** DuckDB. 50 GB fits comfortably on a single machine and DuckDB's columnar engine handles it in seconds. Spark would add cluster overhead with no scaling benefit.

**A2.** Transformations build a plan; only actions execute. Practically: a test that only calls transformations doesn't actually run them. Every PySpark test must include an action (`assertDataFrameEqual`, `count`, `collect`, `write`).

**A3.** `from pyspark.testing.utils import assertDataFrameEqual` (and `assertSchemaEqual` from the same module).

**A4.** SparkSession startup is ~10–20 seconds (JVM init). Without session scope, each test pays this cost. Session-scoped means once per test run.

**A5.** Schema, row count, row group count, per-column min/max/null_count statistics. Useful because many tests can answer from metadata alone — milliseconds even on huge files.

**A6.** (1) Columnar layout — read only the columns you query. (2) Per-row-group statistics in the footer enable predicate pushdown and metadata-only assertions.

**A7.** When the property depends on rare events (fraud, anomalies, low-volume categories). Stratified sampling — sample n per group — gives statistical power for rare classes.

**A8.** `data/table_name/year=2024/month=11/file.parquet`. Engines auto-treat directory values as columns. Lets you test partition existence, completeness, row counts per partition without reading data.

**A9.** OOM. `collect()` brings all data to the driver; 1 TB doesn't fit in driver memory. Either filter to a small subset first, or aggregate in-cluster (`count`, `groupBy + agg`) and collect the small result.

**A10.** Easier: aggregations are nearly free at any scale (the engines handle parallelism). Harder: lazy evaluation means tests can pass without actually running, and statistical sampling replaces simple equality.

---

*Done with Week 10? You can now match the right tool to the data size, write tests that don't OOM, and use Parquet metadata to assert at the speed of file metadata reads. Onward to Week 11 — Data Lake Tools: Delta Lake, Iceberg, Hudi — where Parquet gets ACID transactions, schema evolution, and time travel bolted on.*
