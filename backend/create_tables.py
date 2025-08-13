import dotenv
dotenv.load_dotenv()

from app.db.session import engine
from app.db.base import Base
from sqlalchemy import text

# Import all models so they are registered with Base
from app.db.models import event, user, email_summary, user_token
from app.db.models.plan import Plan

# Enable pgvector extension
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    print("✅ pgvector extension enabled")
except Exception as e:
    print(f"❌ Failed to enable pgvector: {e}")
    print("   Make sure PostgreSQL has the vector extension installed")

metadata = [
    event.__table__,
    user.__table__,
    email_summary.__table__,
    user_token.__table__,
    Plan.__table__,
]

Base.metadata.create_all(bind=engine)
print("✅ Tables created with vector support!")