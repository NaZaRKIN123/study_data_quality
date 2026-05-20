# Week 5 — Great Expectations | Training Materials

> **Companion to:** Week 5 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Learn the industry-standard data testing framework — install it, build a Suite, run a Checkpoint, view Data Docs. By Friday you'll have a stakeholder-shareable HTML quality report for the e-commerce dataset.

> **A note on versions:** Great Expectations had a major rewrite for **1.0** (released 2024). Most tutorials older than late 2024 are written against the 0.18.x API and the code won't run on current GX. Everything in this week's materials is written against **GX 1.x** (latest at time of writing: 1.17.1). If a tutorial you find online uses `context.sources.add_pandas` instead of `context.data_sources.add_pandas`, or imports things like `BaseDataContext`, you're looking at the old API. Stop and find a 1.x source. Citation: [GX PyPI release page](https://pypi.org/project/great-expectations/) and [official Try GX Core walkthrough](https://docs.greatexpectations.io/docs/core/introduction/try_gx/).

---

## How to use this file

- This is the start of Month 2 (Frameworks & Tools). The pattern shifts: less Python you write, more configuration of an existing framework
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday is **suite generation with AI** — the natural fit for a verbose framework
- Answers to all self-checks are at the bottom of the file

---

## One-time setup (~10 minutes)

You'll continue using the project from Weeks 2–4. Add Great Expectations:

```bash
source .venv/bin/activate
pip install great_expectations
```

Sanity check:
```bash
python -c "import great_expectations as gx; print(gx.__version__)"
```

You should see `1.x.x` (anything `0.x.x` is the legacy line and the code in this week won't work — `pip install --upgrade great_expectations`).

Create a folder for GX project files:
```bash
mkdir gx_project
```

GX needs a place to store metadata, suites, checkpoints, and Data Docs. We'll point it at this folder.

---

## Day 1 (Mon) — Install & Core Concepts

### Theory — the GX vocabulary

GX has a lot of nouns. They're worth learning in order, because each builds on the last.

| Concept | What it is | Analogy |
|---|---|---|
| **Data Context** | The root object for a GX project — manages config, suites, checkpoints | Like a pytest `conftest.py` for GX |
| **Data Source** | A connection — pandas, SQL, Spark, etc. | Like a database connection |
| **Data Asset** | A specific table / DataFrame / file under a Data Source | Like a table |
| **Batch Definition** | How to slice the asset into batches (whole table, by date partition, etc.) | Like a query template |
| **Batch** | The actual data being validated, materialized at runtime | Like the result of running a query |
| **Expectation** | One declarative assertion (e.g. "column X is unique") | Like a single `assert` statement |
| **Expectation Suite** | A collection of Expectations | Like a test file (collection of asserts) |
| **Validation Definition** | Pairs a Batch Definition with a Suite | Like "run *this suite* against *this data*" |
| **Checkpoint** | Runs Validation Definitions, triggers actions (alerts, Data Docs updates) | Like a CI job that runs tests |
| **Data Docs** | Auto-generated HTML reports of results | Like the `pytest --html=report.html` output, on steroids |

The first time through, this hierarchy feels *massive* compared to pandera. The benefit appears on Day 4 when one Checkpoint runs hundreds of expectations across multiple data sources and produces a single shareable HTML report. The cost is the upfront ceremony.

### The minimum end-to-end (one expectation, one batch)

```python
import great_expectations as gx
import pandas as pd

# 1. Get a Data Context (in-memory for this example)
context = gx.get_context()

# 2. Define a Data Source and Asset
data_source = context.data_sources.add_pandas("ecommerce_pandas")
data_asset = data_source.add_dataframe_asset(name="orders")

# 3. Define how to slice (the whole DataFrame as one batch)
batch_definition = data_asset.add_batch_definition_whole_dataframe("orders_batch")

# 4. Load your data and build a Batch at runtime
df = pd.read_csv("orders.csv")
batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

# 5. Define an Expectation
expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column="total_amount",
    min_value=0,
    max_value=10_000,
)

# 6. Validate
result = batch.validate(expectation)
print(result.success)        # True or False
print(result.describe())     # human-readable summary
```

Run this against your `orders.csv`. The expectation passes — total amounts are within range. Now change `min_value=0` to `min_value=100` and re-run. It should fail. Look at `result.describe()` — that's GX telling you which rows failed and how.

### Gotchas

1. **Context types matter.** `gx.get_context()` with no arguments creates an *ephemeral* (in-memory) context — fine for scripts and learning. For real projects, use `gx.get_context(mode="file", project_root_dir="./gx_project")` to persist suites and configs to disk.
2. **The 1.x vs 0.x split is brutal.** Old code uses `context.sources` (no underscore), `context.add_or_update_checkpoint(...)`, `validator` objects, and a JSON-based suite editing flow. None of that works in 1.x. If you're stuck, check the import lines and method names against the [Try GX Core walkthrough](https://docs.greatexpectations.io/docs/core/introduction/try_gx/).
3. **Pandas is the easiest backend.** SQL and Spark backends exist but require more setup. For learning, stick with pandas.
4. **Expectations are immutable classes.** You instantiate them once (`gx.expectations.ExpectXyz(...)`) and they're configurable but not stateful. Add them to a suite to compose.
5. **`batch.validate(expectation)` validates one expectation.** For multiple, you build a Suite (Day 3) and validate the suite via a Checkpoint (Day 4).

### Exercises

Create `gx_practice/day1.py`.

1. Set up an in-memory Data Context. Print it.
2. Add a pandas Data Source called `"ecom"`, an Asset for orders, a Batch Definition, and a Batch built from your `orders.csv`.
3. Validate one expectation: `ExpectColumnValuesToNotBeNull(column="order_id")`. Print the result. Does it pass?
4. Validate `ExpectColumnValuesToBeUnique(column="order_id")`. Pass?
5. Validate `ExpectColumnValuesToBeInSet(column="status", value_set=["completed", "cancelled"])`. Pass?
6. **Compare the output formats.** Print `result` (raw), then `result.success` (bool), then `result.describe()` (human-readable summary). Which one would you log in CI? Which would you pass to a stakeholder?

### External practice

- [Try GX Core walkthrough](https://docs.greatexpectations.io/docs/core/introduction/try_gx/) — official, current (1.x)
- [DataCamp — Great Expectations Tutorial (2024)](https://www.datacamp.com/tutorial/great-expectations-tutorial) — readable, written against 1.x
- [Expectation Gallery](https://greatexpectations.io/expectations/) — the catalog of all built-in expectations

### Self-check (Day 1)

> Q1.1 — In one sentence, what does a Data Context do?
> Q1.2 — Why does GX separate "Data Asset" from "Batch Definition"?
> Q1.3 — Without running the code, predict: does `ExpectColumnValuesToNotBeNull(column="email")` pass on your `customers.csv`? Why?
> Q1.4 — A tutorial you find online has the line `validator = context.sources.add_pandas(...).read_dataframe(df)`. Does this work in GX 1.x?

---

## Day 2 (Tue) — Built-in Expectations

### Theory

GX ships with ~50 built-in expectations covering most QA needs out of the box. They map cleanly to the 6 dimensions you learned in Week 4. **Browse the [Expectation Gallery](https://greatexpectations.io/expectations/) once** — knowing what exists saves you from reinventing wheels.

### Common expectations by dimension

**Completeness:**
- `ExpectColumnValuesToNotBeNull(column=...)`
- `ExpectColumnValuesToBeNull(column=...)` — for columns that *should* be all null (e.g. `deleted_at` in active records)
- `ExpectTableRowCountToBeBetween(min_value=..., max_value=...)`
- `ExpectColumnToExist(column=...)`

**Uniqueness:**
- `ExpectColumnValuesToBeUnique(column=...)`
- `ExpectCompoundColumnsToBeUnique(column_list=[...])` — composite key uniqueness

**Validity:**
- `ExpectColumnValuesToBeInSet(column=..., value_set=[...])` — enums
- `ExpectColumnValuesToBeBetween(column=..., min_value=..., max_value=...)` — numeric range
- `ExpectColumnValuesToMatchRegex(column=..., regex=...)` — string format
- `ExpectColumnValuesToBeOfType(column=..., type_=...)` — dtype check
- `ExpectTableColumnsToMatchSet(column_set=[...])` — schema match
- `ExpectColumnValueLengthsToBeBetween(column=..., min_value=..., max_value=...)`

**Consistency:**
- `ExpectColumnPairValuesAToBeGreaterThanB(column_A=..., column_B=...)` — e.g. `end_date >= start_date`
- `ExpectMulticolumnSumToEqual(column_list=[...], sum_total=...)` — line items sum to total

**Distribution / statistical:**
- `ExpectColumnMeanToBeBetween(...)`, `ExpectColumnMedianToBeBetween(...)`
- `ExpectColumnStdevToBeBetween(...)`
- `ExpectColumnKLDivergenceToBeLessThan(...)` — drift detection

There are also **table-level** expectations (no `column=` argument): row count, column set, column count.

### A concrete example — multiple expectations on one batch

```python
import great_expectations as gx
import pandas as pd

context = gx.get_context()
df = pd.read_csv("orders.csv")

ds = context.data_sources.add_pandas("ecom")
asset = ds.add_dataframe_asset(name="orders")
bd = asset.add_batch_definition_whole_dataframe("batch_def")
batch = bd.get_batch(batch_parameters={"dataframe": df})

# Try several expectations one at a time
expectations = [
    gx.expectations.ExpectColumnToExist(column="order_id"),
    gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id"),
    gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"),
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="status", value_set=["completed", "cancelled"]
    ),
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="total_amount", min_value=0, max_value=10_000
    ),
]

for exp in expectations:
    r = batch.validate(exp)
    status = "PASS" if r.success else "FAIL"
    print(f"{status}: {type(exp).__name__}({exp.column if hasattr(exp, 'column') else ''})")
```

This is fine for learning. For production, you'd pack these into an Expectation Suite (Day 3) instead of looping individually.

### The `auto=True` parameter (use carefully)

Many expectations accept `auto=True`, which makes GX *infer* parameters from the batch:

```python
exp = gx.expectations.ExpectColumnValuesToBeBetween(column="total_amount", auto=True)
```

GX looks at the data and picks `min_value` / `max_value` from observed range. **This is a profiling shortcut, not production code** — if your batch happens to contain the only bug in your dataset's history, the inferred range will accept the bug. Use `auto=True` to *suggest* values, then write them in explicitly.

### Gotchas

1. **Expectation parameter names changed in 1.x.** Some old tutorials use `value_set` for sets, others use `column_value_set`. The current API uses `value_set`. When in doubt, check the [Expectation Gallery](https://greatexpectations.io/expectations/) — every expectation page lists current parameters.
2. **"between" expectations are inclusive on both ends.** `min_value=0, max_value=10_000` includes 0 and 10000. If you want strict, use the explicit comparison expectations.
3. **`ExpectColumnValuesToBeOfType` is finicky** because dtype representations vary across pandas, NumPy, and Arrow. Sometimes you need `type_="int64"`; sometimes `"INTEGER"`. Check the gallery; or skip this and rely on schema-match expectations.
4. **Most expectations support `mostly=`** — `mostly=0.95` means "at least 95% of values must satisfy this". Useful when you have known bad rows you can't fix immediately.
5. **Empty DataFrames pass most expectations vacuously.** Always pair with a row-count expectation.

### Exercises

1. For your `customers.csv`, write one expectation per dimension (6 total). At least one should fail on the seed data — call out which and why.
2. Use `auto=True` on `ExpectColumnValuesToBeBetween` for `orders.total_amount`. Print the inferred bounds. Now write the same expectation with explicit values you'd be comfortable defending to a business owner. Is the inferred range too tight or too loose?
3. Use `ExpectCompoundColumnsToBeUnique(column_list=["order_id", "product_id"])` on your `order_items.csv`. Does it pass?
4. Use `ExpectMulticolumnSumToEqual` to check whether `quantity * unit_price` summed across line items per order equals the order total. (Hint: this requires a pre-aggregation step in pandas first; GX won't do the join for you.)
5. Use `mostly=0.9` to allow up to 10% NULLs in `customers.country`. Confirm it now passes.
6. **Coverage exercise:** open the [Expectation Gallery](https://greatexpectations.io/expectations/). Find three expectations you didn't know existed and could see using. Note them in your `notes.md`.

### External practice

- [Expectation Gallery](https://greatexpectations.io/expectations/) — your reference for the rest of the week
- [DataCamp Tutorial](https://www.datacamp.com/tutorial/great-expectations-tutorial) — has a clean walkthrough using common expectations

### Self-check (Day 2)

> Q2.1 — Name three expectations you'd use for a "validity" dimension test on a string column.
> Q2.2 — What does `mostly=0.95` do in an expectation?
> Q2.3 — Why is `auto=True` a learning shortcut rather than a production pattern?
> Q2.4 — An empty DataFrame passes `ExpectColumnValuesToNotBeNull(column="x")`. Why? What second expectation would catch that?

---

## Day 3 (Wed) — Expectation Suites

### Theory

An **Expectation Suite** is a named collection of expectations, persisted across runs. Two main reasons to use suites instead of validating expectations one at a time:

1. **Reusability** — define once, run against many batches (today's data, tomorrow's, next week's)
2. **Discoverability** — your suite is the documentation of "what we expect from this dataset"

Suites are stored in your Data Context. With a `mode="file"` context they live as files inside `gx_project/expectations/`. With an ephemeral context they live only for the script's lifetime.

### Building and running a suite

```python
import great_expectations as gx
import pandas as pd

context = gx.get_context(mode="file", project_root_dir="./gx_project")

# 1. Create or load a suite
suite_name = "orders_dq_suite"
try:
    suite = context.suites.get(suite_name)
except Exception:
    suite = gx.ExpectationSuite(name=suite_name)
    suite = context.suites.add(suite)

# 2. Add expectations to the suite
suite.add_expectation(gx.expectations.ExpectColumnToExist(column="order_id"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id"))
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"))
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="status", value_set=["completed", "cancelled"]
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="total_amount", min_value=0, max_value=10_000
    )
)

# 3. Set up a Data Source / Asset / Batch Definition (same as Day 1)
df = pd.read_csv("orders.csv")
ds = context.data_sources.add_pandas("ecom") if "ecom" not in [d.name for d in context.data_sources.all()] else context.data_sources.get("ecom")
asset = ds.add_dataframe_asset(name="orders") if "orders" not in [a.name for a in ds.assets] else ds.get_asset("orders")
bd = asset.add_batch_definition_whole_dataframe("orders_bd")

# 4. Validate the entire suite against a batch
batch = bd.get_batch(batch_parameters={"dataframe": df})
result = batch.validate(suite)

# 5. Read results
print(f"Suite passed: {result.success}")
print(f"Expectations: {result.statistics}")
for r in result.results:
    if not r.success:
        print(f"FAIL: {r.expectation_config.type} — {r.result}")
```

The "is this in our context already?" boilerplate (step 3) is awkward but real — re-running a script with `add_pandas("ecom")` on a name that already exists raises an error. In practice you wrap this in a helper.

### Two ways to run a suite

GX supports two style for running a suite:

1. **`batch.validate(suite)`** — the inline style above. Useful in scripts, notebooks, debugging.
2. **Validation Definition + Checkpoint** — the production style (Day 4). Decouples *what to validate* from *when and how to act on results*.

For exploratory work, prefer #1. For pipelines and CI, prefer #2.

### Gotchas

1. **`context.suites.add()` raises if the suite name already exists.** The defensive try/except pattern above handles this. Some teams use a wrapper helper that does "get_or_create".
2. **`suite.add_expectation()` doesn't deduplicate.** Adding `ExpectColumnValuesToNotBeNull(column="x")` twice gives you two copies. Be careful when scripting this.
3. **Suites are stored under their name — overwriting is silent.** Recreating a suite with the same name replaces the old one. Use version-aware names (`orders_dq_suite_v2`) if that matters.
4. **The `result.results` list contains one entry per expectation.** Each has `.success`, `.expectation_config`, `.result` (the data), and `.exception_info` (if it crashed). For CI logging, iterate and log failures only.
5. **A suite passing doesn't mean your data is good.** It means your data passed *the rules you wrote*. If your rules are weak, the suite will pass on bad data. (Same lesson as Week 4: a passing test on wrong data is *valid but inaccurate*.)

### Exercises

Switch to a file-based context now: `context = gx.get_context(mode="file", project_root_dir="./gx_project")`.

1. Create a suite `customers_dq_suite` with at least 6 expectations spanning all 6 DQ dimensions.
2. Validate the suite against `customers.csv`. Print pass/fail per expectation with a one-line summary.
3. Create a second suite `orders_dq_suite` with at least 6 expectations.
4. **Inspect the project folder.** Look inside `gx_project/`. What files were created? Where are the suites stored? What format?
5. **Reload from disk:** in a *new* Python session, run `context = gx.get_context(mode="file", project_root_dir="./gx_project")` and `context.suites.get("customers_dq_suite")`. Confirm it persisted.
6. **Edit a suite:** add one new expectation to `customers_dq_suite` and save. Verify the file on disk changed (timestamp or content diff).
7. **Trap exercise:** try to add an expectation that's already in the suite. What happens? Does GX deduplicate? What's the implication for re-running scripts?

### External practice

- [GX Core docs — Create Expectations](https://docs.greatexpectations.io/docs/core/define_expectations/create_an_expectation/) — official, current
- [Pratush Maheshwari — practical GX tutorial (Medium, 2025)](https://medium.com/@pratushmaheshwari/mastering-data-quality-with-great-expectations-a-practical-guide-with-pandas-spark-postgres-1773cc9a22b5) — written against 1.x

### Self-check (Day 3)

> Q3.1 — What's the difference between an Expectation, an Expectation Suite, and a Validation Result?
> Q3.2 — You re-run your suite-creation script. Does GX deduplicate, replace, or add?
> Q3.3 — Where on disk are suites stored when using a file-based context?
> Q3.4 — A suite returns `success=True`. What can you safely conclude about the data? What can you not?

---

## Day 4 (Thu) — Checkpoints & Data Docs

### Theory

A **Checkpoint** is "run a Validation Definition (or several) and do something with the results." That "something" is configurable — most commonly, regenerate Data Docs (the HTML report) and optionally trigger alerts.

This is the production-style workflow. Days 1–3 were exploratory; today's is the version that goes into a CI job or an Airflow DAG.

### The full pipeline (in code)

```python
import great_expectations as gx
from great_expectations.checkpoint import UpdateDataDocsAction
import pandas as pd

context = gx.get_context(mode="file", project_root_dir="./gx_project")

# Assume suite + data source + asset + batch definition already created
suite = context.suites.get("orders_dq_suite")
asset = context.data_sources.get("ecom").get_asset("orders")
bd = asset.get_batch_definition("orders_bd")

# 1. Validation Definition: pairs a batch definition with a suite
val_def = gx.ValidationDefinition(
    name="orders_validation",
    data=bd,
    suite=suite,
)
val_def = context.validation_definitions.add_or_update(val_def)

# 2. Checkpoint: runs validation definitions and triggers actions
checkpoint = gx.Checkpoint(
    name="orders_checkpoint",
    validation_definitions=[val_def],
    actions=[UpdateDataDocsAction(name="update_data_docs")],
)
checkpoint = context.checkpoints.add_or_update(checkpoint)

# 3. Run it
df = pd.read_csv("orders.csv")
result = checkpoint.run(batch_parameters={"dataframe": df})
print(f"Checkpoint passed: {result.success}")

# 4. Open Data Docs
context.open_data_docs()   # opens HTML in your default browser
```

After running, look at `gx_project/uncommitted/data_docs/local_site/index.html`. You'll see a navigable HTML site listing every suite, every validation run, and every result. **This is what makes GX worth its weight** for stakeholder-facing work — non-technical users can browse "what tests we run, when they ran, what passed".

### Why bother with Validation Definitions?

It feels like ceremony — a Checkpoint that wraps Validation Definitions that wrap Suite + Batch Definition pairs. But each level is doing real work:

- **Suite** = what to check (data-agnostic)
- **Batch Definition** = where the data is (suite-agnostic)
- **Validation Definition** = a specific (suite, batch) pair
- **Checkpoint** = a runnable bundle of Validation Definitions plus actions

The payoff is composability. You can have one suite reused across five Batch Definitions (orders today, orders yesterday, orders archive), each producing its own Validation Definition, all run in one Checkpoint.

### Common Checkpoint actions

- `UpdateDataDocsAction` — regenerate the HTML report
- `SlackNotificationAction` — post results to Slack
- `EmailAction` — email the results
- `OpsgenieAlertAction` — fire an Opsgenie alert

You compose them. A typical production Checkpoint has Data Docs + Slack on failure.

### Gotchas

1. **Data Docs are static HTML in a local folder by default.** For team sharing, configure a remote site (S3, GCS, Azure Blob). The default is fine for solo work and CI artifact uploads.
2. **`context.open_data_docs()` requires a graphical desktop.** In CI, skip this — instead, archive `gx_project/uncommitted/data_docs/local_site/` as a build artifact.
3. **Checkpoints don't fail your script by default.** A failed validation produces `result.success = False`, but your Python script keeps running. In CI, wrap with `assert result.success` or check the exit code yourself.
4. **The `batch_parameters` dict at runtime is required when the asset is a DataFrame asset.** For SQL or file assets, the data lookup is automatic.
5. **Re-running the same Checkpoint with different data is correct usage.** That's the design — Checkpoints are stable test plans; data flows through.

### Exercises

1. Build a Validation Definition pairing your `orders_dq_suite` with the `orders` Batch Definition.
2. Build a Checkpoint with one action: `UpdateDataDocsAction`. Run it.
3. Open Data Docs in your browser (`context.open_data_docs()`). Navigate around — find your suite, find the validation run, drill into the per-expectation results.
4. **Multi-suite Checkpoint:** add a second Validation Definition for `customers_dq_suite` against `customers.csv`. Run them both in one Checkpoint. The Data Docs index page should now show two suites.
5. **CI-style assertion:** wrap the Checkpoint run in a script that exits with non-zero status if `result.success` is False. Run it once with the data as-is, and once after deliberately breaking the data (e.g. set `total_amount` to `-1` for one row). Confirm the exit codes differ.
6. **Data Docs as artifact:** zip `gx_project/uncommitted/data_docs/local_site/` and imagine attaching it to a Slack message or a PR comment. This is the real value over plain pytest output.

### External practice

- [GX docs — Validation Definitions](https://docs.greatexpectations.io/docs/core/run_validations/) — current 1.x docs
- [GX docs — Checkpoints overview](https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/create_a_checkpoint_with_actions/) — actions and configuration

### Self-check (Day 4)

> Q4.1 — What's the relationship between a Suite, a Validation Definition, and a Checkpoint?
> Q4.2 — A Checkpoint runs and `result.success` is False. By default, does your Python script exit with non-zero status?
> Q4.3 — What's the production deployment story for Data Docs (i.e., how does your team actually see them)?
> Q4.4 — Why does GX have *Validation Definitions* as a separate concept instead of just letting Checkpoints take a (Suite, Batch) pair directly?

---

## Day 5 (Fri 🤖) — AI Workflow: Auto-Generate Expectation Suites

### What you're learning today

Suite generation. Building an Expectation Suite by hand for a new dataset is tedious and error-prone — you have to enumerate every column, decide on every rule, tune every threshold. It's the perfect work to bootstrap with AI: the first draft is 80% mechanical (the column-by-column expectations), and you can focus on the 20% that requires business knowledge (specific ranges, allowed sets, custom rules).

### Setup (~5 min)

Have a sample of one of your CSVs ready (the first ~20 rows is enough). Open Claude or your AI tool of choice.

### Exercise 1 — From sample data to Suite code

Paste the first 20 rows of `customers.csv` (header + data) into Claude with this prompt:

> *"You are generating a Great Expectations 1.x Suite for the dataset below. For each column, write expectations covering: existence, dtype, nullability, uniqueness if applicable, value-in-set for enums, value-in-range for numerics, regex for emails. Output complete Python code using `gx.expectations.ExpectXyz(...)` calls and `suite.add_expectation(...)`. Use the GX 1.x API, not the legacy 0.x. The suite name should be `customers_auto_suite`."*

Read the output critically. Common issues:

- The AI may pick `auto=True` everywhere — push back, ask for explicit values
- Date columns may get inappropriate range expectations — fix or drop them
- The AI may invent expectations that don't exist (`ExpectColumnToBeUtcTimestamp` is not real)
- Old-API code may sneak in (using `validator.expect_xyz(...)` style instead of `gx.expectations.ExpectXyz(...)`) — ask explicitly for 1.x API only

Run the generated code against your full `customers.csv`. How many expectations? How many fail?

### Exercise 2 — Profile-then-suggest

A more sophisticated workflow: profile the dataset first, give the profile to the AI, and ask for ranges grounded in the actual data:

```python
import pandas as pd
df = pd.read_csv("orders.csv")

profile = {
    "shape": df.shape,
    "dtypes": df.dtypes.astype(str).to_dict(),
    "nulls_per_col": df.isna().sum().to_dict(),
    "uniques_per_col": df.nunique().to_dict(),
    "numeric_summary": df.describe().to_dict(),
    "sample_values": {c: df[c].dropna().head(3).tolist() for c in df.columns},
}
print(profile)
```

Paste the printed `profile` dict into Claude:

> *"Given this dataset profile, generate a GX 1.x Expectation Suite. Use the actual observed ranges as a starting point but tighten them slightly to flag bugs (e.g. if total_amount is observed 0–500, set min=0 max=600 to allow growth). Do NOT use auto=True — set explicit values. Suite name: orders_dq_suite_ai."*

This pattern — **profile first, then ask for grounded suggestions** — produces much better suites than naïve "look at this data" prompts. The AI now has *numeric* context, not just sample rows.

### Exercise 3 — Coverage analysis

Once you have an AI-generated suite, ask the AI to critique its own work:

> *"Review the suite you just generated. For each of the 6 DQ dimensions (completeness, uniqueness, validity, consistency, timeliness, accuracy), tell me whether the suite covers it, and if not, what kind of expectation would close the gap."*

Self-critique catches gaps. Add the missing dimensions manually if they require business context.

### Update your `.cursorrules`

Add a GX section:

```
Great Expectations conventions:
- Always use the GX 1.x API. Never `context.sources` (with no underscore),
  never `validator.expect_xyz`, never `add_or_update_checkpoint(...)`.
- Use `gx.expectations.ExpectXyz(column=..., ...)` to define expectations.
- Build suites via `suite.add_expectation(expectation_obj)`.
- Use file-based contexts (`mode="file"`, `project_root_dir="./gx_project"`)
  for anything beyond throwaway scripts.
- Set explicit values for ranges; never use `auto=True` in committed code.
- Pair every range/null/unique expectation with a row-count expectation —
  empty DataFrames pass most expectations vacuously.
```

### Quality bar — when is an AI-generated Suite "good"?

- [ ] Uses GX 1.x API exclusively (no `validator.expect_xyz` style)
- [ ] One expectation per dimension per relevant column
- [ ] No `auto=True` — all values explicit
- [ ] Includes a row-count expectation
- [ ] Each expectation has thresholds you can defend to a stakeholder
- [ ] No invented expectation names (cross-check against the [Gallery](https://greatexpectations.io/expectations/))

### Reflection (write 3–5 sentences in `notes.md`)

- How did "profile-then-suggest" compare to "look at sample rows"?
- Where did the AI invent expectations or use the legacy API?
- Compare today's `.cursorrules` to Week 4's. What pattern emerged in the rules section across weeks?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 6. 5–7 = re-review the weak day. <5 = redo exercises.

1. List the GX object hierarchy in order: from Data Context to Data Docs. (Hint: ~9 nouns.)
2. Why is the GX 1.x API not backward-compatible with code from 0.x tutorials?
3. What's the difference between an *ephemeral* and a *file-based* Data Context, and when do you use each?
4. Write a one-line `gx.expectations.ExpectXyz(...)` call to assert that `email` matches an `*@*.*` pattern.
5. What does `mostly=0.95` do in an expectation?
6. Why must you pair `ExpectColumnValuesToNotBeNull` with a row-count expectation?
7. What's a Validation Definition, and why does GX have it as a separate concept from Suite and Checkpoint?
8. After running a Checkpoint, where on disk do you find the HTML report?
9. A Checkpoint reports `success=False`. Does your Python script exit with non-zero status by default?
10. The first thing you do with an AI-generated Expectation Suite is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about Great Expectations and the broader DQ-framework landscape.

### IQ1. "Walk me through the workflow for setting up Great Expectations on a new dataset."

*What a good answer covers:*
- Get a Data Context (file-based for persistence)
- Add a Data Source for the storage backend (pandas, SQL, Spark)
- Add a Data Asset that points to the specific dataset (table, DataFrame, file)
- Add a Batch Definition that says how to slice the asset (whole table, by date partition, etc.)
- Build an Expectation Suite — column-by-column rules, ideally covering all DQ dimensions
- Build a Validation Definition pairing the Suite with the Batch Definition
- Build a Checkpoint that runs the Validation Definition and triggers actions (Data Docs, Slack)
- Schedule the Checkpoint via Airflow / cron / CI

*Likely follow-up:* "Where in that pipeline does the data physically live?" (Answer: GX doesn't store data — it stores metadata about data. Data Source is just a configured connection, not a copy.)

### IQ2. "When would you choose Great Expectations over a simpler tool like pandera?"

*What a good answer covers:*
- **Choose pandera when:** you need lightweight schema validation embedded in Python code (transformation boundaries, function decorators), small team, no need for stakeholder-facing reports
- **Choose GX when:** you need stakeholder-facing HTML reports (Data Docs), multiple data sources (warehouse + S3 + Spark), team-shared catalogs of suites, integration with orchestrators (Airflow operators), or your team already runs GX
- Both can coexist — pandera at function boundaries inside Python; GX as the cross-cutting framework that runs daily and produces reports
- Honest take: GX has more ceremony for solo or small projects. The HTML reports and ecosystem are the differentiators that justify the overhead at team scale.

*Likely follow-up:* "Where would you draw the line on adopting GX?" (Answer: if it's just one person testing pandas DataFrames in CI, pandera + pytest is simpler. If multiple stakeholders need to see what's tested and what's failing, GX earns its weight.)

### IQ3. "How do you generate Data Docs and make them accessible to non-technical stakeholders?"

*What a good answer covers:*
- A Checkpoint with `UpdateDataDocsAction` regenerates the HTML site after every run
- Default location is local: `gx_project/uncommitted/data_docs/local_site/index.html`
- For team access, configure a remote site backend (S3, GCS, Azure Blob) — GX writes the HTML there after each run, stakeholders bookmark the URL
- Alternative: archive the local HTML as a CI artifact and link from PRs / Slack — lower-effort if you don't need always-on access
- Data Docs are static HTML, so any static-site host works (Netlify, GitHub Pages); doesn't require a server

*Likely follow-up:* "What if stakeholders want filtering or search in the docs?" (Answer: built-in Data Docs are read-only. For interactive views, you'd push results to a BI tool — Looker, Tableau — or use GX Cloud, the hosted product.)

### IQ4. "How would you handle a column where 5% of values are legitimately NULL but the other 95% must be populated?"

*What a good answer covers:*
- Use the `mostly=` parameter: `ExpectColumnValuesToNotBeNull(column="x", mostly=0.95)` passes if at least 95% of values are non-null
- Caveat: this lets unknown bugs slide as long as they stay under the threshold; pair with row-count and freshness checks
- Alternative: split into two checks — one strict (`mostly=1.0`) on a *subset* defined by another column (e.g. "for active customers, email must always be present"), and one looser on the full table
- Document the rationale for the threshold; don't pick `0.95` arbitrarily — it should reflect what you actually expect

*Likely follow-up:* "What's the failure mode of `mostly=0.95`?" (Answer: if a real bug causes exactly 4% of rows to go null, the test still passes. `mostly=` is a smoothing parameter, not a guarantee — use it intentionally, not as a default.)

### IQ5. "How do you keep an Expectation Suite in sync as the underlying data evolves?"

*What a good answer covers:*
- Treat the Suite like code: store it in version control (your file-based GX project should be a git repo)
- When upstream changes a schema, the Suite should fail — that's the *point*. Update the Suite intentionally, in a PR, with a clear changelog
- Avoid `auto=True` regeneration in production — if you regenerate from current data, you lose the bug-detection capability
- For numeric thresholds (ranges, mostly=), revisit periodically (quarterly?) to widen or tighten based on real production data
- For schema changes, the workflow is: (1) upstream announces change, (2) PR updates Suite + downstream code, (3) merge after Suite passes against the new schema

*Likely follow-up:* "What's the antipattern here?" (Answer: scheduled "auto-regenerate suite from current data" jobs. They mask drift — by the time you notice the suite is too loose, real bugs have shipped.)

---

## If you have extra time this week (stretch)

- Connect GX to a SQL data source — try pointing it at the `ecommerce.db` SQLite from Week 2's `seed_data.py`. The pattern is `context.data_sources.add_sqlite("name", connection_string="sqlite:///ecommerce.db")`.
- Set up a remote Data Docs backend on S3 or local-with-static-server — gives you the production deployment muscle
- Skim [GX Cloud](https://greatexpectations.io/cloud) — the hosted product. Same engine, different UX. Worth knowing exists; you may meet it at an interview.
- Compare [Soda Core](https://docs.soda.io) (preview of Week 13) with GX. Soda's `checks.yml` syntax is simpler — when does that matter?

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — A Data Context is the root object that manages all GX configuration, suites, and checkpoints for a project — like `conftest.py` for a GX deployment.
- **Q1.2** — A Data Asset names *what data exists* (e.g. "the orders table"). A Batch Definition names *how to slice it* (whole table, by date, by tenant). Many slicings can apply to the same asset, so they're separated.
- **Q1.3** — It fails. The seed data has one customer with NULL email (customer_id = 5). That's intentional — the seed data was designed to exercise these checks.
- **Q1.4** — No. That's the 0.x API (`context.sources` without underscore, `validator.read_dataframe`). In 1.x it's `context.data_sources` (with underscore) and there's no `Validator.read_dataframe` — you build a Batch Definition and call `.get_batch(...)`.

### Day 2 answers

- **Q2.1** — Many valid: `ExpectColumnValuesToBeOfType`, `ExpectColumnValuesToMatchRegex`, `ExpectColumnValueLengthsToBeBetween`, `ExpectColumnValuesToBeInSet`.
- **Q2.2** — It says "the expectation passes if at least 95% of values satisfy the rule." Useful for known-imperfect data — e.g. allowing 5% legitimate NULLs.
- **Q2.3** — `auto=True` infers thresholds from the current batch. If your current batch happens to contain a bug, the inferred range *includes* the bug — your future tests will accept the bug as normal. Use `auto=True` to *suggest* values during exploration; commit explicit values to production.
- **Q2.4** — Because `ExpectColumnValuesToNotBeNull` checks *every value in the column* — and there are no values to check on an empty table, so the rule is vacuously true. Pair with `ExpectTableRowCountToBeBetween(min_value=1, ...)` to catch that.

### Day 3 answers

- **Q3.1** — An Expectation is one rule (e.g. "X is unique"). An Expectation Suite is a named collection of rules. A Validation Result is the output of running a suite (or single expectation) against a batch — pass/fail per rule plus details.
- **Q3.2** — `context.suites.add(...)` raises if the name exists. `suite.add_expectation(...)` does not deduplicate — two identical adds give you two copies of the rule. Defensive scripts use a "get_or_create" pattern.
- **Q3.3** — In `gx_project/expectations/` (when using `mode="file"`). They're stored as JSON files keyed by suite name.
- **Q3.4** — You can conclude that the data passed *the rules you wrote*. You cannot conclude the data is correct in any absolute sense — your rules might be too loose, or might miss a dimension entirely. A passing suite on weak rules is still passing.

### Day 4 answers

- **Q4.1** — Suite = the rules. Validation Definition = (rules, data) pair. Checkpoint = (validation definitions + actions) bundle that's runnable.
- **Q4.2** — No. `result.success = False` is just data on the result object. Your script keeps running. For CI, you must explicitly check and exit non-zero (e.g. `sys.exit(0 if result.success else 1)`).
- **Q4.3** — Configure a remote Data Docs site backend (S3, GCS, Azure Blob, or static server). The Checkpoint regenerates the HTML there on every run; stakeholders bookmark the URL. Alternative: archive the local HTML folder as a CI artifact.
- **Q4.4** — Composability. One Suite can pair with many Batch Definitions (today's data, yesterday's, archive) — each pairing is a Validation Definition. One Checkpoint can run several Validation Definitions in one execution. The separation lets you reuse Suites across many "where the data is" scenarios.

### End-of-week answers

**A1.** Data Context → Data Source → Data Asset → Batch Definition → Batch (at runtime) → Expectation → Expectation Suite → Validation Definition → Checkpoint → Data Docs.

**A2.** GX 1.0 was a substantial rewrite — class structure, method names, and core abstractions changed. Notable differences: `context.sources` → `context.data_sources`, `add_or_update_checkpoint` is gone, `Validator` is mostly gone in favor of direct batch-validate calls, expectations are now classes (`gx.expectations.ExpectXyz(...)`) rather than methods on the validator.

**A3.** Ephemeral context (`gx.get_context()`) lives in memory only — fine for scripts and learning. File-based context (`gx.get_context(mode="file", project_root_dir="./gx_project")`) persists suites, checkpoints, and Data Docs to disk — required for any project where you reuse work across runs.

**A4.** `gx.expectations.ExpectColumnValuesToMatchRegex(column="email", regex=r".+@.+\..+")` (regex is approximate; a stricter email regex if needed).

**A5.** It says "the expectation passes if at least 95% of values satisfy the rule." Useful for known-imperfect data — allowing some baseline rate of failure.

**A6.** Empty DataFrames pass most "values" expectations vacuously — there are no values to violate the rule. A row-count expectation catches the empty case.

**A7.** A Validation Definition pairs a Suite with a Batch Definition. GX separates this from Suite (rules without data) and Checkpoint (runnable + actions) so one Suite can be reused across many "where" definitions in one Checkpoint.

**A8.** `gx_project/uncommitted/data_docs/local_site/index.html` (default, file-based context). Configurable to remote backends like S3, GCS, Azure.

**A9.** No. The script keeps running with `result.success = False` available as a value. For CI, wrap with explicit `sys.exit(0 if result.success else 1)` or `assert result.success`.

**A10.** Run it. The first generation will use legacy API or invented expectations. Verify it executes, all expectation names are real, and at least one expectation actually fails on known-bad data — otherwise the suite is theatrical, not protective.

---

*Done with Week 5? You should now be able to scaffold a GX project for any dataset, write a Suite covering all 6 DQ dimensions, run a Checkpoint that produces an HTML report, and recognize when a tutorial is using the legacy API vs current. If yes — onward to Week 6 (dbt Testing), where we leave Python and learn the SQL-first transformation framework that the modern data stack revolves around. If not — focus especially on the Day 1 vocabulary; the rest of GX is just permutations of those nine nouns.*
