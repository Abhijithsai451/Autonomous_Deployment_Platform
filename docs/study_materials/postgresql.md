# PostgreSQL: Comprehensive Reference Guide

PostgreSQL is a powerful, open-source object-relational database system. It is known for its reliability, feature robustness, and performance.

---

## 1. Introduction to PostgreSQL
PostgreSQL (or Postgres) is an **ACID-compliant** RDBMS. It supports both SQL (relational) and JSON (non-relational) data, making it highly versatile for modern applications.

---

## 2. Setting Up (Python)
You will need a running Postgres instance.
Docker: `docker run --name my-postgres -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres`

In Python, the standard library is `psycopg`.
`pip install psycopg`

---

## 3. Core Concepts

### A. Basic CRUD Operations
[Image of relational database table structure]

```python
import psycopg

# Connect to the database
with psycopg.connect("dbname=test user=postgres password=mysecretpassword") as conn:
    # Open a cursor to perform database operations
    with conn.cursor() as cur:
        # Create a table
        cur.execute("CREATE TABLE IF NOT EXISTS users (id serial PRIMARY KEY, name text, age int);")
        
        # Insert data
        cur.execute("INSERT INTO users (name, age) VALUES (%s, %s)", ("Alice", 30))
        
        # Query data
        cur.execute("SELECT * FROM users;")
        print(cur.fetchall())
        
        # Commit changes
        conn.commit()
```

### B. Transactions
PostgreSQL ensures data integrity using ACID (Atomicity, Consistency, Isolation, Durability) properties. Always use context managers to handle transactions.

```python
with conn.transaction():
    cur.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
    cur.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
```

---

## 4. Advanced Topics

### A. Indexing for Performance
Indexes are essential for large datasets.
* **B-Tree:** The default. Good for `=`, `>`, `<`, etc.
* **GIN (Generalized Inverted Index):** Best for JSONB and array searching.

```sql
CREATE INDEX idx_users_name ON users(name);
CREATE INDEX idx_users_data ON users USING GIN (data);
```

### B. JSONB (Document Store capabilities)
Postgres can act like a NoSQL database.
```sql
-- Insert JSON data
INSERT INTO users (name, data) VALUES ('Bob', '{"email": "bob@example.com", "tags": ["admin"]}');

-- Query JSON field
SELECT name FROM users WHERE data->>'email' = 'bob@example.com';
```

---

## 5. Architectural Deep Dive
[Image of PostgreSQL shared memory and background processes architecture]

* **Shared Buffers:** Where data pages are cached.
* **Write-Ahead Logging (WAL):** Ensures durability by logging changes before they are applied to data files.
* **Vacuuming:** A critical process that reclaims storage from deleted or updated rows (MVCC).

---

## 6. Summary Cheat Sheet

| Feature | Concept | Use Case |
| :--- | :--- | :--- |
| **SQL** | Relational | Structured data, complex joins. |
| **JSONB** | Document | Semi-structured data, high flexibility. |
| **Index** | B-Tree/GIN | Drastic query performance improvement. |
| **Vacuum** | Maintenance | Cleaning up dead tuples to prevent bloat. |
