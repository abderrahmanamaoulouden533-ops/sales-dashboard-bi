"""
Nettoyage du dataset House Prices (Kaggle).
Entrée  : data/raw/train.csv
Sortie  : data/processed/houses_clean.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw/train.csv")
PROCESSED_PATH = Path("data/processed/houses_clean.csv")


def load_data(path: Path) -> pd.DataFrame:
    """Charge le dataset brut."""
    df = pd.read_csv(path)
    print(f"📊 Dataset chargé : {df.shape[0]} lignes, {df.shape[1]} colonnes")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Traite les valeurs manquantes selon leur signification."""
    none_cols = [
        'Alley', 'BsmtQual', 'BsmtCond', 'BsmtExposure', 'BsmtFinType1',
        'BsmtFinType2', 'FireplaceQu', 'GarageType', 'GarageFinish',
        'GarageQual', 'GarageCond', 'PoolQC', 'Fence', 'MiscFeature'
    ]
    for col in none_cols:
        if col in df.columns:
            df[col] = df[col].fillna('None')

    zero_cols = [
        'GarageYrBlt', 'GarageArea', 'GarageCars',
        'BsmtFinSF1', 'BsmtFinSF2', 'BsmtUnfSF', 'TotalBsmtSF',
        'BsmtFullBath', 'BsmtHalfBath', 'MasVnrArea'
    ]
    for col in zero_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    if 'LotFrontage' in df.columns:
        df['LotFrontage'] = df.groupby('Neighborhood')['LotFrontage'] \
                              .transform(lambda x: x.fillna(x.median()))

    cat_cols = df.select_dtypes(include=['object']).columns
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0])

    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    return df


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Crée des features utiles pour l'analyse."""
    df['HouseAge'] = df['YrSold'] - df['YearBuilt']
    df['RemodAge'] = df['YrSold'] - df['YearRemodAdd']
    df['TotalSF'] = df['TotalBsmtSF'] + df['1stFlrSF'] + df['2ndFlrSF']
    df['TotalBath'] = (df['FullBath'] + 0.5 * df['HalfBath'] +
                       df['BsmtFullBath'] + 0.5 * df['BsmtHalfBath'])
    df['PricePerSF'] = df['SalePrice'] / df['TotalSF'].replace(0, np.nan)
    df['HasGarage'] = (df['GarageArea'] > 0).astype(int)
    df['HasPool'] = (df['PoolArea'] > 0).astype(int)
    df['HasFireplace'] = (df['Fireplaces'] > 0).astype(int)
    return df


def main():
    df = load_data(RAW_PATH)

    missing_before = df.isnull().sum().sum()
    print(f"🔍 Valeurs manquantes avant : {missing_before}")

    df = handle_missing_values(df)
    df = create_derived_features(df)

    missing_after = df.isnull().sum().sum()
    print(f"✅ Valeurs manquantes après : {missing_after}")

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)
    print(f"💾 Fichier sauvegardé : {PROCESSED_PATH}")
    print(f"📐 Dimensions finales : {df.shape[0]} lignes × {df.shape[1]} colonnes")


if __name__ == "__main__":
    main()