# Week 14 — ML Testing Basics | Training Materials

> **Companion to:** Week 14 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Understand how testing a system that contains a machine-learning model differs from testing pure data pipelines. By Friday you'll know how to detect drift with Evidently, validate training data and find train-test leakage with deepchecks, write performance assertions on ML models, and articulate the fairness/explainability conversation without overselling either. The honest framing: most "ML in production" failures are data quality issues you've already learned to catch in Weeks 4 and 13. ML-specific testing is a smaller addition than the hype suggests.
>
> **Version notes (May 2026):**
> - **Evidently** has a new API since ≥0.7 (`from evidently import Report`, `from evidently.presets import DataDriftPreset`, `report.run(current, reference)`). Older tutorials reference a different API — verify you're using ≥0.7.
> - **deepchecks** 0.19.x is stable. Note: the open-source library is **AGPL 3.0** licensed — fine for in-house use; commercial redistribution needs a separate license. If your project is closed-source SaaS, check your legal team's read on AGPL before adopting.

---

## How to use this file

- This week is more conceptual than coding-deep — the framing matters more than memorizing every check
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday's AI workflow is design-flavored — generating a model-validation suite from a problem description
- Answers to all self-checks are at the bottom

---

## One-time setup (~5 minutes)

```bash
source .venv/bin/activate
pip install "evidently>=0.7" "deepchecks>=0.19" scikit-learn
```

Sanity check:
```bash
python -c "import evidently, deepchecks, sklearn; print('evidently', evidently.__version__, '| deepchecks', deepchecks.__version__, '| sklearn', sklearn.__version__)"
```

You should see `evidently 0.7+`, `deepchecks 0.19+`, `sklearn 1.5+` (or higher). The exercises use scikit-learn for a small classifier; you don't need to be a data scientist to follow them.

---

## Day 1 (Mon) — What's Different About Testing ML?

### Theory

Traditional software testing has a comfortable property: given the same input, the function returns the same output. Test once, trust forever. **ML systems break this.** A model trained on Monday's data and one trained on Tuesday's data may give different predictions for the same input — by design. This single fact unsettles every assumption about testing.

### The four kinds of "things" in an ML system

| Component | What it is | What testing means |
|---|---|---|
| **Training data** | Historical data the model learns from | Data quality, schema, distribution, no leakage |
| **Model** | The fitted parameters / weights | Predictions on held-out data, performance on edge cases |
| **Feature pipeline** | Code that transforms raw data into model inputs | Same as any data pipeline — Weeks 1–13 apply |
| **Inference service** | The runtime that serves predictions | Latency, throughput, error rate — standard service monitoring |

You'll be most involved with #1 and #3 in a data engineering / QA role. #2 is what data scientists own. #4 is shared with platform / SRE teams.

### Why traditional unit tests struggle

A model is a function `predict(x) → y`. You'd think you could write `assert predict(x_known) == y_expected`. Two problems:

1. **Models drift.** Today's model produces 0.73 for input X; tomorrow's retrained model produces 0.71. Both might be correct. A unit test asserting exact equality fails on every retraining.
2. **Models fail probabilistically.** A 95%-accurate classifier is wrong 5% of the time *by design*. A "test" that fires on any wrong prediction would alert constantly.

So ML testing shifts from "exact correctness" to **statistical properties**: "the model's accuracy on this held-out set is ≥ 80%," "predictions for the same input are within 5% across retrainings," "feature distributions haven't shifted by more than X."

### The Google "ML Test Score" framing

In 2017, Google researchers published *"The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction"* — still the most cited framing of ML testing concerns. Four categories:

1. **Tests for features and data** — schema validation, no leakage, expected distributions, no duplication, label correctness
2. **Tests for model development** — reproducibility, performance on slices, regression vs simpler baselines, overfitting checks
3. **Tests for ML infrastructure** — training pipeline runs end-to-end, model can be loaded and served, latency budgets met
4. **Monitoring tests** — feature distributions, prediction distributions, performance metrics over time, retraining triggers

For a QA / data engineer, **categories 1 and 4 are where most of your work lives.** Category 2 is the data scientist's domain; category 3 is shared.

### What ML failures actually look like in production

Real-world ML failures, from incident reports across various tech companies, fall into roughly these buckets:

| Failure mode | Frequency (from public post-mortems) | Caught best by |
|---|---|---|
| Upstream data schema changed | Very common | Data tests (Week 4, 13) |
| Training data quality issue (NULLs, duplicates) | Very common | Data tests + deepchecks integrity |
| Train-test contamination / data leakage | Common — and famous | deepchecks train-test validation |
| Distribution drift between train and serve | Common | Evidently drift + monitoring |
| Model performance regression on retrain | Common | Performance test in CI |
| Concept drift (the world changed) | Common but slow | Long-window monitoring |
| Adversarial / outlier inputs | Less common; high impact | Outlier detection + input validation |
| Fairness / bias regression | Stakeholder-driven; requires labels | Fairness audits + ongoing review |

**The takeaway**: most "ML failures" are data engineering failures with an ML system on the receiving end. The Week 4 and Week 13 skills are the foundation. ML-specific testing is the additional 20% on top.

### Drift — the term used three different ways

"Drift" is ambiguous; clarify when discussing:

- **Data drift** (also "feature drift," "covariate shift"): the *input* distribution changed. Your model still works as designed, but it's seeing inputs unlike its training data.
- **Prediction drift**: the *output* distribution changed. Model predictions look different than they used to. Could be a symptom of data drift, or genuinely different inputs.
- **Concept drift** (also "label drift"): the *relationship* between inputs and outputs changed. The world genuinely behaves differently than when the model was trained. (Hardest to detect; often needs labels or proxy metrics.)

When someone says "the model is drifting," ask which kind. The diagnosis path differs.

### Train-test leakage — the failure that ruins careers

Leakage means information from outside the training set has snuck into training, making the model look better than it is. Some forms:

- **Target leakage** — a feature is computed *after* the prediction would be made (e.g., a "completion_date" column when predicting whether an order will complete)
- **Train-test contamination** — same rows appear in train and test sets (often via duplicates or improper splitting)
- **Time leakage** — training on future data to predict the past (broken time-series split)
- **Group leakage** — a customer's data appears in both train and test (predictions are unfairly easy because the model has seen this customer)

Models with leakage often look great in development and fail catastrophically in production. **deepchecks's `train_test_validation` suite catches several of these classes automatically.** Day 3.

### Gotchas

1. **"More tests" is not the goal.** ML test value comes from coverage of failure modes, not raw count. A drift check + a leakage check + a performance regression check is often enough.
2. **Drift ≠ degradation.** Inputs can drift while accuracy stays fine; accuracy can drop while inputs look unchanged. Track both, but don't conflate them.
3. **Fairness audits need labels and a stakeholder.** They're meaningful when there's a regulatory requirement, a known protected class, and someone willing to act on results. Without those, "fairness" is theater.
4. **Reproducibility is a test, not a feature.** "If I retrain on the same data with the same seed, do I get the same model?" Not always — GPU non-determinism, library version changes, random splits. Tests should pin all of these.
5. **The training-serving skew problem.** Features are computed one way in the training pipeline, slightly differently in the serving pipeline. Famous bug class. Test by computing features both ways on identical inputs and asserting equality.

### Exercises (analysis day, no coding)

1. For each of these production failures, classify the type (data drift / prediction drift / concept drift / leakage / quality issue): (a) marketing model's predicted churn rate is suddenly 3x higher; (b) fraud detection accuracy drops after a new legitimate use case launches; (c) recommendation model recommends only one product to everyone; (d) loan approval model's training data accidentally contains the loan outcome.
2. For your e-commerce project, sketch how an ML system *could* be added (a churn predictor? recommended products? fraud scoring?). For each of the 8 failure modes above, would your hypothetical system be vulnerable? Which ones?
3. Read [Google — Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html). It's eight years old and still painfully accurate. Note which sections still match real-world experience.
4. **Draft (in `notes.md`) a one-page "ML Testing Plan"** for your hypothetical ML system: which Week 4/13 checks transfer? Which ML-specific checks add genuine value? What are your monitoring SLOs?

### External practice

- [Google — ML Test Score paper (2017)](https://research.google/pubs/pub46555/) — original rubric; still the canonical framing
- [Eugene Yan — Practical MLOps overview](https://eugeneyan.com/writing/practical-mlops/) — practitioner perspective, regularly updated
- [Made With ML — Testing](https://madewithml.com/courses/mlops/testing/) — course-level, walks through ML test categories
- [Andrej Karpathy — A Recipe for Training Neural Networks](https://karpathy.github.io/2019/04/25/recipe/) — debugging-focused; emphasizes test-the-pipeline-not-the-model

### Self-check (Day 1)

> Q1.1 — Why does "assert predict(x) == y" usually fail as an ML model test?
> Q1.2 — Three kinds of drift (data / prediction / concept) — give a one-line example of each.
> Q1.3 — Train-test leakage: what is it, and why does it look like a great-performing model?
> Q1.4 — Most production ML failures fall into which bucket — modeling errors, or data engineering errors?

---

## Day 2 (Tue) — Drift Detection with Evidently

### Theory

Evidently is an open-source Python library for evaluating ML data and predictions. The 80% use case is **drift detection**: compare two batches of data (typically a *reference* baseline and a *current* batch) and report which features changed.

### The minimal example

```python
import pandas as pd
from sklearn import datasets
from evidently import Report
from evidently.presets import DataDriftPreset

# Load some data
iris_data = datasets.load_iris(as_frame=True)
df = iris_data.frame

# Treat first 60 rows as "current," next 90 as "reference"
current = df.iloc[:60]
reference = df.iloc[60:]

# Build the report
report = Report([DataDriftPreset(method="psi")], include_tests=True)
result = report.run(current_data=current, reference_data=reference)

# View as HTML in Jupyter, or save to file
result.save_html("drift_report.html")
```

The HTML output is rich — per-column drift verdicts, distribution overlays, statistical test results. For tests, use `include_tests=True` to get explicit pass/fail status per check.

### Drift methods — what's appropriate when

Evidently auto-selects a method based on column type and sample size, but you can override:

| Method | Best for | Returns |
|---|---|---|
| **Kolmogorov-Smirnov (KS)** | Numerical, smaller samples (<1000) | p-value; drift if p < 0.05 |
| **Wasserstein distance** | Numerical, larger samples | Distance value; threshold-based |
| **Jensen-Shannon divergence** | Categorical or binned numerical | Distance 0–1; threshold-based |
| **Chi-square** | Categorical, smaller samples | p-value; drift if p < 0.05 |
| **PSI (Population Stability Index)** | Anything; popular in finance/credit | Distance; <0.1 = no drift, 0.1–0.25 = moderate, >0.25 = significant |

**PSI** is the default many teams use because the thresholds are widely interpreted and reasonably robust. K-S is more sensitive to small differences (false positives in production); Wasserstein is more interpretable.

### What you can detect

Evidently presets cover the common cases:

| Preset | Catches |
|---|---|
| `DataDriftPreset` | Feature distribution changes per column + dataset-level drift |
| `DataSummaryPreset` | Schema, missing values, descriptive statistics |
| `ClassificationPreset` | Model performance: accuracy, precision, recall, ROC, calibration |
| `RegressionPreset` | RMSE, MAE, error distribution |
| `TextEvalsPreset` | Text-specific drift, length / sentiment / language drift |

For drift detection on a daily ML pipeline, `DataDriftPreset` against a stable reference window is the workhorse.

### A realistic drift-detection workflow

```python
import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset, DataSummaryPreset


def daily_drift_check(current_df: pd.DataFrame,
                       reference_df: pd.DataFrame,
                       output_path: str) -> dict:
    """Run drift + data summary; return JSON results."""
    report = Report(
        [DataDriftPreset(method="psi"),
         DataSummaryPreset()],
        include_tests=True,
    )
    result = report.run(current_data=current_df, reference_data=reference_df)
    result.save_html(output_path)

    # Convert to dict for programmatic access (alerting, logging)
    return result.dict()


# Use it
reference_df = pd.read_parquet("data/orders_reference.parquet")  # last 30 days
current_df = pd.read_parquet("data/orders_today.parquet")

result = daily_drift_check(current_df, reference_df, "reports/drift_today.html")
# result is a Python dict; inspect for failed tests and alert
```

### Hooking drift into Airflow

Combining Day 13's Airflow patterns with Evidently:

```python
from airflow.decorators import task


@task(on_failure_callback=soda_failure_callback,
      params={"severity": "notify"})
def check_feature_drift():
    import pandas as pd
    from evidently import Report
    from evidently.presets import DataDriftPreset

    reference = pd.read_parquet("/opt/airflow/data/reference.parquet")
    current = pd.read_parquet("/opt/airflow/data/current.parquet")

    report = Report([DataDriftPreset()], include_tests=True)
    result = report.run(current_data=current, reference_data=reference)

    result_dict = result.dict()
    failed_tests = [t for t in result_dict.get("tests", []) if t.get("status") == "FAIL"]

    if failed_tests:
        names = ", ".join(t["name"] for t in failed_tests)
        raise ValueError(f"Drift detected in {len(failed_tests)} tests: {names}")
```

The same patterns from Week 13 — tier the alerts (drift is usually `notify`, not `page`), aggregate failures into one Slack message, suppress during known maintenance.

### Choosing the reference window

This is where most drift programs go wrong. Options:

- **Fixed reference** — use the training data as reference; never updates. Drift report tells you how far production has drifted from training. Good for catching slow concept drift.
- **Rolling window** — last 30 days as reference. Drift report tells you if today is unusual compared to recent history. Good for catching sudden changes.
- **Same-day-of-week** — for weekly seasonality, compare today to last 4 weeks of same weekday. Good for retail / consumer use cases.

Most teams use *both* — a rolling window for short-term monitoring + a fixed training-data reference for long-term degradation tracking. Two reports, two alerting tiers.

### Gotchas

1. **Reference window matters more than method.** A bad reference (too small, too noisy, not representative) makes any method give nonsense.
2. **Statistical tests are sensitive at scale.** With 1M+ rows, even tiny differences are "statistically significant." Use thresholds you can defend, not p < 0.05.
3. **One-off drift isn't always a problem.** A holiday, a marketing campaign, a known new product — these cause drift that's expected. Plan suppression / annotation.
4. **Categorical drift in unseen categories.** When production has a new value not in reference, some methods fail or give odd results. Configure a "new category" handler.
5. **Evidently HTML reports are heavy.** For 1000+ columns or large samples, reports can be tens of MB. Use the `dict()` or `json()` outputs for automation; reserve HTML for human investigation.

### Exercises

Create a `ml/` directory in your project.

1. From your e-commerce project, take 30 days of synthetic order data. Split: first 21 days = reference, last 9 days = current. Run a `DataDriftPreset` report. Open the HTML — what drifted, if anything?
2. **Inject drift deliberately:** modify "current" to skew `total_amount` 30% higher (multiply by 1.3) and add a new country `XX` not in reference. Re-run. Confirm the report flags both changes.
3. **Method comparison:** run the same drift check with `method="ks"`, `method="wasserstein"`, and `method="psi"`. Where do they agree? Where do they disagree? Read the per-method scores.
4. **Dataset-level vs column-level:** a `DataDriftPreset` reports both per-column drift verdicts and a dataset-level drift summary. Find the dataset summary section. When would you alert on dataset-level vs individual columns?
5. **Production simulation:** wrap the drift check in a function `daily_drift_check(current_df, reference_df, output_path)` returning a dict. Print out failed tests. This is what you'd embed in Airflow.
6. **Stretch:** download a public dataset that genuinely has drift (e.g., a sliced time-series dataset from Kaggle covering 2019 vs 2023). Run drift detection. The "real" drift is much messier than synthetic — useful calibration.

### External practice

- [Evidently AI documentation](https://docs.evidentlyai.com/) — current API
- [Evidently — How to detect data drift](https://www.evidentlyai.com/ml-in-production/data-drift) — practitioner guide
- [Madewithml — Drift detection](https://madewithml.com/courses/mlops/monitoring/) — broader monitoring framing
- [PSI explanation](https://towardsdatascience.com/psi-and-csi-top-2-model-monitoring-metrics-924a2540bed8) — math + intuition for the most common drift metric

### Self-check (Day 2)

> Q2.1 — Three reference-window strategies (fixed / rolling / same-day-of-week) — when does each fit?
> Q2.2 — At very large sample sizes, K-S and Chi-square tests give "drift detected" alerts constantly. Why? What do you switch to?
> Q2.3 — Drift was detected in `signup_country`. Three explanations besides "the data quality broke."
> Q2.4 — When would you treat dataset-level drift differently from column-level drift?

---

## Day 3 (Wed) — deepchecks for Integrity & Train-Test Validation

### Theory

deepchecks is the second major open-source ML testing library. It overlaps with Evidently but emphasizes different things:

| Library | Strength |
|---|---|
| **Evidently** | Drift detection, ongoing monitoring, comparison reports |
| **deepchecks** | Pre-training data integrity, train-test contamination/leakage, model evaluation suites |

Some teams use only one; many use both. They're not competitors so much as different tools for different stages.

### The deepchecks model

deepchecks organizes checks into **suites**:

| Suite | When to use |
|---|---|
| `data_integrity()` | Single dataset; before splitting or training. Catches duplicates, mixed types, special characters, single-value columns, etc. |
| `train_test_validation()` | Train + test datasets; catches leakage, drift between splits, label issues, new categories appearing only in test |
| `model_evaluation()` | Trained model + train + test datasets; performance, calibration, confusion matrix, simple-baseline comparison |
| `production_suite()` | Production model monitoring |
| `full_suite()` | All of the above; slow but comprehensive |

### Data integrity check

```python
import pandas as pd
from deepchecks.tabular import Dataset
from deepchecks.tabular.suites import data_integrity

df = pd.read_parquet("data/orders_train.parquet")

ds = Dataset(
    df,
    label="will_churn",          # if you have a label column
    cat_features=["country", "status"],
    datetime_name="signup_date",
)

suite = data_integrity()
result = suite.run(ds)
result.save_as_html("integrity_report.html")
```

What this catches (a partial list):
- **`DataDuplicates`** — exact-duplicate rows
- **`MixedNulls`** — different null markers in the same column (NaN, "", "null", "NA")
- **`MixedDataTypes`** — strings and numbers mixed in one column
- **`SpecialCharacters`** — unusual characters (zero-width spaces, control chars)
- **`StringMismatch`** — same logical value with different casing/whitespace ("US" vs "us " vs "Us")
- **`ConflictingLabels`** — identical feature rows with different labels (data quality red flag)
- **`IsSingleValue`** — column with only one distinct value (useless feature)
- **`PercentOfNulls`** — high null rate columns
- **`OutlierSampleDetection`** — rows that are far from the rest

That's a lot of checks for one function call. The output HTML groups them by status (passed / failed / didn't run) and surfaces failing-row examples.

### Train-test validation — the leakage detective

```python
from deepchecks.tabular.suites import train_test_validation

train_ds = Dataset(train_df, label="churn", cat_features=["country"], datetime_name="signup_date")
test_ds = Dataset(test_df, label="churn", cat_features=["country"], datetime_name="signup_date")

result = train_test_validation().run(train_ds, test_ds)
result.save_as_html("train_test_validation.html")
```

Checks include:
- **`DateTrainTestLeakageDuplicates`** — same date appears in both train and test (probably a bad time split)
- **`DateTrainTestLeakageOverlap`** — date ranges in train and test overlap
- **`IndexTrainTestLeakage`** — same primary key in both (the most basic leakage)
- **`NewCategoryTrainTest`** — categorical values in test but not in train (the model has never seen them)
- **`NewLabelTrainTest`** — label values in test that don't exist in train (classification only)
- **`FeatureLabelCorrelationChange`** — feature-to-label relationship changed between splits (concept drift signal)
- **`FeatureDrift`** / **`MultivariateDrift`** / **`LabelDrift`** — distribution differences

The "did we split data correctly?" question is genuinely answered here. Most data scientists do this by hand; deepchecks automates it.

### Model evaluation

If you have a trained model:

```python
from deepchecks.tabular.suites import model_evaluation

result = model_evaluation().run(train_ds, test_ds, model)
result.save_as_html("model_evaluation.html")
```

Includes performance metrics, calibration plots, confusion matrices, comparison to a baseline (usually a simple "always predict majority class" model — your trained model should beat this).

### Custom checks

The built-in checks are exhaustive. For domain-specific rules, write a custom check or use the `add_condition_*` family on existing checks:

```python
from deepchecks.tabular.checks import PercentOfNulls

# Customize the threshold
check = PercentOfNulls().add_condition_percent_of_nulls_not_greater_than(0.05)
result = check.run(ds)
```

### Combining the libraries

A workflow that uses both:

| Stage | Tool | Purpose |
|---|---|---|
| Pre-training data validation | deepchecks `data_integrity` | Catch quality issues |
| Train-test split validation | deepchecks `train_test_validation` | Catch leakage |
| Model evaluation in CI | deepchecks `model_evaluation` | Performance + sanity checks |
| Daily production drift | Evidently `DataDriftPreset` | Distribution monitoring |
| Long-term concept drift | Evidently with fixed reference | Slow degradation tracking |

### Licensing note

deepchecks is **AGPL 3.0**. For most internal use (your company runs it on your data, doesn't redistribute) it's fine. For SaaS products that include deepchecks behind a network boundary, consult your legal team — AGPL has implications. (The commercial Deepchecks Hub product offers proprietary licensing if you need it.)

This isn't unique to deepchecks — many quality libraries are AGPL or similar. Worth knowing.

### Gotchas

1. **`Dataset` constructor's `cat_features` matters.** If you don't pass it, deepchecks heuristically guesses; sometimes wrong. For categorical columns with numeric codes (e.g., `customer_segment = 1, 2, 3`), pass them explicitly or they'll be treated as numeric.
2. **Suites can be slow.** `full_suite()` on 1M rows can take minutes. For CI, use targeted check subsets (`data_integrity` only) and let `full_suite` run nightly.
3. **`OutlierSampleDetection` is heuristic.** It uses isolation forest; results vary. Tune thresholds rather than treating outliers as canonical.
4. **`ConflictingLabels` requires a label.** Without `label=` set, this check skips silently.
5. **HTML reports are heavy.** Embed result data via `result.value` or `result.to_json()` for automation; reserve HTML for humans.

### Exercises

1. Convert your e-commerce orders DataFrame into a `Dataset` object. Run `data_integrity()`. Read the report — does anything fail? (If your data is too clean, manually corrupt a few rows and re-run.)
2. **Force-fail exercises:** create three corrupted DataFrames, run `data_integrity` on each, confirm the right check fails:
   - One with 50 duplicate rows → `DataDuplicates` should fail
   - One with the same logical value spelled differently (`US`, `us`, `U.S.`) → `StringMismatch` should fail
   - One with 30% null in a column → `PercentOfNulls` should warn or fail
3. **Build a leakage scenario:** generate orders. Split *poorly* — randomly into 80/20 (instead of by date). Run `train_test_validation()`. What does it find?
4. **Time-leakage exercise:** split by date but accidentally include a few overlapping days. Confirm the `DateTrainTestLeakageOverlap` check fires.
5. **Train a tiny model:** logistic regression on whether a customer's order_count > 5. Run `model_evaluation()`. Note especially the `SimpleModelComparison` check — does your model beat "always predict majority class"?
6. **Stretch:** combine Evidently and deepchecks in a single pre-train-validation pipeline. deepchecks for integrity + leakage on the train/test split; Evidently for drift between training data and a separate "out-of-time" sample. Document the workflow.

### External practice

- [Deepchecks documentation](https://docs.deepchecks.com/) — current
- [Deepchecks tutorials](https://docs.deepchecks.com/stable/tabular/auto_tutorials/quickstarts/index.html) — quickstarts for each suite
- [Train-test leakage examples](https://www.kaggle.com/discussions/general/152327) — real Kaggle stories of leakage; instructive
- [Patterns of data leakage in production](https://eugeneyan.com/writing/data-leakage/) — Eugene Yan's practical taxonomy

### Self-check (Day 3)

> Q3.1 — Difference between `data_integrity` and `train_test_validation` suites — when does each fit?
> Q3.2 — `DataDuplicates` failed on a single dataset. Three plausible reasons (data, ETL, sampling).
> Q3.3 — Train-test leakage: name three classes deepchecks detects automatically.
> Q3.4 — Why is `SimpleModelComparison` check (compare your model to a trivial baseline) a useful sanity check?

---

## Day 4 (Thu) — Performance Testing for ML Models

### Theory

Even if data quality is perfect and there's no drift, your model can degrade on its own — algorithmic issues, hyperparameter regressions, retraining bugs, library upgrades. The standard testing approach: **assert performance on a holdout set, fail if it regresses below threshold.**

### The classification metrics you must know

For a binary classifier (positive/negative class):

| Metric | Definition | When it matters |
|---|---|---|
| **Accuracy** | (TP + TN) / total | Class balance ~50/50; rarely the right metric otherwise |
| **Precision** | TP / (TP + FP) | When false positives are costly (false fraud accusation, unnecessary medical test) |
| **Recall** | TP / (TP + FN) | When false negatives are costly (missing fraud, missing disease) |
| **F1** | 2 * P * R / (P + R) | Balanced summary; harmonic mean |
| **ROC-AUC** | Area under ROC curve | Threshold-independent; robust to class imbalance |
| **PR-AUC** | Area under precision-recall curve | Better than ROC-AUC for very imbalanced classes |
| **Calibration** | Predicted probabilities match observed frequencies | When you use probabilities (not just predictions) downstream |

For regression:

| Metric | Definition | Notes |
|---|---|---|
| **MAE** | mean(\|actual - predicted\|) | Robust; same units as target |
| **RMSE** | sqrt(mean((actual - predicted)²)) | Penalizes large errors more |
| **R²** | 1 - SSres/SStot | "% variance explained"; dimensionless |

### Asserting performance in tests

The standard pattern:

```python
import pytest
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def test_model_meets_minimum_accuracy(trained_model, X_test, y_test):
    predictions = trained_model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    assert accuracy >= 0.80, f"Accuracy {accuracy:.3f} below threshold 0.80"


def test_model_does_not_regress(trained_model, X_test, y_test, baseline_metrics):
    """Compare against a saved baseline; alert if substantial regression."""
    predictions = trained_model.predict(X_test)
    f1 = f1_score(y_test, predictions, average="weighted")

    baseline_f1 = baseline_metrics["f1"]
    assert f1 >= baseline_f1 - 0.02, (
        f"F1 {f1:.3f} regressed >2 points from baseline {baseline_f1:.3f}"
    )


def test_model_beats_majority_baseline(trained_model, X_test, y_test):
    """Sanity: your trained model must beat 'always predict majority'."""
    from collections import Counter
    majority_class = Counter(y_test).most_common(1)[0][0]
    majority_baseline_acc = sum(1 for y in y_test if y == majority_class) / len(y_test)

    actual = accuracy_score(y_test, trained_model.predict(X_test))
    assert actual > majority_baseline_acc + 0.05, (
        f"Model accuracy {actual:.3f} barely beats majority baseline {majority_baseline_acc:.3f}. "
        "Probably overfit on noise or training data is too imbalanced."
    )
```

The third test — beating a majority baseline — is unsexy but catches a surprising number of real failures. Models trained on heavily imbalanced data can have 95% accuracy by predicting the majority class on every input; useless in practice. Asserting > majority + 5% catches this.

### Slice-based performance tests

Aggregate metrics can hide systematic failures. A model that's 90% accurate overall but 50% accurate on customers from country X is a problem your overall test won't catch. Slice tests:

```python
import pandas as pd


def test_performance_per_country(trained_model, X_test, y_test):
    # Get country slice info from the test data
    countries = X_test["country"].unique()
    failures = []
    for country in countries:
        mask = X_test["country"] == country
        if mask.sum() < 50:
            continue   # too few rows to be meaningful

        slice_acc = accuracy_score(
            y_test[mask],
            trained_model.predict(X_test[mask])
        )
        if slice_acc < 0.70:
            failures.append((country, slice_acc, mask.sum()))

    assert not failures, (
        f"Per-country accuracy below 0.70 for: "
        + ", ".join(f"{c} ({a:.2f}, n={n})" for c, a, n in failures)
    )
```

This catches "systematic failures on a sub-population" — usually a stronger signal than aggregate accuracy.

### Calibration

For models whose probability outputs you use (not just final predictions):

```python
from sklearn.calibration import calibration_curve
import numpy as np


def test_model_is_well_calibrated(trained_model, X_test, y_test, max_calibration_error=0.10):
    proba = trained_model.predict_proba(X_test)[:, 1]
    fraction_pos, mean_pred = calibration_curve(y_test, proba, n_bins=10)

    # Expected: in the bin where mean_pred = 0.7, fraction_pos should be ~0.7
    max_error = np.max(np.abs(fraction_pos - mean_pred))
    assert max_error <= max_calibration_error, (
        f"Calibration error {max_error:.3f} exceeds threshold {max_calibration_error}"
    )
```

Calibration matters when you use probabilities for thresholding ("only show recommendations with confidence > 0.8") or for downstream decisions. A 0.7-confidence prediction should be right ~70% of the time. If it's right 50% of the time, your "0.8 confidence" threshold is meaningless.

### Performance over time

For a model in production, you want to track performance trends:

```python
import pandas as pd
from datetime import datetime


def test_weekly_performance_does_not_regress(this_week_metrics, last_4_weeks_metrics):
    """Compare this week's metrics to a rolling baseline."""
    rolling_mean_f1 = pd.Series([w["f1"] for w in last_4_weeks_metrics]).mean()
    this_f1 = this_week_metrics["f1"]

    assert this_f1 >= rolling_mean_f1 - 0.05, (
        f"This week's F1 {this_f1:.3f} dropped >5 points from 4-week avg {rolling_mean_f1:.3f}"
    )
```

This is the kind of check that catches concept drift gradually — the world changing slowly, the model getting slowly worse.

### Fairness checks — when they matter

Fairness audits assess whether a model's performance differs across protected groups (race, gender, age, geography). They matter when:

- **Regulatory requirement**: credit, hiring, healthcare, education
- **Stakeholder-driven**: a product team or compliance team wants to assess
- **Brand or reputational risk**: visible model in customer-facing product

A basic fairness check:

```python
def test_recall_parity_across_genders(model, X_test, y_test, max_disparity=0.10):
    """Equal opportunity: recall should be similar across protected groups."""
    from sklearn.metrics import recall_score

    male_mask = X_test["gender"] == "M"
    female_mask = X_test["gender"] == "F"

    recall_m = recall_score(y_test[male_mask], model.predict(X_test[male_mask]))
    recall_f = recall_score(y_test[female_mask], model.predict(X_test[female_mask]))

    disparity = abs(recall_m - recall_f)
    assert disparity <= max_disparity, (
        f"Recall disparity {disparity:.3f} between gender groups exceeds {max_disparity}. "
        f"Male: {recall_m:.3f}, Female: {recall_f:.3f}"
    )
```

There are dozens of fairness metrics (demographic parity, equalized odds, equal opportunity, predictive parity). Pick *one* that matches your team's policy decision. The technical choice should follow the policy, not vice versa.

**Honest advice:** don't write fairness tests just to look responsible. Either there's a stakeholder driving requirements (then write the right tests for *their* policy) or there isn't (then your tests have no defined success metric and will be removed in 6 months).

### Gotchas

1. **Threshold choice changes everything.** A model's "accuracy" depends on the cutoff threshold. Test at the threshold you actually use in production, not 0.5 by default.
2. **Imbalanced classes hide problems.** A 99% accurate model on a 99/1 dataset may be useless. Always check confusion matrix, not just accuracy.
3. **Calibration drift is sneaky.** A model can stay accurate while becoming poorly calibrated. If you use probabilities downstream, monitor calibration explicitly.
4. **Slice tests can fail flakily.** Slices with too few samples produce noisy metrics. Set a minimum sample size per slice (e.g., n ≥ 50) before testing.
5. **Performance test budget.** Tight thresholds catch real regressions but fail randomly on noise. Allow 1–2 percentage points of noise; alert on persistent regressions, not single-run dips.

### Exercises

1. Train a simple binary classifier on synthetic e-commerce data (e.g., predicting `total_amount > 100`). Use logistic regression — exact algorithm doesn't matter for testing exercises.
2. Write `test_minimum_accuracy`, `test_beats_majority_baseline`, `test_does_not_regress` (against a saved baseline JSON). Run all three. Confirm at least the second passes; tune the others to be appropriate for your data.
3. **Slice test:** the e-commerce dataset has `country` as a categorical. Write a slice test that asserts per-country accuracy ≥ 0.65 for any country with ≥ 50 test samples. Trip it deliberately by training on data heavily skewed toward one country.
4. **Calibration:** plot a calibration curve. Compute the max calibration error. Is your model well-calibrated? If not, try `CalibratedClassifierCV` from sklearn.
5. **Performance regression test:** save your current model's metrics as `baseline.json`. Retrain with intentionally worse hyperparameters. Run the regression test — confirm it fails.
6. **Stretch:** implement a "concept drift" simulation. Save metrics weekly for 4 weeks; in week 5, alter the underlying data distribution. Confirm your `test_weekly_performance_does_not_regress` catches it.

### External practice

- [scikit-learn — model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html) — comprehensive metrics reference
- [Aequitas — fairness audit toolkit](http://aequitas.dssg.io/) — structured fairness analysis
- [Made With ML — Evaluation](https://madewithml.com/courses/mlops/evaluation/) — modern course material on model evaluation
- [Made With ML — Slicing](https://madewithml.com/courses/mlops/evaluation/#slicing) — slice-based testing in depth

### Self-check (Day 4)

> Q4.1 — Three reasons accuracy alone is a misleading metric.
> Q4.2 — A model is 90% accurate overall but 60% accurate on customers from one region. Why might your aggregate test miss this?
> Q4.3 — When does calibration matter, and when can you ignore it?
> Q4.4 — When do fairness tests add value, and when are they "looking responsible" theater?

---

## Day 5 (Fri 🤖) — AI Workflow: Generate an ML Validation Suite

### What you're learning today

Designing a validation suite for an ML system from scratch is genuinely hard — you have to think about data quality, drift, leakage, performance, fairness, and pick a defensible subset given finite engineering time. AI is good at the breadth (covering all the angles) and OK at the depth (specific thresholds need your domain knowledge).

### Setup

Reuse the `anthropic` setup from Weeks 8–13.

### Exercise 1 — Generate a per-stage validation plan

For your hypothetical ML system from Day 1, paste the problem to Claude:

> *"I'm building a customer churn prediction model. Inputs: 50 customer features (demographics, usage patterns, support history). Output: probability of churning in next 30 days. Training data: ~100K customers; daily inference on ~10K active customers.*
>
> *Generate a 4-stage validation plan covering: (1) pre-training data validation, (2) train-test split validation, (3) model evaluation in CI, (4) daily production monitoring.*
>
> *For each stage, list 5–8 specific checks with: tool (Evidently, deepchecks, custom Python), specific check name, threshold or condition, alert tier (page/notify/log), failure mode it catches.*
>
> *Be opinionated; don't list every possible check. Aim for the 20% of checks that catch 80% of issues."*

The AI will produce a structured plan. Review for:
- **Are the tools right?** Day 2/3 covered Evidently for drift, deepchecks for integrity/leakage. Did the AI use them appropriately?
- **Are thresholds defensible?** "Accuracy ≥ 0.85" is fine if your data supports it. AI may invent thresholds without justification.
- **Are tiers proportional?** From Week 13: most checks should be `notify`, not `page`. AI tends to over-classify as critical.
- **Is anything missing?** Slice-based performance? Calibration? Concept drift over weeks?

### Exercise 2 — Generate the actual code

Take one stage from Exercise 1's plan (say, "pre-training data validation") and ask:

> *"Given this validation plan stage, generate the actual Python code using deepchecks 0.19.x. The code should:*
> *- Define the Dataset object with appropriate cat_features and label*
> *- Run a `data_integrity` suite*
> *- Programmatically inspect failures (don't rely on HTML report alone)*
> *- Raise a clear error if specific critical checks fail*
> *- Return a summary dict for logging*
>
> *Plan stage:*
> *[paste from Exercise 1]*
>
> *Return only the Python code; no commentary."*

Verify the code:
- Imports match deepchecks 0.19.x layout (`from deepchecks.tabular import Dataset`, etc.)
- The check names referenced exist in the library
- The threshold conditions use the right `add_condition_*` helpers
- Run it on real data; confirm at least one failure case fires

### Exercise 3 — Slice-test design

Slice tests are easy to overlook. Ask Claude:

> *"For my churn prediction model, suggest 5 meaningful slices for performance testing — slices where the model might have systematic blind spots and we'd want to test separately. For each slice, give: (1) the slice definition, (2) why it matters, (3) the metric and threshold to test, (4) how to handle slices with too few samples.*
>
> *Be opinionated about which slices are most likely to catch real problems."*

You'll get something like: country/region; tenure (new vs old customers); product tier (free vs paid); engagement quartile; primary feature missingness pattern. The AI is good at this brainstorming; you decide which to actually implement.

### Exercise 4 — Drift threshold calibration

You have 30 days of production data; you want to set drift thresholds that fire on real shifts but not noise. Ask:

> *"Here are PSI scores per feature for the last 30 days [paste a sample CSV]. Help me set drift alert thresholds. For each feature:*
> *- Suggest a 'warn' threshold (firing on sustained drift)*
> *- Suggest a 'fail' threshold (firing on dramatic drift)*
> *- Justify with reference to the historical distribution shown*
>
> *If a feature shows clearly bimodal or seasonal behavior, flag that — its drift threshold should account for variance, not just absolute level."*

This is the kind of judgment call AI does reasonably well *given the data*. Without data, AI generates thresholds from generic priors — usually wrong for your specific feature. Always provide the historical data for threshold-tuning prompts.

### Update your `.cursorrules`

```
ML testing conventions:
- Most ML failures are data engineering failures. Apply Week 4 / 13 patterns first; ML-specific tests are additive.
- Always include `SimpleModelComparison` (or equivalent) — model must beat trivial baseline.
- Never assert exact prediction equality (predict(x) == y); use threshold-based assertions.
- Performance tests: aggregate metric + per-slice metrics + calibration (when probabilities matter).
- Drift detection is necessary but not sufficient — drift doesn't always mean degradation.
- Reference window choice matters more than drift method. Document choice; review quarterly.
- Fairness tests need a stakeholder and policy. Don't write fairness tests just to look responsible.
- Tier alerts: drift alerts default to `notify` (rarely page); performance regression to `notify`; sanity-baseline failures to `page` (something is fundamentally wrong).
- Library API check: Evidently ≥0.7 has new API; deepchecks 0.19.x is current; sklearn metrics are stable.
```

### Quality bar — when is a generated ML validation suite "good"?

- [ ] Tools chosen appropriately (Evidently for drift, deepchecks for integrity, sklearn for metrics)
- [ ] Thresholds defensible — either provided historical data or marked as TBD with a note to calibrate
- [ ] Per-slice performance tests included, not just aggregate
- [ ] Calibration check if probabilities are used downstream
- [ ] No fairness theater — fairness tests only if stakeholder driven
- [ ] Sanity baseline (beat majority class / trivial model) included
- [ ] Tier discipline: < 20% of checks are `page`; most are `notify` or `log`

### Reflection (write 3–5 sentences in `notes.md`)

- Did the AI know modern Evidently / deepchecks APIs, or did it use older patterns? (Common AI failure: using ≤0.6.7 Evidently syntax.)
- For threshold calibration with provided data, was the AI's reasoning sound? Or did it just suggest "use 0.1" by default?
- Compared to Weeks 8–13, this Friday's AI workflow required more *judgment* and less code generation. Did the AI hold up?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 15. 5–7 = re-review. <5 = redo exercises.

1. Why doesn't `assert predict(x) == y_expected` work as a model test?
2. Three kinds of drift (data / prediction / concept) — give a one-line distinction for each.
3. Train-test leakage: name three sub-classes deepchecks detects.
4. Most ML failures fall into which bucket — modeling errors or data engineering errors?
5. What's the appropriate use case for Evidently vs deepchecks?
6. Why is reference-window choice more important than drift-detection method?
7. A model is 90% accurate. Three reasons this could still be a bad model.
8. When do calibration tests matter, and when can you ignore them?
9. Fairness tests: what conditions make them genuinely useful, and what makes them theater?
10. After AI generates an ML validation suite, the first thing you do is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about ML testing.

### IQ1. "How is testing an ML system different from testing a traditional software system?"

*What a good answer covers:*
- Traditional tests are deterministic — same input, same output, exact equality assertions
- ML systems are probabilistic — same input may give different predictions across retrainings; performance has natural noise
- Shift to statistical assertions — "accuracy ≥ 0.85" instead of "predict(x) == y"
- Need to test data, model, pipeline, and serving — multiple components, multiple failure modes
- Drift is a new failure category — model can be correct, code can be unchanged, but the world changed
- Reproducibility is harder — depends on random seeds, library versions, hardware

*Likely follow-up:* "What's the same?" (Answer: data validation, schema enforcement, integration testing of the pipeline, CI/CD discipline. Most of the testing work is identical to non-ML data engineering. The ML-specific tests are 20% on top, not a wholesale replacement.)

### IQ2. "Walk me through how you'd validate training data before training a model."

*What a good answer covers:*
- **Schema validation**: types match expected, required columns present
- **Quality checks**: no unexpected nulls, no duplicates, no logically impossible values, consistent encoding
- **Distribution sanity**: check feature distributions look reasonable (not all-zero, not single-value)
- **Label quality**: no conflicting labels (same features, different labels — data error); class balance
- **Train-test split validation**: no leakage, splits are stratified appropriately, no temporal contamination
- **Tools**: deepchecks `data_integrity` and `train_test_validation` automate most of this; pandera/Great Expectations for schema; Evidently for distribution comparison

*Likely follow-up:* "What's the most common training data issue you've seen?" (If you have experience: share. Otherwise: "I've read that label leakage is the most expensive bug — features computed after the label should have happened — and deepchecks's leakage suite specifically targets it.")

### IQ3. "Walk me through how you'd monitor a model in production."

*What a good answer covers:*
- **Input distribution monitoring**: drift detection between production and training/recent reference. Evidently's PSI or equivalent.
- **Prediction distribution monitoring**: are predictions changing in unexpected ways? Could indicate data drift or model issues.
- **Performance monitoring with delayed labels**: when ground truth becomes available (next day, week, month), compute actual accuracy/F1 on that batch; alert on regression.
- **Slice monitoring**: don't just track aggregate; track key segments (geography, customer tier).
- **Service-level monitoring**: latency, throughput, error rate — standard infra monitoring.
- **Alert tiering**: most monitoring failures are `notify`-tier (look at this Monday); reserve `page` for service outages and clear catastrophic regressions.

*Likely follow-up:* "What if you don't have ground-truth labels for production data?" (Answer: rely on input/prediction drift as proxy. They don't directly measure performance but they correlate. Combine with periodic manual labeling of samples for ground-truth checks.)

### IQ4. "How do you decide when to retrain a model?"

*What a good answer covers:*
- **Triggered by drift**: significant input drift suggests the model's training data no longer matches production; retrain.
- **Triggered by performance regression**: sustained drop in accuracy/F1 vs baseline → retrain.
- **Scheduled**: weekly/monthly cadence regardless of drift, to incorporate new data.
- **Triggered by major events**: new product launch, market change, regulatory update.
- **Cost considerations**: retraining isn't free — compute, validation, deployment risk. Don't retrain reactively to every drift alert.
- **Canary deployment**: when retraining, deploy alongside the current model to a subset of traffic; compare; promote only if it wins.

*Likely follow-up:* "What if retraining makes the model worse?" (Answer: rollback. Always have the previous model available; canary deployments make detection easy. Have a documented rollback procedure. The hardest part of MLOps is the boring discipline around deployment, not the modeling.)

### IQ5. "How would you test for fairness in a model?"

*What a good answer covers:*
- **First, define fairness with stakeholders.** Different definitions (demographic parity, equalized odds, equal opportunity) lead to different metrics and conflicting decisions. The technical choice follows policy.
- **Identify protected groups**: who matters for this product/regulation/policy.
- **Compute slice metrics**: performance metrics per group; compare disparities.
- **Common metrics**: recall parity (false-negative rate similar across groups), precision parity, demographic parity (selection rate parity).
- **Set thresholds**: e.g., max 10% disparity in recall across groups.
- **Audit periodically**: not a one-time test; performance can drift unequally across groups.
- **Have a remediation path**: what do you do if a fairness check fails? Reweight training data? Adjust thresholds per group? Don't write tests without a plan for response.

*Likely follow-up:* "When wouldn't you implement fairness tests?" (Answer: when there's no protected class in scope, no regulatory or policy requirement, no stakeholder asking for them, and no remediation path. Writing fairness tests without those is performative — they'll quietly stop running and won't be acted on.)

---

## If you have extra time this week (stretch)

- Try [Aequitas](http://aequitas.dssg.io/) — a fairness audit toolkit. More structured than rolling your own slice tests.
- Read [Patterns of Data Leakage](https://eugeneyan.com/writing/data-leakage/) by Eugene Yan — concrete taxonomy with examples.
- Explore [SHAP](https://shap.readthedocs.io/) for model explainability. Useful for "why did the model predict this?" debugging in production.
- Watch [Andrej Karpathy — A Recipe for Training Neural Networks](https://karpathy.github.io/2019/04/25/recipe/) — debugging framing transfers well to broader ML testing thinking.
- Skim [Google's TFX](https://www.tensorflow.org/tfx) — production ML platform. Heavyweight but the components map cleanly to what we've covered (data validation, transform, train, eval, push to serving).

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Models drift across retrainings; the same input may produce slightly different outputs after each retrain. Models also fail probabilistically by design — a 95%-accurate model is wrong 5% of the time on individual examples. Exact-equality assertions break on every retraining and fire constantly even when the model is healthy.
- **Q1.2** — *Data drift*: marketing channel mix shifts from email to social, so signup feature distributions look different. *Prediction drift*: churn model's predicted-positive rate doubles from 5% to 10% week-over-week. *Concept drift*: the relationship between "customer paid late once" and "customer will churn" changes after a UX redesign that made payment easier.
- **Q1.3** — Information from outside the training set leaks in, making the model look better than it is. Common forms: target leakage (a feature computed after the label happens), train-test contamination (same rows in both splits), time leakage (training on future data), group leakage (same customer in both splits). Looks great in dev because the model has unfair information; fails in production when that information isn't available.
- **Q1.4** — Data engineering errors. Most production ML failures are upstream data quality, schema changes, or training-serving skew — not modeling errors. The Week 4 and Week 13 skills are the foundation; ML-specific testing is the additional 20%.

### Day 2 answers

- **Q2.1** — *Fixed reference* (training data): catches slow drift from the world the model was trained on; long-term degradation. *Rolling window* (last 30 days): catches sudden changes; today vs recent normal. *Same-day-of-week* (last 4 weekdays): for seasonal data; controls for weekly cycles. Most teams use multiple references for different alert tiers.
- **Q2.2** — Statistical tests like K-S and Chi-square are very sensitive at large N — even tiny distribution differences become statistically significant. Switch to magnitude-based metrics like PSI (with thresholds 0.1 / 0.25), Wasserstein distance, or Jensen-Shannon divergence — all of which return distance values rather than p-values, so you can set defensible thresholds.
- **Q2.3** — Beyond data quality: (1) genuine business change (new market entry, marketing campaign in a new country); (2) sampling bias in either reference or current (different time-of-day or user-segment sampling); (3) upstream parsing or normalization change (an ETL update changed how country codes are encoded).
- **Q2.4** — Column-level: a single feature drift suggests an upstream change for that one signal — investigable, often fixable. Dataset-level: many features drifted simultaneously suggests a broader shift (population change, sampling change) — harder to attribute to one cause. Different alerting and triage paths.

### Day 3 answers

- **Q3.1** — `data_integrity` runs on a single dataset; appropriate for fresh data before splitting or training. `train_test_validation` runs on two datasets (train + test); appropriate for catching split-related issues like leakage, distribution mismatches, label drift.
- **Q3.2** — (1) Source data has true duplicates (a system that re-emits events). (2) ETL bug: a join created cross-product or didn't deduplicate. (3) Sampling: when reservoir-sampling for an analytics pipeline, the same row was sampled twice due to a seed bug.
- **Q3.3** — Several valid: target leakage; index/key duplication across splits; date overlap (train and test cover same time period); new categories in test that aren't in train. deepchecks's `train_test_validation` automates several of these.
- **Q3.4** — Catches a common failure mode: a "trained" model that doesn't actually beat trivial baselines. Often caused by extreme class imbalance (model predicts majority class) or features that don't actually carry signal. Without this sanity test, models with 95% "accuracy" can be useless in production.

### Day 4 answers

- **Q4.1** — (1) Imbalanced classes: 99% accuracy on a 99/1 dataset is trivial. (2) Slice asymmetry: 90% overall but 50% on a key segment is a real problem. (3) Calibration: 90% accurate predictions can still be poorly calibrated, breaking downstream probability-thresholding.
- **Q4.2** — Slices with smaller sample sizes get drowned out in aggregates. If 80% of your test set is from one country and that country gets 95% accuracy, the aggregate is high even if other countries are at 50%. Slice tests catch this.
- **Q4.3** — Matters when downstream uses probability outputs (thresholding for "show recommendations only above 0.8 confidence"). Doesn't matter when you only use final predictions (predict positive/negative, ignore probabilities). Calibration can drift independently of accuracy — track it explicitly when probabilities matter.
- **Q4.4** — Genuine when there's a regulatory requirement, a known protected class, a defined fairness policy, and a remediation path. Theater when none of those exist — the tests have no defined success metric and no one acts on results. Better to skip than to perform.

### End-of-week answers

**A1.** Models drift across retrainings; predictions are probabilistic by design. Exact-equality assertions fail constantly. ML testing shifts to statistical assertions on aggregate behavior.

**A2.** Data drift = inputs changed. Prediction drift = outputs changed. Concept drift = the relationship between inputs and outputs (the underlying world) changed.

**A3.** Index leakage; date/time overlap; new categories in test absent from train; target leakage where a feature is computed after the label happens.

**A4.** Data engineering. Schema changes, data quality issues, training-serving skew dominate production ML failures.

**A5.** Evidently — drift detection, ongoing comparison reports, monitoring. Deepchecks — pre-training data integrity, train-test contamination/leakage, model evaluation suites. Some teams use both at different stages.

**A6.** Method differences are small at the margin; reference window differences are large. A bad reference (too small, too noisy, not representative) makes any method give bad results. Decide reference strategy first.

**A7.** Imbalanced classes (90% on a 90/10 split is trivial); systematic failure on key slices; poor calibration; overfit to test data; test set itself is a poor proxy for production.

**A8.** Matters when downstream uses probabilities for thresholding or ranking. Doesn't matter when only final predictions are used.

**A9.** Useful: regulatory or policy requirement, defined protected class, stakeholder driving the decision, remediation path. Theater: writing fairness tests without those — they'll quietly stop running and never be acted on.

**A10.** Verify it. Run the code; check if the API matches current Evidently/deepchecks; confirm thresholds are defensible against your historical data; tier alerts properly. AI is good at breadth, weak at thresholds without data.

---

*Done with Week 14? You can describe how ML testing differs from traditional testing, write drift checks with Evidently, run integrity and leakage suites with deepchecks, write performance assertions including slice-based and calibration tests, and articulate when fairness tests add value vs perform theater. Onward to Week 15 — the End-to-End Capstone Project — where everything from the past 14 weeks comes together into a portfolio-grade artifact.*
