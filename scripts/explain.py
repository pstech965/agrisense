import sys
from sqlalchemy import text
from sqlmodel import Session
from app.database import engine

INDEX_NAME = "idx_price_crop_market_date"

CREATE_INDEX = (
    f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
    "ON price_records (crop_id, market_id, price_date DESC)"
)

QUERIES= {
    "A) One crop + Latest 20 prices of one market": """
    SELECT price_date, modal_price FROM price_records
    WHERE crop_id = 1 AND market_id= 3
    ORDER BY price_date DESC LIMIT 20 """,
    
    "B) Market-wise price for one crop in 2026": """
    SELECT market_id, AVG(modal_price) FROM price_records
    WHERE crop_id= 1 AND price_date >= '2026-01-01'
    GROUP BY market_id""",
    
    "C) Only records of Jul-Sep 2026 (partition pruning test)": """
    SELECT COUNT (*) FROM price_records
    WHERE price_date BETWEEN '2026-07-01'  AND '2026-09-30' """,         
}

def show_plan(session: Session, title: str, sql: str) -> None:
    print(f"\n === {title} ===")
    for row in session.exec(text("EXPLAIN (ANALYZE, BUFFERS)" +sql)):
        print (row[0])
        

def main() -> None:
    with Session(engine) as session:
        if "--index" in sys.argv:
            session.exec(text(CREATE_INDEX))
            session.exec(text("ANALYZE price_records"))
            session.commit()
            print("Index Created")
        if "--drop-index" in sys.argv:
            session.exec(text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
            session.commit()
            print("Index Deleted")
        for title, sql in QUERIES.items():
            show_plan(session, title, sql)
            
if __name__ == "__main__":
    main()