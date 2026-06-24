import asyncio
import random
from datetime import date, timedelta
from sqlalchemy import text
from db import engine, AsyncSessionLocal, init_db, Well, WellProduction

random.seed(42)

FORMATIONS = ["Montney", "Duvernay", "Cardium", "Viking", "Wabamun"]
LICENSEES = [
    "Cenovus Energy", "Tourmaline Oil", "ARC Resources",
    "Spartan Delta", "Headwater Exploration", "Baytex Energy",
    "Whitecap Resources", "Vermilion Energy",
]
REGIONS = ["Peace River", "Pembina", "Red Deer", "Foothills", "Lloydminster"]
REGION_COORDS = {
    "Peace River":   (56.2, -117.3),
    "Pembina":       (53.1, -115.0),
    "Red Deer":      (52.3, -113.8),
    "Foothills":     (50.8, -114.5),
    "Lloydminster":  (53.3, -110.0),
}
STATUSES = ["Active", "Active", "Active", "Suspended", "Abandoned"]
WELL_TYPES = {"Montney": "Gas", "Duvernay": "Gas", "Cardium": "Oil",
              "Viking": "Oil", "Wabamun": "Gas"}
SUBSTANCES = {"Gas": "Natural Gas", "Oil": "Crude Oil"}


def random_coord(base_lat, base_lon):
    return round(base_lat + random.uniform(-1.5, 1.5), 5), \
           round(base_lon + random.uniform(-2.0, 2.0), 5)


def make_well(i):
    formation = random.choice(FORMATIONS)
    region = random.choice(REGIONS)
    well_type = WELL_TYPES[formation]
    base_lat, base_lon = REGION_COORDS[region]
    lat, lon = random_coord(base_lat, base_lon)
    license_date = date(2018, 1, 1) + timedelta(days=random.randint(0, 365 * 6))

    return Well(
        license_number=f"AER-{100000 + i}",
        well_name=f"{region.split()[0].upper()}-{formation[:3].upper()}-{i:04d}",
        licensee=random.choice(LICENSEES),
        formation=formation,
        field_name=f"{region} {formation} Field",
        well_type=well_type,
        well_status=random.choice(STATUSES),
        latitude=lat,
        longitude=lon,
        license_date=license_date,
        substance=SUBSTANCES[well_type],
        region=region,
    )


def make_production(well_id, well_type):
    records = []
    for year in [2024, 2025]:
        for month in range(1, 13):
            if well_type == "Oil":
                oil = round(random.uniform(30, 450), 2)
                gas = round(random.uniform(5, 80), 2)
            else:
                oil = round(random.uniform(0, 10), 2)
                gas = round(random.uniform(80, 4800), 2)
            records.append(WellProduction(
                well_id=well_id,
                year=year,
                month=month,
                oil_volume_m3=oil,
                gas_volume_e3m3=gas,
                water_volume_m3=round(random.uniform(5, 200), 2),
            ))
    return records


async def seed():
    await init_db()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM wells"))
        count = result.scalar()
        if count > 0:
            print(f"Database already has {count} wells. Skipping seed.")
            return

        print("Seeding wells...")
        wells = [make_well(i) for i in range(1, 201)]
        session.add_all(wells)
        await session.flush()

        print("Seeding production records...")
        production = []
        for well in wells:
            if well.well_status == "Active":
                production.extend(make_production(well.id, well.well_type))
        session.add_all(production)

        await session.commit()
        print(f"Done. {len(wells)} wells, {len(production)} production records.")


if __name__ == "__main__":
    asyncio.run(seed())
