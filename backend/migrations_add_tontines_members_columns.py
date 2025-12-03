"""Small migration helper to add missing columns to tontines_members.

Run this from the backend folder with:
    py migrations_add_tontines_members_columns.py

It uses the app's SQLAlchemy config and runs ALTER TABLE to add the
`is_approved` and `is_admin` TINYINT(1) columns with default 0.
"""
from app import app, db
from sqlalchemy import text


def add_columns():
    with app.app_context():
        conn = db.engine.connect()
        try:
            print("Adding column is_approved to tontines_members (if not exists)...")
            conn.execute(text("ALTER TABLE tontines_members ADD COLUMN is_approved TINYINT(1) NOT NULL DEFAULT 0"))
        except Exception as e:
            print(f"Warning / info: could not add is_approved column: {e}")

        try:
            print("Adding column is_admin to tontines_members (if not exists)...")
            conn.execute(text("ALTER TABLE tontines_members ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0"))
        except Exception as e:
            print(f"Warning / info: could not add is_admin column: {e}")

        conn.close()


if __name__ == '__main__':
    add_columns()