"""PostgreSQL reader / writer plugin.

Provides :class:`PostgresReader` and :class:`PostgresWriter` for
interacting with PostgreSQL databases via **SQLAlchemy**.

Both ``sqlalchemy`` and a PostgreSQL driver (e.g. ``psycopg2-binary``)
are required.  A friendly
:class:`~aptdata.plugins.manager.PluginDependencyError` is raised
when either is missing.
"""

from __future__ import annotations

from typing import Any

from aptdata.core.dataset import BaseDataset
from aptdata.plugins.base import BaseReader, BaseWriter
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.manager import PluginDependencyError


def _require_sqlalchemy() -> Any:
    """Import and return the ``sqlalchemy`` module, or raise a friendly error."""
    try:
        import sqlalchemy  # noqa: WPS433
    except ImportError:
        raise PluginDependencyError("postgres", "sqlalchemy") from None
    return sqlalchemy


class PostgresReader(BaseReader):
    """Execute a SQL query against a PostgreSQL database and return the result
    as an :class:`~aptdata.plugins.dataset.InMemoryDataset`.

    Parameters
    ----------
    connection_url:
        SQLAlchemy connection URL, e.g.
        ``"postgresql+psycopg2://user:pass@host:5432/db"``.
    query:
        Raw SQL ``SELECT`` query to execute.
    """

    def __init__(self, connection_url: str, query: str) -> None:
        self.connection_url = connection_url
        self.query = query

    def read(self, **kwargs: Any) -> InMemoryDataset:
        sa = _require_sqlalchemy()
        engine = sa.create_engine(self.connection_url)
        with engine.connect() as conn:
            result = conn.execute(sa.text(self.query))
            columns = list(result.keys())
            records = [dict(zip(columns, row)) for row in result.fetchall()]

        ds = InMemoryDataset(uri=self.connection_url)
        ds.write(records)
        return ds


class PostgresWriter(BaseWriter):
    """Write an :class:`~aptdata.plugins.dataset.InMemoryDataset` to a
    PostgreSQL table.

    Parameters
    ----------
    connection_url:
        SQLAlchemy connection URL.
    table:
        Target table name.
    if_exists:
        Behaviour when the table already exists: ``"append"`` (default),
        ``"replace"``, or ``"fail"``.
    """

    def __init__(
        self,
        connection_url: str,
        table: str,
        *,
        if_exists: str = "append",
    ) -> None:
        self.connection_url = connection_url
        self.table = table
        self.if_exists = if_exists

    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        sa = _require_sqlalchemy()
        records: list[dict[str, Any]] = dataset.read()
        if not records:
            return

        engine = sa.create_engine(self.connection_url)
        meta = sa.MetaData()

        with engine.connect() as conn:
            if self.if_exists == "replace":
                # Use SQLAlchemy DDL to avoid raw SQL interpolation
                tbl = sa.Table(self.table, sa.MetaData())
                tbl.drop(engine, checkfirst=True)

            # Auto-create a simple text-column table when it doesn't exist
            if not sa.inspect(engine).has_table(self.table):
                columns = [sa.Column(k, sa.Text) for k in records[0]]
                sa.Table(self.table, meta, *columns)
                meta.create_all(engine)

            table_obj = sa.Table(self.table, sa.MetaData(), autoload_with=engine)
            conn.execute(table_obj.insert(), records)
            conn.commit()


__all__ = ["PostgresReader", "PostgresWriter"]
