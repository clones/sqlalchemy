"""Support for the PostgreSQL database via py-postgresql.

Connecting
----------

URLs are of the form `postgresql+pypostgresql://user@password@host:port/dbname[?key=value&key=value...]`.


"""
from sqlalchemy.engine import default
import decimal
from sqlalchemy import util
from sqlalchemy import types as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect, PGExecutionContext
from sqlalchemy import processors

class PGNumeric(sqltypes.Numeric):
    def bind_processor(self, dialect):
        return processors.to_str

    def result_processor(self, dialect, coltype):
        if self.asdecimal:
            return None
        else:
            return processors.to_float

class PostgreSQL_pypostgresqlExecutionContext(PGExecutionContext):
    pass

class PostgreSQL_pypostgresql(PGDialect):
    driver = 'pypostgresql'

    supports_unicode_statements = True
    supports_unicode_binds = True
    description_encoding = None
    default_paramstyle = 'pyformat'

    # requires trunk version to support sane rowcounts
    # TODO: use dbapi version information to set this flag appropariately
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = False

    execution_ctx_cls = PostgreSQL_pypostgresqlExecutionContext
    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.Numeric : PGNumeric,
            sqltypes.Float: sqltypes.Float,  # prevents PGNumeric from being used
        }
    )

    @classmethod
    def dbapi(cls):
        from postgresql.driver import dbapi20
        return dbapi20

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if 'port' in opts:
            opts['port'] = int(opts['port'])
        else:
            opts['port'] = 5432
        opts.update(url.query)
        return ([], opts)

    def is_disconnect(self, e):
        return "connection is closed" in str(e)

dialect = PostgreSQL_pypostgresql
