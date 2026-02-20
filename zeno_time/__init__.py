"""
MySQL driver: use mysqlclient if available (preferred), else PyMySQL (Windows-friendly fallback).
Django expects MySQLdb; PyMySQL can emulate it when mysqlclient is not installed.
"""
try:
    import MySQLdb  # noqa: F401  # mysqlclient
except ImportError:
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass  # Neither installed; Django will fail when using MySQL backend
