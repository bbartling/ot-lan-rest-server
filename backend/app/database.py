from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Specify your database connection string here. For SQLite, it can be a file or in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"  # SQLite database file named test.db located in the current directory

# Create a SQLAlchemy engine instance
# connect_args={"check_same_thread": False} is only needed for SQLite. It's not needed for other databases.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a database session. The class itself is not a database session yet.
# But once we create an instance of the SessionLocal class, this instance will be the actual database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# We will inherit from this class to create each of the database models or classes (the ORM models).
Base = declarative_base()
