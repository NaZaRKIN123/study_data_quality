# Week 8 — Mocking & Test Data Management | Training Materials

> **Companion to:** Week 8 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Replace dependence on production data with deterministic, fast, isolated test data. By Friday you'll have built your first **AI-in-the-runtime** subagent — a Python tool that calls Claude to generate realistic synthetic test data on demand. This closes out **Month 2** with a milestone deliverable.

---

## How to use this file

- This week converges everything from Months 1–2 into reusable test infrastructure
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday introduces a new pattern: **AI as a runtime dependency**, not just a code generator. This is a turning point in the curriculum
- Answers to all self-checks are at the bottom of the file

---

## One-time setup (~5 minutes)

You'll continue using the project from Weeks 2–7. Add three libraries:

```bash
source .venv/bin/activate
pip install pytest-mock faker anthropic
```

Sanity check:
```bash
python -c "import faker, anthropic; print('faker', faker.__version__, '| anthropic', anthropic.__version__)"
```

You should see versions like `faker 30.x` (or higher) and `anthropic 0.40.x` (or higher). Both libraries have stable APIs for the patterns we'll use.

For Friday's AI subagent, you'll need an **Anthropic API key**. Get one at [console.anthropic.com](https://console.anthropic.com/) — first $5 credit is free, and the exercises in this file use less than $0.10 of credit total. Save it as an environment variable:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'    # paste your real key
```

(Don't commit this. Add `.env` to `.gitignore` if you store it in a file.)

---

## Day 1 (Mon) — Why Mocking Matters

### Theory

A test should be **deterministic, fast, and isolated**. Production data violates all three:

- **Not deterministic** — yesterday's data passes; tomorrow's might not. A test that depends on "the customer table has at least 1000 rows" breaks when the business shrinks.
- **Not fast** — pulling a real warehouse table takes seconds; running a real API call takes more. A 200-test suite that hits live data is unusably slow.
- **Not isolated** — a test that connects to production can corrupt it. PII / GDPR / compliance issues abound. A teammate running the test on their laptop pulls real customer emails — that's a data breach in waiting.

The fix: **test doubles**. A test double is a stand-in for a real dependency, tuned to be predictable.

### The vocabulary (Martin Fowler's classification)

| Type | What it does | When you use it |
|---|---|---|
| **Dummy** | Just satisfies a parameter slot — never actually called | Filling a method signature you don't care about |
| **Stub** | Returns canned answers | "When asked for the customer count, return 42" |
| **Spy** | Records calls, lets you assert after | "Was `send_email()` called with the right address?" |
| **Mock** | Pre-programmed expectation; fails if call doesn't match | "Expect exactly one call to `save()` with `id=1`" |
| **Fake** | Working implementation, unsuitable for prod | An in-memory SQLite instead of Snowflake |

Most Python tooling collapses these into a single `MagicMock` class — but knowing the distinctions helps you read other people's tests and decide which behavior you actually want.

### What you mock in data testing specifically

| What | Why | How |
|---|---|---|
| **External APIs** | Don't hit Stripe / Salesforce in tests | `unittest.mock.patch` the SDK call |
| **Database connections** | Don't query the live warehouse | `pytest-mock` patches the `connect()` call |
| **Filesystem reads** | Tests should be self-contained | Use `tmp_path` fixture; mock `open()` if needed |
| **Time** | Tests fail at midnight | `freezegun` or `monkeypatch` on `datetime.now` |
| **Random** | Same input should give same output | `random.seed(42)` or mock `random.choice` |

### What you generate (don't mock)

For data inputs themselves, mocking gets clumsy. Instead, **generate** synthetic data with libraries like `Faker` or `mimesis`. That's Day 3 onward.

### Gotchas

1. **Mocking too much hides bugs.** If you mock the function under test, you've tested nothing. Mock *dependencies*, not *the thing you're testing*.
2. **Mocks don't catch interface drift.** If the real API changes its return shape, your mock keeps returning the old shape and tests pass. Periodically run integration tests against the real thing.
3. **Mocking time is harder than it looks.** `datetime.now()` with no timezone, `datetime.utcnow()` (deprecated since Python 3.12), `time.time()` — different code paths need different patches. `freezegun` covers most of them.
4. **Fakes can be too good.** An in-memory SQLite "behaves like" Snowflake but doesn't — different SQL dialect, different NULL handling, different concurrency. Tests pass against SQLite; production breaks against Snowflake.
5. **`pytest-mock` vs `unittest.mock`** — same library underneath. `pytest-mock` provides a `mocker` fixture that auto-cleans up; cleaner in pytest. We'll use it Day 2.

### Exercises (no coding today — analysis day)

1. Open your `validators.py` from Week 2 (or the Week 4 DQ checks). For each function, list:
   - What it depends on (DataFrame, file, time, etc.)
   - Whether that dependency is *deterministic and isolated* in your tests today
   - If not, what would you mock?
2. Look at your dbt project from Week 6. Where does it pull data from?
   - In `dbt seed` mode (your local setup): seeds are part of the repo — already deterministic ✓
   - In a real warehouse: would your tests be deterministic? What would you replace with mocks/seeds?
3. Read [Martin Fowler — Test Doubles](https://martinfowler.com/bliki/TestDouble.html) (~10 minutes). Notice he distinguishes "mock" from "stub" carefully — most Python tooling doesn't. Why might the distinction still matter?
4. **Write a one-page mini-analysis** (in `notes.md`): for the e-commerce project, list every external dependency a comprehensive test suite would need to handle, and your strategy for each (mock vs fake vs synthetic).

### External practice

- [Martin Fowler — Test Doubles](https://martinfowler.com/bliki/TestDouble.html) — the canonical reference
- [Real Python — Understanding the Python Mock Object Library](https://realpython.com/python-mock-library/) — practical, well-paced
- [Hillel Wayne — Beware "Best Practices"](https://buttondown.com/hillelwayne/archive/) (search for "test doubles" articles) — opinionated takes

### Self-check (Day 1)

> Q1.1 — Why is "production data is realistic, so let's just use it for tests" a bad idea — give two reasons.
> Q1.2 — When would you use a *fake* (e.g. in-memory SQLite) versus a *mock* (e.g. patched `connect()`)?
> Q1.3 — A test asserts that `today_count > yesterday_count`. Is this deterministic? What would you change?
> Q1.4 — `assert_frame_equal(df, expected)` where `expected` has 1000 rows of real customer emails. What's the privacy issue, and how do you fix it?

---

## Day 2 (Tue) — `unittest.mock` & `pytest-mock`

### Theory

Python ships `unittest.mock` in the standard library — no install needed. The `pytest-mock` library wraps it with a `mocker` fixture that auto-cleans patches between tests. **Use `pytest-mock` in pytest.**

### The four patterns you need

#### 1. Patch a function

```python
def fetch_customer(customer_id: int) -> dict:
    """Real implementation hits a live API."""
    return external_api.get(f"/customers/{customer_id}")


def get_customer_email(customer_id: int) -> str:
    return fetch_customer(customer_id)["email"]


# test
def test_get_customer_email(mocker):
    mocker.patch(
        "myapp.fetch_customer",
        return_value={"email": "test@example.com", "id": 1},
    )
    assert get_customer_email(1) == "test@example.com"
```

The string `"myapp.fetch_customer"` is **the import path where the function is *used*, not where it's defined**. This trips up everyone the first time. If `get_customer_email` lives in `myapp/customers.py` and imports `from myapp.api import fetch_customer`, you patch `myapp.customers.fetch_customer`, not `myapp.api.fetch_customer`. (Same function, but you're replacing the *reference* in the module that uses it.)

#### 2. Make a mock raise an exception

```python
def test_handles_api_failure(mocker):
    mocker.patch(
        "myapp.fetch_customer",
        side_effect=ConnectionError("network down"),
    )
    with pytest.raises(ConnectionError):
        get_customer_email(1)
```

`side_effect` accepts an exception class, an exception instance, or a function — when you set it, calling the mock either raises or runs your function.

#### 3. Different return values per call

```python
def test_retry_after_failure(mocker):
    mocker.patch(
        "myapp.fetch_customer",
        side_effect=[
            ConnectionError("first try fails"),
            {"email": "ok@x.com", "id": 1},     # second try succeeds
        ],
    )
    # call twice; first raises, second returns the dict
```

#### 4. Assert the mock was called correctly

```python
def test_calls_api_with_correct_id(mocker):
    mock = mocker.patch("myapp.fetch_customer", return_value={"email": "a@b.com"})
    get_customer_email(42)
    mock.assert_called_once_with(42)   # raises if not called exactly once with arg=42
```

`assert_called_once_with`, `assert_called_with`, `assert_not_called`, `call_count`, `call_args_list` — all the standard mock assertion methods are available.

### `monkeypatch` — pytest's lighter built-in

For *attribute* and *environment variable* patching (not function replacement), pytest's built-in `monkeypatch` fixture is cleaner:

```python
def test_reads_env(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "https://test.example.com")
    monkeypatch.setattr(myapp.config, "TIMEOUT", 1)
    # test code uses these; they revert after the test
```

Both `monkeypatch` and `mocker.patch` are common in real projects; both are correct.

### Mocking a database connection in pandas

A common data-testing pattern: a function that runs SQL via pandas. You don't want to hit the DB in unit tests:

```python
import pandas as pd
import sqlite3

def get_active_customers(conn) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM customers WHERE status = 'active'", conn
    )


def test_get_active_customers(mocker):
    fake_df = pd.DataFrame(
        [{"id": 1, "email": "a@x.com", "status": "active"}]
    )
    mocker.patch("pandas.read_sql_query", return_value=fake_df)
    result = get_active_customers(conn=None)   # conn doesn't matter; we patched the call
    assert len(result) == 1
    assert result.iloc[0]["email"] == "a@x.com"
```

The `conn=None` works because we replaced `pd.read_sql_query` entirely — it never actually uses the connection.

### Gotchas

1. **Patch where the function is used, not where it's defined.** This is the #1 mock confusion. If your test patches the wrong import path, the mock silently does nothing — your real function still runs.
2. **`return_value` is the same value for every call.** If you need different returns per call, use `side_effect` with a list.
3. **`MagicMock` is permissive by default** — calling any method on a `MagicMock` returns another `MagicMock`. Tests can pass when they shouldn't because attribute access never raises. Use `spec=` to constrain: `mocker.patch("...", spec=RealClass)`.
4. **Mock leakage between tests.** If you patch using `unittest.mock.patch` directly (without the `mocker` fixture), forgetting to stop the patch leaks the mock into the next test. Use `mocker` (pytest-mock) — it auto-cleans.
5. **You can't easily patch C-extension code.** NumPy and pandas internals written in C/Cython resist mocking. Mock the Python wrapper, not the underlying calls.

### Exercises

Create `tests/test_mocks.py`.

1. Write a function `load_customers_from_warehouse(conn)` that runs a SQL query via `pd.read_sql_query`. Then write a test that mocks `pd.read_sql_query` to return a fake DataFrame, asserting your function returns the fake. Confirm: no warehouse access, fast.
2. Write a function `send_alert(message)` that posts to a webhook (use `requests.post`). Test that:
   - The function calls `requests.post` exactly once
   - It calls with the right URL and JSON payload
   - When `requests.post` raises `ConnectionError`, the function logs and returns `False`
3. **Test a function that depends on the current date.** Write `is_old_account(signup_date) -> bool` returning True if the date is more than 1 year ago. Test it with frozen time so it's deterministic across years. (Hint: `monkeypatch.setattr` on the function's `datetime.now`, or install `freezegun`.)
4. Write a function `get_data_or_fallback(primary_fetch, fallback_fetch)` that calls `primary_fetch()` first, falls back to `fallback_fetch()` on any exception. Use `mocker` to test both paths *and* assert that `fallback_fetch` is *not* called when primary succeeds.
5. **Trap exercise:** patch `pandas.read_csv` to return a fake DataFrame. Then write a test that uses `pd.read_csv("real.csv")` directly. Why does the patch not affect it? (Hint: import paths.)
6. **Stretch:** write a `Recorder` spy that captures every call to your custom logger. Use it to assert that your transformation function emits a warning when it drops rows.

### External practice

- [pytest-mock docs](https://pytest-mock.readthedocs.io/en/latest/) — official, short
- [Real Python — Mocking Library](https://realpython.com/python-mock-library/) — covers patches, side_effect, spec, more
- [Brett Slatkin — Effective Python, Item 78](https://effectivepython.com/) — testing dependencies in real production code

### Self-check (Day 2)

> Q2.1 — A function `myapp.processor.run()` calls `myapp.api.fetch()`. To mock `fetch()` for the test, what string do you pass to `mocker.patch(...)`?
> Q2.2 — `return_value` vs `side_effect` — when do you use which?
> Q2.3 — A `MagicMock` allows calls to any method without raising. Why might this hide bugs in your test, and how do you constrain it?
> Q2.4 — When would you use `monkeypatch` instead of `mocker.patch`?

---

## Day 3 (Wed) — Synthetic Data with Faker

### Theory

`Faker` generates plausible fake data — names, emails, addresses, dates, numbers, lorem ipsum, you name it. It's the standard library for "I need a realistic-looking 1000-row test DataFrame."

### The basics

```python
from faker import Faker

fake = Faker()
fake.seed_instance(42)   # determinism — same seed = same output

print(fake.name())          # 'Allison Hill'
print(fake.email())         # 'donaldgarcia@example.org'
print(fake.country())       # 'Tonga'
print(fake.date_between(start_date="-2y", end_date="today"))   # datetime.date(2023, 8, 14)
print(fake.pyfloat(min_value=0, max_value=1000, right_digits=2))   # 547.83
```

`Faker` ships hundreds of "providers." The most useful ones for data engineering tests:

| Provider | Examples |
|---|---|
| Person | `name`, `first_name`, `last_name`, `email` |
| Address | `address`, `country`, `country_code`, `postcode`, `city` |
| Internet | `email`, `domain_name`, `url`, `ipv4`, `user_agent` |
| Date/time | `date_between`, `date_this_year`, `date_time_this_decade` |
| Numeric | `pyint`, `pyfloat`, `random_int`, `random_element` |
| Text | `text`, `sentence`, `word`, `paragraph` |

### Localized faker

```python
fake_pl = Faker("pl_PL")
fake_jp = Faker("ja_JP")
print(fake_pl.name())       # 'Marek Kowalski'
print(fake_jp.name())       # '山田 太郎'
```

Useful when your tests need to handle non-ASCII names, multi-byte characters, or country-specific formats. Pass a list for mixed locales: `Faker(["en_US", "pl_PL", "ja_JP"])`.

### Generating a DataFrame

```python
import pandas as pd
from faker import Faker

def fake_customers(n: int = 100, seed: int = 42) -> pd.DataFrame:
    fake = Faker()
    Faker.seed(seed)   # global seed, affects all instances
    rows = [
        {
            "customer_id": i + 1,
            "email": fake.email(),
            "country": fake.country_code(),
            "signup_date": fake.date_between(start_date="-3y", end_date="today"),
            "status": fake.random_element(elements=["active", "churned"]),
        }
        for i in range(n)
    ]
    return pd.DataFrame(rows)


df = fake_customers(1000)
print(df.head())
```

This drops in as a pytest fixture — and you can ask for any size dataset for any test.

### Determinism: `Faker.seed()` vs `fake.seed_instance()`

- `Faker.seed(42)` — sets the seed *globally* for all Faker instances. Use at module/test level for full determinism.
- `fake.seed_instance(42)` — sets the seed for *one specific instance*. Use when you have multiple Faker instances and want them independent.

Without seeding, your test passes today and may fail tomorrow purely because the random data drifted. **Always seed in tests.**

### When Faker is the right tool

- You need *plausible* values that *look* real — names, emails, addresses, dates.
- You need *volume* — 100, 1,000, 1,000,000 rows. Faker scales to millions.
- You don't care that the values won't match production reality byte-for-byte.

### When Faker isn't the right tool

- You need *consistency across rows* — Faker's emails don't share a domain pattern; addresses don't agree with countries unless you wire it up. Domain-correctness requires custom code or different libraries.
- You need *business-realistic distributions* — Faker's `pyfloat` picks values uniformly; real revenue is power-law-distributed. For statistical realism, write a custom generator using NumPy distributions.
- You need *narrative content* — long-form descriptions, customer support tickets, product reviews. That's what Friday's AI subagent is for.

### Gotchas

1. **Faker doesn't enforce referential integrity across columns.** A row with `country='US'` may have `phone_number` from Vietnam. If you need consistency, generate the country first and use a localized Faker for the rest.
2. **`fake.email()` uses `example.com`-family domains** by default — fine for testing; real-looking. Don't rely on the domain to filter "fake" data, though.
3. **Determinism is *per-process*.** If your tests parallelize (e.g. `pytest-xdist`), each worker has its own seed. Either seed within the test, not the module, or accept that parallel tests will see different data.
4. **`fake.unique` modifier exhausts.** `fake.unique.email()` guarantees unique values within a Faker instance, but the pool is finite — call it 50,000 times and you'll get `UniquenessException`. Use `fake.unique.clear()` between test scenarios.
5. **Faker is slow per-call.** Generating 1M rows row-by-row takes seconds. For larger volumes, pre-generate columns vectorized with NumPy.

### Exercises

Create `tests/factories/customers.py`.

1. Write `fake_customers(n, seed=42)` from above. Generate 100 rows. Verify reproducibility: call it twice with same seed; assert the DataFrames are equal.
2. Write `fake_orders(customer_ids, n, seed=42)` that takes a list of valid customer IDs and generates orders only with those FKs (referential integrity!). Use `fake.random_element(elements=customer_ids)`.
3. Write `fake_order_items(order_ids, product_ids, n, seed=42)` similarly. Now you can generate a full e-commerce dataset where joins actually work.
4. Run your Week 4 pandera schema (the customers schema) against `fake_customers(100)`. Does it pass? Why or why not? (You may need to tighten Faker's outputs or relax the schema.)
5. **Localization exercise:** generate 100 customers with `Faker(["en_US", "pl_PL", "de_DE"])`. Print the unique countries. Notice how Faker picks names appropriate to the locale.
6. **Volume + drift trap:** generate 100 customers with seed=1, then 100 with seed=2. Compute the unique email domains. Are they the same? Why does that matter for tests that assert "all emails end in `@example.com`"?

### External practice

- [Faker docs — Providers index](https://faker.readthedocs.io/en/stable/providers.html) — the catalog
- [mimesis](https://mimesis.name/) — alternative library, often faster than Faker
- [Hypothesis](https://hypothesis.readthedocs.io/) — property-based testing; generates *adversarial* data to break your code

### Self-check (Day 3)

> Q3.1 — Why must you seed Faker in tests, and at what scope?
> Q3.2 — A row has `country='US'` but `phone_number` looks Vietnamese. What's the fix?
> Q3.3 — When is Faker the wrong choice for synthetic data?
> Q3.4 — `fake.unique.email()` raises `UniquenessException` after many calls. Why, and how do you reset it?

---

## Day 4 (Thu) — Fixtures & Factories

### Theory

You've used pytest fixtures since Week 2. Today you scale them up: **factory fixtures** that return *callables* instead of values, letting tests configure their own data.

### Plain fixtures (Week 2 recap)

```python
@pytest.fixture
def customers_df():
    return pd.read_csv("customers.csv")
```

This works when every test wants the same DataFrame. But what if:
- Some tests want 10 rows, others 10,000?
- Some need only `active` customers, others need a mix?
- Some need a specific bug pre-seeded?

### Factory fixtures

```python
@pytest.fixture
def make_customers():
    """Returns a function — tests call it with their own parameters."""
    def _factory(n=100, status="active", seed=42):
        Faker.seed(seed)
        fake = Faker()
        return pd.DataFrame([
            {
                "customer_id": i + 1,
                "email": fake.email(),
                "country": fake.country_code(),
                "signup_date": fake.date_between(start_date="-3y"),
                "status": status,
            }
            for i in range(n)
        ])
    return _factory


def test_only_active_customers_return(make_customers):
    df = make_customers(n=50, status="active")
    assert (df["status"] == "active").all()


def test_handles_large_volumes(make_customers):
    df = make_customers(n=10_000)
    assert len(df) == 10_000
```

The fixture is the *factory*; the test calls the factory with its own arguments. This pattern is sometimes called "deferred fixture" or "fixture factory."

### Composing factories

Build a hierarchy:

```python
@pytest.fixture
def make_customers():
    def _factory(n=100, **kwargs):
        return fake_customers(n=n, **kwargs)
    return _factory


@pytest.fixture
def make_orders():
    def _factory(customer_ids, n=100, **kwargs):
        return fake_orders(customer_ids=customer_ids, n=n, **kwargs)
    return _factory


@pytest.fixture
def make_dataset(make_customers, make_orders):
    """Generate a referentially-consistent customers + orders dataset."""
    def _factory(n_customers=100, n_orders=300):
        customers = make_customers(n=n_customers)
        orders = make_orders(customer_ids=customers["customer_id"].tolist(), n=n_orders)
        return customers, orders
    return _factory


def test_pipeline_with_referential_integrity(make_dataset):
    customers, orders = make_dataset(n_customers=20, n_orders=50)
    assert orders["customer_id"].isin(customers["customer_id"]).all()
```

This is reusable test infrastructure. Once you build it, every new test starts with `make_dataset(...)` instead of "where's a CSV I can use?"

### `tmp_path` — pytest's built-in filesystem fixture

When you need to write a file in a test:

```python
def test_writes_csv(tmp_path, make_customers):
    df = make_customers(n=10)
    output = tmp_path / "customers.csv"
    df.to_csv(output, index=False)
    assert output.exists()
    reloaded = pd.read_csv(output)
    assert len(reloaded) == 10
```

`tmp_path` is a `pathlib.Path` to a unique-per-test directory that pytest auto-deletes. Never write to your real filesystem in tests.

### Parametrized fixtures

Run the same test against multiple fixture configurations:

```python
@pytest.fixture(params=[10, 100, 1000, 10_000])
def make_customers_at_scale(request, make_customers):
    return make_customers(n=request.param)


def test_validation_at_any_scale(make_customers_at_scale):
    df = make_customers_at_scale
    assert df["customer_id"].is_unique
```

This runs the test 4 times — once per scale. pytest will report each as a separate test case.

### Gotchas

1. **A factory fixture is a function that *returns a function*.** First-time users instinctively put `return _factory()` (calling it) instead of `return _factory` (returning it). The first one runs the factory once; the second lets the test invoke it.
2. **Fixtures with side effects need `yield`, not `return`.** If your fixture creates a database connection, use `yield` and put cleanup after:
   ```python
   @pytest.fixture
   def db_conn():
       conn = sqlite3.connect(":memory:")
       yield conn
       conn.close()
   ```
3. **Fixture scope matters for performance.** A factory fixture is usually `scope="function"` (default) — that's fine because it's just returning a callable, not generating data eagerly.
4. **Factories don't auto-cleanup.** If your factory writes to disk, use `tmp_path` *inside* the factory or have the test pass it in. Otherwise files accumulate across runs.
5. **`request.param`** is how parametrized fixtures access their parameter. Forgetting `request` as a parameter is a common error.

### Exercises

Create `tests/conftest.py` and migrate your Week 2/4 fixtures into factory style.

1. Convert `customers_df` (a Week 2 fixture loading a CSV) into `make_customers(n, seed)` factory using Faker.
2. Add `make_orders(customer_ids, n, seed)` and `make_order_items(order_ids, product_ids, n, seed)` factories. Ensure FK integrity.
3. Compose them into `make_dataset(n_customers, n_orders)` returning a tuple of all needed DataFrames.
4. Migrate one of your Week 4 tests to use `make_dataset` instead of reading from `customers.csv`. Confirm it still passes.
5. **Parametrize** a test of `assert_unique` on `customer_id` over `n=10`, `n=1000`, `n=100_000`. Time the test. Where's the bottleneck — Faker, pandas, or your assertion?
6. **Edge cases as fixtures:** add `make_customers_with_duplicates(n, n_duplicates)` and `make_customers_with_nulls(n, null_columns)` factories. Use them to test that your validators *catch* the seeded bugs.

### External practice

- [pytest fixtures — official](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [factory_boy](https://factoryboy.readthedocs.io/) — heavyweight factory library, common in Django; instructive even if you don't adopt it
- [Stack Overflow: pytest factory fixture pattern](https://stackoverflow.com/questions/tagged/pytest+fixtures?tab=Votes) — many real-world examples

### Self-check (Day 4)

> Q4.1 — A factory fixture returns a function. Why not just call the function in the test directly?
> Q4.2 — When do you use `yield` vs `return` in a fixture?
> Q4.3 — `tmp_path` — what is it, and why is it better than writing to `/tmp/test.csv`?
> Q4.4 — A parametrized fixture has `params=[1, 10, 100]`. How many times does each test using it run?

---

## Day 5 (Fri 🤖) — AI Workflow: Synthetic Data Subagent

### What you're learning today

Until now, every Friday has used AI as a **code generator**: write the test for me, write the YAML for me, debug this log. Today the AI becomes a **runtime dependency** — your test suite calls Claude *while it runs* to generate test data.

This is a turning point. Some teams resist it (cost, non-determinism); others embrace it (realistic content, no domain-specific generators to maintain). Today's exercise gives you the muscle to make that judgment yourself.

### When to use AI for synthetic data (vs Faker)

| Use Faker when | Use Claude when |
|---|---|
| You need volume (1k+ rows) | You need realism in *content* (not just structure) |
| You need determinism | You can tolerate per-call variation |
| Cost matters | The data is text-heavy and Faker would be obviously fake |
| Tests run on every PR | You're seeding a one-time fixture |

A good heuristic: Faker for "100 customers with plausible emails"; Claude for "20 realistic customer support tickets with varied tone and complaints."

### Setup

If you skipped the one-time setup at the top, install the SDK and set your API key now:

```bash
pip install anthropic
export ANTHROPIC_API_KEY='sk-ant-...'
```

### A minimal synthetic-data subagent

Create `tests/ai_factory.py`:

```python
"""Generate realistic synthetic test data via the Claude API."""
import json
import os
from typing import Any
import pandas as pd
from anthropic import Anthropic

_client = Anthropic()   # picks up ANTHROPIC_API_KEY from env


def synth_dataframe(
    schema: str,
    n: int = 10,
    extra_instructions: str = "",
    model: str = "claude-haiku-4-5-20251001",
) -> pd.DataFrame:
    """
    Generate a synthetic DataFrame matching a natural-language schema.

    Args:
        schema: Description of columns and constraints, e.g.
            "customer_id (int, unique), email (string, unique), tier (one of: free, pro, enterprise)"
        n: Number of rows to generate
        extra_instructions: Optional context about the dataset's domain
        model: Claude model to use; default is Haiku for speed and cost

    Returns:
        A pandas DataFrame.
    """
    prompt = f"""Generate exactly {n} rows of realistic synthetic data matching this schema:

{schema}

{extra_instructions}

Output strict JSON: a list of {n} dicts, one per row. No markdown, no commentary,
no surrounding text. Just the JSON array."""

    response = _client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown code fences if Claude added them despite the instruction
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0] if "```" in text else text
    rows: list[dict[str, Any]] = json.loads(text)
    return pd.DataFrame(rows)
```

Use it in a test (or a one-off script):

```python
from tests.ai_factory import synth_dataframe

df = synth_dataframe(
    schema="""
    - ticket_id: int, unique, sequential from 1000
    - customer_email: realistic email
    - subject: short subject line of a customer support ticket
    - body: 2-3 sentence description of the issue
    - category: one of [billing, technical, feature_request, complaint]
    - severity: one of [low, medium, high, critical]
    """,
    n=15,
    extra_instructions="This is a SaaS analytics product. Make complaints sound real.",
)
print(df)
```

You'll get 15 plausible support tickets with realistic subjects and bodies. **Faker can't do this.** That's the value.

### What goes wrong (and how to handle it)

1. **Sometimes Claude wraps the JSON in markdown.** The fence-stripping above handles the common case; for robustness, use a JSON-locating regex or the structured-output beta header (newer feature; verify availability before using).
2. **Sometimes the JSON is malformed.** Wrap the parse in a retry loop with a clearer instruction. After 3 failures, raise.
3. **Cost adds up if you call it from every test.** Don't. Cache the output to disk (a JSON file in `tests/fixtures/`) and only regenerate when you explicitly want fresh data. The cache becomes a deterministic, version-controlled fixture.
4. **Rate limits exist.** Free-tier and low-tier accounts have request-per-minute limits. For test suites, generate fixtures *once* in a setup script, save to disk, then read from disk in tests.
5. **Per-call non-determinism.** Even with `temperature=0` and a fixed seed, you may get slight variation. If determinism matters, generate once and commit the JSON; do *not* regenerate per test run.

### The cache pattern

This is how teams actually use AI for test data — generate once, commit the output, regenerate manually:

```python
import json
import pathlib
import pandas as pd
from tests.ai_factory import synth_dataframe

CACHE = pathlib.Path(__file__).parent / "fixtures" / "support_tickets.json"


def support_tickets_df(force_regenerate: bool = False) -> pd.DataFrame:
    if CACHE.exists() and not force_regenerate:
        return pd.read_json(CACHE)
    df = synth_dataframe(
        schema="ticket_id (int), email (str), subject (str), body (str), category (str)",
        n=50,
    )
    CACHE.parent.mkdir(exist_ok=True)
    df.to_json(CACHE, orient="records")
    return df
```

Now your tests are deterministic — they read from the JSON. To refresh: run a one-off script with `force_regenerate=True`. Commit the new JSON.

### Exercises

1. Implement `synth_dataframe(schema, n)` from above. Test it: generate 5 customer support tickets and print them. (Cost: ~$0.01.)
2. Wrap it in the cache pattern. Generate, save to `tests/fixtures/support_tickets.json`, regenerate only if forced. Use this in a pytest test with a fixture.
3. **Compare AI vs Faker on the same task:** generate 20 customer records using Faker, then 20 using your AI subagent with the same schema. Which feels more "real"? Which would you use for a test that asserts "no two emails are the same"?
4. **Failure-mode exercise:** ask the AI to generate data that *deliberately fails* one of your validators — e.g. "generate 10 customers, but include 2 with NULL emails and 1 duplicate email." Use the resulting DataFrame to test that your validators catch the seeded bugs. (This is a classic adversarial-test pattern.)
5. **Cost tracking:** add a wrapper that logs every API call's input/output token count and approximate cost. Run a test suite. How much did it cost? (Should be cents at most.)
6. **Trap exercise:** disable internet, run a test that calls `synth_dataframe`. What happens? How would you make your test suite resilient to API outages? (Hint: cache + fallback to Faker.)

### Update your `.cursorrules`

Add a section about AI-as-runtime:

```
AI-in-runtime conventions:
- AI calls must be explicitly opt-in. No test should call the API on every run by default.
- Cache AI-generated fixtures to disk under tests/fixtures/, commit the cache.
- Regeneration is manual: `pytest --regenerate-fixtures` or similar, never automatic.
- Always log token counts and approximate cost for AI calls.
- Anthropic SDK pattern: `from anthropic import Anthropic; client.messages.create(model=..., max_tokens=..., messages=[...])`.
- Default to Haiku-tier models for synthetic data; Sonnet/Opus only when content quality demands it.
- Strip markdown fences from JSON outputs defensively — Claude sometimes adds them despite instructions.
```

### Quality bar — when is an AI synthetic data fixture "good"?

- [ ] Fixture is cached to disk; tests don't hit the API on every run
- [ ] Cache file is committed to git so CI is deterministic
- [ ] Regeneration path is documented (a script or a `--regenerate` flag)
- [ ] At least one validator catches a seeded bug in the AI-generated data
- [ ] Cost per generation is tracked and known (per token, per row)
- [ ] No PII, no real names. Verify by inspecting the cache file before committing.

### Reflection (write 3–5 sentences in `notes.md`)

- Which datasets in your project are *content-heavy* enough to justify AI generation?
- For volume (1k+ rows), would you use Faker, AI, or AI-bootstrapped-then-Faker-extended?
- Compare today's `.cursorrules` to Week 7's. The shape of the file changed — there's now a "runtime AI" category, separate from "code-gen AI."

---

## ✅ End of Month 2 Milestone

If you've completed Weeks 5–8 and the exercises in this file, you should now have:

- A **Great Expectations** project (Week 5) with at least one Suite, Validation Definition, and Checkpoint that produces an HTML Data Docs report
- A **dbt project** (Week 6) with built-in tests, singular tests, and source freshness on the e-commerce data, runnable locally via DuckDB
- A **GitHub Actions CI/CD setup** (Week 7) that runs pytest *and* dbt tests on every PR, blocks merge on failure, and caches dependencies
- A **factory-style fixture library** (Week 8) using Faker for volume and a cached AI subagent for content-heavy fixtures
- A `.cursorrules` file that's now seven sections deep, codifying your conventions

That's the milestone. Combined with Month 1's Bronze/Silver/Gold pipeline plus DQ checks across all 6 dimensions, your project is now genuinely portfolio-grade for a Data QA / Analytics Engineering role. Push it to a public GitHub repo with a clean README — it's a stronger artifact than what most candidates show.

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 9. 5–7 = re-review the weak day. <5 = redo exercises.

1. Three reasons production data is a bad choice for unit tests.
2. The difference between a *stub* and a *mock* (Fowler's classification).
3. Why does `mocker.patch("myapp.api.fetch")` sometimes silently fail to mock the real call?
4. Write a one-line `mocker.patch` that makes `requests.get` raise `ConnectionError`.
5. What does `Faker.seed(42)` do, and why is it essential in tests?
6. Faker generates 1000 rows of customers. Your test asserts country='US' implies phone starts with '+1'. Will it pass? Why or why not?
7. What's a *factory fixture*, and how does it differ from a regular fixture?
8. Why do you cache AI-generated test data to disk instead of regenerating on every test run?
9. Name a class of test data where AI-generated synthetic data is clearly better than Faker.
10. After running the AI subagent for the first time, the first thing you do before committing the result is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about test isolation and synthetic data.

### IQ1. "How do you isolate a unit test that depends on a database call?"

*What a good answer covers:*
- Mock the database layer at the boundary — `pd.read_sql_query`, `cursor.execute`, etc.
- For pandas-specific patterns: `mocker.patch("pandas.read_sql_query", return_value=fake_df)` is the cleanest
- Patch where the function is *used*, not where it's *defined* — common bug
- For multiple test cases: use `side_effect` (list, function, or exception) to vary returns
- Alternative: a *fake* — in-memory SQLite. Closer to the real DB behavior but slower than a mock and dialect-divergent for non-SQLite warehouses
- Caveat: mocks don't catch interface drift. Periodically run integration tests against the real DB to catch shape changes

*Likely follow-up:* "What's the failure mode of mocking the wrong import path?" (Answer: the patch silently does nothing; the real function still runs. Test passes when it shouldn't, or fails for the wrong reason. Always verify by deliberately breaking the mock and confirming the test fails.)

### IQ2. "When would you use `Faker` versus production-style sample data versus AI-generated data?"

*What a good answer covers:*
- **Faker** — high volume, plausible structure, deterministic with seeding. Default for unit and integration tests. Cheap, fast, works offline.
- **Sampled production data** — for shape-correctness against real distributions. Anonymize aggressively (hash PII, salt the hashes per environment); store in a separate, locked-down environment. Not suitable for committed test fixtures.
- **AI-generated** — for *content* that needs to feel real (support tickets, product descriptions, free-text feedback). Cache the output to disk; commit the cache. Don't call the API on every test run.
- The decision is about **fidelity vs cost**: Faker is cheapest but least realistic; production samples are most realistic but most regulated; AI sits in between, with the unique strength of generating *narrative* content

*Likely follow-up:* "How do you handle PII in test data?" (Answer: never use real PII. If sampling production, anonymize before extraction — cryptographic hash or fully synthetic replacement. Validate by visual inspection and automated PII scanners before committing the fixture.)

### IQ3. "Walk me through how you'd write a test for a function that hits an external API."

*What a good answer covers:*
- Identify the boundary you mock — usually `requests.get` / `httpx.get` or the SDK's client method
- Mock with `pytest-mock`'s `mocker.patch`, return a structured response object that mirrors the real shape (`mocker.Mock(json=lambda: {...}, status_code=200)`)
- Test the happy path *and* failure paths: 4xx, 5xx, timeouts, connection errors. Use `side_effect=ConnectionError(...)` for failures
- Assert the mock was called correctly: `assert_called_once_with(url, headers=..., timeout=...)` — this catches "wrong URL" bugs
- For SDKs that abstract the HTTP layer: mock the SDK's method, not the underlying HTTP call
- Periodically run a small integration test (in a separate suite, not on every PR) against the real API to catch interface drift

*Likely follow-up:* "How do you decide which response shapes to mock?" (Answer: look at real responses — copy a sanitized example into a fixture file. Don't invent shapes from memory; the API's quirks are exactly what your code needs to handle.)

### IQ4. "How would you design a factory pattern for generating test data in pytest?"

*What a good answer covers:*
- A factory fixture is a fixture that returns a *callable*, not a value — so tests can configure their own data
- Pattern: `@pytest.fixture def make_customers(): return _factory` where `_factory` accepts `n`, `seed`, and other parameters
- Compose factories: `make_dataset` calls `make_customers` and `make_orders` to ensure FK integrity
- Use `tmp_path` for any factory that writes files
- Seed everything for determinism — `Faker.seed(seed)` at the top of the factory body
- For complex hierarchies, consider `factory_boy` — but for most data engineering, a simple function-returning-function is enough

*Likely follow-up:* "How do you balance reusable fixtures with test-specific edge cases?" (Answer: factories accept `**kwargs` overrides, and you write narrow factories for known edge cases — `make_customers_with_duplicates`, `make_customers_with_nulls`. Don't try to make one factory handle every case; that's how factories become unmaintainable.)

### IQ5. "What are the trade-offs of using AI to generate synthetic test data at runtime?"

*What a good answer covers:*
- **Strengths:** realism in *content* (text fields, descriptions, varied tone) that Faker can't match; no domain-specific generators to maintain; fast iteration on schemas
- **Weaknesses:** cost per call (small but non-zero); non-determinism (per-call variation); rate limits; offline failures; potential regulatory questions (where does the AI's training data come from?)
- **Mitigation:** cache to disk and commit the cache. Treat AI-generated fixtures like checked-in fixtures, not like Faker calls. Regenerate manually when needed.
- Cost discipline: track tokens, log costs, default to cheapest model (Haiku-tier) for synthetic data — escalate only when quality demands it
- Privacy: AI-generated data doesn't have PII *by construction*, but verify before committing — always inspect the output

*Likely follow-up:* "When wouldn't you use AI for synthetic data?" (Answer: high volumes (1k+ rows — too slow, too expensive); deterministic-required test suites where any variation is unacceptable; offline CI environments. For all those, Faker is the right tool.)

---

## If you have extra time this week (stretch)

- Try [Hypothesis](https://hypothesis.readthedocs.io/) — property-based testing where the library *generates adversarial inputs* to break your code. Different mindset from Faker; complementary skill.
- Read [Anthropic's structured outputs beta docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — guarantees JSON-schema-conforming outputs, removes the markdown-stripping defensiveness.
- Compare `factory_boy` (heavyweight, OOP) to your simple function-based factories. Which would you reach for in a 50-table project?
- Skim [LangChain](https://python.langchain.com/) or [Instructor](https://python.useinstructor.com/) — alternative Python libraries for AI-as-runtime patterns. Both have pros and cons compared to direct SDK use.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Many valid: (1) PII / GDPR — production data contains real customer information that doesn't belong in dev environments. (2) Determinism — production data shifts daily; tests that pass today fail tomorrow with no code change. (3) Speed — querying live systems is slow. (4) Risk — a buggy test could corrupt production.
- **Q1.2** — A *fake* (in-memory SQLite) gives a working DB-like behavior — closer to integration testing. A *mock* replaces only the call, returns whatever you say. Use a fake when you need to exercise multiple SQL operations and want them to actually work; use a mock when you only care that *some* call happened with the right arguments.
- **Q1.3** — Not deterministic. Yesterday's count and today's count change daily. Either freeze the data (use a fixture / seed) or restate the test as "today_count is in a stable range" with explicit bounds.
- **Q1.4** — Real customer emails are PII. Even in a test fixture, they should never sit in a repo. Replace with synthetic emails (Faker) or salted hashes; commit the synthetic version.

### Day 2 answers

- **Q2.1** — `"myapp.processor.fetch"` — patch where the function is *imported and used* (in `processor`), not where it's *defined* (in `api`). When `processor.py` does `from myapp.api import fetch`, it creates a new reference in `processor`'s namespace; that's the one to patch.
- **Q2.2** — `return_value` returns the *same value* on every call. `side_effect` returns a *different value per call* (when given a list/iterable), or *raises an exception* (when given an exception class), or *runs a function* (when given a callable). Use `return_value` for the simple case; `side_effect` for everything else.
- **Q2.3** — Because attribute access on a `MagicMock` returns *another* `MagicMock`. So `mock.foo.bar.baz()` succeeds even if `foo.bar.baz` doesn't exist on the real object — your test passes even though the production code path would crash. Constrain with `spec=RealClass` or `autospec=True` to require real attributes.
- **Q2.4** — For *attributes* (`monkeypatch.setattr`) and *environment variables* (`monkeypatch.setenv`), `monkeypatch` is cleaner — auto-cleanup, simpler syntax. For *function calls*, both work; pick whichever your team uses.

### Day 3 answers

- **Q3.1** — Without seeding, every run produces different random data. A test that passes today may fail tomorrow purely from drift. Seed at module scope (`Faker.seed(42)`) or instance scope (`fake.seed_instance(42)`) — module is simpler unless you have multiple Fakers running concurrently.
- **Q3.2** — Faker doesn't enforce cross-column consistency. Generate the country first, then use a localized Faker (`Faker(country_code.lower())`) for the address/phone fields, or write a custom function that picks consistent combos.
- **Q3.3** — When you need: (a) *content* realism (long-form text), (b) business-specific distributions (revenue, latencies — usually power-law, not uniform), (c) cross-column consistency that Faker doesn't enforce, or (d) very small custom fixtures where volume isn't the goal.
- **Q3.4** — `fake.unique.email()` guarantees uniqueness within a single Faker instance, but the underlying email pool is finite. After thousands of calls it's exhausted. Reset between scenarios with `fake.unique.clear()` or use a wider pool (custom domains, more name combinations).

### Day 4 answers

- **Q4.1** — A factory fixture lets each test pass *its own* parameters — different `n`, different seeds, different statuses. A regular fixture returns the same value to every test. Factory fixtures share the *recipe*; tests share *configuration*.
- **Q4.2** — `return` for fixtures with no cleanup needed (just return data). `yield` for fixtures with side effects that need teardown — yield the value, then run cleanup code after the yield.
- **Q4.3** — `tmp_path` is a `pathlib.Path` to a unique-per-test directory pytest auto-creates and auto-deletes. Better than `/tmp/test.csv` because: (1) unique per test (no collisions), (2) auto-cleanup (no leftover files), (3) cross-platform (works on Windows where `/tmp` doesn't exist).
- **Q4.4** — Three times — once per param value. Each is reported as a separate test case in pytest output (e.g., `test_xyz[1]`, `test_xyz[10]`, `test_xyz[100]`).

### End-of-week answers

**A1.** PII / regulatory risk; non-determinism (data shifts); speed (live queries are slow); risk of corrupting production with a buggy test.

**A2.** A *stub* returns canned answers and that's it. A *mock* additionally records what was called with what arguments, and you assert against it. Most Python tooling collapses both into `MagicMock`; the distinction matters when you read tests in other languages or systems.

**A3.** Because `mocker.patch` replaces a *reference* in a specific module's namespace. If your function imports the dependency from a different module than where you patched, the real function still runs. Always patch where the function is *used*, not where it's defined.

**A4.** `mocker.patch("requests.get", side_effect=ConnectionError("test"))`.

**A5.** It seeds Faker's underlying random generator so the same calls produce the same outputs across runs. Essential because tests must be deterministic; un-seeded Faker output drifts daily.

**A6.** Will not pass reliably. Faker doesn't enforce cross-column consistency by default — country='US' may have a phone from any locale. Generate the country first, then localize the phone-generating Faker, or write a custom paired generator.

**A7.** A factory fixture returns a *callable* (function) instead of a value. Tests call the function with their own arguments to get configured test data. Differs from a regular fixture which returns the same value to every test.

**A8.** Caching ensures tests are deterministic across runs (no per-call variation), free (no API cost on every test), and able to run offline (no network dependency in CI). Treat the cache as a checked-in fixture; regenerate manually when you want fresh data.

**A9.** Many valid: customer support tickets, product descriptions, narrative free-text fields, varied tone-of-voice content, realistic addresses with local quirks — anything where Faker's outputs would be obviously templated.

**A10.** Inspect the output before committing — verify no PII, no inappropriate content, no obvious leakage of training data. AI generations are "synthetic" but worth a manual sanity check.

---

*Done with Week 8? You've finished Month 2 and the foundation phase. From here forward, the curriculum widens — non-relational data (Week 9), big data (Week 10), data lakes (Week 11), performance testing (Week 12), observability (Week 13), ML testing (Week 14), and a capstone (Week 15–16). All of it builds on what you have now: a real project, a real test suite, real CI, and a personalized AI workflow. Onward to Week 9 — where the data stops being neat tables.*
