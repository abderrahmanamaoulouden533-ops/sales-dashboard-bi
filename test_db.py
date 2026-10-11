import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        print("✅ Connexion PostgreSQL OK")
        print(f"   Version : {version[:60]}...")

        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )).fetchall()
        print(f"   Tables trouvées : {len(tables)}")
        for t in tables:
            print(f"     - {t[0]}")
except Exception as e:
    print(f"❌ Erreur : {e}")