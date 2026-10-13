try:
    import mysql.connector as mysql  # type: ignore[import-not-found]
except ImportError:
    mysql = None

if mysql is not None:
    print(f"MySQL connector loaded: {mysql.__name__}")
else:
    print("MySQL connector is not installed.")