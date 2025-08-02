import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api import email, event
from app.deps import get_db

app = FastAPI()

# Enable CORS (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(event.router)
app.include_router(email.router)

# Example endpoint using DB session dependency
@app.get("/health")
def health_check(db=Depends(get_db)):
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "API is running"}