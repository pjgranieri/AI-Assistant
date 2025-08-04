import dotenv
dotenv.load_dotenv()

from app.db.session import engine
from app.db.base import Base
from sqlalchemy import text

# Import all models so they are registered with Base
from app.db.models import event, user, email_summary, user_token

# Enable pgvector extension
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    print("✅ pgvector extension enabled")
except Exception as e:
    print(f"❌ Failed to enable pgvector: {e}")
    print("   Make sure PostgreSQL has the vector extension installed")

Base.metadata.create_all(bind=engine)
print("✅ Tables created with vector support!")