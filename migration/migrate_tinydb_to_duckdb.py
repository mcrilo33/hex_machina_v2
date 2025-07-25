"""
Migration script: TinyDB (replicated_articles) → DuckDB (ArticleDB, IngestionOperationDB, WorkflowOperationDB)
- Reads all articles from TinyDB table 'replicated_articles' (JSON or .db)
- Maps fields to ArticleDB, stores summary/tags/etc. in article_metadata
- Reads html_content from artifact file
- Creates one IngestionOperationDB and one WorkflowOperationDB for all articles
- Fails on any error (strict mode)
- Usage: poetry run python migration/migrate_tinydb_to_duckdb.py --tinydb-path migration/old_articles.json --db-path data/hex_machina.db
"""

import json
import random
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import sessionmaker
from tinydb import TinyDB

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine

from src.hex_machina.storage.base import Base
from src.hex_machina.storage.enrichment.models import WorkflowOperationDB
from src.hex_machina.storage.models import ArticleDB, IngestionOperationDB
from src.hex_machina.utils.date_parser import DateParser

# --- CONFIG ---
TINYDB_TABLE = "articles"


# --- UTILS ---
def read_artifact(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Artifact file not found: {path}")
        return ""


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate articles from TinyDB to DuckDB."
    )
    parser.add_argument(
        "--tinydb-path", required=True, help="Path to TinyDB JSON/db file"
    )
    parser.add_argument("--db-path", required=True, help="Path to DuckDB file")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="If set, randomly sample this many articles for migration.",
    )
    args = parser.parse_args()

    # --- Connect to TinyDB ---
    tinydb = TinyDB(args.tinydb_path)
    articles = tinydb.table(TINYDB_TABLE).all()
    print(f"Loaded {len(articles)} articles from TinyDB table '{TINYDB_TABLE}'")

    # Optionally subsample
    if args.sample_size is not None and len(articles) > args.sample_size:
        random.seed(42)  # For reproducibility
        articles = random.sample(articles, args.sample_size)
        print(f"Sampling {args.sample_size} articles from {len(articles)} total.")

    # --- Connect to DuckDB ---
    engine = create_engine(f"duckdb:///{args.db_path}")

    # --- Ensure all tables are created ---
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # --- Create operation records ---
    now = datetime.now()
    ingestion_op = IngestionOperationDB(
        start_time=now,
        end_time=now,
        num_articles_processed=len(articles),
        num_errors=0,
        status="completed",
        parameters=json.dumps({"source": "tinydb_migration"}),
    )
    session.add(ingestion_op)
    session.flush()  # get id
    workflow_op = WorkflowOperationDB(
        workflow_name="migration",
        parameters={"source": "tinydb_migration"},
        started_at=now,
        finished_at=now,
        status="completed",
        notes="Migration from TinyDB replicated_articles",
    )
    session.add(workflow_op)
    session.flush()

    # --- Migrate articles ---
    for i, art in enumerate(articles):
        try:
            # Required fields
            title = art["title"]
            url = art["url"]
            url_domain = art["url_domain"]
            published_date = DateParser.parse_date(art["published_date"])
            ingested_at = DateParser.parse_date(art["created_at"])
            author = art.get("author")
            # Read html_content from artifact if present
            if "html_content_artifact" in art:
                html_path = art.get("html_content_artifact", {}).get("path")
                html_content = read_artifact(html_path) if html_path else ""
            else:
                html_content = art.get("html_content", "")
            if "text_content_artifact" in art:
                text_path = art.get("text_content_artifact", {}).get("path")
                text_content = read_artifact(text_path) if text_path else ""
            else:
                text_content = art.get("text_content", "")
            # Metadata
            article_metadata = {}
            if "summary" in art:
                article_metadata["summary"] = art.get("summary", "")
            if "tags" in art:
                article_metadata["tags"] = art.get("tags", [])
            ingestion_metadata = art.get("metadata", {})
            ingestion_metadata["migrated_from"] = "hex_machina_v1"
            # Error handling
            error_info = ingestion_metadata.get("error")
            if isinstance(error_info, dict):
                ingestion_error_status = str(error_info.get("status"))
                ingestion_error_message = error_info.get("message", None)
            elif isinstance(error_info, str):
                ingestion_error_status = None
                ingestion_error_message = error_info
            else:
                ingestion_error_status = None
                ingestion_error_message = None
            if "error" in ingestion_metadata:
                del ingestion_metadata["error"]
            if "duration" in ingestion_metadata:
                del ingestion_metadata["duration"]
            # Insert ArticleDB
            article = ArticleDB(
                title=title,
                url=url,
                source_url=url_domain,  # as requested
                url_domain=url_domain,
                published_date=published_date,
                html_content=html_content,
                text_content=text_content,
                author=author,
                article_metadata=json.dumps(article_metadata),
                ingestion_metadata=json.dumps(ingestion_metadata),
                ingestion_run_id=ingestion_op.id,
                ingested_at=ingested_at,
                ingestion_error_status=ingestion_error_status,
                ingestion_error_message=ingestion_error_message,
            )
            session.add(article)
            # Print comparison if sampling
            if getattr(args, "sample_size", None):

                def truncate(val):
                    if val is None:
                        return None
                    s = str(val)
                    return s[:80] + ("..." if len(s) > 80 else "")

                print("\n--- Article Migration Check ---")
                print("Source:")
                for k, v in art.items():
                    if k in ("html_content", "text_content"):
                        print(f"  {k}: {truncate(v)}")
                    else:
                        print(f"  {k}: {v}")
                print("ArticleDB:")
                for col in article.__table__.columns:
                    val = getattr(article, col.name)
                    if col.name in ("html_content", "text_content"):
                        print(f"  {col.name}: '{truncate(val)}'")
                    else:
                        print(f"  {col.name}: '{val}'")
                print("------------------------------\n")
        except Exception as e:
            print(f"Error migrating article {i}: {e}")
            session.rollback()
            raise
    session.commit()
    print(f"Migration complete: {len(articles)} articles migrated.")


if __name__ == "__main__":
    main()
