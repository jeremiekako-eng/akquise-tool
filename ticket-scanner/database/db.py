"""Datenbankverbindung und Session-Management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from database.models import Base
from config import cfg


engine = create_engine(
    f"sqlite:///{cfg.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Erstellt alle Tabellen falls nicht vorhanden."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Context-Manager für DB-Sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
