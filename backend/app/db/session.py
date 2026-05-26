from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# Create database connection engine for PostgreSQL
engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    # Automates table creation in PostgreSQL
    SQLModel.metadata.create_all(engine)

def get_session():
    # Connection generator dependency
    with Session(engine) as session:
        yield session
