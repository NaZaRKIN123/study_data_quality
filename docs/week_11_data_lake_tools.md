# Week 11 — Data Lake Tools: Delta Lake, Iceberg & Hudi | Training Materials

> **Companion to:** Week 11 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Understand the table formats that turn a directory of Parquet files into a transactional, time-travelable, schema-evolvable lakehouse table. By Friday you'll know how to test ACID guarantees, schema evolution, and time travel — the three superpowers these formats add to plain Parquet.
>
> **Version note (May 2026):** `deltalake` (Rust-based Python lib) is at 0.x but stable enough for production. `pyiceberg` is at 0.7+ — recommended for stable experience per official docs. The `hudi` PyPI package is newer (Rust binding), currently read-only — Hudi writes still typically go through Spark. APIs in this space evolve faster than the rest of the curriculum.
>
> **Honest framing:** This is the fastest-moving area in the data engineering world right now. Iceberg has clear momentum heading into 2026 (Snowflake, BigQuery, Databricks all support it natively); Delta Lake remains the default on Databricks; Hudi has a smaller but real niche around streaming upserts. The exact market shares will shift; the *concepts* you learn this week — ACID via metadata, snapshot isolation, time travel, schema evolution — will not.

---

## How to use this file

- This week is comparative more than coding-deep — knowing *which* format to reach for matters more than memorizing every API
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Day 1 sets up the conceptual frame; Days 2 and 3 go hands-on with Delta and Iceberg; Day 4 covers Hudi conceptually and compares all three; Friday is AI-assisted schema evolution simulation
- Answers to all self-checks are at the bottom

---

## One-time setup (~10 minutes)

```bash
source .venv/bin/activate
pip install deltalake "pyiceberg[pyarrow,sql-sqlite]" duckdb pyarrow pandas
```

Sanity check:
```bash
python -c "import deltalake, pyiceberg, duckdb, pyarrow; print('deltalake', deltalake.__version__, '| pyiceberg', pyiceberg.__version__, '| duckdb', duckdb.__version__)"
```

You should see something like `deltalake 0.21+`, `pyiceberg 0.7+`, `duckdb 1.3+`.

For DuckDB's Iceberg / Delta extensions — those install on first use, no separate pip step:
```python
import duckdb
con = duckdb.connect()
con.sql("INSTALL iceberg; LOAD iceberg;")
con.sql("INSTALL delta; LOAD delta;")
```

We'll skip Hudi installation today — `hudi` on PyPI works for reads but requires an existing Hudi table (typically created via Spark). Day 4 covers Hudi conceptually with the e-commerce dataset rather than building a new one from scratch.

---

## Day 1 (Mon) — Why Table Formats Exist

### Theory

In Week 10 you learned Parquet — efficient columnar storage for a single dataset. So why do we need *table formats* on top of Parquet?

### The Parquet-only world

Imagine you have a Parquet file `orders.parquet` in cloud storage. You want to:

1. Append today's data without rewriting the whole file
2. Update one customer's email
3. Read the data as it was last Tuesday (debugging a downstream report)
4. Add a new column without breaking existing readers
5. Have two writers safely append simultaneously

Plain Parquet does *none* of these. You'd hand-roll all of it: a separate metadata file, locking, versioning conventions, atomic file moves. **That's exactly what Delta Lake, Iceberg, and Hudi automate.** They're not new file formats — they're metadata layers over Parquet that add database-like semantics.

### What table formats add

| Capability | Plain Parquet | Delta / Iceberg / Hudi |
|---|---|---|
| ACID transactions | No | Yes — atomic commits via a transaction log |
| Time travel | No | Yes — read any prior version of the table |
| Schema evolution | Risky (write-side discipline only) | Tracked, with rules for adding/dropping/renaming columns |
| Concurrent writers | Risky (last-writer-wins) | Optimistic concurrency control |
| Upserts (UPSERT, MERGE) | Manual rewrite | `MERGE` operation as a primitive |
| Statistics for pruning | Per-row-group only | Per-file + table-level + partition-level |
| Streaming + batch | Cumbersome | First-class change data feed |

### How they work — the universal pattern

All three formats share the same core idea:

```
my_table/
├── _metadata/                       (format-specific name varies)
│   ├── 00000.json or .avro          (commit log: what files belong to this version)
│   ├── 00001.json
│   └── ...
└── data/
    ├── part-0001.parquet
    ├── part-0002.parquet
    └── ...
```

The metadata directory contains a sequence of **commits** — each commit lists which Parquet files are part of the table at that version. Want to read version 5? Read commit `00005`'s file list. Want to time travel? Same thing, different version number. Want to add data? Write new Parquet files, append a new commit listing them. Want to delete? Append a commit that *removes* files from the listing — the underlying Parquet stays until a future "vacuum" job cleans it up.

That's it. The Parquet files are immutable. The metadata is append-only. **Mutability is a metadata illusion** built on top of immutable storage.

### What's different between the three

The differences matter operationally even though the concept is the same:

| | Delta Lake | Iceberg | Hudi |
|---|---|---|---|
| **Origin** | Databricks (2019, OSS 2022) | Netflix (2017) | Uber (2016) |
| **Metadata format** | JSON commit log | Avro manifests | JSON+Avro timeline |
| **Catalog** | File-based or Unity Catalog | Required (REST, Hive, Glue, SQL) | Optional but recommended |
| **Sweet spot** | Databricks ecosystem, simple ops | Multi-engine interop, schema evolution | Streaming upserts, CDC |
| **Python (no Spark)** | Excellent (`deltalake` lib) | Good (`pyiceberg`) | Limited (read-only via `hudi`) |
| **Schema evolution** | Add/drop columns; rename via overwrite | Add/drop/rename without rewrite | Similar to Delta |
| **Maturity (2026)** | Mature, large ecosystem | Mature, fastest-growing | Mature in streaming, smaller community |

### The "lakehouse" framing

You'll hear "lakehouse" — a portmanteau of data **lake** (cheap blob storage, any format) + data ware**house** (ACID, schemas, fast queries). Table formats are what makes a lakehouse possible — they bring warehouse semantics to lake-priced storage.

The architectural payoff: store data once (in object storage, in Parquet, with a table format), query it from many engines (Spark, Trino, DuckDB, Snowflake, BigQuery), no separate ETL into a warehouse. **In theory.** In practice, multi-engine support is real but uneven; cross-engine writes especially still have rough edges.

### Gotchas

1. **Table formats don't replace Parquet.** They wrap Parquet. If someone says "we use Iceberg instead of Parquet," they're confused — it's "Iceberg *on top of* Parquet."
2. **Time travel doesn't mean infinite history.** "Vacuum" / "expire" jobs delete old files after a retention period (default: 7 days for Delta, configurable for Iceberg). Time-traveling beyond retention fails.
3. **Catalogs matter for Iceberg, less for Delta.** A Delta table is "the directory at this S3 path." An Iceberg table is "the table named `analytics.orders` registered in catalog X." Forgetting the catalog is the #1 Iceberg confusion.
4. **Concurrent-writer safety has limits.** Optimistic concurrency works when conflicts are rare. If 10 writers all try to update the same partition every second, you'll get retry storms. The formats aren't designed for OLTP-grade write throughput.
5. **Format choice can lock you in operationally.** Switching from Delta to Iceberg on a 100-table data lake is a real migration project, not a config change.

### Exercises (analysis day, no coding)

1. Audit any data systems you have access to. For each: what file format is the data stored in? Is there a table-format layer (Delta, Iceberg, Hudi)? If yes, how do you know — what file or directory hints reveal it?
2. Read [Hannes Mühleisen and team — Delta vs Iceberg](https://duckdb.org/2024/06/26/iceberg-extension.html) (DuckDB's perspective on supporting both). Note where the authors say differences are real, vs cosmetic.
3. **Decision exercise:** for each scenario, which format would you reach for, and why? (Write your answers in `notes.md`; full discussion in Day 4 self-check.)
   - You're starting a new analytics project on AWS, no existing infrastructure
   - Your team is already on Databricks
   - You need streaming upserts from Kafka into a lakehouse table
   - You're building a multi-engine setup where Snowflake and Trino both write to the same tables
4. Skim [Apache Iceberg — Tables specification](https://iceberg.apache.org/spec/) (just the table-of-contents). The spec is famously thorough; you don't need to read it, just appreciate that this much rigor is what gives Iceberg its multi-engine portability.

### External practice

- [Bauplan blog — The Lakehouse, the Open Table Format, and the Open Catalog](https://bauplanlabs.com/blog/) — accessible overview
- [Subsurface conferences — recorded talks](https://www.dremio.com/subsurface/) — opinionated content on lakehouse
- [Tabular blog (now Databricks)](https://tabular.io/blog/) — Iceberg-focused, written by core maintainers

### Self-check (Day 1)

> Q1.1 — A friend says "Iceberg replaces Parquet." How do you correct them?
> Q1.2 — Time travel reads the table "as of last week." How is this possible if Parquet files are immutable?
> Q1.3 — Why does Iceberg need a catalog but Delta doesn't (strictly)?
> Q1.4 — When would you NOT reach for a table format and stick with plain Parquet?

---

## Day 2 (Tue) — Delta Lake Hands-On

### Theory

Delta Lake is the easiest of the three to get hands-on with from pure Python because the `deltalake` library (built on Rust, formerly `delta-rs`) doesn't need Spark or a JVM.

### Creating a Delta table

```python
import pandas as pd
from deltalake import write_deltalake, DeltaTable

# Day 1 data
day1 = pd.DataFrame([
    {"order_id": 1, "customer_id": 100, "total": 99.50, "status": "completed"},
    {"order_id": 2, "customer_id": 101, "total": 14.00, "status": "completed"},
    {"order_id": 3, "customer_id": 102, "total": 250.00, "status": "pending"},
])

write_deltalake("data/orders_delta", day1, mode="overwrite")
```

That's a write. Look at `data/orders_delta`:

```
data/orders_delta/
├── _delta_log/
│   └── 00000000000000000000.json
└── part-00000-...-c000.snappy.parquet
```

`_delta_log/00000....json` is the commit. Its contents (abbreviated):

```json
{"add": {"path": "part-00000-...parquet", "size": 1234, "stats": "..."}}
{"metaData": {"id": "...", "schemaString": "...", "partitionColumns": []}}
{"protocol": {"minReaderVersion": 1, "minWriterVersion": 2}}
{"commitInfo": {"timestamp": 1714675200000, "operation": "WRITE", ...}}
```

Each line is an *action* — add a file, set metadata, declare protocol versions, record commit info. The next commit appends another `00000000000000000001.json` with its own actions.

### Append, then read

```python
day2 = pd.DataFrame([
    {"order_id": 4, "customer_id": 100, "total": 75.00, "status": "completed"},
    {"order_id": 5, "customer_id": 103, "total": 30.00, "status": "completed"},
])

write_deltalake("data/orders_delta", day2, mode="append")

# Read latest
dt = DeltaTable("data/orders_delta")
print(dt.to_pandas())
# Returns 5 rows — both day 1 and day 2

# Read history
print(dt.history())
# [{'timestamp': ..., 'operation': 'WRITE', ...}, {'timestamp': ..., 'operation': 'WRITE', ...}]
```

### Time travel

```python
# Read version 0 (just day 1)
dt_v0 = DeltaTable("data/orders_delta", version=0)
print(dt_v0.to_pandas())   # 3 rows

# Read version 1 (after day 2 append)
dt_v1 = DeltaTable("data/orders_delta", version=1)
print(dt_v1.to_pandas())   # 5 rows

# Or by timestamp
dt_at = DeltaTable("data/orders_delta")
dt_at.load_as_version("2026-05-01T12:00:00Z")   # ISO 8601 / RFC 3339 string
print(dt_at.to_pandas())
```

### Updates and deletes

```python
dt = DeltaTable("data/orders_delta")

# UPDATE: change order #3 status to 'completed'
dt.update(
    predicate="order_id = 3",
    updates={"status": "'completed'"}    # SQL expression strings
)

# DELETE: remove cancelled orders
dt.delete(predicate="status = 'cancelled'")

# Each operation creates a new commit
print(dt.history(limit=5))
```

Under the hood, an `UPDATE` rewrites only the affected files (writes new Parquet files, marks old ones as removed in the next commit). The old files remain on disk until vacuumed.

### Merge (upsert)

The `MERGE` operation is the lakehouse killer feature — UPSERT semantics on append-only storage:

```python
import pyarrow as pa

# Source: new + updated orders
source = pa.table({
    "order_id": [3, 6, 7],         # 3 already exists (will update); 6, 7 are new
    "customer_id": [102, 104, 105],
    "total": [250.00, 50.00, 99.99],
    "status": ["completed", "pending", "completed"],
})

dt = DeltaTable("data/orders_delta")
result = (
    dt.merge(
        source=source,
        predicate="target.order_id = source.order_id",
        source_alias="source",
        target_alias="target",
    )
    .when_matched_update_all()
    .when_not_matched_insert_all()
    .execute()
)
print(result)
# {'num_target_rows_updated': 1, 'num_target_rows_inserted': 2, ...}
```

In one atomic commit: matched rows updated, unmatched rows inserted. This is the foundation of CDC (change-data-capture) pipelines.

### Schema evolution

Adding a column is straightforward:

```python
day3 = pd.DataFrame([
    {"order_id": 8, "customer_id": 106, "total": 199.00, "status": "completed",
     "currency": "USD"},   # new column!
])

write_deltalake("data/orders_delta", day3, mode="append", schema_mode="merge")
# schema_mode="merge" allows the new column to be added; existing rows get NULL for it
```

Removing or renaming columns is more involved — Delta's column-mapping mode (`'name'` mode) makes rename possible without rewriting data; default mode rewrites. Read the docs before doing this in production.

### Reading via DuckDB

DuckDB's Delta extension lets you query Delta tables with SQL:

```python
import duckdb
con = duckdb.connect()
con.sql("INSTALL delta; LOAD delta;")

result = con.sql("""
    SELECT status, count(*) AS n, sum(total) AS revenue
    FROM delta_scan('data/orders_delta')
    GROUP BY status
""").df()
print(result)
```

Useful for testing — you can write the data with `deltalake` and assert against it with DuckDB SQL, no engine boundary to worry about.

### Testing patterns for Delta

```python
import pytest
import pandas as pd
from deltalake import DeltaTable, write_deltalake


@pytest.fixture
def delta_table_path(tmp_path):
    path = tmp_path / "orders"
    initial = pd.DataFrame([
        {"order_id": 1, "total": 100.0, "status": "completed"},
        {"order_id": 2, "total": 50.0,  "status": "pending"},
    ])
    write_deltalake(str(path), initial, mode="overwrite")
    return str(path)


def test_initial_state(delta_table_path):
    dt = DeltaTable(delta_table_path)
    df = dt.to_pandas()
    assert len(df) == 2
    assert dt.version() == 0


def test_append_creates_new_version(delta_table_path):
    new_data = pd.DataFrame([{"order_id": 3, "total": 75.0, "status": "completed"}])
    write_deltalake(delta_table_path, new_data, mode="append")

    dt = DeltaTable(delta_table_path)
    assert dt.version() == 1
    assert len(dt.to_pandas()) == 3


def test_time_travel_to_initial_version(delta_table_path):
    new_data = pd.DataFrame([{"order_id": 3, "total": 75.0, "status": "completed"}])
    write_deltalake(delta_table_path, new_data, mode="append")

    # Read v0 — should NOT see the appended row
    dt_v0 = DeltaTable(delta_table_path, version=0)
    assert len(dt_v0.to_pandas()) == 2


def test_history_records_all_operations(delta_table_path):
    new_data = pd.DataFrame([{"order_id": 3, "total": 75.0, "status": "completed"}])
    write_deltalake(delta_table_path, new_data, mode="append")

    dt = DeltaTable(delta_table_path)
    history = dt.history()
    assert len(history) >= 2
    operations = [h["operation"] for h in history]
    assert "WRITE" in operations
```

### Gotchas

1. **`mode="overwrite"` truly overwrites** — replaces all data with the new DataFrame. Use `mode="append"` to add. This catches everyone once.
2. **The `_delta_log` directory is precious.** Deleting any commit JSON corrupts the table. Cloud storage backups: include `_delta_log` or your table is unrecoverable.
3. **`vacuum` is destructive.** `dt.vacuum(retention_hours=168)` deletes Parquet files older than 7 days that aren't in the current commit. Time travel beyond that point will fail. Run vacuum sparingly; understand retention.
4. **Update predicates are SQL strings, not Python.** `dt.update(predicate="status = 'pending'", updates={"status": "'completed'"})` — mind the quoted quotes.
5. **`DeltaTable("path")` reads the metadata immediately.** It doesn't read data. To get data you call `to_pandas()`, `to_pyarrow_table()`, etc.

### Exercises

Create `tests/test_delta.py` and `data/` directory.

1. Write a script `seed_delta.py` that creates a Delta table from your Week 2 e-commerce CSVs (customers, orders, order_items as 3 separate Delta tables). Confirm `_delta_log/` directories appear.
2. Write a test `test_delta_versions_append_correctly` — append 3 batches and assert version goes 0 → 1 → 2, with cumulative row counts.
3. **Time travel exercise:** insert one bad row deliberately, then run an UPDATE to fix it. Use time travel to read the table *before* the fix. Assert the bad row is present in the older version, absent in the current.
4. **Merge / upsert:** simulate CDC. Start with 100 customers; receive a "delta" of 20 changes (10 updates + 10 inserts). Use `merge` with `when_matched_update_all` + `when_not_matched_insert_all`. Verify total row count is 110 and that 10 of the original rows have updated values.
5. **Schema evolution:** add a `phone` column to `customers` via `schema_mode="merge"`. Verify existing rows have NULL phone; new rows have populated phone.
6. **Cross-tool test:** write data with `deltalake`, query with DuckDB's `delta_scan`. Confirm both see the same rows. Now write to the same path with DuckDB's Delta writer (if available in your DuckDB version) and confirm `deltalake` sees the new commit.
7. **Stretch:** call `dt.history()` and write a small assertion library that says "the last operation was a WRITE in append mode, with at least N rows added." Useful for end-to-end pipeline tests.

### External practice

- [Delta Lake Documentation — Python](https://delta-io.github.io/delta-rs/python/) — the `deltalake` library
- [Delta Lake protocol spec](https://github.com/delta-io/delta/blob/master/PROTOCOL.md) — for the curious; readable
- [Delta Lake — official docs](https://docs.delta.io/) — covers both Spark and Python paths
- [Polars + Delta integration](https://pola.rs/posts/delta-lake-polars/) — Polars reads/writes Delta natively

### Self-check (Day 2)

> Q2.1 — `write_deltalake(path, df, mode="overwrite")` vs `mode="append"` — what's the difference?
> Q2.2 — A `DELETE` on a Delta table — what physically happens to the underlying Parquet files?
> Q2.3 — Why is `MERGE` the "lakehouse killer feature"?
> Q2.4 — You time-travel to a version older than your retention period. What happens, and why?

---

## Day 3 (Wed) — Iceberg Hands-On

### Theory

Iceberg is the most catalog-centric of the three. To do anything, you load a *catalog* — a registry of tables. Catalogs come in flavors: REST (production), Hive Metastore (legacy), AWS Glue (cloud), SQL-backed (good for local dev), in-memory (good for tests).

### Setting up a local catalog

For learning, the SQL-backed catalog (SQLite under the hood) is perfect — it's like dbt-duckdb but for Iceberg metadata.

```python
import os
from pyiceberg.catalog import load_catalog

# Make a workspace
os.makedirs("data/iceberg_warehouse", exist_ok=True)

catalog = load_catalog(
    "local",
    **{
        "type": "sql",
        "uri": "sqlite:///data/iceberg_warehouse/catalog.db",
        "warehouse": "file://" + os.path.abspath("data/iceberg_warehouse"),
    },
)
```

Now you have a catalog called `local`. Tables live in **namespaces** (similar to schemas):

```python
catalog.create_namespace_if_not_exists("ecom")
print(list(catalog.list_namespaces()))
# [('ecom',)]
```

### Creating and writing an Iceberg table

```python
import pyarrow as pa

initial = pa.table({
    "order_id":    [1, 2, 3],
    "customer_id": [100, 101, 102],
    "total":       [99.50, 14.00, 250.00],
    "status":      ["completed", "completed", "pending"],
})

table = catalog.create_table_if_not_exists(
    identifier="ecom.orders",
    schema=initial.schema,
)

table.append(initial)

# Read it back
result = table.scan().to_pandas()
print(result)
```

`scan()` returns a `DataScan`; `.to_pandas()` / `.to_arrow()` materializes it. Filtering pushes down to manifest evaluation:

```python
from pyiceberg.expressions import GreaterThan

high_value = table.scan(row_filter=GreaterThan("total", 100)).to_pandas()
print(high_value)   # only order #3
```

### Time travel

Iceberg uses **snapshots** instead of version numbers. Each commit creates a new snapshot with a unique snapshot ID.

```python
# After multiple appends, list snapshots
table = catalog.load_table("ecom.orders")
for s in table.snapshots():
    print(f"snapshot_id={s.snapshot_id}, timestamp_ms={s.timestamp_ms}, op={s.summary['operation']}")

# Read as of a specific snapshot
old_snapshot_id = table.snapshots()[0].snapshot_id
historical = table.scan(snapshot_id=old_snapshot_id).to_pandas()
```

### Schema evolution

Iceberg's schema evolution is the cleanest of the three formats — it's tracked by *field IDs*, not column names, so renaming a column doesn't rewrite any data.

```python
# Add a column
with table.update_schema() as upd:
    upd.add_column("currency", "string")

# Rename a column
with table.update_schema() as upd:
    upd.rename_column("total", "total_amount")

# Drop a column
with table.update_schema() as upd:
    upd.delete_column("currency")

# Reload to see changes
table = catalog.load_table("ecom.orders")
print(table.schema())
```

After a rename, **old snapshots still work** — Iceberg internally tracks the field ID, so `scan(snapshot_id=...)` returns the column under its old name in older snapshots.

### Reading via DuckDB

```python
import duckdb
con = duckdb.connect()
con.sql("INSTALL iceberg; LOAD iceberg;")

# DuckDB needs the metadata.json path explicitly when not using a catalog
metadata_path = "data/iceberg_warehouse/ecom.db/orders/metadata/v3.metadata.json"
result = con.sql(f"""
    SELECT status, count(*) AS n
    FROM iceberg_scan('{metadata_path}')
    GROUP BY status
""").df()
```

> **Heads-up:** DuckDB's Iceberg extension is improving rapidly but as of mid-2026 has rougher edges than its Delta extension — schema evolution edge cases, certain partition transforms — verify against your specific use case before depending on it for tests.

### Testing patterns for Iceberg

```python
import pytest
import pyarrow as pa
from pyiceberg.catalog import load_catalog


@pytest.fixture
def catalog(tmp_path):
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    cat = load_catalog(
        "test",
        **{
            "type": "sql",
            "uri": f"sqlite:///{tmp_path}/catalog.db",
            "warehouse": f"file://{warehouse}",
        },
    )
    cat.create_namespace_if_not_exists("test")
    return cat


@pytest.fixture
def orders_table(catalog):
    initial = pa.table({
        "order_id": [1, 2],
        "total":    [100.0, 50.0],
    })
    table = catalog.create_table("test.orders", schema=initial.schema)
    table.append(initial)
    return table


def test_initial_load(orders_table):
    df = orders_table.scan().to_pandas()
    assert len(df) == 2
    assert df["total"].sum() == 150.0


def test_append_creates_new_snapshot(orders_table):
    initial_snapshot_count = len(orders_table.snapshots())
    new_data = pa.table({"order_id": [3], "total": [75.0]})
    orders_table.append(new_data)

    # Reload to see new state
    orders_table.refresh()
    assert len(orders_table.snapshots()) == initial_snapshot_count + 1


def test_time_travel_to_initial_snapshot(orders_table):
    initial_snapshot_id = orders_table.snapshots()[0].snapshot_id
    new_data = pa.table({"order_id": [3], "total": [75.0]})
    orders_table.append(new_data)
    orders_table.refresh()

    # Read at the initial snapshot
    old_df = orders_table.scan(snapshot_id=initial_snapshot_id).to_pandas()
    assert len(old_df) == 2     # not 3


def test_schema_evolution_add_column(orders_table):
    with orders_table.update_schema() as upd:
        upd.add_column("currency", "string")
    orders_table.refresh()

    field_names = [f.name for f in orders_table.schema().fields]
    assert "currency" in field_names
```

### Iceberg vs Delta — the practical differences you'll hit

| Concern | Delta | Iceberg |
|---|---|---|
| "Where is my table?" | A directory path | A catalog identifier (`namespace.table`) |
| Time travel handle | Version number (integer) | Snapshot ID (long random number) |
| Schema rename | Requires column-mapping mode | Built-in via field IDs |
| Multi-engine support | Good for Databricks-centric stacks | Best in class for cross-engine |
| Setup overhead (local) | None — just write to a path | Catalog setup (small but real) |
| Library APIs match across languages | Mostly | Yes (REST catalog spec) |

### Gotchas

1. **Catalogs are sticky.** If you create a table with the SQL catalog at `path-A`, you can't read it from a SQL catalog at `path-B` without registering it. Catalog choice is a long-term commitment.
2. **`pyiceberg` is younger than `deltalake`.** APIs have evolved across 0.4 → 0.5 → 0.6 → 0.7. Pin your version; check release notes when upgrading.
3. **REST catalog is the production path** but requires running a service. For learning, SQL catalog is fine; for production, REST (Apache Polaris, Nessie, Tabular's REST) is what you'll see.
4. **Hidden partitioning** is an Iceberg feature: a partition column derived from another column (`day(order_timestamp)` partitions by day from a timestamp). Powerful but conceptually different from Hive partitioning. Read [the docs](https://iceberg.apache.org/docs/latest/partitioning/) before relying on it.
5. **Field IDs aren't visible in default `to_pandas()` output.** Iceberg tracks them internally; you only see them in schema introspection. They matter for migrations.

### Exercises

Create `tests/test_iceberg.py`.

1. Set up a local SQL-backed catalog. Create namespace `ecom`. Create a table `ecom.orders` from your Week 2 data. Confirm the warehouse directory has the expected layout (`metadata/`, `data/`).
2. Append a second batch. Print all snapshots — confirm two exist. Print the schema — confirm it matches.
3. **Time travel test:** record the current snapshot ID, append more data, then read at the recorded snapshot. Assert the older snapshot has fewer rows.
4. **Schema evolution test:** add a column `currency`, then rename `total` to `total_amount`. Read both at current state and at the original snapshot. What does each show?
5. **Filter pushdown test:** with a 10,000-row table, scan with `row_filter=GreaterThan("total", 100)`. Time it vs scanning all rows then filtering in pandas. Iceberg should be faster (manifest evaluation skips data).
6. **Cross-tool test:** write data with `pyiceberg`, query with DuckDB's `iceberg_scan` (using the metadata.json path). Note any quirks.
7. **Stretch:** export the table to plain Parquet using `table.scan().to_arrow()` + `pq.write_table(...)`. Compare row counts. (This is one way to "downgrade" out of Iceberg if you ever need to migrate off.)

### External practice

- [PyIceberg documentation](https://py.iceberg.apache.org/) — current
- [Iceberg specification](https://iceberg.apache.org/spec/) — long but thorough
- [Tabular blog — All about Iceberg's metadata](https://tabular.io/blog/) — visual explainers
- [Data Lakehouse Hub — Iceberg series](https://datalakehousehub.com/) — practical walkthroughs

### Self-check (Day 3)

> Q3.1 — Why does Iceberg need a catalog and Delta doesn't?
> Q3.2 — Iceberg renames a column without rewriting data. How is that possible?
> Q3.3 — A snapshot ID in Iceberg vs a version number in Delta — are they interchangeable concepts?
> Q3.4 — When would you choose Iceberg over Delta?

---

## Day 4 (Thu) — Hudi (Briefly) & The Format War

### Theory: Hudi's strengths and Python limitations

Apache Hudi was the *first* of the three formats (Uber, 2016). Its sweet spot is **streaming upserts** — incrementally merging change data into a lakehouse table.

Two key Hudi-specific concepts:

- **Copy-on-Write (CoW) tables** — every update rewrites the affected Parquet files. Slower writes, faster reads. Like Delta and Iceberg's default behavior.
- **Merge-on-Read (MoR) tables** — updates write to small *delta logs* (Avro). Compaction merges them into base Parquet later. Faster writes, slightly slower reads. **Unique to Hudi** among the three.

If you're streaming millions of CDC events per minute and read latency tolerance is loose, MoR tables can absorb writes more cheaply than the always-rewrite model. That's Hudi's niche.

### The Python story

Hudi's Python ecosystem in 2026 is the weakest of the three:

- The traditional path is **PySpark + the Hudi bundle JAR** (`org.apache.hudi:hudi-spark3-bundle`). Powerful, full-featured, but requires JVM, Spark, and considerable setup.
- The newer **`hudi` PyPI package** (Rust-based, from the `hudi-rs` project) supports **read-only** access. You can scan a table and read snapshots; you can't write or merge from pure Python yet.
- Writing from Python without Spark is *not currently practical* for Hudi. (This may change; the format is actively evolving.)

For testing purposes: if your project doesn't already use Hudi, **don't introduce it for testing reasons alone** — Delta or Iceberg will give you a smoother experience. If you inherit a Hudi table, the testing approach is mostly identical to Delta/Iceberg in concept (read snapshots, validate schemas, assert row counts) — you just have fewer Python-native tools.

### Reading a Hudi table from Python (if you have one)

```python
# Assumes a Hudi table already exists at /tmp/trips_table
# (created via Spark or another Hudi writer)
from hudi import HudiTableBuilder

table = HudiTableBuilder.from_base_uri("/tmp/trips_table").build()
batches = table.read_snapshot(filters=[("city", "=", "san_francisco")])

import pyarrow as pa
df = pa.Table.from_batches(batches).to_pandas()
print(df.head())
```

Time travel:
```python
batches = table.read_snapshot_as_of(
    "20240101120000000",   # Hudi timeline timestamp format
    filters=[("city", "=", "san_francisco")],
)
```

### The format-war framing — and why it matters less than the discourse suggests

Online debates about "which format wins" are loud. The truth as of mid-2026:

- **Iceberg has the most momentum.** Snowflake, BigQuery, Redshift, Databricks all read Iceberg; the REST catalog spec is the de-facto industry standard for table catalogs.
- **Delta has the largest installed base on Databricks.** If you work on Databricks, Delta is the default — there's no good reason to switch.
- **Hudi has the most opinionated streaming story.** If you're doing real-time CDC ingestion, Hudi has features the others copied later.
- **All three are "good enough"** for the vast majority of analytical workloads. The choice rarely makes or breaks a project.

What *will* break a project: choosing the wrong **catalog** strategy, ignoring vacuum/retention policies, mixing readers and writers across different format versions, or treating any format as a substitute for proper data modeling.

### Decision matrix

| Scenario | Recommended choice | Why |
|---|---|---|
| Greenfield analytics on AWS / GCP / Azure | Iceberg | Multi-engine future-proof; REST catalog ecosystem |
| Already on Databricks | Delta | Default, deeply integrated, no reason to fight it |
| Streaming upserts from Kafka, MoR for write throughput | Hudi | Built for this case; others added it later |
| Local development, learning, prototyping | Either Delta or Iceberg | Pure-Python paths exist; pick the one your future production will use |
| Cross-engine reads (Snowflake + Trino + Spark on same table) | Iceberg | Best multi-engine support today |
| Want minimum operational complexity | Delta (no catalog needed) | Iceberg's catalog adds a service to manage |
| Want maximum flexibility for future migrations | Iceberg | Strongest spec, broadest engine support |

### Cross-format insights — the lakehouse skills that transfer

Whatever format you use, these things apply:

1. **Vacuum / expire / clean policy** — old files accumulate; you must clean them, but cleaning destroys time-travel history before that point. Decide retention deliberately.
2. **Schema evolution discipline** — adding columns is safe; removing is not (downstream consumers may depend on them); renaming is risky without a migration plan.
3. **Concurrent writer management** — optimistic concurrency is enough for batch ETL, not for high-throughput streams.
4. **Time travel for debugging** — "what did the data look like when this report was generated?" is a powerful debugging move available in all three.
5. **Manifest / metadata reads for fast tests** — like Parquet metadata in Week 10, table-format metadata answers many test questions without reading data.

### Gotchas

1. **Don't introduce a table format because it sounds modern.** If your data is in two CSV files updated weekly by a single writer, plain Parquet (or even CSV) is fine.
2. **Format mixing.** Reading a Delta table with the Iceberg API or vice versa fails — they're different metadata layouts. The data underneath is Parquet; the metadata is format-specific.
3. **Cross-engine writes are still risky.** Cross-engine *reads* are mostly safe. *Writing* the same table from two different engines (e.g., Spark + Trino) — verify your specific engine versions support it cleanly.
4. **Catalog drift in Iceberg.** A table can be registered in two catalogs pointing to the same physical location. Both think they own it; updates from one are invisible to the other until cache refresh. Single source of truth matters.
5. **Hudi MoR's "real-time view" vs "read-optimized view"** is a subtlety that has tripped up many teams. Real-time view merges base + delta logs at read time (slower but current); read-optimized view skips deltas (faster but stale until next compaction). Know which you're querying.

### Exercises

These are conceptual / comparison exercises — write your answers in `notes.md`.

1. **The format-war essay (one page in `notes.md`):** for each of Delta, Iceberg, and Hudi, write 2–3 sentences each on: when to choose it, when *not* to, and one specific feature that's distinctive. Resist the urge to declare a winner.
2. **Migration thought experiment:** you have 200 Delta tables. Your company decides to standardize on Iceberg. What's involved? Sketch the migration plan in 10 bullet points. (No coding; this is interview-question prep.)
3. **Concurrent writer scenario:** two pipelines try to append to the same Delta table at the same second. Which wins? What does the loser see? What if they both try to update the same row? Write your answer based on optimistic concurrency control.
4. **Test design:** for a partitioned Delta table refreshed daily, list five tests you'd run in CI to assert health. Be specific about what each test catches.
5. **Read [Onehouse — The Big Three Lakehouse Comparison](https://www.onehouse.ai/blog/apache-hudi-vs-delta-lake-vs-apache-iceberg-lakehouse-feature-comparison)** (or another current comparison piece). Note where the article is opinionated vs factual. Is the source neutral?
6. **Stretch:** if you have a working Hudi table somewhere (or can spin one up via Spark for an hour), use the `hudi` PyPI package to read it. Compare ergonomics to Delta and Iceberg.

### External practice

- [Onehouse blog — Hudi/Delta/Iceberg comparison](https://www.onehouse.ai/blog/apache-hudi-vs-delta-lake-vs-apache-iceberg-lakehouse-feature-comparison) (Hudi-affiliated; read with that lens)
- [Apache Iceberg vs Hudi vs Delta Lake — Subsurface 2024 talks](https://www.dremio.com/subsurface/) (multi-author perspectives)
- [`hudi-rs` GitHub](https://github.com/apache/hudi-rs) — track the Python read library's progress
- [Hannes Mühleisen — DuckDB's Iceberg support](https://duckdb.org/2024/06/26/iceberg-extension.html) — pragmatic engine-vendor view

### Self-check (Day 4)

> Q4.1 — Hudi's MoR tables — what's distinctive, and when does it pay off?
> Q4.2 — You're staffing a new project on AWS, no existing infrastructure. Default to which format and why?
> Q4.3 — Your team is on Databricks. Should you switch to Iceberg "for the future"?
> Q4.4 — What's the operational cost of keeping a vacuum / expire / clean policy *off* on a long-running lakehouse table?

---

## Day 5 (Fri 🤖) — AI Workflow: Schema Evolution Simulation

### What you're learning today

Schema evolution is the riskiest operation on a lakehouse table — change the wrong way and downstream consumers break silently. Today's AI exercise: have Claude generate a *sequence of evolutions* with corresponding tests at each step. The test suite simulates a series of "real" schema changes and asserts that downstream queries still produce sane results across the migration.

This skill maps directly to a real interview-grade scenario: "Walk me through how you'd safely add a column to a 50-table data lake."

### Setup

Reuse the `anthropic` setup from Weeks 8–10. You'll generate ~5–10 small SQL queries / Python tests; total cost should be well under $0.10.

### Exercise 1 — Generate a schema-evolution plan

Pick a starting schema for one of your e-commerce tables. Paste into Claude:

> *"I have a Delta table `orders` with this schema:*
>
> *- order_id: int*
> *- customer_id: int*
> *- total: double*
> *- status: string (one of: pending, completed, cancelled)*
>
> *Generate a 5-step schema evolution plan that simulates realistic business changes:*
> *1. Step 1: add a column*
> *2. Step 2: add another column with a default behavior*
> *3. Step 3: rename a column*
> *4. Step 4: change a value's allowed enum*
> *5. Step 5: drop a column that's no longer used*
>
> *For each step, give me:*
> *- The Python code (using deltalake) to execute the change*
> *- A pytest test that asserts the change took effect AND that an older snapshot still returns the original schema*
> *- A 'risk to downstream consumers' note*
>
> *Use modern deltalake APIs."*

Review the output. Common AI mistakes:
- **Renaming a column in Delta requires column-mapping mode** — the AI may not know to enable it. Verify via `dt.metadata().configuration`.
- **Dropping a column with `schema_mode="overwrite"`** — possible but loses time travel of the column. The AI may suggest this without noting the trade-off.
- **Generated test data using outdated APIs.** Run each step manually before trusting the test.

### Exercise 2 — Detect a backwards-incompatible change

Give Claude two schema versions and ask which changes are safe vs breaking:

> *"Schema A:*
> *- order_id: int*
> *- email: string*
> *- total: double*
>
> *Schema B:*
> *- order_id: int*
> *- customer_email: string  (renamed from email)*
> *- total: integer  (changed from double)*
> *- created_at: timestamp  (new)*
>
> *For each difference, classify as 'safe', 'risky', or 'breaking', and explain why. Then write a pytest test using deltalake that asserts Schema A consumers (queries that select email and treat total as float) won't break after migration to Schema B. If they would break, name the specific failure mode."*

This is the kind of analysis a senior engineer does in code review. AI gets it mostly right; you'll catch nuances (e.g., "rename" can be safe IF column mapping is enabled AND IF downstream uses field IDs, otherwise breaking).

### Exercise 3 — Generate a vacuum / retention strategy

Vacuum is destructive. Ask Claude to generate a documented policy:

> *"Generate a markdown table comparing reasonable vacuum / expire / clean retention policies for these workloads, across Delta, Iceberg, and Hudi:*
>
> *1. Daily-refreshed marketing dashboard (read-heavy, occasional debugging)*
> *2. Real-time customer-facing analytics (high write rate, low historical-query need)*
> *3. Financial transactions (audit requirements, 7-year retention)*
> *4. ML training data (need to reproduce experiments from any past month)*
>
> *For each, recommend a retention period and a risk note. Don't include code; just the policy table."*

This produces a 12-cell table that's a real-world reference document. Save it to your project. The combination of "I asked an AI" + "I reviewed and adjusted it" is the right level of trust for this kind of policy work — neither blind copy nor from-scratch.

### Update your `.cursorrules`

```
Lakehouse / table-format conventions:
- Default to Delta for Databricks-centric stacks; Iceberg for greenfield multi-engine; Hudi only when streaming upserts is the primary need.
- Pure-Python access: use `deltalake` for Delta, `pyiceberg` for Iceberg.
- For Iceberg, always specify catalog explicitly. Never use 'default' or implicit catalogs in production code.
- Column ADD is safe; RENAME requires column-mapping mode (Delta) or is native (Iceberg); DROP is breaking — always coordinate with downstream consumers.
- Time travel:
  - Delta: by version (int) or timestamp (ISO 8601)
  - Iceberg: by snapshot_id (long)
  - Hudi: by timeline timestamp (yyyyMMddHHmmssSSS)
- Vacuum / expire policy: document retention; never run vacuum without alerting the team.
- Test patterns:
  - Always test that a new write creates a new version/snapshot.
  - Always test that time travel returns expected pre-change state.
  - Always test that schema evolution preserved old data (not silently NULL'd).
- DuckDB's `delta_scan()` and `iceberg_scan()` are great for ad-hoc verification; not a substitute for production-grade engines.
```

### Quality bar — when is a generated lakehouse plan "good"?

- [ ] Each evolution step has a *paired test* that asserts both new state and time-travel-to-old state
- [ ] Risk notes are specific (named consumer types or query patterns), not generic
- [ ] APIs match the version of `deltalake` / `pyiceberg` you have installed
- [ ] Vacuum policy includes both retention duration *and* the trade-off it makes
- [ ] No mixed-format confusion (don't apply Delta APIs to Iceberg tables)
- [ ] Tests don't accidentally read from a future state when meant to test the past

### Reflection (write 3–5 sentences in `notes.md`)

- Was the AI's grasp of "what's safe vs breaking" in schema evolution accurate?
- Did it know about column-mapping mode for Delta renames? (Many AI generations miss it.)
- Comparing Friday workflows from Weeks 8–11: synthetic data → schema inference → CI debugging → schema evolution. Which is the highest-leverage AI use case for your day-to-day?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 12. 5–7 = re-review. <5 = redo exercises.

1. Why are Delta, Iceberg, and Hudi described as "metadata layers over Parquet" instead of "new file formats"?
2. The single-line difference between an APPEND and an OVERWRITE in `write_deltalake`.
3. A Delta `DELETE` removes 100 rows. How many of the underlying Parquet files are physically deleted?
4. Explain how time travel can return last week's data even though you've appended every day since.
5. Iceberg requires a catalog. Delta doesn't. Why does that difference exist?
6. What does Iceberg's "field IDs" approach enable that Delta's column-name approach (in default mode) doesn't?
7. Hudi's distinctive feature among the three formats — name it.
8. You inherited a Delta table with retention=7 days, vacuum runs nightly. Can you time-travel to a snapshot from 30 days ago? Why or why not?
9. After a schema evolution that *renamed* a column, a downstream query that selects the old name fails. Is this a Delta issue, an Iceberg issue, both, or neither — and what's the safe mitigation?
10. After running an AI to generate a lakehouse migration plan, the first thing you do is...?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about lakehouse table formats.

### IQ1. "Walk me through what happens when you call `MERGE` (upsert) on a Delta table."

*What a good answer covers:*
- Delta finds files containing rows matching the merge predicate (uses statistics for skipping)
- Reads those files, applies the merge logic in memory (or via streaming for large merges)
- Writes new Parquet files containing the merged data
- Atomically commits: in one transaction, marks old files as removed and new files as added
- Old files stay on disk until vacuum
- Concurrent writers: each MERGE is a transaction; conflicts are detected at commit time and the loser retries (optimistic concurrency)

*Likely follow-up:* "What's the failure mode if two MERGEs target overlapping rows?" (Answer: one will commit, the other will detect the conflict and either retry or fail depending on configuration. This is fine for batch jobs; problematic for high-frequency concurrent writers.)

### IQ2. "How do you safely add a column to a 50-table lakehouse?"

*What a good answer covers:*
- **Audit consumers first** — what queries / dbt models / dashboards use these tables? List them.
- **Add column with default NULL** — both Delta and Iceberg support this without rewriting historical data.
- **Backfill if needed** — if the new column has a derivable value for historical rows, run a one-time backfill via an UPDATE.
- **Notify downstream consumers** — even though adding a column doesn't break readers, dbt schema tests, GE expectations, etc., need updates to *expect* the new column.
- **Update CI tests** — every schema check (Week 4) should mention the new column.
- **Monitor for surprise consumers** — query logs reveal who reads the table; alert on unfamiliar queries that might break.
- **Document the change** — release notes, schema registry, or whatever the team uses.

*Likely follow-up:* "What about removing a column?" (Answer: much harder. Audit consumers; remove their dependency first; deprecation period of weeks/months; only then drop. Or use a soft-delete: rename the column to `_deprecated_col_name` so existing queries fail loudly rather than silently returning NULL.)

### IQ3. "Compare Delta Lake and Iceberg as table formats."

*What a good answer covers:*
- **Origin and ecosystem**: Delta from Databricks, deeply integrated there; Iceberg from Netflix, broader multi-engine adoption.
- **Catalog model**: Delta is path-based; Iceberg is catalog-based. Delta is simpler to start; Iceberg is more enterprise-ready.
- **Schema evolution**: Iceberg uses field IDs (rename without rewrite is native); Delta uses names (column-mapping mode required for rename).
- **Tooling**: Both have mature Python libraries. `pyiceberg` is younger; `deltalake` is more battle-tested.
- **Performance**: Both are fast; differences are workload-specific. Recent benchmarks favor neither universally.
- **Bottom line**: For new projects, Iceberg has the most momentum (Snowflake, BigQuery, Databricks all support it); for existing Databricks shops, Delta remains the default.

*Likely follow-up:* "Have you used both?" (Answer honestly; if yes, share a specific decision moment. If no, say so and reference what you've read.)

### IQ4. "What's the role of vacuum / expire / clean operations, and what's the risk if you skip them?"

*What a good answer covers:*
- **Why they exist**: every UPDATE / DELETE / MERGE leaves orphan Parquet files that aren't part of the current commit. Vacuum removes them after a retention period.
- **Risk of skipping**: storage cost grows linearly with operation rate; in extreme cases, hundreds of GB of orphan files per table.
- **Risk of running aggressively**: time travel beyond retention fails; reproducibility for audits / debugging is lost.
- **Sweet spot**: align retention with business needs — 7 days for ops debugging, 30 days for analytics, indefinite for audit-bound tables (but plan for the cost).
- **Production discipline**: vacuum runs as a scheduled job, alerted on failure, never run interactively without senior review.

*Likely follow-up:* "How do you decide retention period?" (Answer: combine business needs (audit, compliance), engineering needs (debugging window), and cost (storage of orphan files). Document the decision; review annually.)

### IQ5. "How would you test a CDC pipeline that does upserts into a Delta table?"

*What a good answer covers:*
- **Functional tests**: feed known input → assert known output via `MERGE`. Cover insert-only, update-only, no-op, and mixed batches.
- **Schema tests**: target schema matches expected; merge doesn't accidentally add columns.
- **Idempotency tests**: running the same merge twice produces the same final state (key for replay scenarios).
- **Time-travel tests**: after a merge, you can read the pre-merge state and verify what changed.
- **Volume tests**: at 10x normal volume, merge completes in expected time; doesn't OOM.
- **Concurrency tests**: two simultaneous merges with non-overlapping keys both succeed; with overlapping keys, one retries.
- **Reconciliation**: source row count + target pre-state row count = target post-state row count + duplicates handled. (Same Week 1 reconciliation rule.)

*Likely follow-up:* "What's the failure mode of a non-idempotent merge?" (Answer: replays produce different results — common when the merge logic depends on existing state in a non-deterministic way, like "set updated_at = now()". Catches users when the pipeline retries a failed run and produces a different result than the original would have.)

---

## If you have extra time this week (stretch)

- Set up a [Polaris](https://github.com/apache/polaris) or [Nessie](https://projectnessie.org/) catalog locally. These are open-source REST catalogs for Iceberg — a step closer to production than the SQL catalog.
- Read [Netflix — Iceberg's origin story](https://www.databricks.com/session_eu19/a-deep-dive-into-iceberg-table-format) (recorded talks). Why Iceberg was built; what Hive Metastore couldn't do.
- Try [Apache XTable](https://xtable.apache.org/) — a project for cross-format interop (read a Delta table as if it were Iceberg, etc.). Useful for multi-format environments.
- If you have access to a Hudi table at work, use the `hudi` PyPI package to read it. Compare ergonomics. File any rough edges as GitHub issues — `hudi-rs` is actively developed and maintainers welcome feedback.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Iceberg doesn't replace Parquet; it's a metadata layer that wraps Parquet files to add transactional semantics. The data underneath is still Parquet. "Iceberg vs Parquet" is a category mistake.
- **Q1.2** — Parquet files are immutable, but the metadata (commit log) is append-only. To time-travel, you read the commit log up to a target version, get the list of Parquet files at that version, and read those. Older Parquet files persist on disk until vacuum.
- **Q1.3** — Iceberg by design separates "what tables exist" (catalog) from "where the data is" (storage), enabling multiple engines to share a consistent table view. Delta packages both into the directory itself — simpler, but harder to share across engines that have different naming/discovery conventions.
- **Q1.4** — Single-writer, append-only datasets where you don't need time travel, ACID, or schema evolution. A monthly-refreshed lookup table; static reference data; one-shot exports. The complexity isn't free; if you don't need it, skip it.

### Day 2 answers

- **Q2.1** — `overwrite` replaces all current data with the new DataFrame; `append` adds new rows on top of existing data. Both create new versions; `overwrite` marks the old files as removed.
- **Q2.2** — None are deleted immediately. The DELETE rewrites the affected files (excluding the deleted rows) and commits a new version where the old files are marked removed. The old files stay on disk until vacuum's retention period elapses.
- **Q2.3** — Plain Parquet has no native UPSERT — implementing it manually is brittle. MERGE provides atomic, idempotent upsert semantics on append-only storage, which is the foundation of CDC pipelines, slowly-changing dimensions, and incremental ETL. Without it, every "update" is a full rewrite.
- **Q2.4** — The read fails. Vacuum has deleted the underlying Parquet files for that version; the metadata still references them but they don't physically exist. Some implementations may give a clearer error than others; the result is the same: time travel beyond retention is not possible.

### Day 3 answers

- **Q3.1** — Iceberg's design separates the "logical table" (catalog) from "physical storage." This enables features like rename, multi-table transactions, and consistent multi-engine access. Delta tables are tied to a path; the path *is* the identifier. Simpler, less flexible.
- **Q3.2** — Iceberg tracks every column by a numeric *field ID*, not by name. The schema metadata maps field IDs to current names. Renaming changes only the metadata mapping; the underlying Parquet files (which reference field IDs internally) are untouched.
- **Q3.3** — They serve the same purpose (identify a point-in-time state) but aren't interchangeable APIs. Delta version is a sequential int (0, 1, 2...). Iceberg snapshot ID is a long random number. Both can also be referenced by timestamp.
- **Q3.4** — When you need multi-engine support (Snowflake + Trino + Spark on the same tables); when schema evolution flexibility matters (frequent renames); when REST catalog interop is part of your roadmap; or simply when starting fresh with no Databricks dependency.

### Day 4 answers

- **Q4.1** — Hudi's Merge-on-Read (MoR) tables write small Avro delta logs for updates rather than rewriting Parquet files. Compaction merges them later. This pays off for write-heavy streaming workloads where rewrite-per-update would be too expensive. Trade-off: read latency includes merging deltas (real-time view) or accepting staler data (read-optimized view).
- **Q4.2** — Iceberg. The multi-engine support and fast-growing ecosystem make it the lowest-regret choice for greenfield work. Delta is also fine; the choice is rarely catastrophic. Hudi only if streaming upserts are the primary concern.
- **Q4.3** — Probably not. Delta on Databricks is the path of least resistance — switching imposes migration cost, retraining cost, and potential feature-parity issues. Switch only if there's a concrete pain point Iceberg solves better; "for the future" alone isn't justification.
- **Q4.4** — Operational cost: storage grows linearly with operation rate; orphan files (no longer in any commit) accumulate. Across hundreds of tables this can be tens or hundreds of TB of unnecessary storage. The "saving" of skipping vacuum is illusory — you pay it in storage instead.

### End-of-week answers

**A1.** All three store actual data in Parquet (immutable column files). They add metadata (commit logs, manifests, timelines) that gives Parquet ACID semantics, time travel, and schema evolution. The "format" is the metadata layer; the data format is still Parquet.

**A2.** `mode="append"` adds rows on top of existing data; `mode="overwrite"` replaces all current data with the new DataFrame.

**A3.** Zero immediately. The DELETE rewrites affected files without the deleted rows and commits a new version that marks old files as removed. Old files are physically deleted by a future `vacuum` operation.

**A4.** The Parquet files are immutable; the metadata commit log is append-only. Reading "as of" a past time means reading the commit at that point in the log and then reading exactly the files that commit references. Old files remain on disk until vacuum, which is what enables time travel.

**A5.** Iceberg's design separates "what tables exist" (catalog, an external service) from "where data is" (object storage). This enables multi-engine access and rename without data rewrites. Delta packages catalog-like info into the table directory itself — simpler local setup, harder cross-engine sharing.

**A6.** Field IDs let Iceberg rename columns without rewriting any data — only metadata changes. Old snapshots remain readable under their original column names because field-ID-to-name mapping is per-snapshot. Delta's default mode requires rewriting (or column-mapping mode opt-in).

**A7.** Merge-on-Read (MoR) tables — writes go to small delta logs (Avro), compaction merges them into base Parquet later. Faster writes at the cost of slightly slower reads (or staleness, in read-optimized view).

**A8.** No. Vacuum has deleted the Parquet files for snapshots older than 7 days. The commit log still references them but they don't exist on disk. Time travel beyond the retention period fails.

**A9.** A Delta issue (assuming default column-mapping mode is off). Mitigation: enable column-mapping mode *before* the rename, or use `schema_mode="merge"` patterns to support both old and new names during a transition period. Iceberg, by contrast, handles this natively because it tracks field IDs.

**A10.** Verify it on the actual data. Run each step and confirm the table state matches what the AI claimed. Pay particular attention to: the AI's understanding of column-mapping mode for Delta renames, the difference between a "safe" and a "breaking" change, and whether the tests actually exercise both new state and time-travel-to-old state. The plan looks plausible; validating is what makes it trustworthy.

---

*Done with Week 11? You can match table-format choice to the project, write tests that exercise time travel and schema evolution, and articulate trade-offs clearly enough to defend a choice in a design review. Onward to Week 12 — Performance & Volume Testing — where the question shifts from "is the data correct?" to "is the pipeline fast enough?"*
