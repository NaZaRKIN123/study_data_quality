# Week 13 — Monitoring & Data Observability | Training Materials

> **Companion to:** Week 13 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Shift from "test before deploy" to "watch in production." By Friday you'll know how data observability differs from monitoring, how to write Soda Core checks, how to wire them into Airflow with sensible alerting, and — most importantly — how to design alerts people actually act on instead of ignore. The honest take: most alerting infrastructure is louder than it should be, and learning what *not* to alert on is as valuable as learning what to alert on.
>
> **Version notes (May 2026):**
> - **Soda Core v3** uses SodaCL (Soda Checks Language) — YAML-based checks. It's the most documented and battle-tested path, what we teach this week.
> - **Soda Core v4** is in transition to a Data Contracts–based syntax — release notes describe this as a breaking change. The *concepts* (declarative checks, scans, integration with orchestrators) transfer; exact YAML keys are evolving. Check current docs before adopting in production.
> - **Apache Airflow 3.x** (3.2.1 is current as of mid-2026) — major release in April 2025 with React UI, DAG versioning, asset-centric scheduling, and SLAs removed. We use the TaskFlow API (`@dag` / `@task` decorators), which is the recommended pattern and survives the 2→3 transition cleanly.

---

## How to use this file

- This week is more conceptual + ops-flavored than the previous weeks
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday's AI workflow is generating Soda checks from a schema — saves real time on a dull task
- Answers to all self-checks are at the bottom

---

## One-time setup (~10 minutes)

```bash
source .venv/bin/activate
pip install "soda-postgres" "soda-core" "soda-core-duckdb" requests
```

> **Heads-up:** Soda's PyPI package layout has shifted between v3 and v4. As of mid-2026, the v3 line is still available but the install incantation may differ from older tutorials. If `pip install soda-core-duckdb` fails for you, check [Soda's installation docs](https://docs.soda.io/) for the current package name. The exercises below assume DuckDB-backed checks, which need whatever current package routes Soda's adapter to DuckDB.

For Airflow, we'll *not* install it locally this week — Airflow setup is a meaningful project on its own. Day 3 covers Airflow integration *conceptually*, with code you can adapt when you have an Airflow environment to play with. If you want hands-on, the easiest path is the Astronomer CLI (`brew install astro` or equivalent) which spins up a local Airflow 3.x environment in Docker.

Sanity check what we did install:
```bash
soda --version
python -c "import requests; print('ok')"
```

---

## Day 1 (Mon) — Observability vs Monitoring vs Testing

### Theory

These three terms are often confused. Holding them apart helps you choose the right approach for the right problem.

| | What it answers | When you do it | Failure mode caught |
|---|---|---|---|
| **Testing** | "Is this code correct?" | Before deploy (in CI) | Logic bugs, edge cases |
| **Monitoring** | "Is the system running?" | Always, in production | Outages, latency spikes, errors |
| **Observability** | "Can I tell *why* it's broken?" | Always, by design | Unknown unknowns; novel failures |

**Testing** asserts known properties before code goes live. The tests run in a controlled environment with fixture data. Pass = ship; fail = fix.

**Monitoring** tracks predefined signals (CPU, request count, error rate). When a signal crosses a threshold, an alert fires. Good for *known* failure modes — "the API is down," "the database is full." Bad for novel ones.

**Observability** is the broader idea: building systems whose internal state is *queryable* enough that you can investigate failures you didn't anticipate. In data engineering, this means logging, lineage, schema versioning, sample-row capture, statistics tracking, run history.

### Data observability — the six pillars

The data community has settled on six pillars (popularized by Monte Carlo, but the framing is widely adopted):

1. **Freshness** — when did this table last update? Is it on schedule?
2. **Volume** — how many rows arrived? Is it within the expected range?
3. **Schema** — what columns / types does this table have? Did they change?
4. **Distribution** — what do the values *look* like? Mean, min/max, NULL rates, cardinality
5. **Lineage** — what tables / pipelines feed this one? What downstream consumers depend on it?
6. **Quality** — do the values pass business rules? (The Week 4 dimensions live here.)

Most of the work this week is around 1–4 and 6. Lineage is its own topic (column-level lineage tools like SQLMesh, dbt's exposures, or commercial offerings).

### Why testing isn't enough

Tests run against your test data. Production data is different — bigger, weirder, more skewed, full of edge cases your fixtures didn't cover. **Tests catch what you anticipated; observability catches what you didn't.**

A concrete example: Week 4's pandera schema asserts every email matches a regex. The test passes against your seed data. In production, an upstream system one day starts sending `null` instead of an empty string for missing emails. Your schema validator throws on the *first* row. The pipeline fails. Was your test wrong? No — the test passed, the schema works as designed. The *upstream contract* changed, and your testing didn't surface that.

Observability would have caught this at the **freshness check** ("yesterday's data finished loading by 6 AM; today it's 9 AM and still not done"), or the **distribution check** ("normally 0.1% of emails are NULL; today it's 12%"), or the **volume check** ("only 30% of expected rows landed before failure"). Observability sees the symptom; you investigate; you fix.

### Where these tools sit operationally

- **Tests** live in CI (Week 7). Block merge.
- **Observability checks** live in production. Run on a schedule (every hour, every load), inspect *production data*, alert on anomalies. They don't block anything; they tell you something needs attention.
- **Monitoring** is your infrastructure team's domain (CloudWatch, Datadog, Prometheus). Less about data quality, more about job health: "did the Airflow DAG run? was it slow? did it use too much memory?"

### The tools you'll meet this week

- **Soda Core** — open-source, YAML-based data quality checks. Day 2.
- **Airflow** — orchestrator that runs your pipelines and the checks. Day 3.
- **Slack / PagerDuty / email** — alert delivery. Day 3.

Mentioned but not deeply covered:
- **Monte Carlo, Bigeye, Acceldata** — commercial observability platforms. They auto-detect anomalies, do lineage, and have nice UIs. Solve the same problems Soda Core does but with more polish and a price tag.
- **Datafold** — focuses on diff-style observability ("did this column change vs yesterday?"). Strong on schema and value drift.
- **Great Expectations** (Week 5) — overlaps with Soda; more focused on contract validation than runtime observability.
- **dbt source freshness + tests** (Week 6) — very lightweight observability, often adequate for small teams.

For most projects, **Soda Core + Airflow + Slack** is enough. You only need the commercial tools when scale, lineage, or auto-anomaly-detection becomes a daily pain.

### Gotchas

1. **"Observability" gets used loosely.** Some teams call any logging "observability." Real observability means you can answer questions you didn't precompute. Ad-hoc queryability of state matters more than the buzzword.
2. **Don't over-monitor.** Every check has a maintenance cost. Alert fatigue (Day 4) is the #1 reason teams stop trusting their observability stack.
3. **Production data isn't test data.** Checks that pass against staged samples often fire constantly in production until tuned. Budget time for tuning thresholds, not just writing checks.
4. **Six-pillars framing is useful, not gospel.** Some checks span multiple pillars (a schema change is *also* a distribution change). Don't argue about taxonomy; ship checks.
5. **Lineage tools are expensive to set up and easy to underuse.** If you adopt one, plan how the team will *act* on lineage info — automated impact analysis, blast-radius alerts, etc. Otherwise it's a pretty graph that nobody opens.

### Exercises (analysis day, no coding)

1. For your Week 4 e-commerce project, list three failures *testing* would catch, three *monitoring* would catch, and three *observability* would catch. Where does each best fit?
2. Pick one of your dbt models from Week 6. Map its data quality concerns onto the six pillars (freshness, volume, schema, distribution, lineage, quality). Which pillars are well-covered today; which aren't?
3. Read a recent post-mortem from a public engineering blog (Slack, Cloudflare, GitHub all publish good ones). For the failure described: would more testing have caught it? More monitoring? Better observability? Often the answer is "all three, at different stages."
4. Draft (in `notes.md`) a one-page **observability strategy** for your e-commerce project. For each pillar: what specific checks, at what frequency, with what alerting. Aim for 5–10 checks total — quality over quantity.

### External practice

- [Monte Carlo — What is Data Observability?](https://www.montecarlodata.com/blog-data-observability-explained/) — clear primer; vendor-flavored
- [Charity Majors — Observability is a many-splendored thing](https://charity.wtf/) — broader-software perspective; influential blog
- [Google's SRE Book — Monitoring chapter](https://sre.google/sre-book/monitoring-distributed-systems/) — the canonical infrastructure-monitoring reference; transfers well to data
- [The Data Engineering Podcast — observability episodes](https://www.dataengineeringpodcast.com/) — practitioner conversations, multiple vendors

### Self-check (Day 1)

> Q1.1 — A test passes; a week later, the pipeline fails in production from data your test didn't see. Which discipline (testing, monitoring, observability) was supposed to catch this?
> Q1.2 — Name the six pillars of data observability.
> Q1.3 — Why would a team add observability *and* keep their tests, instead of replacing tests?
> Q1.4 — A "lineage tool" sits in the corner of your data stack and nobody opens it. What's the failure pattern, and what would make it useful?

---

## Day 2 (Tue) — Soda Core & SodaCL

### Theory

Soda Core (v3) is an open-source CLI + Python library for running declarative data quality checks. You write checks in **SodaCL** (Soda Checks Language) — a YAML dialect — and Soda compiles them into SQL queries against your data source.

### The minimal setup

You need three files:

**1. `configuration.yml`** — connect to your data source

```yaml
data_source ecom:
  type: duckdb
  path: data/ecom.duckdb
  read_only: true
```

**2. `checks.yml`** — declare your checks

```yaml
checks for orders:
  - row_count > 0
  - missing_count(customer_email) = 0
  - invalid_count(total_amount) = 0:
      valid min: 0
  - duplicate_count(order_id) = 0
  - schema:
      name: schema validity
      fail:
        when wrong column type:
          order_id: int
          total_amount: double
      warn:
        when forbidden columns present: ['ssn', 'credit_card_number']

checks for customers:
  - row_count between 100 and 1_000_000
  - missing_percent(email) < 5%
  - freshness(signup_date) < 7d
```

**3. Run a scan:**

```bash
soda scan -d ecom -c configuration.yml checks.yml
```

(In v4, the CLI structure changes to a noun-verb pattern. Verify against current docs.)

The output:
```
Soda Core 3.x.y
[INFO] Scan summary:
[INFO] 2/3 checks PASSED:
[INFO]     orders in ecom
[INFO]       row_count > 0 [PASSED]
[INFO]       missing_count(customer_email) = 0 [PASSED]
[INFO] 1/3 checks FAILED:
[INFO]     orders in ecom
[INFO]       invalid_count(total_amount) = 0 [FAILED]
[INFO]         actual: 3
```

Three orders had invalid totals. The check failed; you investigate.

### What you can check

SodaCL is rich. The 80% you'll actually use:

| Check type | Example | Pillar |
|---|---|---|
| `row_count` | `row_count > 1000` | volume |
| `missing_count` / `missing_percent` | `missing_percent(email) < 1%` | quality |
| `duplicate_count` | `duplicate_count(order_id) = 0` | quality |
| `invalid_count` | `invalid_count(total) = 0` with valid range | quality |
| `freshness` | `freshness(updated_at) < 24h` | freshness |
| `schema` | check column types, presence/absence | schema |
| Cross-table: `values in` | values in column appear in another column | quality |
| User-defined SQL | any SQL returning 0 = pass | anything |

Custom SQL gives you escape-hatch flexibility — your Week 1 reconciliation rule lives here:

```yaml
checks for orders:
  - failed rows:
      name: orders.total_amount reconciles with order_items
      fail query: |
        SELECT o.order_id, o.total_amount,
               (SELECT sum(quantity * unit_price) FROM order_items i WHERE i.order_id = o.order_id) AS computed
        FROM orders o
        WHERE abs(o.total_amount -
                  (SELECT sum(quantity * unit_price) FROM order_items i WHERE i.order_id = o.order_id)
                 ) > 0.01
```

If the query returns rows, the check fails and Soda surfaces them.

### Anomaly detection (basic)

SodaCL includes simple anomaly checks for monitoring drift over time:

```yaml
checks for orders:
  - anomaly score for row_count < default
  - change for row_count < 50% same day last week
```

These need historical scan data, which means either Soda Cloud or running scans regularly and persisting results yourself. Most teams either (a) start with explicit thresholds and add anomaly detection later or (b) skip Soda Core's anomaly features and use a commercial tool.

### Soda from Python

Sometimes you want programmatic control:

```python
from soda.scan import Scan

scan = Scan()
scan.set_data_source_name("ecom")
scan.add_configuration_yaml_file(file_path="configuration.yml")
scan.add_sodacl_yaml_file(file_path="checks.yml")
scan.execute()

# Inspect results
print(scan.get_logs_text())
print(f"Errors: {scan.has_error_logs()}")
print(f"Failed checks: {scan.get_checks_fail()}")
```

This pattern is what you embed in an Airflow operator (Day 3). The `Scan` object exposes everything the CLI shows, plus more for programmatic decisions.

### Where Soda fits relative to Great Expectations and dbt tests

You may now have *three* places that could host a "no NULL emails" check: pandera (Week 4), Great Expectations (Week 5), dbt tests (Week 6), Soda. **Pick one place per concern, document the pick.**

A pragmatic split that works for many teams:

| Concern | Where |
|---|---|
| Schema validation in transformation code | pandera or pydantic, in-Python |
| Pre-deploy contract validation | Great Expectations, in CI |
| Transformation correctness | dbt tests, run with each dbt build |
| Production data quality monitoring | Soda Core, scheduled in Airflow |

**Avoid the "test the same thing in three places" antipattern.** It feels safe; it's actually expensive maintenance with diminishing returns. Each tool wins in its domain; let it.

### Gotchas

1. **Scan results aren't actionable on their own.** A check failed — now what? Soda by default just exits with a status code. Wiring failures to alerts is a Day 3 problem.
2. **Soda's check syntax has evolved.** Tutorials from 2023 may use slightly different keys; v4 changes more. Verify against current docs.
3. **`freshness` needs a timestamp column.** Tables without one (immutable reference data) can't be freshness-checked. Use volume or schema checks instead.
4. **Scans can be slow.** Some checks compile to expensive SQL (cross-table consistency, full-column statistics). Budget scan time; consider sampling for very large tables.
5. **`failed rows` queries return data — including PII potentially.** If a check is "rows where SSN is malformed," failing rows may contain (malformed) SSNs. Soda Cloud captures this for review. Plan how that data is handled.

### Exercises

Create a `soda/` directory in your project.

1. Set up `configuration.yml` pointing at your e-commerce DuckDB warehouse from Week 6 (or a fresh one). Confirm `soda test-connection -d ecom -c soda/configuration.yml` succeeds.
2. Write `checks.yml` with at least 8 checks across the orders, customers, and order_items tables. Cover all 6 pillars at least once each. Run with `soda scan ...`. Read the output.
3. Translate the Week 1 reconciliation rule (`orders.total_amount = sum(items.quantity * items.unit_price)`) into a Soda `failed rows` custom-SQL check. Confirm it fails on your seeded bug (order #1006).
4. Add a freshness check (`freshness(signup_date) < 7d` or similar). Backdate one of the columns to last year and re-scan — confirm it fails.
5. **Schema check:** add a check that fails if `customers` is missing the `email` column or has it with the wrong type. Drop the column manually, re-scan, confirm failure.
6. Run scan from Python (the `Scan` class example). Print failed checks. This is what you'll embed in Airflow tomorrow.
7. **Stretch:** add an anomaly check (`anomaly score for row_count`). Run scan twice with different row counts. Notice that the first run can't really evaluate anomaly (no history). What does this tell you about deploying anomaly checks day one?

### External practice

- [Soda Core docs (v3)](https://docs.soda.io/soda-core/overview-main.html) — current; the SodaCL reference
- [SodaCL reference](https://docs.soda.io/soda-cl/soda-cl-overview.html) — full syntax catalog
- [Soda Cloud free trial](https://www.soda.io/) — if you want to try the commercial UI; not required
- [Astronomer — Soda + Airflow tutorial](https://www.astronomer.io/docs/learn/soda-data-quality) — concrete integration walk-through

### Self-check (Day 2)

> Q2.1 — Three places you might check "no NULL emails" — pandera, dbt tests, Soda. Which one belongs where, and why not all three?
> Q2.2 — Soda's `failed rows:` block returns rows that violate a check. What's the privacy concern, and how do you mitigate it?
> Q2.3 — A `row_count > 0` check passes; the actual count is 3 (yesterday it was 3 million). What's missing?
> Q2.4 — Why does anomaly detection ("today's count is 50% off from same day last week") need history before it's useful?

---

## Day 3 (Wed) — Airflow Integration & Alerting

### Theory

Soda checks need to *run somewhere*. Two common deployment models:

1. **Inside the data pipeline** — after the pipeline produces a Silver/Gold table, run Soda checks immediately. If they fail, fail the pipeline (or warn loudly).
2. **As a separate observability schedule** — run Soda checks on production data hourly / every 6 hours. Independent of the pipeline. Catches drift, freshness issues, upstream changes.

Most mature teams do both. The pipeline-attached checks fail the pipeline before bad data is published; the standalone checks notice slower-moving issues (volume drift over weeks, schema additions from upstream).

### Airflow 3.x — TaskFlow API quick tour

We're using Airflow 3.x. The recommended way to write a DAG is the **TaskFlow API** with `@dag` and `@task` decorators. (The older `PythonOperator`-style still works but the decorator API is cleaner.)

```python
from datetime import datetime, timedelta
from airflow.decorators import dag, task


@dag(
    schedule="@daily",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ecom", "data_quality"],
)
def daily_ecom_quality_checks():

    @task
    def run_orders_checks():
        from soda.scan import Scan
        scan = Scan()
        scan.set_data_source_name("ecom")
        scan.add_configuration_yaml_file("/opt/airflow/include/configuration.yml")
        scan.add_sodacl_yaml_file("/opt/airflow/include/checks/orders.yml")
        scan.execute()

        if scan.has_error_logs() or scan.get_checks_fail():
            failed = scan.get_checks_fail()
            raise ValueError(
                f"Soda scan found {len(failed)} failing checks: "
                + ", ".join(c.name for c in failed)
            )
        return {"status": "ok", "checks_passed": len(scan.get_checks_pass())}

    @task
    def run_customers_checks():
        # similar structure
        ...

    @task
    def notify_on_failure(orders_result, customers_result):
        # we get here only if both succeeded
        return f"Daily checks ok: {orders_result}, {customers_result}"

    orders = run_orders_checks()
    customers = run_customers_checks()
    notify_on_failure(orders, customers)


daily_ecom_quality_checks()
```

What this does:
- Defines a DAG that runs daily
- Two tasks run Soda scans against orders and customers
- A third task runs only if both succeed (data flow via TaskFlow `XComArg`)
- If any Soda scan fails (raises), Airflow marks the task `FAILED` and triggers callbacks

### Failure callbacks — where alerting hooks in

Airflow 3 lets you attach callbacks to tasks for various lifecycle events:

```python
def on_failure_callback(context):
    """Called when a task fails."""
    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id
    log_url = context["task_instance"].log_url

    message = (
        f":rotating_light: *Soda scan failed*\n"
        f"DAG: `{dag_id}`\n"
        f"Task: `{task_id}`\n"
        f"<{log_url}|View logs>"
    )
    post_to_slack(message)


@dag(
    schedule="@daily",
    start_date=datetime(2026, 5, 1),
    default_args={
        "retries": 2,
        "on_failure_callback": on_failure_callback,
    },
)
def daily_ecom_quality_checks():
    ...
```

Where `post_to_slack` is a small wrapper around the Slack incoming-webhook API:

```python
import requests
import os


def post_to_slack(message: str):
    webhook = os.environ["SLACK_WEBHOOK_URL"]
    response = requests.post(webhook, json={"text": message}, timeout=5)
    response.raise_for_status()
```

Slack incoming webhooks are the simplest alerting target. Set up: visit Slack's webhook config page, create a webhook for your channel, store the URL in Airflow's `Variable` or as an environment variable. Don't commit the URL — it's a secret.

### Airflow 3 — important changes from 2.x

Things that changed in Airflow 3 that hit observability work specifically:

| Change | What it means for your DAG |
|---|---|
| **SLAs removed** | The old `sla` parameter on tasks is gone. Use callbacks + custom timing checks instead. `DeadlineAlerts` is the planned replacement (not yet generally available as of mid-2026). |
| **`execution_date` removed from context** | Use `logical_date` or `data_interval_start`. Older tutorials still reference `execution_date`. |
| **Datasets renamed to Assets** | Same concept, new name. `Dataset(...)` becomes `Asset(...)` in 3.x. |
| **`conf` removed from context** | Read config differently. Use `context["params"]` or environment variables. |
| **Task SDK** | Tasks can now run outside the cluster. Mostly relevant for advanced users, but worth knowing. |
| **DAG versioning** | The UI now tracks DAG versions over time. Failures from yesterday's DAG version are still inspectable even after you've deployed a new one. |

For most observability work, the only one that bites is **SLA removal**. If your team relied on SLA-miss callbacks ("alert if this didn't finish by 7 AM"), you'll need to implement timing checks differently — either as a separate "deadline DAG" that compares the previous run's end time, or via custom Python in callbacks.

### Two alerting tiers — the pattern that works

Rather than alerting everything to one Slack channel, set up tiers:

| Tier | What | Where |
|---|---|---|
| **Page** | Critical: pipeline broke, downstream consumers will be impacted | PagerDuty / Opsgenie (wakes someone up) |
| **Notify** | Important: a check failed but isn't blocking everything | Slack (team channel; reviewed daily) |
| **Log** | Informational: a check warned but didn't fail | Airflow logs / Soda Cloud / a metrics dashboard |

The tier mapping per check is a *design choice*, not a tooling concern. You need to think about each check: "if this fires at 3 AM Sunday, do I want my phone to ring?" If yes → page. If "I want someone to look at it Monday morning" → notify. If "I want it to be queryable when investigating something else" → log.

**Most checks should be `notify` or `log`.** Paging is for "the SLA-violating, downstream-blocking, customer-visible" tier only. Treating every Soda failure as a page leads to alert fatigue (Day 4) and to people muting the channel.

### A more realistic DAG

```python
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import os, requests


SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")


def slack_alert(severity: str, message: str):
    icon = {"page": ":rotating_light:", "notify": ":warning:", "log": ":information_source:"}[severity]
    if not SLACK_WEBHOOK:
        return  # no-op in dev
    requests.post(SLACK_WEBHOOK, json={"text": f"{icon} {message}"}, timeout=5)


def soda_failure_callback(context):
    task_id = context["task_instance"].task_id
    log_url = context["task_instance"].log_url
    severity = context["params"].get("severity", "notify")
    msg = f"*Data quality check failed:* `{task_id}` <{log_url}|logs>"
    slack_alert(severity, msg)


@dag(
    schedule="@daily",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args={"retries": 1},
    tags=["data_quality"],
)
def ecom_data_quality():

    @task(
        on_failure_callback=soda_failure_callback,
        params={"severity": "page"},   # critical: fail the pipeline
    )
    def critical_orders_checks():
        from soda.scan import Scan
        scan = Scan()
        scan.set_data_source_name("ecom")
        scan.add_configuration_yaml_file("/opt/airflow/include/configuration.yml")
        scan.add_sodacl_yaml_file("/opt/airflow/include/checks/orders_critical.yml")
        scan.execute()
        if scan.get_checks_fail():
            raise ValueError(f"{len(scan.get_checks_fail())} critical checks failed")

    @task(
        on_failure_callback=soda_failure_callback,
        params={"severity": "notify"},   # warning: notify but don't page
        trigger_rule="all_done",         # run regardless of upstream
    )
    def soft_distribution_checks():
        # Distribution drift; might be expected; alert but don't block
        ...

    critical_orders_checks() >> soft_distribution_checks()


ecom_data_quality()
```

The `>>` operator declares dependency. The `trigger_rule="all_done"` runs the task regardless of upstream success/failure — useful for the "warn-only" tier of checks.

### Gotchas

1. **Airflow callbacks fire in the worker process** — heavy callback logic (large API calls, slow database writes) blocks the worker. Keep callbacks fast; offload to a separate task if needed.
2. **Slack rate limits.** Don't post one message per failed check; aggregate. A DAG with 100 failing checks shouldn't blast 100 Slack messages — sum them and post one.
3. **Airflow 3's removed `execution_date`** trips up everyone migrating. Use `logical_date` or `data_interval_start`. Read the migration guide.
4. **Don't put secrets in DAG code.** Use Airflow Variables, Connections, or an external secrets backend (AWS Secrets Manager, HashiCorp Vault). The Slack webhook URL is a secret.
5. **`@dag` decorator + entry point.** Forgetting to call the DAG-decorated function at module level (`daily_ecom_quality_checks()`) means Airflow never sees it. Common first-time bug.

### Exercises

These are conceptual / pseudocode exercises if you don't have an Airflow environment. If you have Astronomer's local CLI or any Airflow 3.x setup, treat them as full hands-on.

1. Sketch (in `notes.md` or a `dags/quality.py` file) a DAG that runs your Soda checks daily on each of three tables (customers, orders, order_items). One task per table. Use TaskFlow API.
2. Add an `on_failure_callback` that posts a formatted Slack message. Use `requests.post(webhook, json={"text": message})`. Test the message format by `print()`-ing it to console first.
3. **Tier your checks:** classify your Day 2 checks into critical / notify / log. Justify each (in `notes.md`). Aim for: 1–2 critical, most notify, plus a few logs.
4. **Failure isolation:** structure your DAG so that one table's checks failing doesn't block other tables' checks. (Hint: `trigger_rule`.) Each table's checks runs independently; only the *aggregation/notify* task needs to know about all of them.
5. **De-duplication:** if the same check fails for 7 consecutive days, alerting every day is noise. Sketch a strategy: track previously-alerted check states in a small persistent store (Airflow Variable, a database table); only re-alert on state changes (newly failing, newly passing). You don't need to implement this; the design exercise is the point.
6. **Stretch:** if you have a local Airflow, deploy and run the DAG. Trigger a check failure (corrupt some data). Confirm the Slack message arrives. Confirm Airflow's UI shows the failed task with logs.

### External practice

- [Airflow 3.x documentation](https://airflow.apache.org/docs/apache-airflow/stable/) — current
- [TaskFlow API tutorial](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html)
- [Astronomer Academy](https://academy.astronomer.io/) — free Airflow courses; current with Airflow 3
- [Slack incoming webhooks](https://api.slack.com/messaging/webhooks) — official setup guide

### Self-check (Day 3)

> Q3.1 — Two deployment models for Soda checks. When does each fit?
> Q3.2 — Why are most data quality alerts `notify` instead of `page`?
> Q3.3 — A check fails for 7 days running. What's wrong with alerting every day, and how do you handle it?
> Q3.4 — Airflow 3 removed SLAs. What's a workable replacement for "alert if this DAG didn't finish by 7 AM"?

---

## Day 4 (Thu) — SLOs, SLIs & Designing Useful Alerts

### Theory

You can write 100 Soda checks and end up worse off than you started. The problem isn't the checks — it's the **alerts**. Bad alerts get ignored. Ignored alerts mean the next real failure goes unnoticed. **Designing alerts people act on is the hard skill of this week.**

### SLI, SLO, SLA — the three letters

Borrowed from SRE (Site Reliability Engineering):

- **SLI (Service Level Indicator)** — a measurable quantity. "Daily order_count," "freshness lag," "% of rows passing schema check."
- **SLO (Service Level Objective)** — your team's target. "Daily order_count is between 80% and 120% of last week's." "Freshness < 4h, 99% of the time."
- **SLA (Service Level Agreement)** — a contract with a consumer about an SLO, often with consequences. "If freshness > 4h for >1% of days, customer gets a credit."

In data engineering you'll usually deal with SLOs (internal targets) more than SLAs (external contracts). Pick a meaningful SLI, set a realistic SLO, and **alert on SLO violations, not SLI fluctuations**.

### A worked example

**Bad alerting**: "Alert if the count is more than 5% off from yesterday's." Fires daily because day-to-day variance is normal. Team mutes the channel.

**Better**: "Alert if the count is more than 30% off from the same day-of-week average over the last 4 weeks." Filters out routine variance and weekly seasonality.

**Better still**: "Alert if the count is outside a 2-sigma band of last 28 days' values." Statistically grounded; adapts to the data's natural noise.

The progression is: from absolute → relative → seasonal → statistical. Each step gets harder to implement and easier to live with.

### Alert fatigue — the failure mode you must avoid

When alerts fire too often, people stop reading them. When the rare *real* failure happens, it's lost in the noise. This isn't hypothetical — it's the dominant failure mode of observability programs.

The pattern that produces alert fatigue:
1. Team adds a check (good)
2. Check fires once / week from real noise (acceptable)
3. Team gets busy; doesn't tune
4. Check fires daily; people start ignoring
5. A real bug fires the same alert; nobody notices for a week

The fix isn't to write fewer checks — it's to be ruthless about the *ratio of true positives to false positives* on alerts. A useful heuristic: **if a check fires more than once a week without a real underlying issue, either tighten the threshold or downgrade it to log-only.**

### Designing a check — the questions to ask

Before adding a Soda check, answer:

1. **What's the failure mode you're catching?** Be specific: "an upstream API stops sending email field" — not "data quality."
2. **What's the SLI?** "% of rows with non-NULL email."
3. **What's the SLO threshold?** "≥ 99.5%."
4. **What does "fail" mean operationally?** Page? Notify? Log? Tied to which tier (Day 3)?
5. **Who acts on it?** Name the team. If nobody owns it, the alert won't be acted on.
6. **What's the false-positive rate you'll tolerate?** "< 1 false positive per month."
7. **How will you know if the alert is working?** Periodic review: are the alerts that fire being acted on?

Walk through the seven questions for any new check. If you can't answer them all, the check isn't ready to deploy.

### Useful patterns

**Trend rather than snapshot.** "Volume is 80% below normal" beats "volume is < 1000." The former adapts; the latter ages poorly.

**Group related checks.** A "schema is healthy" check that aggregates 12 column-level checks into one alert is more useful than 12 independent alerts that all fire together when an upstream rename happens.

**Suppress during expected events.** Running a backfill? Suppress alerts. Major database migration? Plan a quiet window. Many observability platforms support maintenance windows; if yours doesn't, manual suppression is fine.

**Time-of-day awareness.** Most batch pipelines run overnight. A 3 AM page for "row count is 0" might just be "the pipeline hasn't run yet." Your alerting should know the schedule.

**Auto-resolve.** When a failed check passes again, *unfire* the alert. Otherwise people keep manually clearing dashboards. Most platforms support this; configure it.

### Distribution drift — the hardest category

Volume and freshness are easy to alert on. Distribution drift — "the shape of the data has changed" — is much harder.

Common drift detectors:
- **Z-score**: `|today_value - mean(historical)| / stddev(historical) > 3`. Simple; assumes normal distribution.
- **Kolmogorov-Smirnov test**: compares two distributions. Sensitive to any difference; can be noisy.
- **Population Stability Index (PSI)**: bins both distributions; weighted log-ratio. Used heavily in ML feature monitoring.

For analytical pipelines (not ML), simple Z-score on key metrics (mean, P50, P95, NULL rate) is usually enough. ML monitoring (Week 14) goes deeper.

### What to monitor for a typical e-commerce pipeline

A reasonable starter set for the project you've been building:

| What | SLO | Alert tier |
|---|---|---|
| `orders` table arrives by 06:00 UTC daily | 99% of days | Page |
| `orders` row count within 30% of trailing 7-day avg | 95% of days | Notify |
| 0 NULL `customer_email` in `orders` | 100% of rows | Notify |
| 0 negative `total_amount` in `orders` | 100% of rows | Notify |
| Schema unchanged from yesterday | unless explicit migration | Notify |
| Reconciliation rule (orders.total = sum(items)) | 100% within $0.01 | Notify |
| Daily revenue within 50% of trailing 28-day average | 99% of days | Log only (drift is interesting, not actionable) |
| Customer signup rate within historical band | 99% of days | Log only |

Eight checks. One pages. The rest notify or log. **That's intentional.** Most projects need fewer alerts than they think.

### Gotchas

1. **Alerts you can't act on are noise.** "Volume is 5% below normal — for unknown reasons" — what do you do with that? If there's no playbook, downgrade or remove.
2. **Aggregated alerts hide problems.** Going too far the other direction — "one alert covering 50 checks" — means when it fires you don't know which check. Group thoughtfully.
3. **Test your alerts.** Like backups, alerts should be tested. Fire a deliberate check failure quarterly; confirm it reaches the right place. ([Anthropic actually does this](https://docs.claude.com/) for their own systems; many teams don't.)
4. **Alert tracking matters.** A spreadsheet of "alerts fired vs alerts acted on" tells you which alerts are working. Without this, alert quality drifts unseen.
5. **Severity inflation.** Every alert added as "critical" because it felt important when added. Six months later, half the alerts are critical and none of them are. Periodically downgrade.

### Exercises

Mostly thinking exercises today.

1. **Take your Week 4 DQ checks and run the seven design questions through each one.** For each check, write 2–3 sentences answering: failure mode, SLI, SLO, tier, owner, expected false-positive rate, success metric. If you can't, either the check isn't ready or you don't actually need it.
2. **Tier your starter checks** from the table above. Do you agree with my tiering? Where would you change it for your specific project?
3. **Drift detection — Z-score:** for your `orders.total_amount` column, compute mean and stddev over the last 28 days of synthetic data. Write a check that fires if today's mean is more than 3 sigma off. Test by injecting an outlier batch.
4. **Aggregation design:** if you have 12 schema checks (one per column type), should they be 12 separate alerts or one aggregated "schema healthy?" alert? Argue both sides; pick one for your project; justify in `notes.md`.
5. **Maintenance window:** sketch how you'd implement "suppress alerts during a backfill." What technical lever do you pull? (Hint: a flag in a database, an Airflow Variable, or a feature in your alerting tool.)
6. **Stretch:** read [Google's SRE workbook on alerting](https://sre.google/workbook/alerting-on-slos/) (Chapter 5: Alerting on SLOs). Apply *one* concept from it to your project's plan.

### External practice

- [Google SRE Workbook — Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/) — the canonical reference
- [Bryce Lampe — Alert fatigue is the price of vigilance](https://blog.alertmanager.io/) — practitioner perspective
- [Niall Murphy — SLO Adoption and Usage](https://research.google/pubs/pub47783/) — Google paper
- [The Data Quality Engineer — Substack](https://thedataqualityengineer.substack.com/) — running discussion of these problems

### Self-check (Day 4)

> Q4.1 — Difference between SLI, SLO, and SLA in your own words.
> Q4.2 — Alert fatigue — what is it and what causes it?
> Q4.3 — A check fires daily, the team has stopped reading it. What are your options, and which is usually best?
> Q4.4 — Why is "alert on SLO violations" better than "alert on every metric movement"?

---

## Day 5 (Fri 🤖) — AI Workflow: Generate Soda Checks From a Schema

### What you're learning today

Writing comprehensive Soda checks for a 50-table data warehouse is tedious. AI is genuinely good at the boilerplate ("for each column, generate the obvious checks") and at rough-cut anomaly thresholds. You still need to set tiers, tune false-positive rates, and decide what *not* to check — but the AI gets you 60% of the way in 5% of the time.

### Setup

Reuse the `anthropic` setup from Weeks 8–12.

### Exercise 1 — Generate a check file from a schema

Take a schema (your e-commerce one or a fresh sample). Paste into Claude:

> *"Given this table schema, generate a SodaCL `checks.yml` file with comprehensive data quality checks. Cover all 6 pillars: freshness, volume, schema, distribution, lineage, quality. For each check, include a brief comment explaining what failure mode it catches. Use realistic thresholds for an e-commerce dataset (~10K orders/day, ~50K customers).*
>
> *Schema:*
> *```*
> *orders*
> *  order_id INTEGER NOT NULL*
> *  customer_id INTEGER NOT NULL*
> *  total_amount DOUBLE*
> *  status VARCHAR (one of: pending, completed, cancelled)*
> *  order_date DATE NOT NULL*
> *  created_at TIMESTAMP*
> *```*
>
> *Use Soda Core v3 SodaCL syntax. Don't include checks that need historical scan data (skip anomaly_score). Return only the YAML, no commentary."*

Review the output. Common AI mistakes:
- **Wrong syntax keys** between SodaCL versions (`missing_count` vs `count missing` — the spec has changed). Verify against current Soda docs.
- **Unrealistic thresholds** (e.g., `row_count > 1000000`) when you said 10K/day.
- **Missing the reconciliation check** — a domain-specific cross-table rule the AI can't infer from schema alone.
- **Over-zealous schema check** that locks down every column type rigidly when only key columns matter.

### Exercise 2 — Tier the generated checks

Take the YAML from Exercise 1. Paste back into Claude:

> *"For each of the checks below, classify as 'page', 'notify', or 'log' based on these criteria:*
>
> *- 'page' = pipeline-blocking, customer-visible, or financially critical. Wakes someone up at 3 AM.*
> *- 'notify' = needs daytime attention but not urgent. Posts to Slack channel.*
> *- 'log' = informational, useful for forensics but not actionable on its own.*
>
> *For each, give a one-sentence rationale.*
>
> *```yaml*
> *[paste]*
> *```"*

The AI will probably over-classify as "page" — push back. Ask "are you sure all of these are page-worthy? Most teams keep paging to <5 alerts in a similar setup. Reclassify with that constraint." Watch how the AI revises.

This is interview-grade thinking. Being able to push back on your own first instinct ("everything matters") and arrive at a tighter list is the skill.

### Exercise 3 — Design SLOs

> *"For an e-commerce data pipeline that produces a daily `orders` Silver table, define 5 specific SLOs covering the 6 pillars of data observability. For each SLO:*
> *- The SLI (the measurable signal)*
> *- The threshold (the SLO target)*
> *- The window (over what time period it's evaluated)*
> *- The error budget (how often is breach acceptable)*
>
> *Be realistic — these are for a project with a single team and modest infrastructure, not Netflix. Don't over-engineer."*

You'll get a structured table or list. Compare against your starter checks from Day 4. Where does the AI's framing add detail vs over-engineer?

### Exercise 4 — Generate the Airflow DAG

Combine: take the Day 3 DAG sketch + the tiered checks from Exercise 2. Ask:

> *"Generate an Airflow 3.x DAG that:*
> *1. Runs the Soda checks from this YAML file daily at 06:30 UTC*
> *2. Routes failures to Slack, with severity-tier-aware messaging (page tier mentions @channel; notify tier doesn't)*
> *3. Continues running 'notify' tier checks even if 'page' tier checks fail*
> *4. Uses the TaskFlow API (`@dag` / `@task` decorators)*
> *5. Pulls the Slack webhook URL from an Airflow Variable*
>
> *Don't include code that doesn't relate to Soda execution and alerting. Return only the Python file."*

Review for: TaskFlow correctness; correct usage of Airflow 3 APIs (no `execution_date`, no SLAs); proper secrets handling; sensible task structure.

### Update your `.cursorrules`

```
Observability conventions:
- Default tier is 'notify', not 'page'. Paging is reserved for SLO-violating, customer-visible failures.
- Every check needs an owner and a defined success metric (would a 30-day audit show it firing on real issues?).
- SLI / SLO / error budget framing for any new alerting; don't alert on raw metric movement.
- Avoid the same check in multiple tools (pandera + dbt + Soda) — pick one place per concern.
- Soda Core v3 SodaCL is current; v4 is contract-based and breaking. Pin version.
- Airflow 3.x: use TaskFlow (@dag, @task). SLAs are removed; use callbacks. `execution_date` is gone; use `logical_date`.
- Slack alerting via incoming webhook; secrets via Airflow Variables, never in DAG code.
- Aggregate related check failures into one alert message; don't flood Slack.
- Suppression / maintenance windows are a feature you'll need; design for it from day one.
```

### Quality bar — when is a generated checks-file "good"?

- [ ] Every check has a comment explaining the failure mode it catches
- [ ] Thresholds are realistic for the stated data volumes (not absurdly high or low)
- [ ] At least one custom-SQL check captures a domain-specific rule (e.g., reconciliation)
- [ ] Tiering is reviewed: < 20% are 'page' (most should be 'notify' or 'log')
- [ ] Schema check covers structural changes but doesn't lock down every detail
- [ ] No anomaly checks (`anomaly_score`) on day one — they need history
- [ ] Output runs cleanly through `soda scan` (you actually executed it once)

### Reflection (write 3–5 sentences in `notes.md`)

- Did the AI generate sensible thresholds, or were they generic boilerplate?
- When you pushed back on alert tiering, did the AI revise meaningfully or just rearrange?
- Across Weeks 8–13, the AI Friday workflows have spanned synthesis, inference, debugging, scaffolding, and now ops design. Which is the highest-leverage for a junior engineer? For a senior?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 14. 5–7 = re-review. <5 = redo exercises.

1. Difference between testing, monitoring, and observability — explain in your own words.
2. Name the six pillars of data observability.
3. SLI vs SLO vs SLA — give one-sentence definitions.
4. Why does Soda Core run *production* data while pytest runs *test* data?
5. Three places "no NULL emails" might be checked (pandera, dbt, Soda) — pick the right home for it and why.
6. Two deployment models for Soda checks — pipeline-attached vs schedule-attached. When does each fit?
7. Alert fatigue — what causes it and what's the team-level consequence?
8. Why are most data quality alerts `notify` rather than `page`?
9. Airflow 3 removed the `sla` parameter. What's a workable replacement for "alert if this didn't finish by 7 AM"?
10. After AI generates a Soda checks file from your schema, the first thing you do is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about observability and alerting.

### IQ1. "How do you decide whether to add a data quality check?"

*What a good answer covers:*
- Identify the failure mode you're catching, specifically (not generic "data quality")
- Pick the right place: in-pipeline tests vs production observability checks
- Define the SLI and threshold realistically based on historical data
- Decide the tier — is this page, notify, or log?
- Identify the owner — who acts on it?
- Plan the success metric — how will you know in a month if the check is paying off?
- If you can't answer all of these, the check isn't ready

*Likely follow-up:* "What if you can't get historical data to set a threshold?" (Answer: deploy as `log` tier first; collect a few weeks of data; then promote with a real threshold. Don't deploy a `page` tier check on guesses.)

### IQ2. "Walk me through testing vs observability — when do you use each?"

*What a good answer covers:*
- **Testing** runs in CI before deploy. Catches anticipated failures with controlled fixture data. Block merge.
- **Observability** runs in production against real data. Catches *unanticipated* failures by tracking what *normal* looks like. Inform; don't block.
- They're complementary, not alternatives. Tests verify code; observability watches data.
- Concrete: pandera schema in CI catches schema bugs before deploy; Soda freshness check in production catches "upstream stopped sending data."
- Most failures get caught at *some* layer. The goal is short feedback loops at every layer.

*Likely follow-up:* "If you had to pick only one, which?" (Answer: tests, because they prevent shipping bugs in the first place. But the question is a false choice — any team operating on real data needs both. The proportion shifts: a small project may have lots of tests and minimal observability; a 100-table warehouse needs both heavily.)

### IQ3. "How do you handle alert fatigue?"

*What a good answer covers:*
- **Diagnose**: track alert volume, action rate, and signal-to-noise ratio. If most alerts are ignored, you have fatigue.
- **Tighten or remove**: a check firing weekly without a real underlying issue is a false-positive. Tighten threshold or downgrade tier.
- **Aggregate related alerts**: 12 schema checks failing together = one schema-broken alert, not 12.
- **Suppression**: maintenance windows, backfill awareness, time-of-day awareness.
- **Tiering discipline**: keep `page` tier small (< 5 alerts at most projects). Push everything else to `notify` or `log`.
- **Periodic review**: monthly audit of which alerts fired and how many were acted on. Promote useful ones, demote useless ones.

*Likely follow-up:* "What's your hard rule for whether a check earns a `page` tier?" (Answer varies by team, but a defensible answer: "If this fires at 3 AM, will customers notice within 4 hours? If not, it's `notify`, not `page`.")

### IQ4. "How would you set SLOs for a daily ETL pipeline?"

*What a good answer covers:*
- **Identify what matters to the consumer**. The downstream team or product cares about: when is the data ready? Is it complete? Is it accurate?
- **Pick SLIs that match**: freshness lag, row-count completeness, % rows passing schema check.
- **Set SLOs based on historical performance plus a margin**. If freshness has been < 4h on 99.5% of days for 6 months, set the SLO at 99% < 4h — achievable with margin.
- **Define error budget**: 99% < 4h means 1% can be > 4h, which is ~3.6 days/year. That's the budget. Spend it on: deployments, planned maintenance, occasional infrastructure failures.
- **Alert on budget burn rate**, not just SLI threshold. "Have we used 50% of our monthly budget in the first week? Investigate."
- **Review quarterly**. SLOs aren't static; tighten as the system improves.

*Likely follow-up:* "What if business demands a stricter SLO than your error budget allows?" (Answer: that's a conversation about cost. Either invest in reliability (more redundancy, better testing, faster fixes) — which costs engineering time — or accept a wider budget. Don't promise an SLO you can't keep; that's how trust dies.)

### IQ5. "How would you instrument a new pipeline for observability?"

*What a good answer covers:*
- **Day-zero checks**: row count > 0; schema as expected; freshness within budget. These catch the most common failures with minimum effort.
- **Tied to the orchestrator**: in your Airflow DAG, the last task is a Soda scan or equivalent. Failure = pipeline failure.
- **Logging**: structured logs that capture row counts at each stage, runtime, peak memory. These become the SLI history you need for SLOs.
- **Schedule-detached checks**: separately, a daily DAG that just runs the checks against production data. Catches drift even if the pipeline ran fine.
- **First month**: log everything, alert on nothing (or alert only the obvious failures). Watch what fires. Tune.
- **Second month**: graduate stable checks to `notify`. Identify the 1–3 critical paths that warrant `page`.
- **Quarterly review**: alert hygiene, threshold review, SLO compliance.

*Likely follow-up:* "What if the pipeline runs once an hour instead of once a day?" (Answer: hourly schedule means freshness checks are tighter, anomaly windows shorter. Volume thresholds need hour-of-day awareness — 3 AM has different volume than 3 PM. The principles are the same; the parameters change.)

---

## If you have extra time this week (stretch)

- Try [OpenLineage](https://openlineage.io/) — open-source standard for data lineage. Captures what your pipelines write/read at runtime; integrations with Airflow, Spark, dbt.
- Read the "Observability for Data Engineers" chapter of [Designing Data-Intensive Applications](https://dataintensive.net/) — broader context on monitoring distributed systems.
- Compare [Datadog](https://www.datadoghq.com/), [New Relic](https://newrelic.com/), [Grafana Cloud](https://grafana.com/) — three major commercial platforms. What does each pitch as differentiation? What's in their free tiers?
- Spin up [Astronomer's local Airflow environment](https://www.astronomer.io/docs/astro/cli/install-cli) and deploy your Day 3 DAG end-to-end. The first time you watch your code run on a real schedule and alert on a real failure, the abstractions click.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Observability. Tests catch anticipated failures with fixture data; production data is different from test data; observability watches the production system and notices when something has *changed* compared to normal. The test wasn't wrong — its scope was "does the code work as designed," and the code did. Observability's scope is "does production data look like we expect."
- **Q1.2** — Freshness, volume, schema, distribution, lineage, quality.
- **Q1.3** — Different layers catch different failure modes. Tests catch logic bugs in the code; observability catches drift, upstream changes, and unanticipated production behavior. Removing tests means more bugs ship; removing observability means production failures take longer to detect. They complement; they don't replace.
- **Q1.4** — Pattern: built without an action plan. To make it useful, define triggers ("when this column changes, notify these consumers"), automated impact analysis ("if this table is delayed, who's affected?"), or routine audits ("monthly review of unused tables"). Lineage is plumbing; it only matters when something flows through it.

### Day 2 answers

- **Q2.1** — Pick one. The right home depends on the failure mode you're catching: pandera for in-Python pipeline correctness; dbt tests for transformation correctness running with each build; Soda for production data quality monitoring on a schedule. Putting the same check in all three is maintenance debt with diminishing returns — a NULL email fix has to be made in three places.
- **Q2.2** — `failed rows` returns the actual rows that violated the check, which may include sensitive fields (emails, IDs, addresses). Mitigate by: redacting columns before the check fires; using `failed_count` instead of `failed_rows` for sensitive checks; ensuring the alert/log destination is appropriately access-controlled.
- **Q2.3** — Volume context. `row_count > 0` passes against any positive number. The check doesn't catch a 1000× volume drop. Use `row_count between X and Y` with realistic bounds, or `row_count > 0.5 * historical_baseline`.
- **Q2.4** — Anomaly detection compares today's value to the past. Without history, "the past" is empty and the comparison is undefined. The first scan establishes a baseline; subsequent scans evaluate against it. Plan for a quiet first 1–2 weeks of "anomaly checks not yet active."

### Day 3 answers

- **Q3.1** — *Pipeline-attached*: run after the pipeline produces data; failure blocks downstream consumers from seeing bad data. *Schedule-attached*: independent daily/hourly schedule on production data; catches drift, schema changes, freshness issues that happen between pipeline runs. Mature teams use both.
- **Q3.2** — Most data issues need attention but not at 3 AM. Page tier wakes someone; notify tier means "look at this Monday." Reserving page for SLO-violating, customer-impacting failures keeps the page volume low enough that pages get acted on. Treating every Soda failure as a page → alert fatigue → real pages get ignored.
- **Q3.3** — Alerting daily on a known issue is noise. Better: track alert state in a small persistent store; only re-alert on state change (started failing today, started passing again). The first day it fires, alert. Days 2–7 of the same failure: silent. The day it recovers: alert. Most observability platforms support this; if yours doesn't, a small custom layer in Airflow does it in 50 lines.
- **Q3.4** — Implement timing checks differently. Options: a separate "deadline" DAG that runs at the deadline time and alerts if the upstream DAG hasn't completed; a timing-check task at the end of the pipeline that compares actual runtime to budget and alerts if exceeded; manual implementation in callbacks. `DeadlineAlerts` is the planned future replacement but not yet generally available.

### Day 4 answers

- **Q4.1** — SLI = measurable signal (freshness lag in minutes). SLO = your team's target (lag < 240 minutes, 99% of days). SLA = external contract with consequences for breach (customer credit on violation).
- **Q4.2** — Alerts firing too often. Caused by: thresholds that are too tight; checks that catch real but acceptable variance; alerts for things nobody acts on; severity inflation; lack of suppression for expected events. Result: people stop reading alerts. Real failures get lost in the noise.
- **Q4.3** — Options: (a) tighten the threshold; (b) downgrade to `notify` or `log`; (c) remove the check; (d) aggregate with related checks. Usually best is the right combo of (a) and (d) — fix the false positives, group related signals. Removing is sometimes correct but feels like "giving up" — be honest if the check isn't worth the upkeep.
- **Q4.4** — Raw metric movement is constant; SLO violations are rare. Alerting on movement = constant alerts. Alerting on SLO violations = alerts only when the user-visible target is at risk. The latter is much more actionable and proportionally aligned with what you actually need to know.

### End-of-week answers

**A1.** Testing catches anticipated failures pre-deploy with fixture data. Monitoring tracks predefined system signals and alerts on threshold breaches. Observability is the broader discipline of building systems whose internal state is queryable enough to investigate failures you didn't anticipate.

**A2.** Freshness, volume, schema, distribution, lineage, quality.

**A3.** SLI = measurable signal. SLO = team target for that signal. SLA = external contract with consequences.

**A4.** Tests verify code with controlled inputs; production data is different and changes over time. Soda runs on the *actual* production data to catch what tests can't see.

**A5.** Pick one based on where the concern best fits: pandera for in-pipeline correctness, dbt for transformation correctness, Soda for production observability. Putting it in all three is maintenance debt without proportional benefit.

**A6.** Pipeline-attached: blocks downstream when pipeline fails (good for immediate-impact failures). Schedule-attached: catches drift / freshness / upstream changes between runs. Use both for production-grade pipelines.

**A7.** Caused by alerts firing too often without action. Consequence: team mutes the channel or stops reading; real failures get missed. Hard to recover from; better to prevent via discipline on threshold tuning, tiering, and aggregation.

**A8.** Page tier should be reserved for failures that are SLO-violating and customer-visible *right now*. Most data quality issues need daytime attention but not 3 AM paging. Pushing everything to `page` causes alert fatigue and devalues the page tier.

**A9.** Implement timing differently: a separate deadline-watching DAG; a timing-check task at the end of the pipeline; manual checks in callbacks. `DeadlineAlerts` is the future replacement but not yet generally available.

**A10.** Verify it. Run `soda scan` and confirm the YAML parses and runs. Inspect a few thresholds for realism. Tier the checks. Don't trust AI-generated thresholds without checking against your historical data.

---

*Done with Week 13? You can articulate the difference between testing and observability, write Soda checks that catch real production issues, integrate them into Airflow with appropriate alerting tiers, and design SLOs that don't burn out the on-call rotation. Onward to Week 14 — ML Testing Basics — where we shift from "is the data good?" to "is the model good?" — drift detection, prediction quality, and model performance over time.*
