import psycopg

connection = psycopg.connect(
    host="localhost",
    port=5433,
    dbname="port_rag",
    user="rag_user",
    password="incorrect123"
)

print("Connected Successfully!")

cursor = connection.cursor()

cursor.execute("SELECT version();")

version = cursor.fetchone()

print(version)

cursor.close()
connection.close()