"""
Chargement des données nettoyées dans PostgreSQL.
Entrée : data/processed/houses_clean.csv
Tables : neighborhoods, houses
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DB_URL)


def load_neighborhoods(df: pd.DataFrame) -> dict:
    """Insère les quartiers uniques et retourne le mapping nom -> id."""
    neighborhoods = sorted(df['Neighborhood'].unique())
    with engine.begin() as conn:
        for name in neighborhoods:
            conn.execute(
                text("INSERT INTO neighborhoods (neighborhood_name) "
                     "VALUES (:name) ON CONFLICT (neighborhood_name) DO NOTHING"),
                {"name": name}
            )
        # Récupérer le mapping
        result = conn.execute(text(
            "SELECT neighborhood_id, neighborhood_name FROM neighborhoods"
        ))
        mapping = {row[1]: row[0] for row in result}
    print(f"✅ {len(neighborhoods)} quartiers insérés/trouvés")
    return mapping


def load_houses(df: pd.DataFrame, mapping: dict):
    """Insère les maisons dans la table principale."""
    df = df.copy()
    df['neighborhood_id'] = df['Neighborhood'].map(mapping)

    cols = {
        'MSSubClass': 'mssubclass', 'MSZoning': 'mszoning',
        'LotFrontage': 'lotfrontage', 'LotArea': 'lotarea',
        'Street': 'street', 'LotShape': 'lotshape',
        'LandContour': 'landcontour', 'neighborhood_id': 'neighborhood_id',
        'HouseStyle': 'housestyle', 'OverallQual': 'overallqual',
        'OverallCond': 'overallcond', 'YearBuilt': 'yearbuilt',
        'YearRemodAdd': 'yearremodadd', 'RoofStyle': 'roofstyle',
        'Exterior1st': 'exterior1st', 'MasVnrArea': 'masvnrarea',
        'BsmtQual': 'bsmtqual', 'TotalBsmtSF': 'totalbsmtsf',
        '1stFlrSF': 'firstflrsf', '2ndFlrSF': 'secondflrsf',
        'GrLivArea': 'grlivarea', 'FullBath': 'fullbath',
        'HalfBath': 'halfbath', 'BedroomAbvGr': 'bedroomabvgr',
        'KitchenAbvGr': 'kitchenabvgr', 'TotRmsAbvGrd': 'totrmsabvgrd',
        'Fireplaces': 'fireplaces', 'GarageCars': 'garagecars',
        'GarageArea': 'garagearea', 'WoodDeckSF': 'wooddecksf',
        'OpenPorchSF': 'openporchsf', 'SalePrice': 'saleprice',
        'HouseAge': 'house_age', 'RemodAge': 'remod_age',
        'TotalSF': 'total_sf', 'TotalBath': 'total_bath',
        'PricePerSF': 'price_per_sf', 'HasGarage': 'has_garage',
        'HasPool': 'has_pool', 'HasFireplace': 'has_fireplace'
    }

    df_to_load = df[list(cols.keys())].rename(columns=cols)

    # Vider la table avant (au cas où on relance)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE houses RESTART IDENTITY"))

    df_to_load.to_sql('houses', engine, if_exists='append', index=False)
    print(f"✅ {len(df_to_load)} maisons insérées")


def main():
    print("📂 Lecture du CSV nettoyé...")
    df = pd.read_csv("data/processed/houses_clean.csv")

    print("🏘️  Chargement des quartiers...")
    mapping = load_neighborhoods(df)

    print("🏠 Chargement des maisons...")
    load_houses(df, mapping)

    # Vérification
    with engine.connect() as conn:
        n_houses = conn.execute(text("SELECT COUNT(*) FROM houses")).scalar()
        n_neigh = conn.execute(text("SELECT COUNT(*) FROM neighborhoods")).scalar()
    print(f"\n📊 Vérification finale :")
    print(f"   - {n_houses} maisons en base")
    print(f"   - {n_neigh} quartiers en base")


if __name__ == "__main__":
    main()