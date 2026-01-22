import psycopg2

conn_string = "postgres://postgres:XDC85D8mnoEbVRN@still-resonance-8688.flycast:5432/postgres"
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
cursor.close()
conn.close()
