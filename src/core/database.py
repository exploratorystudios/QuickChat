from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import DATABASE_URL
from src.core.models import Base

class DatabaseManager:
    def __init__(self, db_url=DATABASE_URL):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._scoped_session = scoped_session(self.SessionLocal)

    def init_db(self):
        """Initialize the database schema."""
        Base.metadata.create_all(bind=self.engine)

        # Add missing columns for existing databases
        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(messages)"))
            columns = [row[1] for row in result]

            # Add thinking column if it doesn't exist
            if 'thinking' not in columns:
                conn.execute(text("ALTER TABLE messages ADD COLUMN thinking TEXT"))
                conn.commit()

            # Add images column if it doesn't exist
            if 'images' not in columns:
                conn.execute(text("ALTER TABLE messages ADD COLUMN images TEXT"))
                conn.commit()

        # Create images directory if it doesn't exist
        from config.settings import DATA_DIR
        import os
        images_dir = os.path.join(DATA_DIR, "images")
        os.makedirs(images_dir, exist_ok=True)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()
    
    def get_scoped_session(self):
        """Get a thread-local scoped session."""
        return self._scoped_session()

    def close_scoped_session(self):
        """Remove the scoped session."""
        self._scoped_session.remove()

# Global instance
db = DatabaseManager()
