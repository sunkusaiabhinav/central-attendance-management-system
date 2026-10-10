"""Verify database tables were created correctly."""
import psycopg

conn = psycopg.connect("host=localhost dbname=attendance_db user=postgres password=nanobanana")
cur = conn.cursor()
cur.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='public' ORDER BY table_name"
)
tables = [row[0] for row in cur.fetchall()]
print("Tables created:", tables)
conn.close()
