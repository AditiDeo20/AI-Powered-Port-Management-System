from app.services.postgres_service import PostgreSQLService


db = PostgreSQLService()

db.close()

print("Connection Closed Successfully")