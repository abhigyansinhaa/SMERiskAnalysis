"""Create database tables from SQLAlchemy models. Run after MySQL is set up."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tables created successfully.")
