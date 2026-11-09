"""Provide the shared SQLAlchemy declarative base used by models and Alembic."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all Telaryn database models."""
    pass

