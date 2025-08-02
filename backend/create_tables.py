import dotenv
dotenv.load_dotenv()

from app.db.session import engine
from app.db.base import Base  # Shared Base

# Import all models so they are registered with Base
from app.db.models import event, user, email_summary

Base.metadata.create_all(bind=engine)
print("Tables created!")