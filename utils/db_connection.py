import psycopg2
from django.conf import settings

def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT'],
            options="-c search_path=sijarta"
        )
        return connection
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        raise