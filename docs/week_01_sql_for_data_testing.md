# Week 1 — SQL for Data Testing | Training Materials

> **Companion to:** Week 1 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Become fluent in the SQL patterns you'll write daily as a data quality engineer.

---

## How to use this file

- Each day has four blocks: **Theory → Gotchas → Exercises → Self-check**
- Don't skim the gotchas — most real-world data quality bugs hide there
- Friday is **hands-on AI workflow practice**, not a passive read
- Answers to all self-checks are at the bottom of the file (no peeking 🙂)

---

## One-time setup (~15 minutes, do this before Monday)

You need somewhere to *run* SQL. Pick one — order of effort, low to high:

| Option | Setup effort | Best for |
|---|---|---|
| [**DB Fiddle**](https://www.db-fiddle.com/) (PostgreSQL flavour) | 0 min — just open browser | Pasting in the practice schema below and running queries |
| [**SQLZoo**](https://sqlzoo.net/) | 0 min | Pre-loaded sample DBs, instant feedback |
| [**SQLBolt**](https://sqlbolt.com/) | 0 min | Interactive lessons, in-browser execution |
| [**DuckDB**](https://duckdb.org/docs/installation/) CLI | 5 min, one binary | Closest to real data engineering — you'll use it later anyway |
| SQLite via [DB Browser for SQLite](https://sqlitebrowser.org/) | 5 min | GUI, file-based |

**Recommendation for this week:** DB Fiddle for the structured exercises + SQLZoo/SQLBolt for warm-up drills.

### Practice schema for this week

Paste this into DB Fiddle (PostgreSQL 16) once, then reuse all week. It's a deliberately *messy* mini e-commerce dataset — NULLs, duplicates, an orphaned order, mismatched amounts. That's the point.

```sql
CREATE TABLE customers (
    customer_id   INT PRIMARY KEY,
    email         TEXT,
    signup_date   DATE,
    country       TEXT,
    status        TEXT
);

CREATE TABLE products (
    product_id    INT PRIMARY KEY,
    name          TEXT,
    category      TEXT,
    price         NUMERIC(10,2),
    active        BOOLEAN
);

CREATE TABLE orders (
    order_id      INT PRIMARY KEY,
    customer_id   INT,
    order_date    DATE,
    total_amount  NUMERIC(10,2),
    status        TEXT
);

CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY,
    order_id      INT,
    product_id    INT,
    quantity      INT,
    unit_price    NUMERIC(10,2)
);

INSERT INTO customers VALUES
 (1, 'anna@example.com',  '2024-01-15', 'PL',  'active'),
 (2, 'ben@example.com',   '2024-02-03', 'US',  'active'),
 (3, 'carla@example.com', '2024-02-20', NULL,  'active'),       -- missing country
 (4, 'dan@example.com',   '2024-03-01', 'DE',  'churned'),
 (5, NULL,                '2024-03-12', 'PL',  'active'),       -- missing email
 (6, 'eve@example.com',   '2024-04-04', 'UA',  NULL),           -- missing status
 (7, 'frank@example.com', '2024-04-04', 'UA',  'active');

INSERT INTO products VALUES
 (101, 'Wireless Mouse',     'electronics', 25.00, TRUE),
 (102, 'Mechanical Keyboard','electronics', 90.00, TRUE),
 (103, 'Coffee Mug',         'home',         8.50, TRUE),
 (104, 'Old Headphones',     'electronics', 40.00, FALSE),     -- inactive
 (105, 'Notebook',           'office',       3.00, TRUE);

INSERT INTO orders VALUES
 (1001, 1,    '2024-05-01', 115.00, 'completed'),
 (1002, 2,    '2024-05-02',  17.00, 'completed'),
 (1003, 3,    '2024-05-02',  90.00, 'completed'),
 (1004, 4,    '2024-05-03',  NULL,  'completed'),               -- missing total
 (1005, 7,    '2024-05-04',  25.00, 'cancelled'),
 (1006, 999,  '2024-05-05',  50.00, 'completed'),               -- orphaned customer
 (1007, 1,    '2024-05-06',  25.00, 'completed');

INSERT INTO order_items VALUES
 (1, 1001, 101, 1, 25.00),
 (2, 1001, 102, 1, 90.00),
 (3, 1002, 103, 2,  8.50),
 (4, 1003, 102, 1, 90.00),
 (5, 1004, 105, 3,  3.00),   -- items sum to 9.00, but order.total is NULL
 (6, 1005, 101, 1, 25.00),
 (7, 1006, 101, 2, 30.00),   -- unit_price 30 ≠ products.price 25 (drift!)
 (8, 1007, 101, 1, 25.00);
```

Run `SELECT COUNT(*) FROM customers;` to confirm everything loaded.

---

## Day 1 (Mon) — NULL Handling & Data Integrity

### Theory

SQL uses **three-valued logic**: `TRUE`, `FALSE`, and `UNKNOWN`. A `NULL` represents *"unknown / absent"*, not a value. This breaks many beginner intuitions:

- `NULL = NULL` → `UNKNOWN` (not `TRUE`!)
- `NULL <> 'something'` → `UNKNOWN`
- `WHERE x = NULL` will never match any row — you must use `IS NULL`
- A `WHERE` clause only keeps rows where the predicate is `TRUE` (not `UNKNOWN`)

**Why this matters for QA:** roughly half of the "the report shows wrong numbers" tickets in real data teams trace back to silently dropped rows because someone wrote `WHERE status <> 'cancelled'` and forgot that `NULL` statuses don't satisfy `<>`.

### Functions you must know cold

| Function | What it does | Example |
|---|---|---|
| `IS NULL` / `IS NOT NULL` | The only correct way to test for NULL | `WHERE email IS NULL` |
| `COALESCE(a, b, c, ...)` | Returns the first non-NULL argument | `COALESCE(country, 'UNKNOWN')` |
| `NULLIF(a, b)` | Returns `NULL` if `a = b`, else `a` | `NULLIF(division, 0)` to avoid divide-by-zero |
| `IFNULL(a, b)` (MySQL) / `ISNULL(a, b)` (SQL Server) | Two-arg COALESCE — vendor-specific | Prefer `COALESCE` (ANSI SQL, portable) |

### Gotchas (memorize these)

1. **`COUNT(*)` counts all rows** (including all-NULL ones). **`COUNT(col)` counts only non-NULL values of `col`**. The difference between them = number of NULLs.
2. **Aggregates ignore NULLs by default.** `AVG(price)` over `(10, 20, NULL)` = `15`, not `10`. Sometimes that's wrong for your QA case.
3. **`NOT IN (subquery)` is dangerous.** If the subquery returns even one NULL, the whole expression becomes UNKNOWN and you get *zero rows back*. Use `NOT EXISTS` or `LEFT JOIN ... WHERE ... IS NULL` instead.
4. **String concatenation with NULL = NULL** in standard SQL. `'Hello ' || NULL` → `NULL`. Use `CONCAT_WS` or `COALESCE` to defend.
5. **`DISTINCT` treats all NULLs as equal** for the purpose of deduplication — even though `NULL = NULL` is UNKNOWN. SQL is wonderfully inconsistent.

### Exercises (write these against the practice schema)

1. Find all customers with a missing email **or** missing country.
2. Show every customer with `country` defaulted to `'UNKNOWN'` when NULL — sorted by signup date.
3. Count, for each table, how many NULLs exist in every column. (Hint: `COUNT(*) - COUNT(col)` per column.)
4. Find orders where `total_amount IS NULL`. What should the QA action be?
5. Write a query that returns `TRUE` if **any** customer has a NULL email, else `FALSE`. (One row, one column.)
6. **Trap exercise:** write `SELECT * FROM customers WHERE country <> 'PL';`. How many rows? Does it include Carla (country = NULL)? Why not? Now rewrite to *also* include the NULLs.

### External practice

- [SQLBolt — Lesson 8: NULLs](https://sqlbolt.com/lesson/select_queries_with_null) — short, interactive
- [PostgreSQL Tutorial — NULL handling](https://www.postgresqltutorial.com/postgresql-tutorial/postgresql-is-null/)

### Self-check (Day 1)

> Q1.1 — `SELECT COUNT(*) FROM customers WHERE country = NULL;` returns?
> Q1.2 — What does `COALESCE(NULL, NULL, 'fallback', 'never')` return?
> Q1.3 — A pipeline runs `WHERE status NOT IN ('cancelled', 'refunded')`. Some rows have `status IS NULL`. Are they kept or dropped?
> Q1.4 — Why is `NULLIF(numerator / denominator, 0)` *not* a safe divide-by-zero guard? What's the right pattern?

---

## Day 2 (Tue) — Aggregations for QA

### Theory

Aggregations are how you **reduce a column to a single value** — and how you **spot anomalies at a glance**. For QA, you'll combine them with `GROUP BY` to compare row counts, sums, distinct values across slices (per day, per source, per country, etc.).

| Aggregate | Does what | NULL behavior |
|---|---|---|
| `COUNT(*)` | Counts rows | Counts NULL rows |
| `COUNT(col)` | Counts non-NULL values | Ignores NULL |
| `COUNT(DISTINCT col)` | Counts unique non-NULL values | Ignores NULL |
| `SUM(col)` | Total | Ignores NULL (treats as 0 for sum purposes) |
| `AVG(col)` | Mean of non-NULL values | Ignores NULL — denominator shrinks! |
| `MIN(col)` / `MAX(col)` | Smallest / largest non-NULL | Ignores NULL |

### The QA aggregation playbook

For any new table, run these checks first — they catch ~70% of obvious data issues:

```sql
-- 1. Is the table even populated?
SELECT COUNT(*) FROM orders;

-- 2. NULL profile per column
SELECT
  COUNT(*)                                        AS total_rows,
  COUNT(*) - COUNT(customer_id)                   AS null_customer_id,
  COUNT(*) - COUNT(total_amount)                  AS null_total_amount,
  COUNT(DISTINCT customer_id)                     AS unique_customers,
  COUNT(*) - COUNT(DISTINCT order_id)             AS duplicate_order_ids   -- should be 0
FROM orders;

-- 3. Numeric range sanity
SELECT
  MIN(total_amount) AS min_amount,
  MAX(total_amount) AS max_amount,
  AVG(total_amount) AS avg_amount
FROM orders;

-- 4. Categorical distribution
SELECT status, COUNT(*) AS cnt
FROM orders
GROUP BY status
ORDER BY cnt DESC;
```

If `min_amount` is negative, you have a bug. If a status appears that wasn't in the spec, schema drift. If `unique_customers` equals `total_rows` and that wasn't expected — also a bug.

### Gotchas

1. **`AVG` silently ignores NULLs**, so the average of `(10, 20, NULL, NULL)` is `15`, not `7.5`. If you want NULL treated as 0: `AVG(COALESCE(col, 0))`.
2. **`COUNT(DISTINCT col)` can be slow on huge tables** — many warehouses have approximate variants like `APPROX_COUNT_DISTINCT` (BigQuery, Snowflake) that are far faster.
3. **`HAVING` filters groups, `WHERE` filters rows.** A surprisingly common bug: putting an aggregate in `WHERE` (which won't compile) or filtering pre-aggregation in `HAVING` (which works but is slower).
4. **Empty result sets:** `SUM` of zero rows = `NULL`, but `COUNT` of zero rows = `0`. Wrap sums in `COALESCE` if you need a number.

### Exercises

1. For each `country`, count active vs churned customers. Order by total customers descending.
2. For each `status`, return order count and total revenue (sum of `total_amount`). Be careful with the NULL `total_amount`.
3. For each customer, count how many orders they placed and the total they spent. Include only customers with at least 1 order.
4. **Anomaly hunt:** Find any product whose `unit_price` in `order_items` differs from its current `products.price`. (You'll need a JOIN — preview of Day 4.)
5. Compute: how many distinct emails do we have, and how many customers? If those differ, it's a duplicate-email bug.
6. Daily order count for the last 7 days of data — flag any day with `0` orders.

### External practice

- [SQLZoo — SUM and COUNT](https://sqlzoo.net/wiki/SUM_and_COUNT)
- [LeetCode SQL — Easy/Medium aggregation problems](https://leetcode.com/studyplan/top-sql-50/) (free tier covers most)
- [DataLemur — free SQL questions](https://datalemur.com/questions) — interview-style, includes anomaly detection

### Self-check (Day 2)

> Q2.1 — Why might `SELECT AVG(total_amount) FROM orders` give a different answer than business expects, even with no bug in the data?
> Q2.2 — What's the result of `SELECT SUM(quantity) FROM order_items WHERE order_id = 99999;` (assuming order 99999 doesn't exist)?
> Q2.3 — You want "products that have been ordered more than 5 times". Is the predicate in `WHERE` or `HAVING`?

---

## Day 3 (Wed) — Window Functions

### Theory

A **window function** computes across a set of rows *related to the current row*, **without collapsing them into one row** like `GROUP BY` does. That's the key idea: you keep every row, and add a computed column that "looks across" peers.

The general shape:

```sql
function_name(...) OVER (
    [PARTITION BY col1, col2, ...]   -- split into independent groups
    [ORDER BY   col3 ASC|DESC]       -- order within each group
    [ROWS|RANGE BETWEEN ... AND ...] -- frame (advanced — skip on day 3)
)
```

### The four functions every QA engineer needs

| Function | Returns | Typical QA use |
|---|---|---|
| `ROW_NUMBER()` | 1, 2, 3, 4… (no ties, no gaps) | Deduplication: keep first row per key |
| `RANK()` | 1, 2, 2, 4… (ties skip ranks) | Ranking with tie awareness |
| `DENSE_RANK()` | 1, 2, 2, 3… (ties don't skip) | Ranking without gaps |
| `LAG(col, n) / LEAD(col, n)` | Previous / next row's value | Detect gaps, time-between-events, value drift |

### Canonical patterns

**Pattern 1: Find duplicates by key**
```sql
SELECT *
FROM (
    SELECT
        email,
        customer_id,
        ROW_NUMBER() OVER (PARTITION BY email ORDER BY customer_id) AS rn
    FROM customers
    WHERE email IS NOT NULL
) sub
WHERE rn > 1;   -- every row here is a duplicate-by-email
```

**Pattern 2: Detect gaps in a sequence**
```sql
SELECT
    order_id,
    LAG(order_id) OVER (ORDER BY order_id) AS prev_id,
    order_id - LAG(order_id) OVER (ORDER BY order_id) AS gap
FROM orders
ORDER BY order_id;
-- Any gap > 1 = a missing order_id
```

**Pattern 3: Day-over-day change**
```sql
SELECT
    order_date,
    COUNT(*) AS daily_orders,
    LAG(COUNT(*)) OVER (ORDER BY order_date) AS prev_day,
    COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY order_date) AS delta
FROM orders
GROUP BY order_date
ORDER BY order_date;
```

### Gotchas

1. **`PARTITION BY` is *not* `GROUP BY`.** It defines the window scope — rows are still returned individually.
2. **`OVER ()` with empty parens is valid** — it means "the whole result set as one window". E.g. `SUM(x) OVER ()` gives every row a column with the grand total.
3. **`LAG`/`LEAD` return NULL at the boundary** (first row's `LAG` is NULL). Wrap with `COALESCE` if you need a default.
4. **Window functions can't go in `WHERE`.** They run *after* `WHERE`. To filter on a window result, wrap in a subquery / CTE.
5. Performance: window functions force a sort. On big tables, an `ORDER BY` inside `OVER` can be expensive — index helps.

### Exercises

1. Find any duplicate emails in `customers`. Return all duplicate rows (not just one per group).
2. Number each customer's orders chronologically — column `order_seq` = 1 for their first order, 2 for second, etc.
3. For each order, compute days since the customer's previous order (NULL if it's their first). Hint: `LAG` partitioned by customer.
4. Spot any gap of 2+ days between consecutive orders in the whole dataset.
5. Rank products by total revenue (`SUM(quantity * unit_price)` from `order_items`). Use `DENSE_RANK`. What changes if you use `RANK`?
6. **Stretch:** find the second-highest order total per customer. (Two valid approaches — one with `ROW_NUMBER`, one with `RANK`. Try both and compare.)

### External practice

- [PostgreSQL Tutorial — Window Functions](https://www.postgresqltutorial.com/postgresql-window-function/) — best free walkthrough
- [Mode Analytics — Advanced SQL: Window Functions](https://mode.com/sql-tutorial/sql-window-functions/)
- [HackerRank — Advanced Select / Aggregations](https://www.hackerrank.com/domains/sql) — has window-function problems

### Self-check (Day 3)

> Q3.1 — Difference between `RANK()` and `DENSE_RANK()` when there are ties?
> Q3.2 — Why can't you write `WHERE ROW_NUMBER() OVER (...) = 1`? How do you achieve that filter?
> Q3.3 — `SUM(amount) OVER (PARTITION BY customer_id ORDER BY order_date)` — what does this compute?

---

## Day 4 (Thu) — JOINs for Cross-Table Validation

### Theory — the JOIN family from a QA perspective

| JOIN | Keeps | Typical QA question |
|---|---|---|
| `INNER JOIN` | Only matching rows from both | "How many orders DO have a valid customer?" |
| `LEFT JOIN` | All left rows; NULL for unmatched right | "Which orders have NO matching customer?" (anti-join) |
| `RIGHT JOIN` | Mirror of LEFT | Rare; just flip table order and use LEFT |
| `FULL OUTER JOIN` | All rows from both; NULLs where unmatched | Reconciliation between two sources |
| `CROSS JOIN` | Cartesian product | Almost never on purpose. Test data generation, calendars. |
| Anti-join (`LEFT JOIN ... WHERE ... IS NULL`) | Rows in A with no match in B | **The QA workhorse** |

### The anti-join pattern (commit this to memory)

Find every row in **A** that has **no match** in **B**:

```sql
SELECT a.*
FROM table_a a
LEFT JOIN table_b b ON a.key = b.key
WHERE b.key IS NULL;
```

This is your bread and butter for **referential integrity** checks: orphaned orders (no customer), order_items pointing to deleted products, customers who never ordered, etc.

Equivalent — and often clearer / sometimes faster — with `NOT EXISTS`:
```sql
SELECT a.*
FROM table_a a
WHERE NOT EXISTS (SELECT 1 FROM table_b b WHERE b.key = a.key);
```

### Gotchas

1. **JOIN explosion (Cartesian or fan-out).** If your join key isn't unique on the right side, your row count multiplies. Always ask: "Should this JOIN preserve row count?" If yes, after every JOIN run `COUNT(*)` and confirm.
2. **`LEFT JOIN` + a `WHERE` on the right table = silent INNER JOIN.** A predicate like `WHERE b.status = 'active'` filters out the NULL rows from unmatched LEFT rows. Move the predicate into the `ON` clause to preserve the LEFT semantics.
3. **NULL won't equal NULL in JOIN keys.** If both sides have NULL `customer_id`, they will **not** match. Sometimes you actually want them to — use `IS NOT DISTINCT FROM` (PostgreSQL) or wrap with `COALESCE` on both sides.
4. **`USING (col)` vs `ON a.col = b.col`** — `USING` collapses the column to one in the output. Same matching logic, different output shape.

### Exercises

1. **Orphan orders:** find every order whose `customer_id` does not exist in `customers`. (Spoiler: there's one.)
2. **Customers with zero orders:** anti-join the other direction.
3. **Item ↔ product price drift:** for each row in `order_items`, return rows where `unit_price <> products.price`. Why might this be intentional in real life?
4. **Order-total reconciliation:** for each order, compute `SUM(quantity * unit_price)` from `order_items` and compare to `orders.total_amount`. Return any order where they differ (treating NULL totals as a failure).
5. **Inactive products in active orders:** find any non-cancelled order containing an `active = FALSE` product.
6. **Trap exercise:** Write `SELECT COUNT(*) FROM orders LEFT JOIN order_items USING (order_id);`. Compare to `SELECT COUNT(*) FROM orders;`. Why are they different? What does that tell you about row-count preservation?

### External practice

- [SQL Joins Visualizer](https://sql-joins.leopard.in.ua/) — interactive Venn diagrams
- [SQLZoo — JOIN](https://sqlzoo.net/wiki/The_JOIN_operation)
- [LeetCode SQL — Hard joins](https://leetcode.com/studyplan/top-sql-50/) — anti-join problems are gold for QA practice

### Self-check (Day 4)

> Q4.1 — Without running it: how many rows does `customers CROSS JOIN products` return given our 7 customers and 5 products?
> Q4.2 — You wrote `LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE o.status = 'completed'`. A user reports that customers with no orders disappeared. What's wrong?
> Q4.3 — What's the difference in *row count* between an anti-join and an inner join on the same two tables?

---

## Day 5 (Fri 🤖) — AI Workflow: SQL Test Generation

### What you're learning today

How to use AI (Claude / Cursor / Copilot) as a **first-draft generator** for data quality SQL — and just as importantly, how to **review and correct** what it produces. Treating AI output as gospel is the #1 way junior engineers ship bad tests. The skill you're building is the *review loop*.

### Setup (~10 min)

- Open Claude in browser (free tier is fine), or install [Cursor](https://cursor.sh/) (free tier covers this)
- Have your practice schema (above) and exercises from Day 1–4 handy

### Exercise 1 — Schema → Data Quality SQL

Paste the full `CREATE TABLE` + `INSERT` block from the setup section into Claude with this prompt:

> *"You are a senior data quality engineer. Given the schema below, write 12 SQL data quality assertions that I can run as standalone queries. Each assertion should return zero rows when the data passes the check, and one or more rows when it fails. Cover at minimum: NULL checks on critical columns, uniqueness, referential integrity (orphans), value-range sanity, status/enum validity, and reconciliation between order totals and order_items. Format as numbered queries with a one-line comment above each explaining the rule."*

Then **run every query** against your DB Fiddle. For each:

- Did it return zero rows? Then either the data is clean for that rule, or the test is wrong.
- Did it return rows? Are they real failures (good catch!) or false positives (bad test)?

### Exercise 2 — Iterate

Pick one query that's wrong or weak and ask Claude to fix it:

> *"This query was supposed to check referential integrity for order_items.product_id, but it doesn't catch the case where product_id is NULL. Rewrite it correctly and explain what was wrong."*

Notice how the second-round output is usually noticeably better. **This is the loop.**

### Exercise 3 — Compare two AI outputs

Run the same prompt in Claude and in another tool (Cursor chat / Copilot Chat / Gemini — whatever you have).

- What's the same?
- What does one catch that the other misses?
- Which formatting do you actually prefer?

This builds calibration. Different models have different blind spots.

### Quality bar — when is an AI-generated test "good"?

Use this as your review checklist:

- [ ] **Specific:** the test asserts one thing, not seven
- [ ] **Deterministic:** running it twice on the same data returns the same result
- [ ] **Diagnoseable:** the failing rows tell you *what* failed, not just that something did
- [ ] **No false positives on clean data:** seed data that's known-good should pass
- [ ] **Catches the seeded bugs:** the orphan order, the NULL total, the price drift — all should be flagged
- [ ] **Performant on real volumes:** no `SELECT DISTINCT` over a billion rows when you don't need to

### Reflection (write 3–5 sentences in a notes file)

- What did the AI get right that would have taken you 30 minutes to write?
- What did it get *subtly* wrong in a way you'd have shipped?
- What prompt phrasing produced the best output?

Save this — you'll keep refining it across the 16 weeks.

### Bonus — try a `.cursorrules` file

If you went the Cursor route, create a `.cursorrules` file in your project:

```
You are helping write SQL for data quality testing on PostgreSQL.

Conventions:
- All assertions return zero rows on pass.
- Use snake_case identifiers.
- Prefer NOT EXISTS over NOT IN.
- Use IS NULL / IS NOT NULL — never = NULL.
- Add a one-line SQL comment above each query stating the rule.
- Use COALESCE only when defending against NULL would otherwise silently change behavior.
```

Now ask Cursor for a new test and watch the output respect those rules. **This is the foundation of every Friday session for the rest of the plan** — you're slowly building a personalized AI workflow.

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score yourself: 8/10+ = ready for Week 2. 5–7 = re-review the weak day. <5 = redo the exercises.

1. Why does `WHERE country = NULL` always return zero rows?
2. Write the expression that returns the number of NULLs in `customers.email` in a single SELECT.
3. What's the difference between `COUNT(*)`, `COUNT(email)`, and `COUNT(DISTINCT email)`?
4. Given `(10, NULL, 20, NULL, 30)`, what does `AVG()` return? What about `SUM()`?
5. In a window function, what does `PARTITION BY customer_id` do that `GROUP BY customer_id` doesn't?
6. Sketch (in pseudo-SQL) how to find duplicate rows in a table by `email`, returning every duplicate occurrence.
7. Write the anti-join pattern in two equivalent forms (`LEFT JOIN ... IS NULL` and `NOT EXISTS`).
8. Why does adding `WHERE b.status = 'active'` after a `LEFT JOIN b` quietly turn it into an inner join? How do you fix it?
9. Two methods to find the second-highest order total per customer — name them.
10. You ask Claude for "10 data quality SQL checks" and it gives you 10 queries. What's the *first* thing you do before trusting any of them?

---

## Interview Prep — Common Questions for This Week's Material

> 4–5 questions a real interviewer would ask about SQL for data quality. Try to answer aloud (or in writing) before peeking at "what a good answer covers". The goal isn't to memorize — it's to know which trade-offs the interviewer is probing.

### IQ1. "Explain how NULLs work in SQL. Why is `WHERE col = NULL` a bug?"

*What a good answer covers:*
- SQL uses three-valued logic: `TRUE`, `FALSE`, `UNKNOWN`. Comparisons involving NULL evaluate to UNKNOWN, not TRUE
- A `WHERE` clause keeps a row only if the predicate is TRUE — UNKNOWN is treated as "drop this row"
- Therefore `col = NULL` matches no rows, ever; you must use `IS NULL` / `IS NOT NULL`
- `NOT IN (subquery)` is the classic trap: if the subquery returns even one NULL, the whole expression is UNKNOWN and the outer query returns zero rows. Use `NOT EXISTS` instead.

*Likely follow-up:* "What does `SELECT NULL = NULL` return? And `SELECT NULL IS NULL`?" (Answer: NULL/UNKNOWN for the first, TRUE for the second.)

### IQ2. "How would you find duplicate records in a table using SQL?"

*What a good answer covers:*
- For finding *which keys* are duplicated: `GROUP BY key HAVING COUNT(*) > 1`
- For returning *every duplicate row* (not just one per group): a window function — `COUNT(*) OVER (PARTITION BY key) > 1` in a subquery, or `ROW_NUMBER() OVER (PARTITION BY key ORDER BY ...) > 1` to keep the "duplicates after the first"
- Mention that "duplicate" needs a definition — by primary key, by business key (email + tenant_id), by all columns. The query depends on which.
- For data quality testing, you usually want `keep=False` semantics — return *all* offending rows so the failure is fully diagnosable

*Likely follow-up:* "What if the table has 500 million rows? Does your query still work?" (Answer: window functions force a sort and may not scale. For huge tables, prefer `GROUP BY ... HAVING` to identify duplicate keys, then a second join to fetch the rows.)

### IQ3. "Walk me through how you'd test referential integrity between two tables in SQL."

*What a good answer covers:*
- Anti-join pattern: `SELECT a.* FROM child a LEFT JOIN parent b ON a.fk = b.pk WHERE b.pk IS NULL` returns child rows with no matching parent
- Equivalent and often clearer: `WHERE NOT EXISTS (SELECT 1 FROM parent b WHERE b.pk = a.fk)`
- The test passes when the result is empty (zero rows)
- Edge cases worth raising: NULL foreign keys (do you treat them as "no parent" or as "intentionally unmapped"?), case sensitivity, leading/trailing whitespace in keys

*Likely follow-up:* "What's wrong with `WHERE a.fk NOT IN (SELECT b.pk FROM parent)` for the same check?" (Answer: if any `b.pk` is NULL, the whole `NOT IN` evaluates to UNKNOWN and you get zero rows back — false negative.)

### IQ4. "What's the difference between `RANK()`, `DENSE_RANK()`, and `ROW_NUMBER()`?"

*What a good answer covers:*
- All three are window functions assigning a number per row within a partition, ordered by some criterion
- `ROW_NUMBER()` always gives 1, 2, 3, 4… — no ties, no gaps. Useful for deduplication ("keep first row per key")
- `RANK()` allows ties and skips the next rank: 1, 2, 2, 4. Useful when ties should "consume" rank slots
- `DENSE_RANK()` allows ties but doesn't skip: 1, 2, 2, 3. Useful for "find the second-highest value" where ties shouldn't push the answer further down

*Likely follow-up:* "Find the second-highest salary per department — which would you use, and why?" (Answer: depends on intent. `DENSE_RANK` if "second-highest distinct salary"; `ROW_NUMBER` with deterministic ordering if "the second-paid employee"; `RANK` if you want to expose ties as such.)

### IQ5. "Describe a JOIN bug you've seen in real life and how you'd test for it."

*What a good answer covers:*
- The classic: `LEFT JOIN` followed by a `WHERE` predicate on the right table, which silently turns it into an inner join. Fix: move the predicate into the `ON` clause
- The other classic: JOIN explosion / fan-out — joining on a non-unique key on the right side multiplies rows. Test by asserting the row count after the join equals the row count before, when that's the intent.
- A test pattern: `SELECT COUNT(*) FROM a` should equal `SELECT COUNT(*) FROM a LEFT JOIN b ON ...` — if it doesn't, your `b` side has duplicate keys
- Bonus point: mention you'd write the test as a SQL assertion that returns zero rows on pass, runnable in CI alongside the pipeline

*Likely follow-up:* "How do you debug a JOIN that's producing too many rows?" (Answer: count distinct keys on each side; check for `NULL`s in join keys; check for whitespace or case mismatches; isolate one suspicious key and trace it.)

---

## If you have extra time this week (stretch)

- Read [Use The Index, Luke!](https://use-the-index-luke.com/) — chapter 1 only. SQL performance intuition pays off forever.
- Try [Advent of SQL](https://adventofsql.com/) — daily SQL puzzles, retroactively browsable
- Skim [pgexercises.com](https://pgexercises.com/) — a slightly larger schema to flex on

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — `0`. `country = NULL` is never TRUE. Use `IS NULL`.
- **Q1.2** — `'fallback'`. COALESCE returns the first non-NULL.
- **Q1.3** — Dropped. `NULL NOT IN (...)` evaluates to UNKNOWN, which `WHERE` treats as FALSE. Use `(status NOT IN (...) OR status IS NULL)` if you want them kept.
- **Q1.4** — `NULLIF(numerator/denominator, 0)` evaluates the division *first*, which already crashes on zero. Wrap the **denominator**: `numerator / NULLIF(denominator, 0)`. The result will be NULL when the denominator is 0, no crash.

### Day 2 answers

- **Q2.1** — Because `AVG` ignores NULLs entirely. If half the rows have NULL `total_amount`, the "average" is over only the populated half — possibly misleading. Business may have meant "treat NULL as 0".
- **Q2.2** — `NULL`. `SUM` of zero rows returns NULL, not 0. Wrap in `COALESCE(SUM(...), 0)` if you need a number.
- **Q2.3** — `HAVING`. `WHERE` runs before aggregation, so it can't reference `COUNT(*)`. Pattern: `GROUP BY product_id HAVING COUNT(*) > 5`.

### Day 3 answers

- **Q3.1** — `RANK` skips ranks after ties (1, 2, 2, 4). `DENSE_RANK` doesn't (1, 2, 2, 3).
- **Q3.2** — Window functions evaluate *after* `WHERE`. Wrap the window query in a subquery/CTE and filter on its alias: `SELECT * FROM (...) WHERE rn = 1`.
- **Q3.3** — A running total of `amount` per customer, in date order. (Cumulative sum.)

### Day 4 answers

- **Q4.1** — 7 × 5 = 35 rows. Cartesian product.
- **Q4.2** — The `WHERE` predicate touches the right side, filtering out NULL-from-unmatched rows. Either move the condition into the `ON` clause, or wrap in `OR o.customer_id IS NULL`.
- **Q4.3** — Inner join keeps only matched rows; anti-join returns only *unmatched* rows. They're complementary — together they sum to the full left table.

### End-of-week answers

1. Three-valued logic — `= NULL` evaluates to UNKNOWN, never TRUE.
2. `COUNT(*) - COUNT(email)`.
3. `COUNT(*)` = all rows. `COUNT(email)` = non-NULL emails. `COUNT(DISTINCT email)` = unique non-NULL emails.
4. `AVG = 20` (ignores NULLs, so (10+20+30)/3). `SUM = 60`.
5. `PARTITION BY` keeps every row in the output and computes the function within each partition. `GROUP BY` collapses each group to one row.
6. Use `COUNT(*) OVER (PARTITION BY email) > 1` in a subquery, then filter where that count > 1 — returns every duplicate occurrence, not just one per group.
7. `LEFT JOIN b ON a.k = b.k WHERE b.k IS NULL` ↔ `WHERE NOT EXISTS (SELECT 1 FROM b WHERE b.k = a.k)`.
8. Because the predicate filters NULLs introduced by unmatched rows. Move it into the `ON` clause, or add `OR b.col IS NULL` to the WHERE.
9. (a) `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total DESC)` then `WHERE rn = 2`. (b) `DENSE_RANK()` then `WHERE rnk = 2` — handles ties differently.
10. Run them against known-bad data and check they fail; run against known-good and check they pass. Trust comes from execution, not from the AI's confident tone.

---

*Done with Week 1? You should feel comfortable opening any unfamiliar table and writing 5+ data-quality assertions in 10 minutes. If yes — onward to Week 2 (Python for Testing). If not — redo the exercise sets you skipped; the rest of the plan compounds on this foundation.*
