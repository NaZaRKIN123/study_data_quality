# Week 9 — Non-Relational Data: JSON, XML, Raw & Unstructured | Training Materials

> **Companion to:** Week 9 of the *Data Automation Testing* study plan
> **Time budget:** ~6–10 hours across 5 days (1–2 hours/day)
> **Goal:** Move beyond neat tabular data. You'll learn to validate JSON with formal schemas, parse and test XML, handle raw/unstructured text, and revisit the Bronze/Silver/Gold pattern through a semi-structured lens. By Friday you'll have an AI-assisted workflow for inferring schemas from messy real-world payloads — the kind of problem you face when integrating with a third-party API that has no documentation.

---

## How to use this file

- This week is a mindset shift: not every dataset arrives as a spreadsheet
- Each day has the same four blocks: **Theory → Gotchas → Exercises → Self-check**
- Friday's AI workflow is genuinely useful in real jobs — schema-inference is a slog by hand
- Answers to all self-checks are at the bottom

---

## One-time setup (~5 minutes)

```bash
source .venv/bin/activate
pip install jsonschema lxml xmlschema
```

Sanity check:
```bash
python -c "import jsonschema, lxml, xmlschema; print('jsonschema', jsonschema.__version__, '| lxml', lxml.__version__, '| xmlschema', xmlschema.__version__)"
```

You should see versions like `jsonschema 4.26+`, `lxml 5.x`, `xmlschema 3.x` or higher. APIs are stable across minor versions.

> **Note:** `lxml` ships C-extension code — pip will compile if no wheel exists for your platform. On macOS/Linux/Windows with modern Python, wheels are pre-built so install is instant.

---

## Day 1 (Mon) — JSON & Validation Theory

### Theory

JSON (JavaScript Object Notation) is the lingua franca of API responses, configuration files, log streams, and event data. Unlike CSV, it carries **nested structure** — objects within objects, arrays of objects, mixed types — which is exactly why it doesn't map cleanly to a DataFrame.

### The five JSON types

```
object   { "key": "value" }     → Python dict
array    [1, 2, 3]              → Python list
string   "hello"                → Python str
number   42 or 3.14             → Python int or float
boolean  true / false           → Python True / False
null     null                   → Python None
```

That's it. Five types, infinitely composable.

### What "validation" means for JSON

Three escalating questions you can ask of a JSON document:

1. **Is it well-formed JSON?** — does `json.loads(text)` succeed?
2. **Does it match the expected structure?** — required fields present, types correct, no unexpected keys?
3. **Are values within business rules?** — `total_amount > 0`, `email matches regex`, `country in known_codes`?

Question 1 is `json.loads`. Question 2 is **JSON Schema**. Question 3 is custom logic — Python, pandera (after flattening), or richer schema tools.

### JSON Schema in 90 seconds

JSON Schema is a JSON-formatted way to describe what valid JSON looks like. It's a spec (multiple drafts: 4, 6, 7, 2019-09, **2020-12**) and the Python `jsonschema` library implements all of them.

A schema for an order:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "order_id": {"type": "integer"},
    "customer_email": {"type": "string", "format": "email"},
    "total_amount": {"type": "number", "minimum": 0},
    "status": {"enum": ["pending", "completed", "cancelled"]},
    "items": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "product_id": {"type": "integer"},
          "quantity": {"type": "integer", "minimum": 1}
        },
        "required": ["product_id", "quantity"]
      }
    }
  },
  "required": ["order_id", "customer_email", "items"],
  "additionalProperties": false
}
```

Key keywords:

| Keyword | Meaning |
|---|---|
| `type` | One of: `object`, `array`, `string`, `number`, `integer`, `boolean`, `null` |
| `properties` | Per-key sub-schemas for an object |
| `required` | Array of property names that *must* be present |
| `additionalProperties: false` | Reject any keys not listed in `properties` — strict mode |
| `enum` | Value must be one of the listed alternatives |
| `format` | Semantic constraint like `email`, `uri`, `date`, `uuid` (not enforced unless you opt in) |
| `minimum` / `maximum` | Numeric bounds |
| `minItems` / `maxItems` | Array length bounds |
| `pattern` | Regex for strings |

### NDJSON: streaming JSON

When you have millions of records, a single JSON document is wasteful (whole-file parse). Newline-Delimited JSON (NDJSON) puts one JSON object per line:

```
{"order_id": 1, "total": 99.5}
{"order_id": 2, "total": 14.0}
{"order_id": 3, "total": 250.0}
```

Validate each line independently. This is the format of most event streams, log files, and `pd.read_json(..., lines=True)`.

### Gotchas

1. **`format` is opt-in.** Out of the box, `format: "email"` validates *nothing*. You have to pass a `FormatChecker` to actually enforce email-ness. Easy to miss.
2. **`type: "number"` includes integers and floats.** `type: "integer"` is stricter. If you expect an int, say so.
3. **`additionalProperties: false` breaks compatibility.** Strict mode rejects new fields — useful for catching typos, painful when the upstream API adds a field. Decide per-domain whether to be strict.
4. **JSON has no native datetime type.** Dates are strings. Use `format: "date"` or `format: "date-time"` plus `FormatChecker` to validate.
5. **Schema *drafts* matter.** A schema written for draft-7 may misbehave under draft-2020-12 (e.g. `items` semantics changed). Always set `$schema` in production.

### Exercises

No coding today — analysis day.

1. Find a real JSON sample. If your project doesn't have one, grab a public API response (e.g., [JSONPlaceholder](https://jsonplaceholder.typicode.com/users)) and save 5 records.
2. **By hand**, draft a JSON Schema for that data. Document at minimum:
   - Required vs optional fields
   - Type per field
   - Any enums (status, category)
   - Any numeric bounds
   - Whether to allow extra fields
3. Identify one field where `type` alone is insufficient — for example, an "email" field. What would make it valid beyond just being a string?
4. Sketch a one-page comparison: tabular data validation (pandera, Great Expectations) vs nested JSON validation (jsonschema). When would you reach for each?

### External practice

- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/) — the canonical tutorial; ~30 minute read
- [JSONPlaceholder](https://jsonplaceholder.typicode.com/) — free public API for sample JSON
- [jq](https://stedolan.github.io/jq/) — CLI tool for JSON wrangling. Worth learning the basics.

### Self-check (Day 1)

> Q1.1 — What's the difference between "well-formed" JSON and "valid against a schema" JSON?
> Q1.2 — Why is `format: "email"` not enforced by default in `jsonschema`?
> Q1.3 — A schema has `additionalProperties: false`. The upstream API adds a new field. Your validation breaks. What's the trade-off you made?
> Q1.4 — Why is NDJSON used for event streams instead of one big JSON array?

---

## Day 2 (Tue) — `jsonschema` in Practice

### Theory

Today you write actual Python code. Same library, same patterns regardless of how nested your data gets.

### The basic flow

```python
from jsonschema import validate, Draft202012Validator, ValidationError

schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "order_id": {"type": "integer"},
        "total_amount": {"type": "number", "minimum": 0},
    },
    "required": ["order_id", "total_amount"],
}

instance = {"order_id": 1, "total_amount": 99.5}

# Approach 1 — top-level validate (simple, raises on first error)
validate(instance=instance, schema=schema)   # no exception = valid

# Approach 2 — explicit Validator (recommended for tests; multiple errors)
validator = Draft202012Validator(schema)
errors = list(validator.iter_errors(instance))
assert errors == []
```

`iter_errors` is what you use in tests — it gives you *all* errors, not just the first. That matters when you want a helpful failure message listing every wrong field at once.

### Validating NDJSON

```python
import json
from jsonschema import Draft202012Validator

def validate_ndjson_file(path: str, schema: dict) -> list[tuple[int, str]]:
    """Return a list of (line_number, error_message) for every invalid record."""
    validator = Draft202012Validator(schema)
    failures = []
    with open(path, "r") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                failures.append((line_no, f"Malformed JSON: {e.msg}"))
                continue
            for err in validator.iter_errors(obj):
                failures.append((line_no, err.message))
    return failures
```

In a pytest test:
```python
def test_orders_ndjson_is_valid(tmp_path):
    path = tmp_path / "orders.ndjson"
    path.write_text('{"order_id": 1, "total_amount": 50}\n')
    failures = validate_ndjson_file(path, ORDERS_SCHEMA)
    assert failures == [], f"Found {len(failures)} validation failures: {failures[:5]}"
```

### Enforcing `format` (emails, dates, UUIDs)

By default, `format: "email"` is just an annotation — not enforced. To enforce:

```python
from jsonschema import Draft202012Validator, FormatChecker

validator = Draft202012Validator(schema, format_checker=FormatChecker())
```

This activates format validation for `email`, `uri`, `ipv4`, `date`, `date-time`, `uuid`, etc. Some formats need extra packages — install with `pip install 'jsonschema[format]'` for the full set.

### Reusing schemas with `$ref`

A bigger schema breaks into reusable pieces:

```python
schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": {
        "money": {"type": "number", "minimum": 0},
        "non_empty_string": {"type": "string", "minLength": 1},
    },
    "type": "object",
    "properties": {
        "subtotal": {"$ref": "#/$defs/money"},
        "tax":      {"$ref": "#/$defs/money"},
        "currency": {"$ref": "#/$defs/non_empty_string"},
    },
    "required": ["subtotal", "tax", "currency"],
}
```

For a 50-field schema, `$defs` is the difference between maintainable and unreadable.

### Handling nested objects and arrays

A real-world e-commerce order with line items:

```python
ORDER_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$defs": {
        "line_item": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "quantity":   {"type": "integer", "minimum": 1},
                "unit_price": {"type": "number", "minimum": 0},
            },
            "required": ["product_id", "quantity", "unit_price"],
            "additionalProperties": False,
        }
    },
    "type": "object",
    "properties": {
        "order_id":       {"type": "integer"},
        "customer_email": {"type": "string", "format": "email"},
        "order_date":     {"type": "string", "format": "date"},
        "status":         {"enum": ["pending", "completed", "cancelled"]},
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/line_item"},
        },
        "total_amount":   {"type": "number", "minimum": 0},
    },
    "required": ["order_id", "customer_email", "items", "total_amount"],
    "additionalProperties": False,
}
```

### Cross-field rules: when JSON Schema isn't enough

JSON Schema can express "field X must be a number ≥ 0," but not "field X must equal the sum of array Y's quantities × prices." That's a *cross-field rule* — the Week 1 reconciliation problem in JSON form.

Two approaches:
1. **Two-pass validation** — JSON Schema for shape; a custom Python function for cross-field business rules.
2. **`if/then/else` keywords** in JSON Schema — limited but useful for "if status='cancelled', then cancellation_reason is required."

For the reconciliation rule (`total_amount == sum(quantity * unit_price)`), Python wins:

```python
def validate_order_reconciliation(order: dict) -> list[str]:
    """Return error messages, empty list if valid."""
    expected = sum(item["quantity"] * item["unit_price"] for item in order["items"])
    if abs(order["total_amount"] - expected) > 0.01:   # float tolerance
        return [f"total_amount={order['total_amount']} != computed sum {expected}"]
    return []
```

### Gotchas

1. **`integer` is not `number`.** `42.0` validates as `number` but not `integer`. JSON has no separate int type — `jsonschema` checks the Python type. Be explicit.
2. **`null` is not "missing".** A field set to `null` is *present* with type `null`. To allow either a value or null: `"type": ["string", "null"]` (or use `nullable: true` if your schema dialect supports it).
3. **Default values aren't applied.** `jsonschema` validates; it doesn't fill in defaults. If you want defaults, post-process the validated object yourself or use a library like `pydantic`.
4. **`additionalProperties: false` cascades.** It only applies to the level where it's declared, not nested objects. You have to declare it at every level you want strict.
5. **Validation can be slow on huge schemas.** Compile the validator once, reuse it. `Draft202012Validator(schema)` does compilation; calling `iter_errors` many times is cheap.

### Exercises

Create `tests/test_json_validation.py`.

1. Adapt `ORDER_SCHEMA` above. Write 5 example orders — 3 valid, 2 invalid (one missing required field, one with wrong type). Validate each with `iter_errors`. Assert the right ones pass and the right ones fail.
2. Build an NDJSON file with 100 orders (use Faker from Week 8 to generate). Mix in 3 deliberate bugs: one with no `order_id`, one with `total_amount: -5`, one with malformed JSON. Run `validate_ndjson_file` and confirm exactly 3 failures.
3. Write the cross-field validator `validate_order_reconciliation`. Combine it with JSON Schema validation: a fully-valid order passes both checks; an order with a wrong `total_amount` passes schema validation but fails reconciliation.
4. Add `format_checker=FormatChecker()` to enforce email format. Pass an order with `customer_email: "not_an_email"` — does it now fail? Without `FormatChecker`, did it fail?
5. **`$ref` exercise:** refactor `ORDER_SCHEMA` so `email` and `non_negative_number` are reusable `$defs`. Use them for `customer_email` and any monetary field. Confirm validation still works.
6. **Stretch:** write a function `pretty_print_errors(errors)` that turns a list of `ValidationError` into a human-readable report (path + message). Useful for failing tests to actually be informative.

### External practice

- [`jsonschema` Quickstart](https://python-jsonschema.readthedocs.io/en/stable/) — short, clear
- [Understanding JSON Schema — Reference](https://json-schema.org/understanding-json-schema/reference/) — keyword-by-keyword
- [check-jsonschema](https://github.com/python-jsonschema/check-jsonschema) — CLI for validating JSON files; useful in CI as a pre-commit hook

### Self-check (Day 2)

> Q2.1 — `validate()` raises on the first error. What do you use instead to get *all* errors at once, and why does that matter for tests?
> Q2.2 — A field can be a string or null. How do you express that in JSON Schema?
> Q2.3 — Why doesn't `format: "email"` enforce email-ness by default? How do you turn enforcement on?
> Q2.4 — Why can't JSON Schema express "field X equals the sum of array Y's prices"? What's the fix?

---

## Day 3 (Wed) — XML with `lxml`

### Theory

XML predates JSON by years. You won't see it in greenfield projects, but you *will* see it in:
- Legacy enterprise systems (ERP, banking, healthcare)
- Government data feeds (tax forms, regulatory filings)
- B2B integrations (EDI replacements, invoicing formats like UBL)
- SOAP APIs (older, but still alive in finance/insurance)
- RSS/Atom feeds, SVG, KML/GPX — wherever structured documents are needed

For data testing, you need to know how to: parse XML, extract values via XPath, and validate against a formal schema (XSD).

### `lxml` vs `xml.etree.ElementTree`

Both are in the toolkit. `xml.etree.ElementTree` ships with Python (no install). `lxml` is a third-party C-extension wrapper around libxml2 — faster, supports XPath 1.0 fully, supports XSLT and XSD validation.

**Use `lxml`.** It's faster, more capable, and the standard in industry.

### Parsing and traversing XML

```python
from lxml import etree

xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<order id="1001">
  <customer>
    <email>buyer@example.com</email>
  </customer>
  <items>
    <item product_id="P100" quantity="2" unit_price="25.00"/>
    <item product_id="P200" quantity="1" unit_price="49.99"/>
  </items>
  <total>99.99</total>
</order>"""

root = etree.fromstring(xml_text.encode())
print(root.tag)                            # 'order'
print(root.attrib["id"])                   # '1001'
print(root.find("customer/email").text)    # 'buyer@example.com'
print(root.find("total").text)             # '99.99'

# All items
for item in root.iter("item"):
    print(item.attrib["product_id"], item.attrib["quantity"], item.attrib["unit_price"])
```

### XPath: querying XML

XPath is a query language for XML — like SQL for documents. `lxml` supports it via `tree.xpath(...)`.

```python
# All product IDs
ids = root.xpath("//item/@product_id")
# ['P100', 'P200']

# Total quantity (XPath aggregates)
total_qty = root.xpath("sum(//item/@quantity)")
# 3.0  (XPath returns float for sums)

# Items with quantity > 1
multi = root.xpath("//item[@quantity > 1]")
# [<Element item>] — list of matching nodes

# The text of <total>
total_text = root.xpath("string(//total)")
# '99.99'
```

XPath is a *huge* topic. The 80/20:
- `//tag` — all elements named `tag` anywhere in the document
- `/order/customer` — direct child path from root
- `@attr` — attribute selector
- `[predicate]` — filter, e.g. `[@id="1001"]`
- `text()` — text content of an element
- `count(...)`, `sum(...)`, `string(...)` — aggregates

### XSD validation

XSD (XML Schema Definition) is the formal-schema sibling of JSON Schema, but for XML.

```python
from lxml import etree

xsd_text = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="customer">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="email" type="xs:string"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="items">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="item" minOccurs="1" maxOccurs="unbounded">
                <xs:complexType>
                  <xs:attribute name="product_id" type="xs:string" use="required"/>
                  <xs:attribute name="quantity" type="xs:positiveInteger" use="required"/>
                  <xs:attribute name="unit_price" type="xs:decimal" use="required"/>
                </xs:complexType>
              </xs:element>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
        <xs:element name="total" type="xs:decimal"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:string" use="required"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""

schema = etree.XMLSchema(etree.fromstring(xsd_text.encode()))
schema.assertValid(root)   # raises DocumentInvalid if invalid
# Or non-raising:
print(schema.validate(root))   # True
```

### XPath in tests

Validating shape with XSD is one half. The other half is **business-rule checks via XPath**:

```python
def test_order_xml_business_rules(order_xml: bytes):
    root = etree.fromstring(order_xml)

    # 1. Customer email is present and non-empty
    emails = root.xpath("//customer/email/text()")
    assert emails and emails[0].strip(), "Missing or empty customer email"

    # 2. At least one item
    items = root.xpath("//item")
    assert len(items) >= 1, "Order must have at least one item"

    # 3. All quantities are positive integers
    quantities = [int(q) for q in root.xpath("//item/@quantity")]
    assert all(q > 0 for q in quantities), f"Found non-positive quantity: {quantities}"

    # 4. Total reconciles with sum of (quantity * unit_price)
    expected = sum(
        int(item.get("quantity")) * float(item.get("unit_price"))
        for item in items
    )
    actual = float(root.xpath("string(//total)"))
    assert abs(actual - expected) < 0.01, f"Reconciliation: actual={actual}, expected={expected}"
```

### Gotchas

1. **Namespaces.** Real XML uses XML namespaces (`xmlns="..."`), and namespaced elements need namespace-aware XPath: `root.find("ns:customer/ns:email", namespaces={"ns": "http://example.com/schema"})`. Forgetting namespaces is the #1 XML bug — XPath returns nothing and you wonder why.
2. **`lxml.etree.fromstring()` needs bytes, not str, when there's an XML declaration.** Encode first or use `lxml.etree.parse(StringIO(text))`.
3. **External entities = security risk.** XML supports `<!ENTITY>` declarations that can read files or fetch URLs (XXE attacks). Use `etree.XMLParser(resolve_entities=False)` for untrusted input.
4. **Elements vs attributes.** XML lets you express the same data as either an element (`<item><quantity>2</quantity></item>`) or attribute (`<item quantity="2"/>`). XPath is different for each. Read the actual document before assuming.
5. **Encoding declarations matter.** `<?xml version="1.0" encoding="UTF-8"?>` tells the parser the byte encoding. Mismatched encoding causes garbled characters or parse errors.

### Exercises

Create `tests/test_xml_validation.py`.

1. Save the example XML from above to `tests/fixtures/order_1001.xml`. Parse with `lxml`, extract: customer email, all product IDs, total quantity (use XPath `sum`).
2. Write the XSD schema (or use the one above). Validate the XML against it. Confirm it passes.
3. Modify the XML so `quantity` is `0` (invalid per `xs:positiveInteger`). Confirm XSD validation now fails. Print the error.
4. Write `validate_order_xml(xml: bytes) -> list[str]` that runs both XSD validation and business-rule XPath checks (item count, reconciliation). Return list of error messages (empty if valid).
5. **Namespace exercise:** wrap the XML root with `xmlns="http://ecom.example.com/order"`. Watch your `find` / `xpath` calls return nothing. Fix by passing `namespaces={"o": "http://ecom.example.com/order"}` and prefixing paths.
6. **Stretch:** write a small CLI script `validate_xml.py path_to_xml` that returns exit code 0 on valid, 1 on invalid, with helpful messages. Wire it into pre-commit.

### External practice

- [lxml tutorial](https://lxml.de/tutorial.html) — official, covers parsing and XPath
- [XPath Cheatsheet (Devhints)](https://devhints.io/xpath) — quick reference
- [xmlschema docs](https://xmlschema.readthedocs.io/) — Python wrapper that's higher-level than `lxml.etree.XMLSchema`; some teams prefer it
- [OWASP — XXE prevention](https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html) — security checklist

### Self-check (Day 3)

> Q3.1 — Why use `lxml` over `xml.etree.ElementTree`?
> Q3.2 — Your XPath query returns nothing, but you can clearly see the element in the document. What's the most likely bug?
> Q3.3 — Difference between an element and an attribute in XML, and how does that change your XPath?
> Q3.4 — A coworker parses untrusted XML with default settings. What's the security risk, and how do you fix it?

---

## Day 4 (Thu) — Raw, Unstructured & Bronze/Silver/Gold Revisited

### Theory

You've now seen JSON (semi-structured) and XML (semi-structured, older). The third bucket is **unstructured** — free text, logs, documents, audio transcriptions. Test strategies differ.

### The structure spectrum

```
Structured       Semi-structured           Unstructured
   |                  |                         |
CSV, Parquet     JSON, XML, Avro          Free text, PDFs,
SQL tables       (schema is implicit       images, audio
                  or carried by data)
```

The further right, the harder validation gets. For **unstructured text**, you can't write a JSON Schema. What you *can* do:

- **Presence checks** — file exists, non-empty, byte size in expected range
- **Encoding checks** — valid UTF-8, no null bytes, BOM consistency
- **Pattern checks** — regex for expected fragments (e.g., `r"order #\d+"` somewhere in the body)
- **Statistical checks** — character entropy, word count distribution, language detection
- **Domain-specific parsers** — extract fields with NLP, then validate the extraction

### Bronze/Silver/Gold for semi-structured data

You met this pattern in Week 3 for tabular ETL. It applies cleanly to JSON/XML pipelines:

| Layer | What it holds | What you test |
|---|---|---|
| **Bronze** | Raw payloads — JSON or XML stored exactly as received, one file/row per event | (1) ingest succeeded; (2) source-system contract is intact (per-record JSON Schema or XSD); (3) volume in expected range |
| **Silver** | Parsed, flattened, deduplicated — one row per logical entity | (4) flattening logic preserved fields; (5) referential integrity within entity types; (6) no rows lost in flattening |
| **Gold** | Aggregated, business metrics, joined across entities | (7) aggregations match raw counts (sum/total reconciliation); (8) business rules hold; (9) downstream consumer contract is honored |

The Week 3 reconciliation rule still applies — *the total volume / sum / count at Bronze must reconcile against Silver and Gold within tolerance.*

### Flattening JSON to a DataFrame

`pandas` provides `json_normalize` for this:

```python
import pandas as pd

raw = [
    {"order_id": 1, "customer": {"email": "a@x.com", "country": "US"},
     "items": [{"product_id": "P1", "quantity": 2}]},
    {"order_id": 2, "customer": {"email": "b@x.com", "country": "PL"},
     "items": [{"product_id": "P2", "quantity": 1}]},
]

# Top-level: customer.email becomes a column, items stays nested
df = pd.json_normalize(raw)
print(df.columns)
# Index(['order_id', 'customer.email', 'customer.country', 'items'], dtype='object')

# To explode items into separate rows:
df_items = pd.json_normalize(raw, record_path="items", meta=["order_id"])
print(df_items)
#    product_id  quantity  order_id
# 0         P1         2         1
# 1         P2         1         2
```

The Week 4 pandera schema you wrote works on this *flat* DataFrame. The flattening step itself needs its own tests.

### Testing the flattening step

```python
def test_flatten_orders_preserves_record_count():
    raw = [order_1, order_2, order_3]
    df = pd.json_normalize(raw)
    assert len(df) == len(raw), "Flattening should not drop or duplicate top-level records"


def test_flatten_orders_with_items_explodes_correctly():
    raw = [
        {"order_id": 1, "items": [{"p": "A"}, {"p": "B"}]},
        {"order_id": 2, "items": [{"p": "C"}]},
    ]
    df = pd.json_normalize(raw, record_path="items", meta=["order_id"])
    assert len(df) == 3, "2 items + 1 item = 3 rows"
    assert set(df["order_id"]) == {1, 2}
    assert (df.groupby("order_id").size() == [2, 1]).all()
```

### Schema-on-read vs schema-on-write

A philosophical split that matters:

- **Schema-on-write** (traditional databases, dbt) — define the schema first, reject incoming data that doesn't match. Strong guarantees, but rigid.
- **Schema-on-read** (data lakes, Bronze layer of lakehouse) — store everything as-is, parse and apply schema when reading. Flexible, but you can store garbage and only find out later.

The Bronze layer is schema-on-read. The Silver layer is where you enforce schema-on-write (or its equivalent — validating before inserting into the curated zone). **Test at both points** — Bronze validation catches contract drift, Silver validation guarantees downstream consumers see clean data.

### Gotchas

1. **`json_normalize` silently drops fields.** If a record is missing a key that another record has, you get NaN. Fine for clean data, dangerous if you assumed all records had all keys.
2. **Mixed-type fields.** A field might be `null`, a string, a list, or a dict across records. pandas will infer `object` dtype and your schema validation downstream may fail unpredictably. Normalize types in the flattening step.
3. **Deeply nested arrays of arrays** can't be normalized in one call. You either do recursive normalization or restructure the JSON upstream.
4. **Bronze ingestion size matters.** Storing every raw payload forever is expensive. Common pattern: keep raw for N days (replay window), then drop. Tests should verify retention policy.
5. **"Unstructured" doesn't mean "untestable."** Word counts, encoding, language, line counts — all measurable. The bar is lower, but it's not zero.

### Exercises

Use the cumulative e-commerce project. Today you add JSON ingest as a new path.

1. Create `data/orders.ndjson` — 50 orders in NDJSON form. Use Faker (Week 8) to generate them with varying nested item counts. Include 3 deliberate bugs: one missing required field, one with negative `total_amount`, one malformed line.
2. Write `bronze_validate(path) -> list[failure]` that runs JSON Schema validation on each line. Confirm 3 failures.
3. Write `bronze_to_silver(path) -> pd.DataFrame` that parses, flattens (one row per item), drops or quarantines bad records, and returns a clean DataFrame. Test that:
   - Row count = sum of items in valid records
   - Bad records are quarantined to a separate file/log
   - Silver DataFrame passes the Week 4 pandera schema
4. Add reconciliation: assert `bronze_total_records - quarantined - silver_orders_distinct == 0`. (The Week 3 rule.)
5. **Statistical check on free-text field:** add a `notes` field to your orders (Faker `text()`). Write a check that flags records where `notes` is suspiciously short (< 10 chars) or suspiciously long (> 500 chars).
6. **Stretch:** simulate schema drift. Add a new field `discount_code` to a few records (not in your schema). Confirm strict mode (`additionalProperties: false`) catches it. Decide what your team's policy should be — strict reject, or accept-and-warn?

### External practice

- [pandas `json_normalize` docs](https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html) — short
- [Martin Kleppmann — Designing Data-Intensive Applications, Chapter 4](https://dataintensive.net/) — schema evolution; the canonical reference
- [Databricks — Lakehouse architecture](https://www.databricks.com/glossary/medallion-architecture) — Bronze/Silver/Gold framing in their own words

### Self-check (Day 4)

> Q4.1 — When does `json_normalize` lose data, and how do you defend against it in tests?
> Q4.2 — Schema-on-read vs schema-on-write — when do you use each, and where is each in a typical Bronze/Silver/Gold pipeline?
> Q4.3 — A truly unstructured field (free-text notes) — give three properties you can still test about it.
> Q4.4 — Why test reconciliation between Bronze and Silver, not just within Silver?

---

## Day 5 (Fri 🤖) — AI Workflow: Schema Inference

### What you're learning today

Last week you used Claude to *generate* synthetic data. This week you flip it — give Claude a sample of *real* data and ask for a schema. This is genuinely useful when:

- You're integrating with a third-party API and the docs are missing or wrong
- You inherited a JSON dataset from another team with no schema
- You're writing tests for a pipeline where the contract was never written down

The AI does the tedious shape-inference; you review and tighten.

### Setup

Reuse the `anthropic` setup from Week 8.

### Exercise 1 — Single-record schema inference

Take a single JSON record (the most complex one you have — a real or synthetic order with nested items, customer, addresses). Paste into Claude:

> *"Generate a JSON Schema (draft 2020-12) for this record. Use `$defs` for any sub-objects that look reusable. Include `required`, set sensible `type` constraints, and use `enum` where the value is clearly one-of-a-set. Don't add `additionalProperties: false` unless I ask. Return only the schema, no explanation:*
>
> *[paste your record here]"*

Validate the AI's output:
- Does running `Draft202012Validator(generated_schema).check_schema(generated_schema)` confirm it's a valid schema?
- Does the original record validate against it?
- Are there obvious overgeneralizations? (e.g., the AI might say `"customer_id": {"type": "string"}` when it should be `integer`)
- Are there obvious undergeneralizations? (e.g., the AI might say `"status": {"enum": ["completed"]}` because it only saw one value)

Tighten the schema by hand. Document what you changed.

### Exercise 2 — Multi-record inference

A single record can mislead the AI. Give it 5–10 records and ask:

> *"Here are 8 records of the same type from a production system. Infer a JSON Schema (draft 2020-12) that matches all of them. Pay attention to:*
>
> *- Fields that are present in some records but not others — are they truly optional, or is it an oversight?*
> *- Numeric ranges — what bounds make sense?*
> *- Enum candidates — fields where the set of values appears closed.*
> *- Nullability — fields that are sometimes null.*
>
> *Return only the schema. Note any uncertain decisions in JSON comments — actually, JSON doesn't support comments. Use a `description` field on each property instead.*
>
> *Records: [paste 5–10 records]"*

This is closer to real practice. Variation across records is what reveals the true schema.

### Exercise 3 — XML schema inference

Same flow for XML. Give Claude a sample XML document and ask for an XSD. Then validate. XSD is more verbose than JSON Schema and AI-generated XSDs more often have errors (especially around namespaces and `complexType` ordering) — review carefully.

### Exercise 4 — From inferred schema to test suite

Take the schema from Exercise 2. Have Claude generate a pytest test file that:

> *"Given this JSON Schema [paste], write a pytest test file that:*
> *1. Validates a sample valid record passes.*
> *2. Validates each required field's absence causes failure.*
> *3. Validates each enum field's wrong value causes failure.*
> *4. Validates each numeric field's out-of-bounds value causes failure.*
>
> *Use `Draft202012Validator(schema).iter_errors(instance)`. Return only the Python code."*

The output is your test scaffold. Review for missing edge cases — AI typically misses: (a) deeply nested fields, (b) cross-field rules, (c) malformed-JSON cases.

### Update your `.cursorrules`

```
JSON / XML schema inference conventions:
- Always pass MULTIPLE records to the AI for schema inference, never a single record.
- Treat AI-inferred schemas as drafts. Always tighten by hand.
- Common AI overgeneralizations: too-broad type unions, missing enum constraints.
- Common AI undergeneralizations: enums based on only seen values, required-fields based on presence in the sample.
- For XSD: review namespace declarations and element ordering carefully.
- After inferring a schema, write at least 3 failing-case tests to confirm constraints actually fire.
```

### Quality bar — when is an AI-inferred schema "good"?

- [ ] Validates the original sample records (sanity check)
- [ ] Has been *tightened* in at least one place after AI generation (the AI almost always overgeneralizes)
- [ ] Has at least one *negative* test — a record that should fail validation, with a clear error
- [ ] Uses `$defs` for sub-objects appearing more than once (avoids duplication)
- [ ] Includes `$schema` declaring the draft version
- [ ] Documented somewhere — what was the source data? When was the schema inferred? When does it need re-review?

### Reflection (write 3–5 sentences in `notes.md`)

- Did the AI's inferred schema pass your sanity tests on the first try?
- Where did it overgeneralize? Where did it undergeneralize?
- For your project's data, would you generate the schema by hand, by AI-and-tighten, or by writing a sample-and-validate-loop tool? When does each win?

---

## End-of-Week Self-Assessment (10 questions, ~15 min)

Don't peek at answers. Score: 8/10+ = ready for Week 10. 5–7 = re-review. <5 = redo exercises.

1. The five JSON types — name them.
2. What's the difference between `type: "number"` and `type: "integer"` in JSON Schema?
3. A schema field allows either a string or null — write the JSON Schema fragment.
4. Why use `validator.iter_errors(instance)` instead of `validate(instance, schema)`?
5. How do you enforce `format: "email"` actually enforces email-ness?
6. Three reasons XPath returns nothing when you can see the element in the XML.
7. What's an XXE attack, and how do you prevent it in `lxml`?
8. Schema-on-read vs schema-on-write — at which Bronze/Silver/Gold layer do you typically apply each?
9. After an AI infers a schema from sample data, the first thing you do is...?
10. The reconciliation rule: at Bronze you have N raw records. At Silver you have M cleaned rows. What relationship between N and M should your tests assert?

---

## Interview Prep — Common Questions for This Week's Material

> 5 questions a real interviewer would ask about non-relational data testing.

### IQ1. "Walk me through testing a pipeline that ingests JSON from a third-party API."

*What a good answer covers:*
- **Bronze layer**: validate each incoming payload against a JSON Schema (the API's contract — or your inferred one if undocumented). Reject or quarantine invalid records. Track rejection rate over time as a metric.
- **Silver layer**: after parsing/flattening, validate the resulting DataFrame with pandera or Great Expectations — same rules as for any tabular data.
- **Cross-layer reconciliation**: count of valid Bronze records = count of Silver rows + quarantine. If they don't add up, you lost data somewhere.
- **Schema drift detection**: if rejection rate spikes, the upstream changed. Alert on this. The schema change might be a new field (low risk) or a renamed required field (high risk).
- **Source freshness**: payloads stop arriving — separate type of failure from invalid payloads. Test both.

*Likely follow-up:* "What if the third-party API has no documented schema?" (Answer: derive one from samples — Friday's AI-inference workflow, or write it by hand from production samples. Either way, version it; treat it as a contract you've adopted.)

### IQ2. "What's the difference between schema-on-read and schema-on-write, and when do you use each?"

*What a good answer covers:*
- **Schema-on-write**: schema enforced at insertion (traditional RDBMS, dbt, the Silver/Gold layers). Strong guarantees downstream; rigid against upstream change.
- **Schema-on-read**: data stored as-is; schema applied during query (data lakes, Bronze layer). Flexible against upstream change; risk of storing garbage.
- **Use both** — schema-on-read for ingestion (capture everything, sort it out later); schema-on-write at the curated boundary (consumers see clean, contract-honored data).
- **Testing implications**: at Bronze, validate per-record but allow some failures (quarantine). At Silver, validate strictly — failures should rarely happen, and when they do they're a bug.

*Likely follow-up:* "How do you handle schema evolution in a schema-on-read system?" (Answer: versioned schemas; backwards-compatible parsing — old records use old schema, new records use new schema, and reads tolerate both. Avoid breaking changes; deprecate fields gradually.)

### IQ3. "How would you test an XML feed from a partner where the document structure is documented in an XSD?"

*What a good answer covers:*
- **First gate**: parse the XML. Malformed bytes fail here.
- **Second gate**: validate against the XSD using `lxml.etree.XMLSchema(...).validate()`. Catches structural and type errors.
- **Third gate**: business rules via XPath — totals reconcile, required IDs are present, references resolve.
- **Test infrastructure**: keep representative XML samples in `tests/fixtures/` (sanitized, no real PII). Run all three gates as separate test functions for cleaner failure messages.
- **Be aware of namespaces** — if the XML uses `xmlns="..."`, your XPath must be namespace-aware. This is the most common XML bug.
- **Security**: configure parsers to disable external entity resolution; XXE is a real attack class for partner-supplied XML.

*Likely follow-up:* "What if the partner's XML uses element ordering that isn't strictly defined in the XSD?" (Answer: XSD `<xs:sequence>` requires order; `<xs:all>` is unordered. If the partner's docs say "any order" but their XSD uses sequence, your tests will pass but real traffic might fail. Read the actual incoming data, don't trust the schema.)

### IQ4. "How would you test that flattening a nested JSON to a DataFrame preserves all the data?"

*What a good answer covers:*
- **Count test**: number of top-level records in raw JSON matches number of distinct entities in the flattened DataFrame.
- **Reconciliation**: the *value* of a measured field (e.g., `sum(total_amount)`) at the JSON level matches the same sum at the DataFrame level (within float tolerance).
- **Field presence**: every required field from the JSON Schema appears as a column in the DataFrame.
- **Round-trip test**: flatten → reconstruct → compare to original. Useful for catching mistakes in the flattening function. Sometimes infeasible due to lossy normalization, but valuable when it works.
- **Type test**: column dtypes are what you expect (especially after flattening, when pandas often infers `object` for fields that should be numeric).

*Likely follow-up:* "What about deeply-nested arrays — like items containing tags containing IDs?" (Answer: recursive normalization, or restructure upstream. Test each layer's flattening independently. The deeper you go, the more brittle the assertions; consider whether flattening that deep is the right move at all.)

### IQ5. "If you had to validate a stream of 10 million JSON events per day, how would you approach testing?"

*What a good answer covers:*
- **Sample, don't validate every event in CI**. CI tests a representative subset; production validation runs on the live stream.
- **In production**: validate every event with a compiled validator (`Draft202012Validator(schema)` once, reused). Performance overhead is real but manageable — millions of small validations per minute is achievable.
- **Sampling for deep checks**: business-rule and reconciliation checks too expensive for every event. Run on hourly or daily samples.
- **Quarantine, don't drop**: invalid events go to a dead-letter queue; engineers review periodically. Tests assert quarantine rate stays low (e.g., < 0.1%).
- **Alerting**: rejection rate spikes are a critical signal — schema drift, upstream bug, or our schema is too tight. Alert on the *delta*, not the absolute rate.
- **Replay capability**: keep raw payloads for N days so you can re-process after a parsing-bug fix.

*Likely follow-up:* "What's the trade-off between strict and loose validation at scale?" (Answer: strict catches bugs faster but rejects on every minor schema drift; loose accepts garbage that pollutes downstream. The right level depends on the cost of a false rejection vs the cost of bad data downstream. Most teams start strict, loosen specific fields when the upstream change is benign.)

---

## If you have extra time this week (stretch)

- Try [Pydantic](https://docs.pydantic.dev/latest/) — Python class-based modeling that doubles as JSON Schema generation. A different ergonomics from `jsonschema`, popular in API codebases.
- Read [Confluent — Schema Registry](https://docs.confluent.io/platform/current/schema-registry/index.html) — how big-streaming systems version and enforce schemas across Kafka topics. Avro, Protobuf, JSON Schema all supported.
- Skim [Apache Avro](https://avro.apache.org/) — a binary format with embedded schema, common in big-data pipelines. Different testing approach (schema is part of the data, not separate).
- Build a tiny CLI tool: `validate.py path schema_path` that handles both JSON and XML based on file extension. Wire it into a pre-commit hook for any data files you check in.

---

## Answers — Self-checks

> Don't scroll here until you've attempted the questions for that day.

### Day 1 answers

- **Q1.1** — Well-formed = parses as JSON without syntax errors (matched braces, valid types). Valid against a schema = additionally meets structure and content rules (required fields, type constraints, enums). Well-formed is `json.loads`; valid is `jsonschema.validate`.
- **Q1.2** — Because formats vary in cost and dependencies (e.g., `idn-email` requires Unicode tables; `uri` needs a URI library). The spec made format optional so the library doesn't fail to install on systems without those deps. You opt in with `format_checker=FormatChecker()`.
- **Q1.3** — You traded *strictness* for *flexibility*. Strict catches typos and unauthorized fields; flexible tolerates upstream evolution. Real teams often use strict for inbound contracts they own, flexible for third-party APIs they don't control.
- **Q1.4** — A single huge JSON array requires the entire file to be parsed as one document — one corruption, all is lost; can't stream. NDJSON lets you parse line-by-line, recover from individual bad records, and process unbounded streams.

### Day 2 answers

- **Q2.1** — `validator.iter_errors(instance)` yields *all* validation errors. Tests use it because a failure message listing every wrong field is far more useful than "first error: missing field X" — you fix one bug, run again, see another, repeat. Lazy reporting saves debug cycles.
- **Q2.2** — `{"type": ["string", "null"]}` — types can be a single string or an array of strings.
- **Q2.3** — Format is opt-in by spec design (cost/dependencies). Enable with `Draft202012Validator(schema, format_checker=FormatChecker())`. Some formats need extra packages: `pip install 'jsonschema[format]'`.
- **Q2.4** — JSON Schema is fundamentally per-instance structural validation; cross-field arithmetic isn't in its grammar. The `if/then/else` keyword handles simple conditional requirements, but full cross-field rules need Python (or a richer schema language like CEL).

### Day 3 answers

- **Q3.1** — Speed (C-extension via libxml2), full XPath 1.0 support, XSLT, XSD validation, and battle-tested handling of namespaces/encoding. `xml.etree.ElementTree` ships with Python and is fine for trivial cases — `lxml` is the standard once your needs grow at all.
- **Q3.2** — Almost certainly namespaces. The element is `{http://example.com/ns}order`, but your XPath `//order` doesn't match it. Pass `namespaces={"ns": "http://example.com/ns"}` and use `//ns:order`.
- **Q3.3** — Element: `<quantity>2</quantity>` — has children/text. Attribute: `<item quantity="2"/>` — a key-value pair on an element. XPath: `quantity/text()` for the element; `@quantity` for the attribute. Both common; you have to look at the actual XML.
- **Q3.4** — XXE (XML External Entity) attack — malicious XML can declare entities that read local files or fetch URLs. Set `etree.XMLParser(resolve_entities=False, no_network=True)` (or use `defusedxml`). Always assume XML from outside your trust boundary is hostile.

### Day 4 answers

- **Q4.1** — When records have varying field sets, missing fields become NaN (silent data loss in the sense that the absence isn't flagged). Defend by validating each record against a JSON Schema *before* normalizing — make missing fields explicit failures rather than silent NaN.
- **Q4.2** — Schema-on-read at Bronze (raw zone — store everything, parse later); schema-on-write at Silver/Gold (curated zones — strict contracts to downstream consumers). You need both: flexibility on intake, rigor on output.
- **Q4.3** — Many valid: presence/non-empty; encoding (valid UTF-8, no null bytes); length distribution (within expected min/max); language detection (matches expected language); pattern matches (regex for required fragments); statistical (entropy, vocabulary size).
- **Q4.4** — Cross-layer reconciliation catches data loss in transformation. If Bronze has 1000 records and Silver has 850 with no quarantine record explaining 150, you've silently lost data — likely a flattening bug, dedupe over-aggressive, or a join discarding rows. Within-layer tests can't detect that.

### End-of-week answers

**A1.** Object, array, string, number, boolean, null. (Counted as five since "number" covers ints and floats.)

**A2.** `number` accepts both ints and floats; `integer` only ints. `42.0` validates as `number`, fails as `integer`.

**A3.** `{"type": ["string", "null"]}`.

**A4.** `iter_errors` returns *all* errors; `validate` raises on the first. For tests, listing every problem is more useful than fixing one at a time.

**A5.** Pass `format_checker=FormatChecker()` when constructing the validator. Optionally `pip install 'jsonschema[format]'` for the full set of format dependencies.

**A6.** Many valid: namespaces (most common); wrong path syntax (e.g., `/order` requires the root to be `order`, while `//order` matches anywhere); case mismatch in tag name (XML is case-sensitive).

**A7.** XML External Entity attack — malicious XML declares entities that fetch local files or URLs. Prevent by configuring the parser: `etree.XMLParser(resolve_entities=False, no_network=True)`, or use `defusedxml`.

**A8.** Schema-on-read at Bronze (capture everything, validate at query time); schema-on-write at Silver/Gold (strict contract enforcement at the curated boundary).

**A9.** Validate it. Run `Draft202012Validator(generated_schema).check_schema(generated_schema)` to confirm the schema itself is valid; then run sample records through it to confirm it accepts known-good and rejects known-bad. Then tighten — AI almost always overgeneralizes.

**A10.** `bronze_count == silver_count + quarantined_count` (within tolerance for any expected dedupe). If the equation doesn't hold, data was silently lost.

---

*Done with Week 9? You can now ingest JSON, XML, and unstructured payloads, validate them at every layer, and infer schemas from messy real-world samples. The data is no longer required to be tidy. Onward to Week 10 — Big Data Specifics: PySpark, DuckDB, Parquet, and what changes when "the data" is too large to fit in memory.*
