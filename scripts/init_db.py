
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import initialize_database, check_database_connection
from app.config import settings


def main():
    print("Initializing Enterprise RAG local database...")

    settings.create_directories()

    if not check_database_connection():
        raise RuntimeError("SQLite database connection failed.")

    initialize_database()

    print("DATABASE INITIALIZED SUCCESSFULLY")
    print(f"Database location: {settings.DATABASE_PATH}")
    print("Database engine: SQLite")
    print("Database connection: Successful")


if __name__ == "__main__":
    main()
