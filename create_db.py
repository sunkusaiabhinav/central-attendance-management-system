"""Create the attendance_db database if it doesn't exist."""
import psycopg

conn = psycopg.connect("host=localhost dbname=postgres user=postgres password=nanobanana")
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname='attendance_db'")
exists = cur.fetchone()
if not exists:
    cur.execute("CREATE DATABASE attendance_db")
    print("Database 'attendance_db' created successfully.")
else:
    print("Database 'attendance_db' already exists.")
conn.close()
