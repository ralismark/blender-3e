#!/usr/bin/env python3

from contextlib import asynccontextmanager
import logging
import sqlite3

from . import config
from .arlock import ARLock

_L = logging.getLogger(__name__)

def _connect() -> sqlite3.Connection:
    """
    Create a database connection
    """
    con = sqlite3.connect(config.get("sql.path"), isolation_level=None)
    con.row_factory = sqlite3.Row
    return con

DATABASE = _connect()
DB_LOCK = ARLock()

@asynccontextmanager
async def transact():
    """
    Async transaction which locks the database
    """
    async with DB_LOCK:
        _L.debug("entering savepoint")
        DATABASE.execute("savepoint auto")
        try:
            yield DATABASE
        except:
            DATABASE.execute("rollback to auto")
            _L.debug("rolling back savepoint")
            raise
        finally:
            DATABASE.execute("release auto")
            _L.debug("exiting savepoint")

def esc(ident: str) -> str:
    """
    Escape an identifier for use in SQLite.

    This should used as late as possible - only when actually accessing the
    database. Don't escape early.
    """
    ident = str(ident)
    return '"' + ident.replace('"', '""') + '"'

def require_table(name, schema):
    """
    Create a table with a certain name if it does not yet exist
    """
    # TODO maybe check duplicates
    DATABASE.execute(f"create table if not exists {name} ({schema})")
    _L.info("creating table %s", name)

def query(statement, *args, **kwargs):
    """
    Return all matches to given query
    """
    _L.debug("query `%s` with args %s", statement, args or kwargs)
    return DATABASE.execute(statement, tuple(args) or kwargs).fetchall()
