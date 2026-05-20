# Week 2 — Python for Testing | Training Materials

> **Companion to:** Week 2 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Become fluent in the Python patterns you'll use daily — pandas for inspecting data, pytest for asserting on it.

---

## How to use this file

- Each day has four blocks: **Theory → Gotchas → Exercises → Self-check**
- Don't skim the gotchas — pandas has more silent-failure traps than SQL does
- Friday is **hands-on AI workflow practice**, not a passive read
- Answers to all self-checks are at the bottom of the file (no peeking 🙂)

---

## One-time setup (~20 minutes, do this before Monday)

### 1. Python environment

You need Python 3.10+ and a project folder. Pick whichever virtual-env approach you already know — if you don't have one, this works everywhere:

```bash
mkdir week2-python-testing && cd week2-python-testing
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install pandas pytest
```

Sanity check:
```bash
python -c "import pandas as pd, pytest; print(pd.__version__, pytest.__version__)"
```

You should see something like `2.2.x 8.x.x`. If pandas is < 2.0, **upgrade** — the nullable types (`Int64`, `Float64`, `string`) only behave correctly from 2.0 onward.

### 2. Editor

Anything that runs Python is fine. Recommended:
- [**VS Code**](https://code.visualstudio.com/) with the Python extension (free, ubiquitous)
- [**Cursor**](https://cursor.sh/) — VS Code fork with built-in AI; you'll use it Friday
- [**PyCharm Community**](https://www.jetbrains.com/pycharm/download/) — heavier but excellent for Python

### 3. Practice data

Create a file `seed_data.py` in your project folder and paste this. It generates the same e-commerce dataset from Week 1 as four CSV files (and one SQLite DB). Run it once with `python seed_data.py` — you'll reuse these files all week.

```python
# seed_data.py
import sqlite3
import pandas as pd

customers = pd.DataFrame(
    [
        (1, "anna@example.com",  "2024-01-15", "PL", "active"),
        (2, "ben@example.com",   "2024-02-03", "US", "active"),
        (3, "carla@example.com", "2024-02-20", None, "active"),
        (4, "dan@example.com",   "2024-03-01", "DE", "churned"),
        (5, None,                "2024-03-12", "PL", "active"),
        (6, "eve@example.com",   "2024-04-04", "UA", None),
        (7, "frank@example.com", "2024-04-04", "UA", "active"),
    ],
    columns=["customer_id", "email", "signup_date", "country", "status"],
)

products = pd.DataFrame(
    [
        (101, "Wireless Mouse",      "electronics", 25.00, True),
        (102, "Mechanical Keyboard", "electronics", 90.00, True),
        (103, "Coffee Mug",          "home",         8.50, True),
        (104, "Old Headphones",      "electronics", 40.00, False),
        (105, "Notebook",            "office",       3.00, True),
    ],
    columns=["product_id", "name", "category", "price", "active"],
)

orders = pd.DataFrame(
    [
        (1001, 1,    "2024-05-01", 115.00, "completed"),
        (1002, 2,    "2024-05-02",  17.00, "completed"),
        (1003, 3,    "2024-05-02",  90.00, "completed"),
        (1004, 4,    "2024-05-03", None,   "completed"),
        (1005, 7,    "2024-05-04",  25.00, "cancelled"),
        (1006, 999,  "2024-05-05",  50.00, "completed"),
        (1007, 1,    "2024-05-06",  25.00, "completed"),
    ],
    columns=["order_id", "customer_id", "order_date", "total_amount", "status"],
)

order_items = pd.DataFrame(
    [
        (1, 1001, 101, 1, 25.00),
        (2, 1001, 102, 1, 90.00),
        (3, 1002, 103, 2,  8.50),
        (4, 1003, 102, 1, 90.00),
        (5, 1004, 105, 3,  3.00),
        (6, 1005, 101, 1, 25.00),
        (7, 1006, 101, 2, 30.00),
        (8, 1007, 101, 1, 25.00),
    ],
    columns=["order_item_id", "order_id", "product_id", "quantity", "unit_price"],
)

# CSVs
customers.to_csv("customers.csv", index=False)
products.to_csv("products.csv", index=False)
orders.to_csv("orders.csv", index=False)
order_items.to_csv("order_items.csv", index=False)

# SQLite (used Day 4)
with sqlite3.connect("ecommerce.db") as conn:
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    order_items.to_sql("order_items", conn, if_exists="replace", index=False)

print("Seeded 4 CSVs + ecommerce.db")
```

You should now see five files in your folder. That's your sandbox for the week.

---

## Day 1 (Mon) — pandas Refresher

### Theory

A pandas **DataFrame** is a 2D table with labeled rows (`Index`) and columns. A **Series** is one column or row of it. Almost everything you do is one of: filter rows, select columns, transform values, aggregate, or check shape.

The mental model that matters for QA:

1. **A DataFrame has a schema** — column names + dtypes + index. Most data quality bugs are schema bugs in disguise.
2. **Missing values are explicit but slippery.** pandas uses `NaN` for floats, `NaT` for datetimes, `None` for objects, and `pd.NA` for the new nullable dtypes — and they don't always behave the same.
3. **Operations are columnar.** Loops over rows are almost always wrong; learn vectorized patterns.

### Functions you must know cold

| Pattern | Returns | Use for |
|---|---|---|
| `df.shape` | `(rows, cols)` tuple | Row count assertion |
| `df.dtypes` | Series of types | Schema check |
| `df.info()` | Printed summary | Quick eyeball — not for assertions |
| `df.describe()` | Stats per numeric column | Min/max/mean sanity |
| `df.isnull()` / `.isna()` | Boolean DataFrame, same shape | NULL profiling |
| `df.isnull().sum()` | NULLs per column | The single most useful QA query in pandas |
| `df.duplicated(subset=[...])` | Boolean Series | Duplicate detection |
| `df.nunique()` | Distinct count per column | Cardinality check |
| `df.loc[mask]` | Rows matching mask | Filter (label-aware) |
| `df.iloc[i]` | Position-based selection | Avoid for QA — use `.loc` |
| `df["col"].value_counts(dropna=False)` | Histogram of values | Categorical distribution |
| `df.sort_values("col")` | Sorted DataFrame | Inspecting extremes |

### Gotchas (the ones that ship bugs)

1. **`NaN != NaN`** — same as SQL's three-valued logic. Use `.isna()`, never `== np.nan`. `df["col"] == np.nan` returns all `False`.
2. **A column with even one NaN can change dtype.** An integer column with a missing value becomes `float64` (because `NaN` is a float). pandas 2.0+ fixes this with nullable `Int64` (capital I) — but only if you opt in.
3. **`object` dtype is a warning sign.** It usually means strings, but can hide mixed types (some `int`, some `str`, some `None`). Use `df["col"].map(type).value_counts()` to confirm.
4. **`SettingWithCopyWarning`** appears when you chain `df[df["x"] > 0]["y"] = 5`. The assignment may or may not stick. Use `df.loc[df["x"] > 0, "y"] = 5` instead. Always.
5. **`df.duplicated()` with no `subset=` argument** considers *all columns*. To find duplicate emails specifically: `df.duplicated(subset=["email"], keep=False)` — and `keep=False` returns *all* duplicate occurrences, not just the second-and-onward.
6. **`df.dropna()` defaults to dropping any row with at least one NaN** in any column. Often not what you want. Use `subset=` to be explicit.
7. **CSV reads infer dtypes** — and they get it wrong constantly. A `"0001"` ID column becomes integer `1`. Always pass an explicit `dtype=` for ID-like columns. (More on this Day 4.)

### Exercises (against the seed CSVs)

Create a file `day1_practice.py` and write code for each. Run with `python day1_practice.py`.

1. Load `customers.csv` into a DataFrame `c`. Print its shape, dtypes, and the count of NULLs per column.
2. Find all customers with a missing email **or** missing country. (Equivalent to your Day 1 SQL exercise from Week 1.)
3. Use `value_counts(dropna=False)` on `country` to see the distribution including NULLs. Why does the default `dropna=True` lie to you for QA purposes?
4. Find duplicate emails. Return *every* row involved in a duplicate, not just one per group.
5. Add a column `country_clean` filled with `"UNKNOWN"` where `country` is null, otherwise the original value. (Hint: `.fillna()`.)
6. **Trap exercise:** read `orders.csv` and check the dtype of `total_amount`. Now print `df["total_amount"].dtype` — is it `int64` or `float64`? Why? Even though the original data was meant as money?

### External practice

- [Kaggle — Pandas course (free, ~4 hrs)](https://www.kaggle.com/learn/pandas) — interactive, matches this depth
- [100 pandas puzzles](https://github.com/ajcr/100-pandas-puzzles) — graded difficulty, Jupyter-friendly
- [pandas Getting Started tutorials](https://pandas.pydata.org/docs/getting_started/intro_tutorials/index.html) — official, surprisingly readable

### Self-check (Day 1)

> Q1.1 — Why does `df["email"] == None` return all `False`, even for rows where email is actually missing?
> Q1.2 — A CSV column contains the values `1, 2, 3, NaN`. After `pd.read_csv`, what dtype does it have? What dtype would you want for an ID column?
> Q1.3 — What's the difference between `df.duplicated()` and `df.duplicated(keep=False)`?
> Q1.4 — Why is seeing `object` in `df.dtypes` a yellow flag for a numeric or boolean column?

---

## Day 2 (Tue) — pytest Basics

### Theory

**pytest** discovers test files automatically (any `test_*.py` or `*_test.py`), runs every function whose name starts with `test_`, and reports pass/fail. The whole framework is built around three ideas:

1. **`assert` is the test.** No `self.assertEqual` ceremony — pytest rewrites bare `assert` statements to give detailed error messages.
2. **Fixtures provide setup data.** Reusable, composable, scoped (per-test, per-module, per-session).
3. **Parametrization runs the same test against many inputs.** One test function, many cases.

### The minimum pytest you need this week

```python
# test_basic.py
import pytest

# 1. A plain test function
def test_addition():
    assert 1 + 1 == 2

# 2. A fixture — anything `yielded` or returned is injected by name
@pytest.fixture
def sample_emails():
    return ["a@x.com", "b@x.com", "c@x.com"]

def test_count_emails(sample_emails):
    assert len(sample_emails) == 3

# 3. Parametrization — same test, many inputs
@pytest.mark.parametrize(
    "email, is_valid",
    [
        ("a@b.com",     True),
        ("",            False),
        ("no-at-sign",  False),
        (None,          False),
    ],
)
def test_email_format(email, is_valid):
    assert (email is not None and "@" in email) == is_valid
```

Run:
```bash
pytest                    # run everything
pytest -v                 # verbose: show each test name
pytest -k "email"         # only tests with "email" in the name
pytest test_basic.py::test_addition   # one specific test
pytest -x                 # stop at first failure
pytest --tb=short         # shorter tracebacks
```

### `conftest.py` — the special file

If you put fixtures in a file named `conftest.py`, **every test in the same folder (and subfolders) can use them without importing anything.** That's the whole magic. It's how you share fixtures across many test files cleanly.

```python
# conftest.py
import pandas as pd
import pytest

@pytest.fixture
def customers_df():
    return pd.read_csv("customers.csv")
```

```python
# test_customers.py
def test_customers_have_rows(customers_df):
    assert len(customers_df) > 0
```

No `import` needed — pytest wires it up.

### Gotchas

1. **Filenames and function names matter.** `customer_tests.py` won't be discovered. It must be `test_*.py` or `*_test.py`.
2. **Fixture scope defaults to `"function"`** — meaning the fixture runs *fresh for every test*. For expensive setup (loading a large CSV), use `scope="module"` or `scope="session"`.
3. **`assert` rewriting only happens inside test files.** If you `assert` inside a helper module, the error message will be terse. Put assertions in test files, or use the `pytest.assertion.rewrite` registration trick (advanced, skip for now).
4. **Parametrize IDs auto-generated from values can get ugly** for DataFrames or long strings. Pass `ids=["case1", "case2", ...]` to label them.
5. **`pytest` runs from the current working directory.** Relative file paths in your tests (like `pd.read_csv("customers.csv")`) only work if you run pytest from the folder where the CSVs live. Use `pathlib.Path(__file__).parent / "customers.csv"` to be robust.
6. **A failing fixture skips, doesn't fail, the dependent test** by default. Watch for `ERRORS` in the report, not just `FAILED`.

### Exercises

Create `test_warmup.py` first (no pandas yet).

1. Write three tests for a function `is_valid_email(s)` you also implement: returns True if `s` is a non-empty string containing exactly one `@`. Use `parametrize` with at least 5 cases including edge cases.
2. Add a fixture `sample_users` returning a list of 4 user dicts. Write two tests that consume it.
3. Move the fixture to `conftest.py`. Confirm it still works without importing.
4. Add a `scope="module"` fixture that creates a temp file. Print something inside it (use `print(..., flush=True)` and run with `pytest -s` to see prints). Verify it runs once for the whole module, not once per test.
5. Run with `pytest -v -k "email"` and confirm only the email tests execute.
6. **Trap exercise:** create a test file named `email_tests.py` with a function `test_something()`. Run pytest. Why isn't it discovered? Fix it.

### External practice

- [Real Python — pytest intro](https://realpython.com/pytest-python-testing/) — best free tutorial
- [pytest Getting Started (official)](https://docs.pytest.org/en/stable/getting-started.html) — short and accurate
- [Brian Okken's pytest course / book](https://pythontest.com/) — if you want depth, this is the source

### Self-check (Day 2)

> Q2.1 — pytest is run in a folder with three files: `test_one.py`, `tests_two.py`, `three_test.py`. Which are discovered?
> Q2.2 — You have a 200MB CSV that 30 tests need. What fixture scope would you use, and why?
> Q2.3 — What's the difference between an `ERROR` and a `FAILED` in pytest output?
> Q2.4 — Why does `assert df.empty == False` give a worse error message than `assert not df.empty`?

---

## Day 3 (Wed) — Testing pandas DataFrames

### Theory

You now have data (Day 1) and a test framework (Day 2). Today you put them together: assertions *over DataFrames*.

There are two complementary tools:

1. **`pd.testing` utilities** — strict equality checks with rich diff output. Use when you have an *expected* DataFrame.
2. **Custom validation functions** — assert *properties* (no nulls, unique key, value in range). Use when you don't have a literal expected output, just rules.

### The `pd.testing` utilities

```python
import pandas as pd
from pandas import testing as tm

expected = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
actual   = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

tm.assert_frame_equal(expected, actual)   # passes silently, raises with diff if not
```

**Important options:**

- `check_dtype=False` — accept e.g. `int64` vs `Int64` differences
- `check_like=True` — accept rows in any order (sorts both before comparing)
- `check_exact=False, rtol=1e-3` — allow float wobble
- `tm.assert_series_equal` and `tm.assert_index_equal` exist with the same options

There's also `df.equals(other)` which returns a `bool` instead of raising — fine for `if` statements but useless for tests because it gives no diff on failure.

### Building reusable validators

Real data tests almost never compare to a literal expected DataFrame — you assert properties. Build a small toolbox:

```python
# validators.py
from typing import Iterable
import pandas as pd

def assert_no_nulls(df: pd.DataFrame, cols: Iterable[str]) -> None:
    nulls = df[list(cols)].isna().sum()
    failing = nulls[nulls > 0]
    assert failing.empty, f"Found NULLs:\n{failing}"

def assert_unique(df: pd.DataFrame, cols: Iterable[str]) -> None:
    dupes = df[df.duplicated(subset=list(cols), keep=False)]
    assert dupes.empty, f"Found {len(dupes)} duplicate rows on {list(cols)}:\n{dupes}"

def assert_in_range(df: pd.DataFrame, col: str, min_val=None, max_val=None) -> None:
    s = df[col].dropna()
    if min_val is not None:
        bad = s[s < min_val]
        assert bad.empty, f"{col}: {len(bad)} values below {min_val}"
    if max_val is not None:
        bad = s[s > max_val]
        assert bad.empty, f"{col}: {len(bad)} values above {max_val}"

def assert_in_set(df: pd.DataFrame, col: str, allowed: set) -> None:
    bad = df[~df[col].isin(allowed) & df[col].notna()]
    assert bad.empty, f"{col}: {len(bad)} values outside allowed set {allowed}"

def assert_row_count(df: pd.DataFrame, min_rows: int, max_rows: int = None) -> None:
    assert len(df) >= min_rows, f"Only {len(df)} rows, need ≥ {min_rows}"
    if max_rows is not None:
        assert len(df) <= max_rows, f"{len(df)} rows, max is {max_rows}"
```

Then your tests become declarative:

```python
# test_customers.py
from validators import assert_no_nulls, assert_unique, assert_in_set

def test_customer_keys_present(customers_df):
    assert_no_nulls(customers_df, ["customer_id"])

def test_customer_id_unique(customers_df):
    assert_unique(customers_df, ["customer_id"])

def test_customer_status_valid(customers_df):
    assert_in_set(customers_df, "status", {"active", "churned"})
```

This is the foundation. Every framework you'll learn later (Great Expectations, Soda, dbt tests) is essentially a polished version of this same idea — declarative assertions that produce readable failures.

### Gotchas

1. **`assert_frame_equal` is strict by default.** Different index, different dtype, different column order → fail. Use the `check_*` flags deliberately, not as a habit of "loosen everything".
2. **Float comparisons are *not* exact.** `0.1 + 0.2 == 0.3` is `False` in Python. Use `check_exact=False` or `pytest.approx`.
3. **Sorting before comparison hides bugs** if the test was supposed to verify ordering. Only use `check_like=True` when row order genuinely doesn't matter.
4. **A failing assertion mid-test stops execution.** If you have 5 assertions in one test, the first failure hides the others. Either split into 5 tests, or collect failures yourself (advanced — `pytest-check` library does this).
5. **`assert df.empty` is your friend** — but **`assert df`** raises `ValueError: The truth value of a DataFrame is ambiguous.` Don't use a DataFrame as a boolean directly.

### Exercises

Create `validators.py` with the five functions above (or your own variants). Then in `test_data_quality.py`:

1. Use `customers_df` fixture (from `conftest.py`). Write tests asserting:
   - `customer_id` is unique and never null
   - `status` is in `{"active", "churned"}` (note: there's a NULL in the seed data — your test should fail; that's the point)
   - `email` follows `*@*.*` shape (write a custom validator)
2. Write a test using `assert_frame_equal` that loads `customers.csv`, applies a known transformation (e.g. uppercase emails), and compares to a hardcoded expected DataFrame.
3. Add a `total_amount` validator: assert all non-null values are between `0` and `10_000`. Confirm it passes on seed data.
4. Write a single parametrized test that runs `assert_no_nulls` on each table for its primary-key column. (Hint: parametrize over `(table_name, csv_path, pk_col)` tuples.)
5. **Reconciliation test:** write a test that loads `orders.csv` and `order_items.csv`, computes `sum(quantity * unit_price)` per order, and asserts it equals `orders.total_amount`. Where does it fail and why? (You should see two failures: order 1004 has NULL total, order 1006 has the price drift.)
6. **Stretch:** add a `pytest --tb=short` run alias to confirm your validators produce useful failure messages, not just `AssertionError`.

### External practice

- [pandas testing API reference](https://pandas.pydata.org/docs/reference/general_utility_functions.html#testing-functions) — official
- [Real Python — Effective pandas testing](https://realpython.com/python-testing/) — broader

### Self-check (Day 3)

> Q3.1 — When would you use `df.equals(other)` instead of `tm.assert_frame_equal(df, other)`?
> Q3.2 — Why does the row-order in your DataFrame matter to `assert_frame_equal` by default? How do you opt out?
> Q3.3 — A test asserts five things. The first assertion fails. What happens to the other four?
> Q3.4 — What's wrong with `assert df` as a check that the DataFrame is non-empty?

---

## Day 4 (Thu) — Reading Data Sources

### Theory

A test is only as good as the data it loads. **Most "the test was wrong" bugs in data QA are actually "the loader was wrong" bugs** — IDs silently coerced to integers, dates parsed as strings, encoding chaos. Today is about reading data correctly and *defensively*.

### Three sources, three patterns

**CSV — `pd.read_csv`** is wonderful and treacherous:

```python
import pandas as pd

# The cautious way
df = pd.read_csv(
    "customers.csv",
    dtype={
        "customer_id": "Int64",       # nullable integer (pandas 2.0+)
        "email":       "string",
        "country":     "string",
        "status":      "string",
    },
    parse_dates=["signup_date"],
    na_values=["", "NA", "N/A", "null"],   # what counts as NULL
    keep_default_na=True,
)
```

**JSON — `pd.read_json` and `pd.json_normalize`:**

```python
import pandas as pd

# Flat JSON array
df = pd.read_json("data.json")

# Nested JSON — flatten one level
import json
with open("nested.json") as f:
    raw = json.load(f)
df = pd.json_normalize(raw, record_path=["orders"], meta=["customer_id"])
```

**SQLite — `sqlite3` + `pd.read_sql_query`:**

```python
import sqlite3
import pandas as pd

with sqlite3.connect("ecommerce.db") as conn:
    df = pd.read_sql_query(
        "SELECT customer_id, email FROM customers WHERE status = ?",
        conn,
        params=("active",),
    )
```

Note: parameter binding (`?` and `params=`) — never f-string SQL with user input. SQL injection is real.

### Gotchas

1. **`read_csv` dtype inference is lossy and silent.** A column of zip codes `"02134"` becomes integer `2134`. Always pass `dtype=` for IDs, codes, postal codes, phone numbers — anything where leading zeroes or padding matters.
2. **`parse_dates` is per-column.** Pass a list of column names. If the format is unusual, pass `date_format=` (pandas 2.0+) or use `pd.to_datetime(...)` after loading.
3. **Encoding.** Default is UTF-8. If you get `UnicodeDecodeError`, common culprits are `latin-1` (Windows exports) or `utf-8-sig` (BOM-prefixed). Use the `chardet` library to detect.
4. **`low_memory=True`** (the default) processes CSVs in chunks and can produce mixed dtypes per column. For QA work, set `low_memory=False` so dtype is inferred from the whole column at once — safer, slower.
5. **`pd.read_json` is brittle for nested structures.** Use `pd.json_normalize` for anything beyond a flat array of objects.
6. **SQL with pandas: `pd.read_sql_query` returns python `int`/`str`/`datetime`** for most types — but NULLs become NaN, which can flip your dtypes (see Day 1 gotcha #2). Specify `dtype=` if it matters.
7. **The connection's lifecycle.** Always use `with sqlite3.connect(...) as conn:` — it commits and closes on exit. Otherwise you leak file handles.

### Exercises

Create `day4_loading.py`.

1. Load `customers.csv` *defensively* using explicit `dtype=` and `parse_dates=`. Print `df.dtypes` and confirm `customer_id` is `Int64`, `signup_date` is `datetime64[ns]`.
2. Re-load it the *naive* way (just `pd.read_csv("customers.csv")`). Compare `dtypes`. What changed?
3. Open `ecommerce.db` and run a query: orders joined with customers, returning `email`, `order_date`, `total_amount`. Use `pd.read_sql_query` with parameter binding for the status filter.
4. Write a generic `load_csv(path, schema)` function that takes a path and a `dict` of `{col_name: dtype}` and returns a DataFrame with strict dtype enforcement. Raise a clear `ValueError` if any column from the schema is missing from the file.
5. Save `customers.csv` re-encoded as `latin-1` (do this in Python: `df.to_csv("customers_latin.csv", encoding="latin-1")`). Then load it with the default UTF-8 read — observe the error. Now load it correctly.
6. **Trap exercise:** create a CSV with one column containing `"007", "008", "009"`. Read it with `pd.read_csv` (no dtype). Print the values. What happened to your leading zeroes? Now do it correctly.

### External practice

- [pandas IO docs — read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html) — every parameter matters; skim once
- [Real Python — Reading and writing CSV files](https://realpython.com/python-csv/) — covers the stdlib `csv` module too, useful for malformed files
- [Stack Overflow: top-voted pandas read_csv questions](https://stackoverflow.com/questions/tagged/pandas+csv?tab=Votes) — the gotchas you'll meet are documented here

### Self-check (Day 4)

> Q4.1 — A CSV column has values `"00012", "00045", "00099"`. After `pd.read_csv` with no dtype, what does the column contain? What dtype?
> Q4.2 — You see `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9`. What are two encodings worth trying?
> Q4.3 — Why is f-string SQL (`f"SELECT * FROM users WHERE id = {user_id}"`) dangerous, even in a test?
> Q4.4 — What does `parse_dates=["signup_date"]` do that `dtype={"signup_date": "datetime64[ns]"}` cannot?

---

## Day 5 (Fri 🤖) — AI Workflow: Test Suite Scaffolding

### What you're learning today

How to use AI to **scaffold a pytest test suite from a DataFrame in seconds** — and how to harden the output so it's actually trustworthy. This Friday session builds directly on Week 1's Friday: same review-loop muscle, applied to Python.

### Setup (~5 min)

- Have your `seed_data.py` files generated
- Open Cursor (or Claude in browser, or VS Code + Copilot — whichever you're using)
- Open the project folder so the AI has access to your files

### Exercise 1 — DataFrame → pytest test suite

Open `customers.csv` in Cursor. In the chat panel, paste this prompt (or attach the file with `@customers.csv` in Cursor):

> *"You are a senior data quality engineer working in pytest. Given the attached `customers.csv`, generate a complete `test_customers.py` file. It should:*
> *- Use a pytest fixture (in conftest.py) to load the file once per session*
> *- Apply explicit dtypes for customer_id, email, country, status, and parse signup_date as datetime*
> *- Include at least 8 data quality tests, each as a separate `test_*` function: row count threshold, customer_id uniqueness and non-null, email format, signup_date not in future, status in {active, churned}, country in a sensible set, etc.*
> *- Use clear assertion messages so failures are diagnoseable*
> *Return both files in code blocks."*

Save the output. **Run it: `pytest -v`**. Some tests will fail (the seed data has deliberate gaps). For each failure, decide:

- Real bug in the data → test is correct
- The test is wrong → fix it (or ask the AI to)
- The test is too strict / too loose → tighten or relax

### Exercise 2 — Iterate the validation library

Take the `validators.py` you wrote on Day 3. In Cursor, open the file and use inline edit (`Ctrl+K` / `Cmd+K`):

> *"Add three more validators: assert_email_format(df, col), assert_date_not_in_future(df, col), assert_referential_integrity(child_df, child_col, parent_df, parent_col). Each should follow the same style as the existing validators — clear failure messages, type hints."*

Review the diff carefully. The AI will probably:

- Get the basic shape right
- Miss edge cases (empty DataFrames, NULL parent keys, timezone-aware vs naive datetimes)
- Sometimes invent imports or use slightly wrong pandas APIs

Fix what it gets wrong manually. **This editing-the-AI-output skill is the entire point of the exercise.**

### Exercise 3 — Build a `.cursorrules` for the project

Create a file `.cursorrules` in your project root with conventions you want the AI to respect:

```
You are helping write Python tests for data quality on pandas DataFrames.

Stack:
- Python 3.10+, pandas 2.x, pytest 8.x
- Use type hints on all function signatures
- Use pathlib.Path for filesystem paths, never raw strings

Conventions:
- All test files live in tests/ and start with test_
- Fixtures shared across files go in tests/conftest.py
- Validators (reusable assertions) live in src/validators.py and are imported, not redefined
- Use pd.testing.assert_frame_equal for expected/actual comparisons
- Use explicit dtype= when reading CSVs — never trust inference for IDs or codes
- Prefer .loc[mask, "col"] over chained indexing
- Use pytest.mark.parametrize for any test repeated over inputs

Style:
- Failure messages must include the offending values, not just "assertion failed"
- No print() in tests — use pytest -v output
```

Now ask the AI for one more test — for `orders.csv`. Notice how the output respects your rules. **This file gets richer every Friday** for the rest of the plan.

### Quality bar — when is an AI-generated pytest suite "good"?

Use this checklist:

- [ ] All tests are runnable as-is (`pytest -v` reports `passed` or `failed`, never `error`)
- [ ] Every test asserts one thing, with a custom message
- [ ] Fixtures are scoped sensibly (CSV loads = `session`, not `function`)
- [ ] No hardcoded absolute paths (`/Users/me/...` or `C:\...`)
- [ ] No `try: ... except: pass` that hides assertion failures
- [ ] Imports are real (not made-up `from data_quality_lib import magic`)
- [ ] The known-bad rows in the seed data are caught by at least one test

### Reflection (write 3–5 sentences in `notes.md`)

- Which prompts produced runnable code on the first try, and which needed correction?
- What was the most subtle bug the AI introduced?
- Compare today's `.cursorrules` to last Friday's. What pattern emerged?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 3. 5–7 = re-review. <5 = redo exercises.

1. A CSV has a column `id` with values `1, 2, , 4`. After `pd.read_csv` with default options, what dtype does `id` have, and why?
2. You want to filter a DataFrame to rows where `email` is not null *and* `country` is `"PL"`. Write the boolean mask.
3. Why is `df["x"] == np.nan` always False?
4. What's the difference between `df.duplicated()` and `df.duplicated(keep=False)`?
5. Write a pytest fixture that loads `orders.csv` once per session.
6. Where do shared fixtures live so they don't need to be imported?
7. Why does `assert_frame_equal(df1, df2)` give a better failure than `assert df1.equals(df2)`?
8. You're testing that `total_amount` is between 0 and 10,000. The column has NULLs. Should your test fail on the NULLs? Why or why not?
9. Write the safe pattern for executing a parameterized SQL query through `pd.read_sql_query`.
10. After running an AI-generated test suite, the first thing you do is...?

---

## Interview Prep — Common Questions for This Week's Material

> 4–5 questions a real interviewer would ask about Python and pytest for data testing. Try to answer aloud (or in writing) before peeking at "what a good answer covers". The goal isn't to memorize — it's to know which trade-offs the interviewer is probing.

### IQ1. "How does pandas represent missing data, and what gotchas does that introduce?"

*What a good answer covers:*
- pandas uses `NaN` (a float) for missing numeric values, `NaT` for missing datetimes, `None` for object columns, and `pd.NA` for the new nullable dtypes
- Because `NaN` is a float, an integer column with even one missing value gets upcast to `float64` — IDs lose their integer type silently
- `NaN != NaN`, so `==` doesn't work for missing-value checks; use `.isna()` / `.notna()`
- pandas 2.0+ nullable dtypes (`Int64`, `string`, `boolean`) fix the upcast issue, but only if you opt in with explicit `dtype=`

*Likely follow-up:* "What would you change in a CSV-loading function to avoid integer-to-float upcasting?"

### IQ2. "You're given a 5GB CSV from a partner team. Walk me through your loading strategy for testing."

*What a good answer covers:*
- Don't trust dtype inference — pass an explicit `dtype=` map for IDs, codes, anything where leading zeroes matter
- Specify `parse_dates=` for date columns and `na_values=` for the partner's NULL conventions (`""`, `"N/A"`, `"NULL"`, etc.)
- For 5GB, consider `chunksize=` to iterate in batches, or switch to DuckDB / Polars / PyArrow for a one-shot read
- Encoding: default UTF-8, fall back to `latin-1` or use `chardet` if it errors
- Sanity-check on load: row count, dtypes, NULL profile per column — *before* writing any business-logic tests

*Likely follow-up:* "What if the file has malformed rows that crash `read_csv`?" (Answer: `on_bad_lines="warn"` or `"skip"`, and log the count of skipped rows as part of the test report.)

### IQ3. "Explain pytest fixtures. When do you use `function`, `module`, and `session` scope?"

*What a good answer covers:*
- A fixture is a setup-and-teardown function, injected by name into any test that declares it as a parameter
- `function` (default): runs fresh for every test — best for stateful / mutable fixtures so tests can't pollute each other
- `module`: runs once per test file — good for moderately expensive setup like a small CSV load
- `session`: runs once per pytest invocation — for slow setup like loading a multi-GB file or starting a Docker container
- Fixtures placed in `conftest.py` are auto-available to all tests in that directory and below — no import needed

*Likely follow-up:* "What happens if a session-scoped fixture is mutated by one test? How do you defend against that?" (Answer: return an immutable copy, or use `function` scope, or document the contract.)

### IQ4. "How would you write tests for a function that takes a DataFrame and returns a transformed DataFrame?"

*What a good answer covers:*
- Two layers of tests: **schema/structure** (column names, dtypes, row count expectations) and **values** (specific transformations are correct on known inputs)
- Use `pd.testing.assert_frame_equal` for full equality against a small expected DataFrame
- Use individual property assertions (`assert_no_nulls`, `assert_in_range`) for rule-based checks where there's no single "expected" output
- Parametrize over a few representative inputs: empty DataFrame, all-NULL column, single-row, normal case, edge case
- Test failure modes too: does the function raise the right exception on bad input?

*Likely follow-up:* "Your test passes locally but fails in CI. What's your debugging process?" (Answer: check pandas version, locale, timezone, file encoding, working directory; reproduce with `pytest -v --tb=long`; consider deterministic seed / sort_values before comparison.)

### IQ5. "What's the difference between `assert df.equals(other)` and `pd.testing.assert_frame_equal(df, other)` — when do you use each?"

*What a good answer covers:*
- `df.equals(other)` returns a `bool`. Useful in normal control flow (`if df.equals(other): ...`). Useless inside a test because the failure message is just `assert False`.
- `assert_frame_equal` raises `AssertionError` with a rich diff: which columns differ, which rows, dtype mismatches, index mismatches. That's what you want in tests.
- Both are strict on dtype, column order, and index by default. `assert_frame_equal` lets you relax with `check_dtype=False`, `check_like=True` (sort first), `rtol=` for float tolerance.
- Float comparisons are the main "gotcha" — never use exact equality for derived numbers.

*Likely follow-up:* "Show me how you'd assert two DataFrames are equal *ignoring row order*." (Answer: `assert_frame_equal(df1, df2, check_like=True)` or sort both by primary key first.)

---

## If you have extra time this week (stretch)

- [Pytest tricks](https://docs.pytest.org/en/stable/how-to/index.html) — skim the `how-to` section for hidden gems (markers, expected failures, `tmp_path`)
- [Hypothesis](https://hypothesis.readthedocs.io/) — property-based testing for Python; a different way to think about data tests
- [Polars](https://pola.rs/) — pandas-alternative, much faster, increasingly common in data engineering. Try porting one Day 1 exercise.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Because `None` (and `np.nan`) doesn't equal anything via `==`. pandas treats missing values as "unknown", same idea as SQL's three-valued logic. Use `df["email"].isna()`.
- **Q1.2** — `float64`, because `NaN` is a float in NumPy. For an ID column you want `Int64` (capital I — pandas nullable integer), so missing values stay missing without forcing the type to float.
- **Q1.3** — `df.duplicated()` returns True for every duplicate *except the first occurrence*. `keep=False` returns True for *all* duplicate rows including the first. For QA, you almost always want `keep=False`.
- **Q1.4** — `object` is pandas' fallback dtype, often holding strings — but it can also hide *mixed* types (some int, some str, some None) because no other dtype fit. For a column you expect to be numeric or boolean, `object` means at least one value isn't.

### Day 2 answers

- **Q2.1** — Only `test_one.py` and `three_test.py` are discovered. `tests_two.py` doesn't match either of the default patterns (`test_*.py` or `*_test.py`).
- **Q2.2** — `scope="session"`. Loading 200MB once for 30 tests is fine; loading it 30 times is wasteful. Use `scope="module"` if tests in different modules need their own copies.
- **Q2.3** — `FAILED` means the test ran and an assertion was wrong. `ERROR` means something blew up *outside* the assertion logic — typically in a fixture, an import, or setup. Errors are usually environmental bugs to fix before you can trust the assertions.
- **Q2.4** — `assert df.empty == False` — pytest sees `False == False` and just says "False is False" on failure. `assert not df.empty` — pytest knows the original expression and shows you `assert not True`, plus introspects the DataFrame.

### Day 3 answers

- **Q3.1** — When you want a `bool` to use in a normal `if` statement or a return value. `df.equals()` gives you `True`/`False`. Inside a test, prefer `assert_frame_equal` because it produces a useful diff on failure.
- **Q3.2** — Because the index *is* part of the DataFrame's identity by default. Two DataFrames with the same data but different row order have different indexes and aren't "equal". Pass `check_like=True` to compare contents only after sorting.
- **Q3.3** — They never run. The `AssertionError` raised by the first assertion stops the test. Either split into separate tests, or use a library like `pytest-check` that collects multiple soft assertions.
- **Q3.4** — `assert df` raises `ValueError: The truth value of a DataFrame is ambiguous`. pandas refuses to coerce a DataFrame to a single bool. Use `assert not df.empty` or `assert len(df) > 0`.

### Day 4 answers

- **Q4.1** — Values become integers `12, 45, 99`, dtype `int64`. The leading zeroes are gone forever (well — until you re-load with `dtype={"col": "string"}`).
- **Q4.2** — `latin-1` (also called ISO-8859-1, common in Windows/Excel exports) and `utf-8-sig` (UTF-8 with a byte-order mark). The `chardet` library can auto-detect.
- **Q4.3** — SQL injection. Even in a test, if `user_id` ever comes from an external source (a CSV, an env var, a teammate), an attacker-controlled value can drop tables or exfiltrate data. Always use parameter binding.
- **Q4.4** — `parse_dates` can handle multiple input formats and runs `pd.to_datetime` with full parsing. The `dtype=` form is stricter and many string layouts won't coerce cleanly. They're not equivalent — `parse_dates` is the right tool for date columns from CSVs.

### End-of-week answers

**A1.** `float64` — because the empty value becomes `NaN`, which is a float, and pandas widens the column to fit. To keep integers, use `dtype={"id": "Int64"}`.

**A2.** `df[df["email"].notna() & (df["country"] == "PL")]`. Note the parentheses around the `==` — required because `&` has higher precedence than `==`.

**A3.** Because `np.nan` is defined as not equal to anything, including itself. IEEE 754 standard, inherited by NumPy and pandas. Use `.isna()`.

**A4.** `df.duplicated()` returns True for duplicates *after the first*. `keep=False` returns True for *all* duplicate rows including the first occurrence.

**A5.** A session-scoped fixture, like this:

```python
@pytest.fixture(scope="session")
def orders_df():
    return pd.read_csv("orders.csv", parse_dates=["order_date"])
```

**A6.** In `conftest.py`, in the same folder as the test files (or any parent folder).

**A7.** `assert_frame_equal` raises with a structured diff showing column-level differences, dtype mismatches, and offending row indexes. `df1.equals(df2)` returns just a bool; the assertion error message is `assert False`.

**A8.** The test should *ignore* NULLs (drop them before the range check), unless asserting "no NULLs" is a separate test. Mixing the two concerns hides which rule actually failed. Day 3's `assert_in_range` does `s = df[col].dropna()` first for exactly this reason.

**A9.** Use `?` placeholders and the `params=` argument:

```python
with sqlite3.connect("db.sqlite") as conn:
    df = pd.read_sql_query(
        "SELECT * FROM t WHERE id = ?",
        conn,
        params=(some_id,),
    )
```

Never f-string the value into the SQL.

**A10.** Run them. Trust comes from execution, not from confident-sounding generated code. Test against known-good and known-bad data; verify failure messages are useful.

---

*Done with Week 2? You should be able to load any CSV defensively, write a 5-test pytest module against it in 10 minutes, and recognize when AI-generated test code is silently wrong. If yes — onward to Week 3 (ETL Concepts & Pipeline Thinking). If not — focus on the day that felt weakest and redo its exercises; everything from here forward assumes pytest fluency.*
