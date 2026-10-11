-- Table de dimension : quartiers
CREATE TABLE IF NOT EXISTS neighborhoods (
    neighborhood_id SERIAL PRIMARY KEY,
    neighborhood_name VARCHAR(100) UNIQUE NOT NULL
);

-- Table principale : maisons
CREATE TABLE IF NOT EXISTS houses (
    house_id SERIAL PRIMARY KEY,
    mssubclass INTEGER,
    mszoning VARCHAR(10),
    lotfrontage NUMERIC(6,1),
    lotarea INTEGER,
    street VARCHAR(20),
    lotshape VARCHAR(10),
    landcontour VARCHAR(20),
    neighborhood_id INTEGER REFERENCES neighborhoods(neighborhood_id),
    housestyle VARCHAR(30),
    overallqual INTEGER,
    overallcond INTEGER,
    yearbuilt INTEGER,
    yearremodadd INTEGER,
    roofstyle VARCHAR(20),
    exterior1st VARCHAR(30),
    masvnrarea NUMERIC(8,1),
    bsmtqual VARCHAR(10),
    totalbsmtsf INTEGER,
    firstflrsf INTEGER,
    secondflrsf INTEGER,
    grlivarea INTEGER,
    fullbath INTEGER,
    halfbath INTEGER,
    bedroomabvgr INTEGER,
    kitchenabvgr INTEGER,
    totrmsabvgrd INTEGER,
    fireplaces INTEGER,
    garagecars INTEGER,
    garagearea NUMERIC(8,1),
    wooddecksf INTEGER,
    openporchsf INTEGER,
    saleprice INTEGER NOT NULL,
    house_age INTEGER,
    remod_age INTEGER,
    total_sf INTEGER,
    total_bath NUMERIC(4,1),
    price_per_sf NUMERIC(10,2),
    has_garage INTEGER,
    has_pool INTEGER,
    has_fireplace INTEGER
);

-- Index pour les requêtes analytiques
CREATE INDEX IF NOT EXISTS idx_houses_neighborhood ON houses(neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_houses_saleprice ON houses(saleprice);
CREATE INDEX IF NOT EXISTS idx_houses_yearbuilt ON houses(yearbuilt);