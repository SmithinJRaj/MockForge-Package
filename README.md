# MockForge Engine

> **O(1) memory-safe synthetic data generator and intelligent database seeder for Python.**

MockForge Engine enables Data Engineers and Backend Developers to generate and stream millions of structurally accurate synthetic records directly into SQL databases without exhausting memory or writing boilerplate insertion logic.

Built with database introspection and fault-tolerant insertion strategies, MockForge automatically validates schemas, guards against constraint violations, and isolates bad records through a Dead Letter Queue (DLQ).

---

## ✨ Features

### 🚀 O(1) Memory Footprint

Generate and insert millions of records using Python generators (`yield`) without loading datasets into memory.

* Stream 10M+ rows on commodity hardware
* No intermediate files
* No Out-Of-Memory crashes

---

### 🧠 Intelligent Pre-Flight Validation

Uses SQLAlchemy reflection to inspect target database schemas before inserting data.

* Validates column existence
* Checks datatype compatibility
* Prevents runtime deployment failures

---

### 🛡️ Auto-Truncation Guardrails

Automatically detects database column limits and safely truncates generated strings in-memory.

* Supports `VARCHAR` length detection
* Prevents SQL overflow exceptions
* Eliminates manual sanitization logic

---

### ⚡ Fault-Tolerant Batch Insertion

Batch inserts are wrapped in nested SQL savepoints.

If a batch fails due to:

* `UNIQUE` constraint violations
* Duplicate primary keys
* Invalid records

MockForge automatically degrades to row-by-row insertion, quarantines the bad records, and inserts the remaining valid data.

---

### 📦 Dead Letter Queue (DLQ)

Failed records are automatically written to JSON for later inspection.

```text
failed_rows.json
```

This enables:

* Error auditing
* Data quality debugging
* Replay of failed records

---

### 🌳 Deeply Nested Schema Support

Generate realistic data structures including:

* Nested objects
* Arrays
* Enums
* Regex-generated strings
* Recursive JSON documents

---

## 📦 Installation

```bash
pip install mockforge-engine
```

**Requirements**

* Python 3.10+
* SQLAlchemy 2.0+

---

## ⚡ Quick Start

### Define a Schema

```python
schema = {
    "full_name": {"type": "name"},
    "role": {
        "type": "enum",
        "choices": ["Admin", "User", "Guest"]
    },
    "email": {"type": "email"},
    "age": {
        "type": "integer",
        "min": 18,
        "max": 99
    }
}
```

### Generate and Stream Data

```python
from mockforge import (
    DataEngine,
    DatabaseSeeder,
    SchemaMismatchError
)

try:
    engine = DataEngine(schema=schema)

    data_stream = engine.stream(count=50000)

    seeder = DatabaseSeeder(
        db_url="sqlite:///dev_database.db"
    )

    inserted = seeder.insert_stream(
        table_name="users",
        schema=schema,
        data_stream=data_stream,
        batch_size=10000
    )

    print(f"Inserted {inserted} records.")

except SchemaMismatchError as e:
    print(f"Pre-flight validation failed: {e}")
```

---

## 🛡️ Execution Modes

### Best-Effort Mode (Default)

Continues inserting valid records even when some rows fail.

```python
seeder.insert_stream(
    table_name="users",
    schema=schema,
    data_stream=data_stream,
    strict_mode=False,
    dlq_file="failed_rows.json"
)
```

**Behavior**

```text
Batch Insert
      ↓
Constraint Error
      ↓
Row-by-Row Retry
      ↓
Good Rows → Database
Bad Rows  → DLQ JSON
```

---

### Strict Mode (All-or-Nothing)

Rolls back the entire transaction if a single row violates a constraint.

```python
seeder.insert_stream(
    table_name="users",
    schema=schema,
    data_stream=data_stream,
    strict_mode=True
)
```

Ideal for:

* CI/CD pipelines
* Integration testing
* Deterministic environments

---

## 📖 Schema Definition

### Primitive Types

```python
{
    "first_name": "name",
    "age": {
        "type": "integer",
        "min": 18,
        "max": 65
    },
    "is_active": "boolean"
}
```

---

### Nested Objects

```python
{
    "company_details": {
        "type": "object",
        "schema": {
            "company_name": "string",
            "established_date": "date"
        }
    }
}
```

---

### Arrays

```python
{
    "tags": {
        "type": "array",
        "size": [1, 5],
        "items": {
            "type": "string"
        }
    }
}
```

---

### Regex-Based Generation

```python
{
    "product_sku": {
        "type": "string",
        "regex": "^[A-Z]{3}-[0-9]{4}$"
    }
}
```

Example output:

```text
ABC-4821
XYZ-1930
KLM-8891
```

---

## 🏗️ Architecture

```text
JSON Schema
      ↓
 DataEngine
      ↓
 Generator Stream (yield)
      ↓
 Batch Processor
      ↓
 Database Reflection
      ↓
 Transaction Manager
      ↓
 ┌──────────────┴──────────────┐
 │                             │
Success                     Failure
 │                             │
Database                  Dead Letter Queue
```

---

## 🔧 Built With

* Faker
* SQLAlchemy
* rstr
* Python Generators
* SQL Savepoints & Nested Transactions

---

## 🎯 Use Cases

* Database benchmarking
* Integration testing
* Local development environments
* Data engineering pipelines
* Performance testing
* Synthetic data generation at scale

---

## 📈 Why MockForge?

| Feature                  | MockForge | Traditional Seed Scripts |
| ------------------------ | --------- | ------------------------ |
| O(1) Memory Usage        | ✅         | ❌                        |
| Streaming Inserts        | ✅         | ❌                        |
| Database Reflection      | ✅         | ❌                        |
| DLQ Support              | ✅         | ❌                        |
| Constraint Recovery      | ✅         | ❌                        |
| Nested Schema Generation | ✅         | Limited                  |

---

## 📄 License

MIT License
