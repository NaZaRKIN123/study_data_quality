# Week 4 — Data Quality Concepts | Training Materials

> **Companion to:** Week 4 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Formalize what "good data" means with the 6 dimensions of DQ, and turn that vocabulary into a reusable Python module. By Friday you'll have hit the **End of Month 1 milestone**: a pytest suite validating a dataset across 5+ quality dimensions.

---

## How to use this file

- This is the consolidation week for Month 1 — every concept ties into the Bronze/Silver/Gold pipeline you built last week
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday is the **multi-file AI workflow** session — your first time using Cursor Composer (or equivalent) to generate code across multiple files
- Answers to all self-checks are at the bottom of the file

---

## One-time setup (~5 minutes)

You'll continue using the project from Weeks 2 and 3. Add two libraries:

```bash
source .venv/bin/activate
pip install pandera scipy
```

Sanity check:
```bash
python -c "import pandera as pa, scipy; print(pa.__version__, scipy.__version__)"
```

You should see something like `0.2x.x` for pandera and `1.x.x` for scipy. Pandera versions before 0.20 work fine for everything this week — if you have 0.20+, the `pandera.pandas` import path is also available; both work.

---

## Day 1 (Mon) — The 6 Dimensions of Data Quality

### Theory

The **6 dimensions of data quality** are a checklist for "what could be wrong with this data?" They give you and your stakeholders shared vocabulary. The list below is the most common version (DAMA-DMBoK style) but be aware: different sources list 5, 6, 7, or 10 dimensions. The exact count doesn't matter — what matters is having a *complete* mental checklist when you design tests.

| # | Dimension | Question it answers | Typical test pattern |
|---|---|---|---|
| 1 | **Completeness** | Are all required values present? | `assert_no_nulls`, row count vs source |
| 2 | **Uniqueness** | Are there unintended duplicates? | PK uniqueness, business-key uniqueness |
| 3 | **Validity** | Does the value conform to format/type/range/enum? | dtype, regex, `isin(...)`, value-in-range |
| 4 | **Consistency** | Does the same data agree across places? | Cross-table reconciliation, format consistency |
| 5 | **Timeliness** | Is the data recent enough to be useful? | `max(updated_at)` within SLA |
| 6 | **Accuracy** | Does the data match reality? | Sample audit vs system-of-record; **hardest to automate** |

### Why accuracy is the odd one out

The first five dimensions can be tested with **just the data itself**. Accuracy can't — you need an **external source of truth**. If your `customers.email` says `anna@example.com` and reality is `anna.smith@example.com`, no amount of pandas can detect that. You'd need to call an email-verification API, sample-audit against the source system, or compare against a curated reference dataset.

That's why most automated DQ frameworks (Great Expectations, Soda, dbt tests) primarily catch **completeness, uniqueness, and validity**. Accuracy almost always falls back to manual sampling or stakeholder feedback.

### Mapping the dimensions to tests you already wrote

Look back at your work from Weeks 1–3. Every test you wrote already maps to one of these dimensions:

| Test you wrote | Dimension |
|---|---|
| `assert_no_nulls(df, ["customer_id"])` (Wk2 Day 3) | Completeness |
| `assert_unique(df, ["order_id"])` (Wk2 Day 3) | Uniqueness |
| `assert_in_set(df, "status", {"active", "churned"})` (Wk2) | Validity |
| Reconciling `orders.total_amount` vs `SUM(quantity * unit_price)` (Wk1, Wk2, Wk3) | Consistency |
| Anti-join: every order has a valid customer (Wk1 Day 4) | Consistency (referential) |
| (You haven't written one yet) | Timeliness — Day 3 today |
| (You haven't written one yet) | Accuracy — discussed but not coded |

This week formalizes that vocabulary so you can map any test to a dimension on demand — useful for documentation, code review, and interviews.

### Gotchas

1. **The dimensions overlap.** A "no orphan customer_id" test is both a *completeness* check (the FK isn't NULL) and a *consistency* check (the FK resolves). Pick one label, document the rationale, move on. Don't get philosophical.
2. **"Accuracy" is often misused** to mean "the data is right" in a vague sense. Be precise: in DQ vocabulary, accuracy specifically means *agreement with reality*, not "the test passes". A test passing on wrong data is *valid but inaccurate*.
3. **Some lists separate "Conformity" or "Integrity"** as their own dimensions. They're slicing validity and consistency more finely. Use whatever vocabulary your team uses; don't argue about lists.
4. **The dimensions don't tell you *which* values to test** — only what *categories* of test exist. The schema, business rules, and stakeholder context decide which columns get which check.

### Exercises (no coding today — vocabulary day)

1. Open your project and walk through every test file. Beside each test (in a comment or a notes file), label which dimension it belongs to. Are any dimensions missing entirely?
2. For each of your project's tables (customers, orders, order_items, products), write a one-line test idea per dimension — even ones you can't easily implement. You should have ~24 ideas. Note which ones are easy, hard, or "needs external source of truth" (= accuracy).
3. **Missed dimension hunt:** which dimension are you weakest on across the project so far? (For most learners, it's *timeliness* — we haven't written any freshness tests yet.) This becomes Day 3's focus.
4. **Industry reading:** skim one of these (15 min):
   - [Atlan — 6 data quality dimensions](https://atlan.com/data-quality-dimensions/) — a clear modern overview
   - [Monte Carlo — 5 pillars of data observability](https://www.montecarlodata.com/blog-data-observability-five-pillars/) — different framing, same idea, with monitoring lens
   - DAMA-DMBoK chapter on Data Quality — the canonical industry reference if you can borrow it (textbook, dense)

### External practice

- [Atlan — 6 dimensions](https://atlan.com/data-quality-dimensions/) — readable, accurate
- [Great Expectations — Expectations Gallery](https://greatexpectations.io/expectations/) — every built-in expectation maps to a dimension; useful to skim
- [r/dataengineering — "what's your data quality framework"](https://www.reddit.com/r/dataengineering/) (search) — see how teams talk about this in practice

### Self-check (Day 1)

> Q1.1 — Name the 6 dimensions of data quality.
> Q1.2 — Which dimension is hardest to test with just the data, and why?
> Q1.3 — Classify these tests by dimension: (a) `email matches *@*.* regex`, (b) `count of rows today within 20% of 7-day average`, (c) `customer_id in orders exists in customers`.
> Q1.4 — Why does it not matter much whether your team uses 6 or 7 dimensions?

---

## Day 2 (Tue) — Schema Validation with pandera

### Theory

A **schema validator** lets you declare *the expected shape of a DataFrame* — column names, types, constraints — and then check any DataFrame against that declaration. It's a natural fit for the boundary of every transformation: validate inputs going in, outputs coming out.

In Week 2 you wrote your own `validators.py` with functions like `assert_no_nulls`. **pandera** does the same thing in a declarative, composable, type-aware way. Once you learn it, you'll rarely hand-write column validators again.

### The two pandera styles

**Object-based (Schema/Column):**

```python
import pandera as pa

orders_schema = pa.DataFrameSchema(
    columns={
        "order_id":     pa.Column(int, unique=True, nullable=False),
        "customer_id":  pa.Column(int, nullable=False),
        "total_amount": pa.Column(float, pa.Check.greater_than_or_equal_to(0), nullable=True),
        "status":       pa.Column(str, pa.Check.isin(["completed", "cancelled"])),
        "order_date":   pa.Column("datetime64[ns]"),
    },
    strict=True,   # reject DataFrames with extra columns
)

# Use it
orders_schema.validate(df)   # raises pandera.SchemaError on failure
```

**Class-based (DataFrameModel — feels more like Pydantic):**

```python
import pandera as pa
from pandera.typing import Series

class OrdersSchema(pa.DataFrameModel):
    order_id:     Series[int]   = pa.Field(unique=True)
    customer_id:  Series[int]
    total_amount: Series[float] = pa.Field(ge=0, nullable=True)
    status:       Series[str]   = pa.Field(isin=["completed", "cancelled"])
    order_date:   Series["datetime64[ns]"]

    class Config:
        strict = True

OrdersSchema.validate(df)
```

Both styles produce the same result. Use whichever feels natural; many teams pick the class-based style because IDEs auto-complete it and it's easier to read in diffs.

### What pandera gives you over hand-rolled validators

- **One declaration covers many checks** — no separate `assert_no_nulls`, `assert_unique`, etc.
- **Rich error messages** — pandera tells you which column failed which check on which rows
- **Composable schemas** — you can extend an existing schema (`OrdersSchema.update_columns(...)`)
- **Type inference for downstream code** (with `@pa.check_types` decorator on functions)
- **Ecosystem hooks** — Great Expectations, dbt, FastAPI, Pydantic all integrate with pandera

### The `@pa.check_types` decorator

This is the killer feature. Decorate a function and pandera validates inputs and outputs automatically:

```python
from pandera.typing import DataFrame

@pa.check_types
def silver_orders(
    bronze: DataFrame[BronzeOrdersSchema],
    customers: DataFrame[CustomersSchema],
) -> DataFrame[SilverOrdersSchema]:
    ...
```

Now if `bronze` violates `BronzeOrdersSchema` on entry, or your function returns something violating `SilverOrdersSchema` on exit, pandera raises before any downstream code sees it. This is contract-by-construction.

### Gotchas

1. **`strict=True` is opt-in but should be your default.** Without it, pandera ignores extra columns silently — schema drift goes undetected. Always set `strict=True` unless you have a specific reason not to.
2. **`nullable=False` is the default for `pa.Column`** but `nullable=True` is the default for many `pa.Field()` configurations. Read the [docs page on nullable](https://pandera.readthedocs.io/en/stable/) once — these defaults will surprise you.
3. **pandera's int type doesn't accept NaN** because regular `int` can't hold NaN. Use pandas nullable `"Int64"` if you need integers + nullability (same lesson as Week 2 Day 1).
4. **Slow on huge DataFrames.** Pandera runs every check on every row by default. For million-row tables, sample first or use `pa.Check(..., element_wise=False)` for vectorized checks.
5. **`pa.Check` can wrap any boolean function** — `pa.Check(lambda s: s.str.contains("@"))` works. Useful for quick custom checks; for anything reused, write a named function.

### Exercises

Create `pipeline/schemas.py`.

1. Write a `pa.DataFrameSchema` for `customers.csv` covering: `customer_id` (int, unique, not null), `email` (str, nullable), `signup_date` (datetime), `country` (str, nullable, in a sensible set), `status` (str, in `{"active", "churned"}`, **not** nullable). Set `strict=True`.
2. Validate it: `customers_schema.validate(df)` — does it pass on your seed data? It shouldn't, because there's a customer with NULL `status`. Look at the error message — is it useful?
3. Convert your custom Week 2 validators (`assert_no_nulls`, `assert_unique`, `assert_in_set`) on the customers DataFrame into a single pandera schema. Compare the line counts.
4. Write a class-based version (`pa.DataFrameModel`) of the same customers schema. Run both — confirm they raise the same error on the same bad row.
5. Write schemas for `orders` and `order_items` too. Now decorate your `silver_orders` function from Week 3 with `@pa.check_types` so inputs and outputs are auto-validated. Run your existing tests — do they still pass?
6. **Trap exercise:** what happens if you remove `strict=True` from the customers schema and add an extra column to the seed CSV? Run validation. Does it fail? Why is `strict=True` essentially mandatory for catching schema drift?

### External practice

- [pandera — Getting Started](https://pandera.readthedocs.io/en/stable/) — short, well-organized
- [pandera — Lazy validation](https://pandera.readthedocs.io/en/stable/lazy_validation.html) — collect all errors instead of failing fast; useful for QA reports
- [pandera vs Great Expectations](https://medium.com/@noor.zaidi/pandera-vs-great-expectations-which-is-best-for-your-data-validation-needs-2024-update-2b0c87f5cc0c) — opinionated comparison; preview of Week 5

### Self-check (Day 2)

> Q2.1 — What does `strict=True` do on a `pa.DataFrameSchema`, and why is it essentially mandatory?
> Q2.2 — Write a one-line pandera Column declaration for "an integer column that's unique, not null, and always positive."
> Q2.3 — What's the practical difference between `pa.DataFrameSchema` (object-style) and `pa.DataFrameModel` (class-style)?
> Q2.4 — Your function returns a DataFrame that violates its declared output schema. With `@pa.check_types`, when does pandera catch this?

---

## Day 3 (Wed) — Volume & Freshness Checks

### Theory

Two of the most common production data bugs are:

1. **The pipeline didn't run** — yesterday's data is missing entirely. Tests pass on yesterday's *old* data.
2. **The pipeline ran but produced way fewer rows than usual** — data is "current" but suspiciously sparse, and downstream metrics quietly drop.

These map to **Timeliness** and **Completeness** in the dimension framework, but operationally they need their own dedicated tests because they're so common and so silent.

### Freshness checks

The pattern: assert that the **most recent timestamp** in the data is within an SLA window.

```python
from datetime import datetime, timedelta, timezone
import pandas as pd

def assert_fresh(df: pd.DataFrame, ts_col: str, max_age: timedelta) -> None:
    if df.empty:
        raise AssertionError(f"Dataset is empty — can't check freshness")
    latest = pd.to_datetime(df[ts_col]).max()
    age = datetime.now(timezone.utc) - latest.tz_localize("UTC") if latest.tzinfo is None else datetime.now(timezone.utc) - latest
    assert age <= max_age, f"Stale: latest {ts_col} = {latest}, age = {age}, max = {max_age}"
```

Note the timezone gymnastics — naive vs aware datetimes is the #1 freshness-test bug. Always normalize to UTC at the boundary.

### Volume checks

Two flavors:

**Absolute threshold** — "fail if today < N rows":
```python
def assert_min_rows(df, min_rows):
    assert len(df) >= min_rows, f"{len(df)} rows, expected ≥ {min_rows}"
```

Simple, but wrong over time — N gets stale as your business grows.

**Statistical drift** — "fail if today is unusual compared to recent history":
```python
import statistics

def assert_volume_normal(today: int, history: list[int], n_std: float = 3) -> None:
    if len(history) < 3:
        return  # not enough history to assert
    mean = statistics.mean(history)
    stdev = statistics.stdev(history) or 1   # avoid /0
    z = abs(today - mean) / stdev
    assert z <= n_std, f"Volume anomaly: today={today}, mean={mean:.0f}, z={z:.2f}"
```

Both have their place. Absolute thresholds for "we should never have fewer than 1 row"; statistical drift for "we should never have *unusual* row counts". Most teams need both.

### Gotchas

1. **Naive vs timezone-aware datetimes.** Mixing them raises `TypeError: Invalid comparison`. Force everything to UTC at ingestion. *Always*.
2. **`max()` on a column with NaN can return NaT** in pandas. Drop NaN first or use `.dropna().max()`.
3. **Statistical drift checks need history.** If your test computes the baseline from the same DataFrame it's testing, it's circular — you'll never catch a problem because the "baseline" includes the bug. History should come from external storage (a metrics table, a JSON file, observability backend).
4. **Watermark vs freshness aren't the same thing.** Watermark = "I won't accept data older than X" (Week 3 Day 2). Freshness check = "the data I have should be no older than X". Same number, different actor.
5. **Empty DataFrame edge case.** `df["ts"].max()` on an empty DataFrame returns `NaT`, and any comparison to `NaT` returns False — your assertion may silently pass on a totally empty dataset. Always check `if df.empty: fail` first.

### Exercises

Continue working in `pipeline/`. Add a `dq/` subfolder for the new check modules.

1. Create `dq/freshness.py` with `assert_fresh(df, ts_col, max_age)`. Test it against your `orders.csv` — does any row have an `order_date` within the last 30 days?
2. Add a `loaded_at` column to your bronze ingestion (use `pd.Timestamp.now(tz="UTC")`). Now write a freshness test asserting `loaded_at` is within the last 24 hours. Confirm it passes immediately after ingestion and fails after you sleep for a day (well — confirm in principle).
3. Write `assert_min_rows(df, n)` in `dq/volume.py`. Use it in `test_orders.py` to assert orders has at least 5 rows.
4. **Statistical volume drift:** create a small `history.json` with the last 7 days' row counts (make up plausible numbers like `[120, 115, 130, 125, 122, 118, 128]`). Write `assert_volume_normal(today, history, n_std=3)`. Test it both ways — pass with `today=124`, fail with `today=50`.
5. **Time zone trap:** make a naive datetime (`datetime(2024, 5, 1, 9, 0)`), make a UTC-aware one (`datetime(2024, 5, 1, 9, 0, tzinfo=timezone.utc)`), and try `naive - aware`. Observe the error. Now write a small helper `to_utc(dt)` that normalizes either form to UTC.
6. **Empty-DataFrame trap:** call `assert_fresh(empty_df, "ts", timedelta(hours=1))`. Does it fail correctly? If not, fix the function to handle the empty case explicitly.

### External practice

- [Great Expectations — concepts](https://docs.greatexpectations.io/docs/oss/core/define_expectations/freshness_expectations/) — freshness is a first-class GX concept (preview of Week 5)
- [Monte Carlo — Freshness, the most actionable signal](https://www.montecarlodata.com/blog-data-freshness/) — practical
- [Effective Python by Brett Slatkin — Item 53](https://effectivepython.com/) — datetime/timezone handling, if you want it deeply right

### Self-check (Day 3)

> Q3.1 — Why is "freshness" worth a dedicated test category instead of being lumped under "completeness"?
> Q3.2 — A volume drift test computes the mean and stdev from the DataFrame it's currently testing. What's the bug?
> Q3.3 — What's the right way to compare two datetimes when one is naive and one is timezone-aware?
> Q3.4 — `df["ts"].max()` on an empty DataFrame returns... what? And what does that imply for naive freshness checks?

---

## Day 4 (Thu) — Statistical Anomaly Basics

### Theory

Sometimes you don't know the right "valid range" for a column up front — you just know what *normal* looks like. Statistical anomaly detection lets the data tell you what's normal, then flags departures.

Two simple, robust methods:

#### Z-score

The number of standard deviations a value is from the mean:

```
z = (x - mean) / standard_deviation
```

Rule of thumb: `|z| > 3` is unusual (only ~0.27% of normally-distributed data exceeds this). For QA you might use `|z| > 4` to reduce false alarms.

```python
from scipy import stats
import numpy as np
import pandas as pd

def find_outliers_zscore(s: pd.Series, threshold: float = 3) -> pd.Series:
    s_clean = s.dropna()
    if len(s_clean) < 3:
        return pd.Series(dtype=s.dtype)
    z = np.abs(stats.zscore(s_clean))
    return s_clean[z > threshold]
```

#### IQR (Interquartile Range)

Robust alternative — doesn't assume a bell curve. Uses quartiles instead of mean/stdev.

- Q1 = 25th percentile, Q3 = 75th percentile, IQR = Q3 − Q1
- Outlier = below `Q1 − 1.5 × IQR` or above `Q3 + 1.5 × IQR`
- Multiplier 1.5 is the classic ("Tukey fences"). Use 3.0 for more conservative flagging.

```python
def find_outliers_iqr(s: pd.Series, k: float = 1.5) -> pd.Series:
    s_clean = s.dropna()
    q1, q3 = s_clean.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    return s_clean[(s_clean < lower) | (s_clean > upper)]
```

### When to use which

| | Z-score | IQR |
|---|---|---|
| Assumes distribution shape? | Roughly bell-shaped | None — robust to skew |
| Sensitive to existing outliers? | **Yes** — outliers inflate stdev, masking themselves | No — quartiles are robust |
| Best for | Symmetric continuous data (e.g. measurement noise) | Skewed data (e.g. revenue, durations, counts) |
| Threshold | `|z| > 3` (or 4) | `1.5 × IQR` (or 3) |

For most data engineering applications — revenue, latencies, row counts — IQR is the safer default.

### The critical caveat: outliers ≠ bugs

A statistical outlier is a value far from the rest. It is **not** the same as a bug. Real-world data has legitimate outliers all the time:

- Black Friday spikes in order volume
- A whale customer's order being 100× the median
- A measurement device hitting its max range

**Outlier detection should produce a *warning* or a *report*, not a hard test failure**, unless you've validated with stakeholders that any outlier is genuinely a bug. The right pattern in production is to *flag for review* — log the outliers somewhere visible, optionally alert, but don't block the pipeline.

### Gotchas

1. **Z-score is fragile when there are existing outliers** — they inflate the standard deviation, which raises the z-score threshold, which masks the outliers. Catch-22. IQR doesn't have this problem.
2. **Both methods need enough data.** With 5 data points, "outlier" is meaningless. Skip the check or fall back to fixed bounds.
3. **The 1.5 IQR multiplier is a convention, not a law.** It comes from John Tukey's original 1977 paper on box plots — it works well for "moderately" skewed data. For very skewed data, raise to 3.0.
4. **Outliers in time series often correlate with weekends, holidays, or marketing campaigns.** Make sure your "history" excludes known anomaly days, or partition by day-of-week.
5. **Don't use these for categorical or discrete data.** A z-score on `country` makes no sense. Use frequency-based anomaly detection instead (e.g. "any country with a count below 1% of total is suspicious").

### Exercises

1. Load `order_items.csv`. Use `find_outliers_zscore` and `find_outliers_iqr` on the `unit_price` column. Compare results — do they agree?
2. Load `orders.csv`. Same exercise on `total_amount`. Note: there's a NULL — your function should handle it.
3. Generate a synthetic dataset of 1000 normally-distributed values, then add 5 deliberate outliers. Run both methods. Which catches more? Are there false positives?
4. Repeat exercise 3 with a *skewed* synthetic distribution (e.g. exponential — `numpy.random.exponential(1, 1000)`). What do z-score and IQR say? Which is more sensible?
5. Write a small DQ check `assert_no_strong_outliers(s, k=3.0)` — using IQR with a generous multiplier — that fails on values *very* far outside the IQR fences. Run it on `order_items.unit_price`. Does it pass on the seed data?
6. **Reflection exercise:** for each of these columns in your seed data, would you write a hard outlier test, a flag-for-review check, or neither? Justify briefly: `customers.signup_date`, `orders.total_amount`, `products.price`, `order_items.quantity`.

### External practice

- [scipy.stats.zscore docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.zscore.html) — official, terse
- [Towards Data Science — outlier detection in pandas](https://towardsdatascience.com/) (search "outlier detection pandas") — many practical write-ups
- [Penn State STAT 415 — outliers](https://online.stat.psu.edu/stat415/) — if you want the statistics formally

### Self-check (Day 4)

> Q4.1 — Z-score and IQR both detect outliers. Name one situation where IQR is the safer choice.
> Q4.2 — Why is z-score said to be "self-defeating" in the presence of multiple outliers?
> Q4.3 — A statistical anomaly check fires every Black Friday. Is the test wrong, or is the data wrong?
> Q4.4 — You have a column with 8 values. Is z-score reliable? Is IQR? What should you do?

---

## Day 5 (Fri 🤖) — AI Workflow: Automated DQ Module Generation

### What you're learning today

Multi-file generation. Until now you've used AI for single files — one prompt, one output. Today you orchestrate the AI across **two coordinated files** (`dq_checks.py` + `test_dq.py`) with a single specification. This is the workflow that scales: it's how you build an entire test suite in 30 minutes that would otherwise take 4 hours.

If you're using **Cursor**, this is the use case for **Cursor Composer** (`Ctrl+Shift+I` / `Cmd+Shift+I`) — multi-file agent mode. If you're using Claude in browser, you'll just paste a longer prompt and copy outputs to multiple files. [Aider](https://aider.chat/) is a free CLI alternative that does similar multi-file coordination.

### Setup (~5 min)

In your project root, create `specs/dq_spec.md` with a clean specification:

```markdown
# Data Quality Module Specification

## Goal
Implement a reusable data quality module covering the 6 DQ dimensions for our
e-commerce dataset (customers, orders, order_items, products).

## Files to produce
- src/dq/checks.py      — reusable check functions, one per dimension
- src/dq/schemas.py     — pandera schemas for each table
- tests/test_dq.py      — pytest tests applying the checks/schemas

## Dimensions to cover
1. Completeness  — required columns, key columns, no-null rules
2. Uniqueness    — primary keys (customer_id, order_id, product_id, order_item_id)
3. Validity      — dtypes, value ranges, enums (status in {active, churned}, etc.)
4. Consistency   — order.total_amount reconciles with sum(order_items.quantity * unit_price)
5. Timeliness    — orders.order_date within the last 365 days (relax for our seed data)
6. Accuracy      — note as "manual / out of scope" with a stub function

## Conventions
- Type hints on every function
- Use pandera for schema-shaped checks
- Use plain functions for non-schema checks (reconciliation, freshness)
- Each check raises AssertionError with a useful message
- Tests use the conftest.py fixtures from Week 2/3
- Strict mode on schemas
```

### Exercise 1 — Multi-file generation

In Cursor Composer (or by pasting into Claude with both files attached):

> *"Read specs/dq_spec.md. Implement the three files described. Match the style and conventions of my existing src/validators.py and tests/pipeline/test_silver.py. Where checks belong to multiple dimensions, label them in a docstring. Don't reimplement existing validators — extend them."*

Take the output and **run it**: `pytest -v tests/test_dq.py`. Some tests will fail on the seed data (good — that's the point; the seed data has known issues). For each failure, decide:

- Real issue in seed data → test is correct
- Test is too strict / too loose → adjust
- Test is wrong → fix or ask the AI to fix

### Exercise 2 — Iterate on a single file

The first generation will be 80% right. Pick the file that needs the most work and iterate on it specifically:

> *"In src/dq/checks.py, the freshness check uses `datetime.now()` without a timezone — that breaks in CI on machines configured for non-UTC. Refactor to use `datetime.now(timezone.utc)` and handle naive timestamps in the input by assuming UTC."*

Notice how scoped follow-up prompts produce much better output than re-generating the whole module. **Iterate, don't regenerate** is the rule.

### Exercise 3 — Coverage analysis

Now ask the AI to look at the test file and tell you what's missing:

> *"Look at tests/test_dq.py and the seed data in customers.csv, orders.csv, etc. For each of the 6 DQ dimensions, list any rules that *could* be tested but aren't. Don't suggest implementations yet — just gaps."*

Read the gaps. Pick 2–3 that you actually want, and ask for implementations:

> *"Implement these three suggestions as additions to tests/test_dq.py. Use the existing fixture and validator patterns."*

### Update your `.cursorrules`

Add a Data Quality section:

```
Data Quality conventions:
- Every test maps to one of the 6 DQ dimensions: completeness, uniqueness,
  validity, consistency, timeliness, accuracy.
- Schema-shaped checks use pandera with strict=True.
- Non-schema checks (reconciliation, freshness, drift) are plain Python.
- Outlier detection is *flag-for-review*, not pipeline-blocking — log to stderr,
  don't raise.
- Freshness checks must handle empty DataFrames explicitly.
- All datetimes are UTC at ingestion; conversion only at the display layer.
```

### Quality bar — when is a multi-file AI generation "good"?

- [ ] All three files exist, are runnable, and import each other correctly
- [ ] No mock or placeholder code (no `# TODO: implement this`)
- [ ] Every function has a clear single purpose, mapped to one dimension
- [ ] At least one test fails on the seed data — meaning the tests are real, not toy
- [ ] No duplication between `checks.py` and your existing `validators.py`
- [ ] The code style matches your existing files (you can tell within 5 seconds it belongs)

### Reflection (write 3–5 sentences in `notes.md`)

- How was multi-file generation different from single-file?
- Where did the AI lose context across files? (Common: importing functions that don't exist yet, or duplicating logic between files.)
- How does Friday week 4 differ from Friday weeks 2 and 3? (Hint: the trajectory is single test → test suite → multi-file module. You're scaling up.)

---

## ✅ End of Month 1 Milestone

If you've completed Weeks 1–4 and the exercises in this file, you should now have:

- A SQL practice schema (Week 1) you can write data quality assertions against in your sleep
- A Python project (Weeks 2–4) with `pipeline/`, `dq/`, `tests/`, and `validators.py`
- A pytest suite running across **at least 5 of the 6 DQ dimensions**, with both hand-written and AI-scaffolded tests
- A small Bronze → Silver → Gold pipeline (Week 3) with tests at each layer
- A `.cursorrules` file four sections deep, capturing your conventions

That's the milestone. Save your project as a portfolio piece — even at this stage, it's better than what most candidates show in entry-level interviews.

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 5. 5–7 = re-review the weak day. <5 = redo exercises.

1. List the 6 dimensions of data quality.
2. Which dimension cannot be tested with just the data, and what does it require?
3. Write a one-line pandera Column for "a unique non-null integer column".
4. Why is `strict=True` essentially mandatory on a `pa.DataFrameSchema`?
5. What's the difference between a watermark and a freshness check?
6. A volume drift test fires on day 8 because today's count is 3 stdev below the mean of days 1–7. How do you tell if the test is wrong vs the data is wrong?
7. Why is z-score a poor choice for outlier detection on revenue data?
8. The IQR method uses what threshold, and what does the multiplier mean in plain English?
9. You ask Claude to generate a 3-file DQ module. The first draft has bugs. What's the rule of thumb for fixing them?
10. After the milestone, you have ~25 tests across the 6 dimensions. One day a test fails for the first time in 2 months. What's the first thing you check?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about data quality concepts. Try to answer aloud (or in writing) before peeking at "what a good answer covers".

### IQ1. "What are the dimensions of data quality? Walk me through one example test for each."

*What a good answer covers:*
- Six dimensions: completeness, uniqueness, validity, consistency, timeliness, accuracy. Acknowledge that the count varies by source — DAMA lists more, some lists fewer; the framework is the same.
- Examples (one per dimension):
  - **Completeness:** `customer_id` is non-null on every order
  - **Uniqueness:** `order_id` is unique
  - **Validity:** `status` is in `{"completed", "cancelled"}`
  - **Consistency:** `order.total_amount` equals `SUM(order_items.quantity * unit_price)`
  - **Timeliness:** `MAX(loaded_at)` is within the last 1 hour
  - **Accuracy:** sample 50 orders and verify the customer's email against the source system manually
- Highlight that accuracy is uniquely hard: it requires an external source of truth, which is why most automated frameworks focus on the other five

*Likely follow-up:* "Which of these is hardest to test, and why?" (Answer: accuracy — needs an external source of truth, can't be done with the data alone.)

### IQ2. "How would you validate that a DataFrame matches an expected schema in production?"

*What a good answer covers:*
- Use a schema validation library — pandera is the Python standard, Pydantic for non-DataFrame data, dbt YAML schemas for warehouse tables
- Define column names, dtypes, nullability, uniqueness constraints, value ranges, allowed values
- Set `strict=True` (in pandera) or equivalent — reject DataFrames with *extra* columns, not just missing or wrong ones. This is essential for catching schema drift.
- Validate at boundaries: input to a transformation function, output of an ingestion job. Not in the middle of a function.
- For long-running pipelines, the `@pa.check_types` decorator (or framework equivalent) lets you contractualize transformations with no runtime overhead in the function body

*Likely follow-up:* "What's the difference between schema validation and a unit test?" (Answer: schema validation is a *runtime* contract on the data shape; unit tests verify logic on small examples. They're complementary — schema validation catches "the data we got is wrong"; unit tests catch "the logic we wrote is wrong".)

### IQ3. "Walk me through how you'd detect a 'stale data' bug in a daily pipeline."

*What a good answer covers:*
- Two sub-problems: (1) the pipeline didn't run, (2) the pipeline ran but produced no fresh data
- For (1): job-status check at the orchestration layer (Airflow, GitHub Actions). Did the job exit successfully? Did it run within the last N hours?
- For (2): freshness assertion on the data itself — `MAX(loaded_at)` or `MAX(event_timestamp)` is within an SLA window. Pin the SLA to the business need (1 hour for ops dashboards, 24 hours for analytics)
- Critical edge case: empty dataset returns `NaT` from `MAX()`, and naive comparisons silently pass. Always check for empty first.
- Time zone: standardize everything to UTC at ingestion to avoid naive-vs-aware datetime bugs

*Likely follow-up:* "What if the pipeline appears to succeed but writes the same yesterday's data again?" (Answer: that's a *recency* bug, not a *job-status* bug. Catch it with a freshness check on the data, not on the job. This is exactly why both layers of test are needed.)

### IQ4. "How do you decide whether an outlier is a bug or legitimate data?"

*What a good answer covers:*
- Statistical outliers are not the same as bugs. Real data has legitimate outliers all the time — Black Friday, whale customers, edge cases.
- The right pattern in production: **flag for review**, don't fail the pipeline. Log to a monitoring channel, alert if there are many, but don't block.
- Use IQR (more robust to skewed data) over z-score (sensitive to existing outliers and assumes a bell curve) for most data engineering use cases
- Investigation pattern: when an outlier fires, look for context — what day was it? What customer? Was there a known event? Is the value plausible given the business?
- Hard outlier *bounds* (e.g. "no order can be > $1M") are different from statistical outliers — those *should* fail the pipeline because they violate a business invariant

*Likely follow-up:* "Give me a value of `total_amount` you'd consider 'definitely a bug' vs 'maybe interesting' for an e-commerce site." (Answer: definitely a bug — negative numbers, or values exceeding the product catalog's max possible. Maybe interesting — 10× the median, but plausible for a B2B order. The boundary is a business decision.)

### IQ5. "If you were designing a reusable data quality library for your team, how would you structure it?"

*What a good answer covers:*
- Organize by dimension, not by table — `checks/completeness.py`, `checks/uniqueness.py`, etc. Reusable across datasets.
- Two layers: **schema-based** (pandera or equivalent — declarative, table-shaped) and **rule-based** (Python functions for cross-table reconciliation, statistical drift, etc.)
- Conventions: every check returns/raises consistently (e.g. raises `AssertionError` with a useful message; or returns a structured `CheckResult` for reporting). Pick one and stick with it.
- Provide both a "fail fast" mode (first failure stops the pipeline) and a "collect all failures" mode (run everything, report a list — pandera's `lazy=True` does this).
- Document the dimension each check maps to. This is what makes the library *understandable* over time.
- Version it. Treat it like real internal infrastructure — semver, tests on the tests, examples folder.

*Likely follow-up:* "How do you balance generic reusability with team-specific business rules?" (Answer: split into two layers — a generic dimension-based library (open-sourceable) plus a team-specific business-rule layer that uses the generic one. Don't pollute the reusable side with project specifics.)

---

## If you have extra time this week (stretch)

- Read the [Great Expectations docs intro](https://docs.greatexpectations.io/docs/oss/core/define_expectations/expectations/) — preview of Week 5; you'll see how a full DQ framework formalizes everything you wrote this month
- Try porting one pandera schema to Pydantic v2 — different framework, similar idea, different ergonomics
- Skim DAMA-DMBoK chapter 13 (Data Quality) if your library has it — it's the canonical reference and will give you vocabulary that lands well with senior data folks

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Completeness, uniqueness, validity, consistency, timeliness, accuracy.
- **Q1.2** — Accuracy. It requires comparing the data to an external source of truth — sample audit, system-of-record reconciliation, or trusted reference data — because the data itself can't tell you whether it matches reality.
- **Q1.3** — (a) Validity (regex format check). (b) Volume / Timeliness (drift against historical baseline). (c) Consistency (referential integrity across tables).
- **Q1.4** — Because the dimensions overlap and exact taxonomy varies. The point is having a complete *checklist* when designing tests, not arguing about whether "conformity" is a separate dimension or a subset of "validity".

### Day 2 answers

- **Q2.1** — `strict=True` rejects DataFrames containing columns not declared in the schema. Without it, schema drift (a new column added upstream) goes undetected — your tests pass against a silently-changed shape.
- **Q2.2** — `pa.Column(int, unique=True, nullable=False, checks=pa.Check.greater_than(0))`.
- **Q2.3** — Functionally identical. `pa.DataFrameSchema` is a runtime object you build with constructor calls. `pa.DataFrameModel` is a class with type-annotated fields. The class style works better with IDEs and static analysis; the object style is easier to construct dynamically.
- **Q2.4** — At the moment the function returns. The decorator wraps the function so on entry it validates inputs against their declared schemas, and on exit it validates the return value. A violation raises `pandera.SchemaError`.

### Day 3 answers

- **Q3.1** — Because freshness has its own failure mode that other dimensions don't: the data is *complete and valid*, but *outdated*. A test for completeness can pass on yesterday's data; a freshness test specifically catches "yesterday's data is here today".
- **Q3.2** — It's circular — the bug is in the data being tested, but the baseline is also from the data being tested, so the bug is averaged into "normal". Use external history.
- **Q3.3** — Convert one to match the other. `aware - naive` raises `TypeError`. Force everything to UTC at the boundary, or explicitly localize: `naive.replace(tzinfo=timezone.utc)` if you know it represents UTC.
- **Q3.4** — Returns `NaT`. Comparing `NaT` to anything (e.g. `NaT < some_threshold`) returns `False`, which means the assertion silently passes on an empty DataFrame. Always handle empty explicitly: `if df.empty: raise`.

### Day 4 answers

- **Q4.1** — When data is skewed (revenue, durations, request counts). IQR uses quartiles, which are robust to skew; z-score assumes a roughly bell-shaped distribution.
- **Q4.2** — Outliers inflate the standard deviation, which is the denominator of the z-score — so the same outliers' z-scores stay below threshold. The presence of outliers masks them.
- **Q4.3** — Neither. The data is *legitimate but unusual*. The test is doing what it should — flagging the unusual point. The right action is to *acknowledge*, not pass or fail. This is why outlier detection should be flag-for-review, not pipeline-blocking.
- **Q4.4** — Neither is reliable with so few points. Either skip the check (return early) or use a fixed business-defined bound instead of a statistical one.

### End-of-week answers

**A1.** Completeness, uniqueness, validity, consistency, timeliness, accuracy.

**A2.** Accuracy — it requires comparing data to an external source of truth (a system-of-record, a sample audit, or a trusted reference dataset).

**A3.** `pa.Column(int, unique=True, nullable=False)`.

**A4.** Without `strict=True`, pandera ignores extra columns in the DataFrame — schema drift (an upstream-added column) goes undetected and tests still pass.

**A5.** A watermark is the upstream rule "I won't accept events older than X". A freshness check is the downstream assertion "the data I have should be no older than X". Same number, different actor — one rejects late data; the other validates that recent data has arrived.

**A6.** Investigate before reacting: was today a known event (Black Friday, holiday)? Did upstream change something? Look at the actual data for the day. If it's a real anomaly, alert the data owner; if the test is too strict for legitimate variation, widen the threshold or move to flag-for-review.

**A7.** Revenue is heavily right-skewed (most orders small, a few huge), so it's not roughly bell-shaped — z-score's normality assumption fails. IQR is robust to skew and a better fit.

**A8.** Outliers are values below `Q1 − 1.5 × IQR` or above `Q3 + 1.5 × IQR`. The 1.5 multiplier is Tukey's "inner fence" convention — it flags moderately unusual values. Multiplier of 3.0 is the "outer fence" — only the most extreme. In plain English: "more than 1.5 IQRs outside the middle 50% of the data".

**A9.** Iterate, don't regenerate. Scoped follow-up prompts ("fix this specific function") produce better output than asking the whole module to be rewritten.

**A10.** Look at the data first, the test second. The test has been stable for 2 months — by far the most likely explanation is that something in the *data* changed, not that the test is suddenly wrong. Schema drift, upstream rerun, holiday, business change.

---

*Done with Week 4? You've finished Month 1. By now, the language of data quality should feel natural — every test you write maps to a dimension, every dimension has a tool, and the AI workflow from single-file to multi-file is fluent. Onward to Month 2 (Frameworks & Tools), starting with Great Expectations — the industry-standard DQ framework that formalizes everything you've built by hand.*
