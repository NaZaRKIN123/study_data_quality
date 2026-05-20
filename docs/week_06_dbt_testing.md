# Week 6 — dbt Testing | Training Materials

> **Companion to:** Week 6 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Build a working dbt project on your e-commerce data and write tests at every layer — built-in, singular, and source-freshness. By Friday you'll be able to read any team's `schema.yml` and add meaningful tests to it.

> **A note on versions:** As of dbt 1.8 (mid-2024), the YAML key `tests:` was renamed to `data_tests:` (because *unit tests* were added as a separate concept). The legacy `tests:` key still works but emits a deprecation warning, and you'll see it everywhere in older tutorials. **All examples in this file use the modern `data_tests:` key.** If your team's repo still uses `tests:`, that's fine — both work for now. Citation: [dbt v1.8 upgrade guide](https://docs.getdbt.com/docs/dbt-versions/core-upgrade/upgrading-to-v1.8).

---

## How to use this file

- This week leaves Python behind (mostly) — you'll be writing YAML and SQL
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday is **AI-assisted YAML population** — the boilerplate-heavy nature of dbt makes it a great AI fit
- Answers to all self-checks are at the bottom

---

## One-time setup (~20 minutes, do this before Monday)

### 1. Install dbt-core + dbt-duckdb

dbt is a SQL-first transformation framework. It runs against a "warehouse" — for local development, DuckDB is by far the easiest target (zero config, just a file).

```bash
source .venv/bin/activate              # your Week 2 virtualenv
pip install dbt-core dbt-duckdb
```

Sanity check:
```bash
dbt --version
```

You should see something like `Core: 1.x` and `Plugins: duckdb: 1.x`. Anything 1.8+ will work for everything in this week's materials. If you have 1.7 or earlier, upgrade — `data_tests:` syntax requires 1.8+.

### 2. Create the project

```bash
mkdir ecom_dbt && cd ecom_dbt
dbt init
# When prompted:
#   project name: ecom_dbt
#   database: duckdb
#   path: dev.duckdb        (or just press enter for default)
#   threads: 4
```

This creates a `~/.dbt/profiles.yml` with your DuckDB connection and a project folder structure. Verify:
```bash
dbt debug
```

You should see `All checks passed!`.

### 3. Bring in the seed data

dbt has a built-in command `dbt seed` that loads CSVs from `seeds/` into the warehouse as tables. Copy the four CSVs from Week 2 into your dbt project:

```bash
mkdir -p seeds
cp /path/to/week2-python-testing/customers.csv seeds/
cp /path/to/week2-python-testing/orders.csv seeds/
cp /path/to/week2-python-testing/products.csv seeds/
cp /path/to/week2-python-testing/order_items.csv seeds/

dbt seed
```

After this, your DuckDB has four tables (`customers`, `orders`, `products`, `order_items`). Verify:
```bash
duckdb dev.duckdb -c "SELECT COUNT(*) FROM customers;"
```

You should see `7`.

You're ready for Monday.

---

## Day 1 (Mon) — dbt Core Setup & Models

### Theory

**dbt is the "T" in ELT.** It takes raw data already loaded in your warehouse and transforms it into business-ready tables, using SQL files called **models**. dbt itself doesn't move data; it just runs your SQL inside the warehouse and tracks dependencies between models.

The mental model:

| You write | dbt produces |
|---|---|
| `models/stg_orders.sql` containing `SELECT ... FROM {{ ref('orders') }}` | A view (or table) named `stg_orders` in your warehouse |
| `models/marts/daily_revenue.sql` containing `SELECT ... FROM {{ ref('stg_orders') }}` | A view/table built *after* `stg_orders`, because dbt sees the dependency |

`{{ ref('xxx') }}` is the magic. dbt resolves it at compile time to the actual database identifier and uses it to build a DAG of dependencies.

### Project structure

After `dbt init`, you have:

```
ecom_dbt/
├── dbt_project.yml          # project config
├── seeds/                   # CSV files loaded via `dbt seed`
├── models/                  # SQL transformations
│   └── example/             # delete this when ready
├── macros/                  # reusable Jinja/SQL functions
├── tests/                   # singular tests (Day 3)
├── snapshots/               # SCD Type 2 (advanced, skip for now)
└── analyses/                # ad-hoc SQL, not run by `dbt run`
```

And in your home directory, `~/.dbt/profiles.yml` holds the warehouse connection.

### Materializations

When dbt builds a model, it has to decide *how* — a view (just a saved query), a table (precomputed), or something more advanced. The four standard options:

| Materialization | What dbt creates | Use when |
|---|---|---|
| `view` (default) | A SQL view in the warehouse | Lightweight transformations, small data |
| `table` | A physical table, rebuilt every run | Frequently queried marts, larger data |
| `incremental` | A table that only adds *new* rows on each run | Big append-only tables (events, orders) |
| `ephemeral` | A CTE inlined into downstream models — never materialized | Scratch logic that doesn't need to be queryable |

Set materialization in `dbt_project.yml`:
```yaml
models:
  ecom_dbt:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

Or per-model, with a config block at the top of the SQL file:
```sql
{{ config(materialized='table') }}
SELECT ...
```

### A first model

Create `models/staging/stg_orders.sql`:
```sql
SELECT
    order_id,
    customer_id,
    order_date,
    total_amount,
    status
FROM {{ ref('orders') }}
WHERE status = 'completed'
```

Run it:
```bash
dbt run -s stg_orders
```

dbt will compile the SQL (replacing `{{ ref('orders') }}` with the real table name), execute it against DuckDB, and create a view named `stg_orders`. Now query it:
```bash
duckdb dev.duckdb -c "SELECT COUNT(*) FROM stg_orders;"
```

### Gotchas

1. **`dbt run` doesn't run tests.** It builds models. Use `dbt test` for tests, or `dbt build` to do both in dependency order. Most teams use `dbt build` in CI.
2. **`{{ ref('x') }}` is required.** Don't write the raw table name. If you do, dbt can't see the dependency, and your model might run before its inputs exist.
3. **Models compile to one SQL statement.** Multi-statement scripts won't work — break them into multiple models.
4. **`profiles.yml` lives in `~/.dbt/`, not the project.** Easy to forget when sharing projects via git. Best practice: commit a `profiles.yml.template`, ignore the real one.
5. **DuckDB is single-process.** Two `dbt run` invocations against the same `dev.duckdb` file at once will conflict. Not a problem for solo learning; surprising in CI if you parallelize naively.

### Exercises

1. Run `dbt seed`. Verify the four tables exist via `duckdb dev.duckdb -c "SHOW TABLES;"`.
2. Delete the `models/example/` folder.
3. Create `models/staging/stg_customers.sql` that selects from `{{ ref('customers') }}` and renames `customer_id` to `id` for clarity. Run it with `dbt run -s stg_customers`.
4. Create `models/staging/stg_orders.sql` (per the example above), and `models/staging/stg_order_items.sql` (a passthrough of order_items). Run all staging models: `dbt run -s staging`.
5. Create `models/marts/daily_revenue.sql`:
   ```sql
   {{ config(materialized='table') }}
   SELECT
       order_date,
       SUM(total_amount) AS revenue
   FROM {{ ref('stg_orders') }}
   GROUP BY order_date
   ORDER BY order_date
   ```
   Run with `dbt run -s daily_revenue`. Confirm dbt builds `stg_orders` first (the dependency) automatically.
6. Run `dbt docs generate && dbt docs serve`. A static site opens with your DAG visualized — find the dependency arrow from `stg_orders` to `daily_revenue`.

### External practice

- [dbt Learn — Fundamentals (free)](https://learn.getdbt.com/courses/fundamentals) — official, ~5 hours; the canonical first-pass
- [dbt-utils package](https://github.com/dbt-labs/dbt-utils) — extends dbt with extra macros and tests; you'll meet this in Week 7
- [Jaffle Shop](https://github.com/dbt-labs/jaffle_shop) — dbt's example project; clone and read the SQL

### Self-check (Day 1)

> Q1.1 — What does `{{ ref('orders') }}` resolve to at compile time? Why use it instead of writing `orders` directly?
> Q1.2 — When would you use `materialized: table` vs `materialized: view`?
> Q1.3 — `dbt run` finished successfully. Did it run any tests?
> Q1.4 — Where do `dbt seed` files come from, and what does the command produce?

---

## Day 2 (Tue) — Built-in Generic Tests

### Theory

dbt ships with **four generic tests** that cover ~60% of common data quality needs. They're declared in YAML alongside model definitions:

| Test | What it asserts | Maps to DQ dimension |
|---|---|---|
| `not_null` | Column has no NULL values | Completeness |
| `unique` | Column has no duplicate values | Uniqueness |
| `accepted_values` | All values are in a given list | Validity |
| `relationships` | Every value exists in a referenced parent column | Consistency (referential) |

That's it. Four. The lesson: **most production data quality tests are covered by these four checks** — you just write a lot of them.

### YAML structure

Tests live in a `schema.yml` (or any `.yml`) file inside the `models/` folder. Convention: one schema file per folder.

Create `models/staging/_schema.yml`:
```yaml
version: 2

models:
  - name: stg_orders
    description: Completed orders from the source system
    columns:
      - name: order_id
        description: Primary key
        data_tests:
          - not_null
          - unique
      - name: customer_id
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: id
      - name: status
        data_tests:
          - accepted_values:
              values: ['completed']     # we filtered cancelled in the model

  - name: stg_customers
    columns:
      - name: id
        data_tests:
          - not_null
          - unique
```

Run:
```bash
dbt test
```

You'll see one row per test, pass or fail. Failed tests print the SQL that was run — useful for debugging.

### `accepted_values` argument syntax (a versioning note)

The values list can be passed two ways. Both work in current dbt:

**Older style** (top-level keys, works in all versions):
```yaml
- accepted_values:
    values: ['active', 'churned']
```

**New style** (explicit `arguments` block, available v1.10.5+):
```yaml
- accepted_values:
    arguments:
      values: ['active', 'churned']
```

Use whichever you see in your team's existing code. Both are correct.

### Severity: warn vs error

By default, a failing test fails the `dbt test` command. To downgrade to a warning:

```yaml
- not_null:
    config:
      severity: warn
```

Useful for known-imperfect columns where you want visibility but not pipeline failure. Same trade-off as `mostly=` in pandera and Great Expectations — use deliberately, not as a default.

### `where:` and `config:` to scope a test

You can filter the rows a test runs against:

```yaml
- unique:
    config:
      where: "order_date >= '2024-01-01'"
```

This is the standard pattern for "the constraint holds *for new data*, but legacy rows are grandfathered."

### Gotchas

1. **`tests:` vs `data_tests:`** — both work. `data_tests:` is the modern name (since dbt 1.8) and what new code should use. Old tutorials and older repos use `tests:`. Don't be confused when you see both in the same project.
2. **`not_null` doesn't catch `''` (empty string).** It only catches actual SQL `NULL`. For "non-empty string", you'll need a custom test or `dbt-expectations` (Week 7).
3. **`unique` requires `not_null` separately.** `unique` allows multiple NULLs (because `NULL = NULL` is UNKNOWN — see Week 1 Day 1!). For a primary key, declare both.
4. **`relationships` only checks the FK side.** It doesn't catch parents with no children — that's a different question. Use a singular test (Day 3) for that.
5. **Tests run in your warehouse**, not on your machine. They're SQL queries. On a billion-row table, `unique` is expensive — consider `where:` clauses or sampling.

### Exercises

1. Add a `_schema.yml` to `models/staging/` covering `stg_customers`, `stg_orders`, `stg_order_items`. Each model gets the four built-in tests where applicable. Aim for 10+ tests total across the three models.
2. Run `dbt test`. How many pass? How many fail?
3. **Schema drift check:** in `_schema.yml`, declare every column you expect (`columns: - name: ...`). Now drop a column from `stg_orders.sql`. Re-run `dbt test`. What happens? (Hint: dbt warns about an undocumented column or a missing one — depending on which side of the contract.)
4. For `stg_orders.status`, write an `accepted_values` test allowing only `['completed']`. It should pass (because the model filters to completed only). Now temporarily remove the WHERE clause from the model. Re-run. The test now fails — confirm.
5. Add a `relationships` test on `stg_order_items.order_id → stg_orders.order_id`. Does it pass? Why or why not? (Hint: `stg_orders` filters to completed only, so cancelled orders' line items are orphaned in this model.)
6. **Severity exercise:** change one failing test to `severity: warn`. Run `dbt test`. Notice the exit code — does the command "succeed"?

### External practice

- [dbt docs — Data tests](https://docs.getdbt.com/docs/build/data-tests) — official, current
- [dbt-utils — extra generic tests](https://github.com/dbt-labs/dbt-utils#generic-tests) — `equal_rowcount`, `recency`, `expression_is_true`, etc.
- [DataCamp — Comprehensive Guide to dbt Tests](https://www.datacamp.com/tutorial/dbt-tests) — clean walkthrough

### Self-check (Day 2)

> Q2.1 — Name the four built-in dbt generic tests and what each asserts.
> Q2.2 — Why does `unique` not imply `not_null`?
> Q2.3 — A test fails. By default, does `dbt test` exit with non-zero status? How would you change that for a specific test?
> Q2.4 — You see `tests:` in a colleague's `schema.yml`. Should you change it to `data_tests:`?

---

## Day 3 (Wed) — Singular Tests

### Theory

A **singular test** is just a SQL file in `tests/` that returns rows when something is wrong. **If the query returns zero rows, the test passes.** That's the entire mental model.

This is the same convention you wrote in pure SQL on Week 1 — assertions return zero rows when clean. dbt automates running them.

### When to use singular vs generic

- **Generic tests** are reusable patterns (the four built-ins, plus custom generics — see Week 7). Apply them in YAML.
- **Singular tests** are one-off rules specific to your business logic. Write them as SQL files.

If you find yourself writing the same singular test against five different columns, that's the signal to refactor it into a custom generic test (covered next week with `dbt-utils` and `dbt-expectations`).

### Examples

**Reconciliation: order_items sum equals orders.total_amount.** This is the same business rule you've now tested in pandas (Week 2), Python pipeline (Week 3), and pandera (Week 4). Now in dbt:

`tests/order_total_reconciles.sql`:
```sql
WITH order_item_sums AS (
    SELECT
        order_id,
        SUM(quantity * unit_price) AS computed_total
    FROM {{ ref('order_items') }}
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.total_amount,
    s.computed_total
FROM {{ ref('orders') }} o
JOIN order_item_sums s ON o.order_id = s.order_id
WHERE o.total_amount IS NULL
   OR ABS(o.total_amount - s.computed_total) > 0.01
```

Run:
```bash
dbt test --select test_name:order_total_reconciles
```

Or just `dbt test` to run everything.

**No future-dated orders:**

`tests/no_future_orders.sql`:
```sql
SELECT order_id, order_date
FROM {{ ref('stg_orders') }}
WHERE order_date > CURRENT_DATE
```

**Customer signup before any order:**

`tests/orders_after_signup.sql`:
```sql
SELECT o.order_id
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.id
WHERE o.order_date < c.signup_date
```

### Documenting singular tests

Add a description in `tests/_schema.yml`:
```yaml
version: 2

data_tests:
  - name: order_total_reconciles
    description: >
      Order's total_amount must match the sum of its line items
      (quantity * unit_price). Catches silent corruption between
      the orders aggregate and the order_items detail rows.
```

This is optional but useful — `dbt docs serve` will show the description.

### Gotchas

1. **A singular test passes when its query returns zero rows.** Counterintuitive at first. If you write `SELECT * FROM bad_orders`, the test *passes* when `bad_orders` is empty.
2. **Singular tests can't be referenced in `models.yml`.** They're not generic tests — they don't take parameters. Putting them in a model's `data_tests:` list will error.
3. **Use `{{ ref('model') }}` in singular tests, not raw table names.** Same rule as models. If you use raw names, dbt won't know the dependency and might run the test before the model is built.
4. **Singular tests don't get automatic descriptions in docs** unless you write them in YAML (as above). Most teams skip this; do it for your business-critical tests.
5. **Watch performance.** A singular test that does a 5-table join on every dbt run is slow. Use `where:` clauses, sample, or move expensive checks to a daily schedule rather than every-PR CI.

### Exercises

1. Write the order-total reconciliation singular test from above. Save as `tests/order_total_reconciles.sql`. Run it — does it fail? Why?
2. Write `tests/no_orphan_orders.sql`: any row in `stg_orders` whose `customer_id` doesn't appear in `stg_customers`. (You should already have this as a `relationships` test — write it as singular too, for practice. Compare the SQL each generates with `dbt compile -s ...`.)
3. Write `tests/no_inactive_products_in_completed_orders.sql`: any `order_items` row pointing to a product where `active = false`, where the parent order is not cancelled.
4. Write `tests/customers_have_unique_emails.sql`: any duplicate non-NULL email in `stg_customers`. Note: this is *not* covered by the built-in `unique` test if you allow NULL emails.
5. Run all your tests with `dbt test`. Capture the output. How many pass? Fail?
6. **Stretch:** add `--store-failures` to `dbt test`. Look in the warehouse — dbt now creates tables of failing rows for each test. This is invaluable for debugging.

### External practice

- [dbt docs — Singular data tests](https://docs.getdbt.com/docs/build/data-tests#singular-data-tests) — official
- [Vivek — Custom tests in dbt (Medium, 2025)](https://medium.com/@vivekmcm1/understanding-custom-tests-in-dbt-generic-vs-data-tests-with-examples-e7591cd6b670) — current, well-explained

### Self-check (Day 3)

> Q3.1 — A singular test passes when its query returns ___ rows?
> Q3.2 — Why can't you list a singular test under a model's `data_tests:` in `schema.yml`?
> Q3.3 — Translate this rule to a singular test (just describe the SQL): "every row in `orders` has at least one matching `order_items` row."
> Q3.4 — When should you turn a singular test into a custom generic test?

---

## Day 4 (Thu) — Source Freshness

### Theory

So far, you've used `dbt seed` to load CSVs as tables — and referenced them via `{{ ref('orders') }}`. In real projects, raw data isn't seeded — it's loaded by an external tool (Fivetran, Airbyte, custom Python) into the warehouse. dbt doesn't build those tables; it consumes them.

For these external tables, dbt has the **source** abstraction. You declare them in a `sources.yml`, then reference them via `{{ source('schema_name', 'table_name') }}` instead of `ref()`.

The big payoff: **freshness checks**. dbt can query each source and assert that its most recent record is within an SLA — catching "the upstream pipeline didn't run today" before downstream models compute against stale data.

### Declaring sources

Create `models/staging/_sources.yml`:
```yaml
version: 2

sources:
  - name: raw
    description: Raw tables loaded by upstream pipelines
    schema: main          # the DuckDB schema where tables live
    tables:
      - name: orders
        description: Raw orders from the OLTP database
        loaded_at_field: order_date    # which column to use for freshness
        freshness:
          warn_after: {count: 7, period: day}
          error_after: {count: 14, period: day}
        columns:
          - name: order_id
            data_tests:
              - not_null
              - unique
      - name: customers
        loaded_at_field: signup_date
        freshness:
          warn_after: {count: 30, period: day}
```

Then in your models, change:
```sql
FROM {{ ref('orders') }}    -- before
```
to:
```sql
FROM {{ source('raw', 'orders') }}    -- after
```

### Running freshness

```bash
dbt source freshness
```

dbt runs `SELECT MAX({{ loaded_at_field }}) FROM ...` for each source, computes the age, and emits warnings or errors based on your thresholds. Output looks like:

```
1 of 2 START freshness of raw.orders ............................. [RUN]
1 of 2 ERROR STALE freshness of raw.orders ....................... [ERROR in 0.02s]
2 of 2 START freshness of raw.customers .......................... [RUN]
2 of 2 PASS freshness of raw.customers ........................... [PASS in 0.01s]
```

### When freshness should warn vs error

**Warn** is a soft signal — visible in CI logs but doesn't block. Use it for "we'd want to know" thresholds.

**Error** is a hard fail — the command exits non-zero. Use it for "definitely broken" thresholds, where downstream pipelines would produce wrong answers.

A common pattern: `warn_after: 1 day, error_after: 3 days` for a daily-refreshed table.

### Gotchas

1. **`loaded_at_field` is *the data's own timestamp*, not an `inserted_at` audit column.** Be deliberate — for a daily-loaded `orders` table, `order_date` works; for an event stream, you probably want a true ingestion timestamp from the loader.
2. **Time zones bite again.** `loaded_at_field` is compared against `CURRENT_TIMESTAMP` in the warehouse's timezone. If your data is UTC and the warehouse is local, freshness will look wrong by hours. Standardize on UTC.
3. **Freshness in CI is awkward** because the data on a CI runner may be old (e.g. a static fixture). Consider running freshness only against production, or against a real recent fixture.
4. **`dbt source freshness` is a separate command** from `dbt test`. Easy to forget. In production, run both as part of your daily pipeline (or `dbt build` if your version supports source freshness as part of build — check release notes).
5. **A source has to actually be referenced** in some model for `dbt source freshness` to know about it. Declared-but-unused sources are silently ignored.

### Exercises

1. Refactor your project: rename `orders.csv` etc. to be conceptually "raw" data, declare them as sources in `_sources.yml`, and update your `stg_*.sql` models to use `{{ source('raw', 'xxx') }}` instead of `{{ ref('xxx') }}`. (You'll keep `dbt seed` so the data exists locally.)
2. Add freshness blocks for `orders` (warn after 7 days, error after 14 days) and `customers` (warn after 30 days). Run `dbt source freshness`. Does it pass?
3. Modify the `loaded_at_field` for `orders` to a date that ensures the test fails — e.g. set the threshold absurdly tight: `warn_after: {count: 1, period: hour}`. Confirm the warning fires.
4. **Schema documentation as a side effect.** Run `dbt docs generate && dbt docs serve`. Notice how your sources now appear in the DAG with their freshness state. This is what stakeholders see.
5. **Trap exercise:** declare a source but don't reference it in any model. Run `dbt source freshness`. Does it run? Now reference it. Re-run. (Spoiler: depends on whether you select it explicitly. Check with `dbt source freshness --select source:raw.orders`.)
6. Add a `freshness:` block at the top level of `_sources.yml` (under `sources: - name: raw`) to apply a default to all tables. Then override per-table where needed.

### External practice

- [dbt docs — Sources](https://docs.getdbt.com/docs/build/sources) — official, current
- [dbt docs — Source freshness](https://docs.getdbt.com/docs/deploy/source-freshness) — adjacent, deeper

### Self-check (Day 4)

> Q4.1 — What's the difference between `{{ ref('x') }}` and `{{ source('s', 'x') }}`?
> Q4.2 — `loaded_at_field` is — the column you want to use for what?
> Q4.3 — A source's freshness check fails. Does this stop downstream `dbt run` from executing?
> Q4.4 — Why might `freshness` produce confusing results in CI?

---

## Day 5 (Fri 🤖) — AI Workflow: dbt Test Co-Pilot

### What you're learning today

The boilerplate-to-meaning ratio in dbt YAML is high — a `schema.yml` with tests for every column on every model takes hours to write by hand and looks 90% the same across projects. **This is the perfect AI use case.** Today you'll generate a dbt schema file from a model's SQL plus a description of the table, then iterate.

### Setup (~5 min)

- Have your project from Days 1–4 ready
- Open Cursor (or Claude in browser, or VS Code + Copilot)

### Exercise 1 — From SQL to schema.yml

Open `models/staging/stg_orders.sql` in Cursor. Use inline edit (`Ctrl+K` / `Cmd+K`) — or paste into Claude — with this prompt:

> *"Generate a dbt schema.yml entry for this model using the modern `data_tests:` syntax (not legacy `tests:`). For each column, suggest appropriate built-in generic tests (`not_null`, `unique`, `accepted_values`, `relationships`) based on the column name and what makes sense for a `stg_orders` staging model. For `customer_id`, add a `relationships` test pointing to `stg_customers`. Output valid YAML I can paste into models/staging/_schema.yml."*

Run `dbt test`. Some tests will pass, some fail. For each:

- Pass → keep it
- Fail because the data is bad → investigate, decide if real bug or test too strict
- Fail because the test is wrong → fix the test (or ask the AI)

### Exercise 2 — Generate a singular test from a business rule

Pick one of these rules (or invent your own from the seed data):

- "An order's `total_amount` must equal `SUM(quantity * unit_price)` from its line items"
- "No order can be placed before the customer's `signup_date`"
- "If `products.active = false`, no completed order should contain that product"

Prompt Claude:

> *"Write a dbt singular test as a SQL file for this business rule: '[rule]'. The test should return rows when the rule is violated (zero rows on pass). Use `{{ ref('xxx') }}` to reference models. Save as `tests/[descriptive_name].sql`. Include a one-paragraph comment at the top explaining what the test catches and why it matters."*

Run with `dbt test --select [test_name]`. Iterate if wrong.

### Exercise 3 — Coverage analysis

Once you have a populated `schema.yml`:

> *"Look at this schema.yml and the model SQL files in models/staging/. For each of the 6 DQ dimensions (completeness, uniqueness, validity, consistency, timeliness, accuracy), evaluate whether the existing tests cover it. List specific gaps as bullet points; don't write the YAML for fixes yet."*

Read the gaps. Pick the 2–3 you actually want covered, then ask:

> *"Write the YAML and SQL for these gaps. Use modern `data_tests:` syntax for generics, and singular tests for cross-table rules."*

Apply, run `dbt test`, iterate.

### Update your `.cursorrules`

Add a dbt section:

```
dbt conventions:
- Use the modern `data_tests:` YAML key, never legacy `tests:`.
- Singular tests live in tests/ and use `{{ ref('model') }}`, not raw table names.
- Reference upstream tables via `{{ source('schema', 'table') }}` if external,
  or `{{ ref('model') }}` if built within the project.
- Every staging model has at minimum: not_null + unique on its PK, and
  relationships on every FK that resolves within the project.
- Keep test names descriptive — `customer_email_must_be_unique` over
  `unique_test_1`.
- Use `severity: warn` deliberately, not as a default.
- For rules tested in three places (raw, staging, mart), implement once at
  staging — the layer where business keys are conformed.
```

### Quality bar — when is an AI-generated dbt test set "good"?

- [ ] Modern `data_tests:` syntax (not legacy `tests:`)
- [ ] Every PK has both `not_null` and `unique` (not just `unique`)
- [ ] Every FK has `relationships` to the right parent model
- [ ] No test references invented columns or models
- [ ] `accepted_values` lists are based on the actual data, not assumptions
- [ ] Singular tests use `{{ ref(...) }}` and have descriptive filenames
- [ ] At least one test fails on the seed data — meaning the suite is real

### Reflection (write 3–5 sentences in `notes.md`)

- Did the AI use `tests:` or `data_tests:` by default? (Many models still default to legacy.)
- Where did the AI invent tests that don't exist (e.g. `dbt_utils.unique_combination_of_columns` — that one *is* real, but the AI may invent others)?
- How does Friday Week 6 compare to Week 5's GX-suite generation? (Hint: dbt's YAML is more constrained than GX's Python — the AI has fewer ways to go wrong, but also fewer ways to be useful.)

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 7. 5–7 = re-review the weak day. <5 = redo exercises.

1. What does `{{ ref('orders') }}` do, and why is it different from typing `orders` directly?
2. Name the four built-in dbt generic tests.
3. Modern dbt YAML uses `data_tests:` instead of `tests:`. Why was the rename made (1.8+)?
4. Where does a singular test live, and what defines "passing" for one?
5. What does `relationships` test, and what does it *not* test?
6. Write a YAML snippet asserting that `stg_orders.status` only contains `'completed'`.
7. What's the difference between `severity: warn` and the default?
8. What's a `loaded_at_field`, and what command uses it?
9. You see `tests:` in a colleague's repo. Should you migrate to `data_tests:` immediately?
10. The first thing you do with an AI-generated `schema.yml` is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about dbt and dbt testing.

### IQ1. "What's dbt, and where does it fit in the modern data stack?"

*What a good answer covers:*
- dbt is a SQL-first transformation framework — the "T" in ELT
- It runs *inside* the warehouse (Snowflake, BigQuery, Redshift, Databricks, DuckDB) — dbt doesn't move or store data, it orchestrates SQL transformations
- Uses Jinja for templating: `{{ ref('model') }}`, `{{ source('s', 't') }}`, macros for reusable logic
- Tracks dependencies between models via `ref()`, builds a DAG, runs them in order
- Has built-in testing (the four generic tests + singular tests + custom generics) — this is its biggest differentiator
- Two flavors: dbt Core (open source CLI) and dbt Cloud (hosted, with IDE, scheduler, and observability)

*Likely follow-up:* "Where does dbt *not* fit?" (Answer: anything that isn't SQL inside a warehouse — streaming, Python ML pipelines, raw ingestion. dbt assumes data is already loaded.)

### IQ2. "Walk me through the four built-in dbt tests and a real-world example of each."

*What a good answer covers:*
- `not_null` — completeness check. Example: `customer_id` on every row in `orders`.
- `unique` — uniqueness check. Example: `order_id` is unique in `orders`.
- `accepted_values` — validity / enum check. Example: `status` is in `{'completed', 'cancelled', 'refunded'}`.
- `relationships` — referential integrity. Example: every `order.customer_id` exists in `customers.id`.
- Mention that `unique` doesn't imply `not_null` (a column can be all-NULL and still pass `unique` — same SQL three-valued logic from Week 1)
- Mention you'd combine these with singular tests for cross-table business rules and `dbt-utils` / `dbt-expectations` for richer checks

*Likely follow-up:* "Why doesn't `unique` imply `not_null`?" (Answer: because `NULL = NULL` is UNKNOWN in SQL, so multiple NULLs aren't considered duplicates. Declare both for a true primary key.)

### IQ3. "When would you write a singular test versus a generic test?"

*What a good answer covers:*
- Generic tests are **reusable patterns** — declare in YAML, parameterize over models and columns. Use for rules that apply across many places.
- Singular tests are **one-off SQL queries** — file in `tests/`, return zero rows on pass. Use for business-specific rules that only apply to one model or join.
- The decision rule: if you're writing the same singular test 3+ times with different inputs, refactor into a custom generic test. Place it in `tests/generic/` or `macros/`.
- For complex multi-table reconciliation (like "order total equals sum of items"), singular tests are usually clearer than trying to parameterize.

*Likely follow-up:* "What's a custom generic test, and when have you written one?" (Answer: a Jinja `{% test xyz(model, column_name) %}...{% endtest %}` block. Real-world example: `test_no_empty_strings(model, column_name)` to extend `not_null` to also catch empty strings.)

### IQ4. "How does dbt source freshness work, and why does it matter?"

*What a good answer covers:*
- A *source* in dbt is an external table loaded by another tool (Fivetran, Airbyte) that your dbt project consumes via `{{ source(...) }}`
- Freshness blocks declare an SLA: `warn_after: {count: 1, period: day}` and `error_after: {count: 3, period: day}`
- `dbt source freshness` queries `MAX(loaded_at_field)` for each source and compares to current time
- Catches "the upstream pipeline didn't run" *before* downstream models compute against stale data — the most actionable signal for data observability
- In CI / scheduled pipelines, run `dbt source freshness` first; if it errors, abort the rest of the run rather than silently producing yesterday's metrics

*Likely follow-up:* "What's the difference between freshness and a watermark in a streaming pipeline?" (Answer: same number, different actor — freshness is a *consumer's* assertion that data has arrived; watermark is a *producer's* rule about late data. See Week 3 Day 2.)

### IQ5. "How would you test a complex business rule like 'an order's total must equal the sum of its line items'?"

*What a good answer covers:*
- This is a **reconciliation rule** — a Consistency dimension test (Week 4 framework)
- Cleanest implementation in dbt: a singular test in `tests/`. SQL pattern: aggregate `order_items` to per-order totals, JOIN to `orders`, return rows where totals don't match within tolerance
- Floating-point comparisons need tolerance: `ABS(a - b) > 0.01` rather than `a != b`
- Handle NULLs explicitly — does NULL `total_amount` count as a failure or as a separate test?
- For a recurring pattern (multiple "X equals SUM of Y" rules), consider `dbt-utils.equal_rowcount` or a custom generic test
- In production, store failures via `--store-failures` so you can join to the failing rows for debugging

*Likely follow-up:* "How would you make this test fast on a billion-row table?" (Answer: scope with `where` to the last N days, partition on `order_date`, only run the full reconciliation daily not on every PR, or pre-aggregate `order_items` into a table that's incrementally maintained.)

---

## If you have extra time this week (stretch)

- Install `dbt-utils`: add to `packages.yml`, run `dbt deps`. Try `dbt_utils.equal_rowcount` and `dbt_utils.expression_is_true`.
- Install `dbt-expectations`: a Great Expectations-style port that gives you ~50 additional generic tests. Try `dbt_expectations.expect_column_values_to_be_between`.
- Skim [dbt-osmosis](https://github.com/z3z1ma/dbt-osmosis) — it auto-populates schema.yml from existing models. Compare its output to your AI-generated YAML.
- Read [the Jaffle Shop](https://github.com/dbt-labs/jaffle_shop) example project end-to-end. Notice the conventions: staging/intermediate/marts folders, schema files alongside SQL, descriptions everywhere.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — At compile time, `{{ ref('orders') }}` resolves to the fully-qualified database identifier (e.g. `"dev"."main"."orders"`). Using it instead of the raw name lets dbt build the dependency graph — without it, dbt doesn't know `orders` is one of your models, so it might run dependent models before `orders` exists.
- **Q1.2** — `view` for cheap, frequently-changing logic where you don't want to maintain a precomputed result. `table` for marts that are queried often and where compute cost > storage cost. As volumes grow, switch hot views to tables, and tables to incrementals.
- **Q1.3** — No. `dbt run` builds models. `dbt test` runs tests. `dbt build` does both in dependency order.
- **Q1.4** — From `seeds/*.csv`. The command loads each CSV into the warehouse as a table, with the same name as the file. Useful for static reference data — *not* for production-volume data.

### Day 2 answers

- **Q2.1** — `not_null` (no NULLs), `unique` (no duplicates), `accepted_values` (values in a given list), `relationships` (FK exists in parent table).
- **Q2.2** — Because in SQL, `NULL = NULL` is UNKNOWN, not TRUE. `unique` looks for duplicate values, and NULLs are never "equal" to each other — so a column with three NULLs and three distinct values passes `unique`. Declare both for a true primary key.
- **Q2.3** — Yes, by default a failing test produces a non-zero exit code. To downgrade, add `config: severity: warn` — the test still runs and reports, but doesn't fail the command.
- **Q2.4** — Not necessarily. `tests:` still works; both keys are accepted. If the team is migrating, do it as part of a planned cleanup. If you're adding a new test, use `data_tests:` for new code and let old code coexist.

### Day 3 answers

- **Q3.1** — Zero. A singular test passes when its SQL query returns no rows.
- **Q3.2** — Because singular tests aren't generic — they don't accept parameters (model, column_name). They're standalone SQL, not parameterized. The `data_tests:` list under a model expects test names that resolve to generic test definitions.
- **Q3.3** — Anti-join: `SELECT o.order_id FROM {{ ref('orders') }} o LEFT JOIN {{ ref('order_items') }} oi ON o.order_id = oi.order_id WHERE oi.order_id IS NULL`. Returns parent orders with no children.
- **Q3.4** — When you'd write the same singular test 3+ times with different inputs (different models or columns). At that point, refactor into a custom generic test in `tests/generic/` or `macros/`.

### Day 4 answers

- **Q4.1** — `ref()` is for models built *inside* your dbt project (your own SQL files in `models/`). `source()` is for tables loaded *outside* dbt (by Fivetran, Airbyte, manual loads). Both compile to fully-qualified database identifiers, but they declare different ownership and enable different features (only sources support freshness).
- **Q4.2** — The column dbt should use to determine "how recent is this data?" — typically a load timestamp or, if you trust the source, an event timestamp. dbt computes age as `current_timestamp - MAX(loaded_at_field)`.
- **Q4.3** — No, not by default. `dbt source freshness` is its own command. To enforce in CI, you run it explicitly and check its exit code, or chain commands: `dbt source freshness && dbt build`.
- **Q4.4** — Because the data on a CI runner may be a static fixture, not a live load. The freshness check would always fail (or always pass) regardless of upstream pipeline health. Run freshness against production, not CI.

### End-of-week answers

**A1.** It compiles to the fully-qualified database identifier of the `orders` model (e.g. `"dev"."main"."orders"`). Without it, dbt can't see the dependency, so the DAG is wrong — your model might run before `orders` exists.

**A2.** `not_null`, `unique`, `accepted_values`, `relationships`.

**A3.** Because dbt 1.8 added `unit_tests:` as a separate concept (testing model logic against fake input data, not testing real data). To distinguish, the existing `tests:` key was renamed to `data_tests:`. The legacy `tests:` still works for backward compat.

**A4.** In `tests/` (or its subfolders), as `.sql` files. The test passes when the query returns zero rows.

**A5.** It tests that every value in a child column exists in a parent column (FK → PK). It does *not* test that every parent has at least one child — that's a different question requiring a separate test.

**A6.**
```yaml
- name: status
  data_tests:
    - accepted_values:
        values: ['completed']
```

**A7.** Default severity makes a failed test fail the `dbt test` command (non-zero exit). `severity: warn` reports the failure but lets the command exit zero. Use `warn` for known imperfect data, not as a default.

**A8.** A `loaded_at_field` is the column dbt uses to compute data age for freshness checks. It's used by `dbt source freshness`.

**A9.** Not urgently. Both work; `data_tests:` is the modern key but the rename was non-breaking. Migrate as part of planned work, use `data_tests:` for any new YAML.

**A10.** Run `dbt test`. Verify (a) it executes without errors, (b) at least one test fails on known-bad seed data — otherwise the suite is theatrical, not protective.

---

*Done with Week 6? You should be able to bootstrap a dbt project on any warehouse, write tests across the four built-in plus a handful of singular tests, and recognize the difference between modern and legacy YAML syntax. If yes — onward to Week 7 (CI/CD for Data Pipelines), where everything you've built so far gets automated. If not — Day 1 (project setup) is the foundation; if anything there feels shaky, redo it before moving on.*
