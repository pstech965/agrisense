from sqlmodel import Session, SQLModel, create_engine
from app.config import settings
# Engine = database se connection pool. App start hone par ek hi baar banta hai.
engine = create_engine(settings.database_url, pool_size=10, max_overflow=20)

def create_db_and_tables() -> None:
  from app import models # noqa: F401 (import zaroori hai taaki tables register ho jayein)
  
  SQLModel.metadata.create_all(engine)

def get_session():
# Har request ko apna session milta hai, request khatam -> session band
  with Session(engine) as session:
    yield session