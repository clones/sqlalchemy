from sqlalchemy import types as sqltypes
from sqlalchemy.dialects.mssql.base import MSDateTime, MSDialect
import sys

class MSDateTime_adodbapi(MSDateTime):
    def result_processor(self, dialect, coltype):
        def process(value):
            # adodbapi will return datetimes with empty time values as datetime.date() objects.
            # Promote them back to full datetime.datetime()
            if type(value) is datetime.date:
                return datetime.datetime(value.year, value.month, value.day)
            return value
        return process


class MSDialect_adodbapi(MSDialect):
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = True
    supports_unicode = sys.maxunicode == 65535
    supports_unicode_statements = True
    driver = 'adodbapi'
    
    @classmethod
    def import_dbapi(cls):
        import adodbapi as module
        return module

    colspecs = MSDialect.colspecs.copy()
    colspecs[sqltypes.DateTime] = MSDateTime_adodbapi

    def create_connect_args(self, url):
        keys = url.query

        connectors = ["Provider=SQLOLEDB"]
        if 'port' in keys:
            connectors.append ("Data Source=%s, %s" % (keys.get("host"), keys.get("port")))
        else:
            connectors.append ("Data Source=%s" % keys.get("host"))
        connectors.append ("Initial Catalog=%s" % keys.get("database"))
        user = keys.get("user")
        if user:
            connectors.append("User Id=%s" % user)
            connectors.append("Password=%s" % keys.get("password", ""))
        else:
            connectors.append("Integrated Security=SSPI")
        return [[";".join (connectors)], {}]

    def is_disconnect(self, e):
        return isinstance(e, self.dbapi.adodbapi.DatabaseError) and "'connection failure'" in str(e)

dialect = MSDialect_adodbapi
