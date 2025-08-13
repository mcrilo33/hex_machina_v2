"""Check database schema and create enrichments table if needed."""

import duckdb


def check_db_schema():
    """Check what tables exist in the database."""
    conn = duckdb.connect("storage/articles14.db")

    # List all tables
    tables = conn.execute("SHOW TABLES").fetchall()
    print("Available tables:")
    for table in tables:
        print(f"  - {table[0]}")

    # Check if enrichments table exists
    enrichments_exists = any(table[0] == "enrichments" for table in tables)

    if not enrichments_exists:
        print("\nCreating enrichments table...")
        create_enrichments_table(conn)
    else:
        print("\nEnrichments table already exists.")

    # Check articles table schema
    print("\nArticles table schema:")
    articles_schema = conn.execute("DESCRIBE articles").fetchall()
    for column in articles_schema:
        print(f"  - {column[0]}: {column[1]}")

    # Check enrichments table schema
    print("\nEnrichments table schema:")
    enrichments_schema = conn.execute("DESCRIBE enrichments").fetchall()
    for column in enrichments_schema:
        print(f"  - {column[0]}: {column[1]}")

    conn.close()


def create_enrichments_table(conn):
    """Create the enrichments table."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS enrichments (
        id INTEGER PRIMARY KEY,
        article_id INTEGER NOT NULL,
        enrichment_type VARCHAR(100) NOT NULL,
        content JSON NOT NULL,
        enrichment_metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

    conn.execute(create_table_sql)
    print("✅ Enrichments table created successfully!")


if __name__ == "__main__":
    check_db_schema()
