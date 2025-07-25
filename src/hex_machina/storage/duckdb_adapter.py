import os
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .adapter import BaseDBAdapter
from .models import Article, Base, IngestionOperation


class DuckDBAdapter(BaseDBAdapter):
    """DuckDB implementation of BaseDBAdapter using SQLAlchemy.

    Args:
        db_path (str): Path to the DuckDB database file. Defaults to 'data/hex_machina.db'.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is None:
            db_path = os.path.join("data", "hex_machina.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = create_engine(f"duckdb:///{db_path}")
        Base.metadata.create_all(self.engine)  # Create tables if they don't exist
        self.SessionLocal = sessionmaker(bind=self.engine)

    # --- IngestionOperation CRUD ---

    def add_ingestion_operation(
        self, ingestion_op: IngestionOperation
    ) -> IngestionOperation:
        """Add a new ingestion operation to the database."""
        with self.SessionLocal() as session:
            session.add(ingestion_op)
            session.commit()
            session.refresh(ingestion_op)
            return ingestion_op

    def get_ingestion_operation(self, op_id: int) -> Optional[IngestionOperation]:
        """Retrieve an ingestion operation by its ID."""
        with self.SessionLocal() as session:
            return session.get(IngestionOperation, op_id)

    def update_ingestion_operation(
        self, ingestion_op: IngestionOperation
    ) -> IngestionOperation:
        """Update an existing ingestion operation in the database."""
        with self.SessionLocal() as session:
            db_obj = session.get(IngestionOperation, ingestion_op.id)
            if db_obj is None:
                raise ValueError(
                    f"IngestionOperation with id {ingestion_op.id} not found."
                )
            for attr, value in vars(ingestion_op).items():
                if attr != "_sa_instance_state":
                    setattr(db_obj, attr, value)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def delete_ingestion_operation(self, op_id: int) -> None:
        """Delete an ingestion operation by its ID."""
        with self.SessionLocal() as session:
            db_obj = session.get(IngestionOperation, op_id)
            if db_obj:
                session.delete(db_obj)
                session.commit()

    def list_ingestion_operations(self) -> List[IngestionOperation]:
        """List all ingestion operations in the database."""
        with self.SessionLocal() as session:
            return session.query(IngestionOperation).all()

    # --- Article CRUD ---

    def add_article(self, article: Article) -> Article:
        """Add a new article to the database."""
        with self.SessionLocal() as session:
            session.add(article)
            session.commit()
            session.refresh(article)
            return article

    def get_article(self, article_id: int) -> Optional[Article]:
        """Retrieve an article by its ID."""
        with self.SessionLocal() as session:
            return session.get(Article, article_id)

    def update_article(self, article: Article) -> Article:
        """Update an existing article in the database."""
        with self.SessionLocal() as session:
            db_obj = session.get(Article, article.id)
            if db_obj is None:
                raise ValueError(f"Article with id {article.id} not found.")
            for attr, value in vars(article).items():
                if attr != "_sa_instance_state":
                    setattr(db_obj, attr, value)
            session.commit()
            session.refresh(db_obj)
            return db_obj

    def delete_article(self, article_id: int) -> None:
        """Delete an article by its ID."""
        with self.SessionLocal() as session:
            db_obj = session.get(Article, article_id)
            if db_obj:
                session.delete(db_obj)
                session.commit()

    def list_articles(self) -> List[Article]:
        """List all articles in the database."""
        with self.SessionLocal() as session:
            return session.query(Article).all()

    def get_article_by_domain_and_title(
        self, url_domain: str, title: str
    ) -> Optional[Article]:
        """Retrieve an article by its url_domain and title.

        Args:
            url_domain (str): The domain of the article URL.
            title (str): The title of the article.

        Returns:
            Optional[Article]: The ORM object if found, else None.
        """
        with self.SessionLocal() as session:
            return (
                session.query(Article)
                .filter_by(url_domain=url_domain, title=title)
                .first()
            )
