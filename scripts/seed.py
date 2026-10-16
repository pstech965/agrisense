
import math
import random
import sys
from datetime import date, timedelta

from sqlalchemy import insert, text
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import Crop, Market, PriceRecord


# Make generated data reproducible
random.seed(42)


# ---------------------------------------------------------
# MARKETS
# ---------------------------------------------------------

MARKETS = [
    ("Indore", "Madhya Pradesh", "Indore"),
    ("Ujjain", "Madhya Pradesh", "Ujjain"),
    ("Mandsaur", "Madhya Pradesh", "Mandsaur"),
    ("Bhopal", "Madhya Pradesh", "Bhopal"),

    ("Jaipur", "Rajasthan", "Jaipur"),
    ("Kota", "Rajasthan", "Kota"),
    ("Jodhpur", "Rajasthan", "Jodhpur"),

    ("Nagpur", "Maharashtra", "Nagpur"),
    ("Pune", "Maharashtra", "Pune"),
    ("Nashik", "Maharashtra", "Nashik"),

    ("Ahmedabad", "Gujarat", "Ahmedabad"),
    ("Rajkot", "Gujarat", "Rajkot"),
    ("Surat", "Gujarat", "Surat"),

    ("Lucknow", "Uttar Pradesh", "Lucknow"),
    ("Kanpur", "Uttar Pradesh", "Kanpur"),
    ("Agra", "Uttar Pradesh", "Agra"),

    ("Ludhiana", "Punjab", "Ludhiana"),
    ("Amritsar", "Punjab", "Amritsar"),

    ("Karnal", "Haryana", "Karnal"),
    ("Hisar", "Haryana", "Hisar"),

    ("Patna", "Bihar", "Patna"),
    ("Gaya", "Bihar", "Gaya"),

    ("Kolkata", "West Bengal", "Kolkata"),
    ("Siliguri", "West Bengal", "Darjeeling"),

    ("Hyderabad", "Telangana", "Hyderabad"),
    ("Warangal", "Telangana", "Warangal"),

    ("Bengaluru", "Karnataka", "Bengaluru"),
    ("Hubballi", "Karnataka", "Dharwad"),

    ("Raipur", "Chhattisgarh", "Raipur"),
    ("Bhubaneswar", "Odisha", "Khordha"),
]


# ---------------------------------------------------------
# CROPS
# name, category, base price
# ---------------------------------------------------------

CROPS = [
    ("Wheat", "grain", 2400),
    ("Rice", "grain", 3300),
    ("Maize", "grain", 2100),
    ("Bajra", "grain", 2400),
    ("Jowar", "grain", 3200),

    ("Soybean", "oilseed", 4600),
    ("Mustard", "oilseed", 5800),
    ("Groundnut", "oilseed", 6200),

    ("Chana", "pulse", 5500),
    ("Tur", "pulse", 7400),
    ("Moong", "pulse", 8200),
    ("Urad", "pulse", 7000),

    ("Cotton", "fibre", 7300),

    ("Onion", "vegetable", 1800),
    ("Potato", "vegetable", 1500),
    ("Tomato", "vegetable", 2200),

    ("Garlic", "spice", 12000),
    ("Turmeric", "spice", 13000),
    ("Coriander", "spice", 7500),
    ("Ginger", "spice", 6000),
]


# ---------------------------------------------------------
# DATE RANGE
# ---------------------------------------------------------

START = date(2024, 1, 1)
END = date(2026, 9, 30)

# Insert records in batches
BATCH = 10_000


# ---------------------------------------------------------
# SEED FUNCTION
# ---------------------------------------------------------

def seed(force: bool = False) -> None:

    # Create database tables if they don't exist
    create_db_and_tables()

    # -----------------------------------------------------
    # CREATE MARKETS AND CROPS
    # -----------------------------------------------------

    with Session(engine) as session:

        # Check whether market data already exists
        if session.exec(select(Market)).first():

            if not force:
                print(
                    "Data already exists. "
                    "To overwrite existing data, run with --force."
                )
                return

            # Delete old data
            session.exec(
                text(
                    "TRUNCATE TABLE "
                    "price_records, crop, market "
                    "RESTART IDENTITY CASCADE"
                )
            )

            session.commit()

        # Create markets
        session.add_all(
            [
                Market(
                    name=name,
                    state=state,
                    district=district,
                )
                for name, state, district in MARKETS
            ]
        )

        # Create crops
        session.add_all(
            [
                Crop(
                    name=name,
                    category=category,
                )
                for name, category, _ in CROPS
            ]
        )

        session.commit()

        # Read the newly created records
        markets = session.exec(select(Market)).all()
        crops = session.exec(select(Crop)).all()

    # -----------------------------------------------------
    # RANDOM FACTORS
    # -----------------------------------------------------

    # Give every state a slightly different price factor
    state_factor = {
        market.state: random.uniform(0.92, 1.12)
        for market in markets
    }

    # Give every crop a different seasonal phase
    crop_phase = {
        crop.id: random.random()
        for crop in crops
    }

    # Map crop database ID -> base price
    base = {
        crop.id: CROPS[index][2]
        for index, crop in enumerate(crops)
    }

    # These markets should contain data for every crop
    home = {
        "Indore",
        "Ujjain",
        "Mandsaur",
        "Bhopal",
    }

    # -----------------------------------------------------
    # CREATE MARKET + CROP PAIRS
    # -----------------------------------------------------

    pairs = [
        (market, crop)
        for market in markets
        for crop in crops
        if market.name in home or random.random() < 0.55
    ]

    # Number of days
    days = (END - START).days + 1

    rows = []
    total = 0

    # -----------------------------------------------------
    # INSERT PRICE DATA
    # -----------------------------------------------------

    with engine.begin() as conn:

        for day_number in range(days):

            day = START + timedelta(days=day_number)

            # Position of the year
            year_pos = day.timetuple().tm_yday / 365

            # Small long-term price growth
            growth = 1 + 0.04 * (day_number / 365)

            for market, crop in pairs:

                # Randomly skip some records
                if random.random() > 0.85:
                    continue

                # Seasonal price variation
                season = (
                    1
                    + 0.10
                    * math.sin(
                        2
                        * math.pi
                        * (year_pos + crop_phase[crop.id])
                    )
                )

                # Random market noise
                noise = 1 + random.gauss(0, 0.02)

                # Calculate modal price
                modal = round(
                    base[crop.id]
                    * state_factor[market.state]
                    * season
                    * growth
                    * noise,
                    2,
                )

                # Create price record
                rows.append(
                    {
                        "crop_id": crop.id,
                        "market_id": market.id,
                        "price_date": day,
                        "modal_price": modal,
                        "min_price": round(modal * 0.94, 2),
                        "max_price": round(modal * 1.06, 2),
                    }
                )

                # Insert when batch becomes large
                if len(rows) >= BATCH:

                    conn.execute(
                        insert(PriceRecord.__table__),
                        rows,
                    )

                    total += len(rows)
                    rows = []

        # Insert remaining records
        if rows:

            conn.execute(
                insert(PriceRecord.__table__),
                rows,
            )

            total += len(rows)

    # -----------------------------------------------------
    # FINAL MESSAGE
    # -----------------------------------------------------

    print(
        f"Done: {len(markets)} markets, "
        f"{len(crops)} crops, "
        f"{total:,} price records"
    )


# ---------------------------------------------------------
# RUN SCRIPT
# ---------------------------------------------------------

if __name__ == "__main__":
    seed(force="--force" in sys.argv)
