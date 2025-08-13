import dotenv
dotenv.load_dotenv()

from app.db.session import engine
from app.db.models.user import User
from app.db.models.event import Event
from app.db.models.plan import Plan
# ... import other models as needed ...

from sqlalchemy import MetaData

metadata = MetaData()
tables = [
    User.__table__,
    Event.__table__,
    Plan.__table__,
    # ... add other model tables here ...
]

for table in tables:
    table.create(bind=engine, checkfirst=True)

print("✅ Tables created")