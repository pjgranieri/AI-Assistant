import dotenv
dotenv.load_dotenv()

from app.db.session import engine
from app.db.models.event import Base  # Import Base from one of your model files

Base.metadata.create_all(bind=engine)
print("Tables created!")