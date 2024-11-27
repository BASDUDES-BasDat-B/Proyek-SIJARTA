import psycopg
from django.conf import settings

def get_db_connection():
    try:
        connection = psycopg.connect(
            dbname=settings.DATABASE_CONFIG['dbname'],
            user=settings.DATABASE_CONFIG['user'],
            password=settings.DATABASE_CONFIG['password'],
            host=settings.DATABASE_CONFIG['host'],
            port=settings.DATABASE_CONFIG['port'],
        )
        return connection
    except psycopg.Error as e:
        print(f"Database connection failed: {e}")
        raise
        