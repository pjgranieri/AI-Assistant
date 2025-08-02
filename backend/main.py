import dotenv
dotenv.load_dotenv()
import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import email, event, auth
from app.deps import get_db

app = FastAPI()

# Add SessionMiddleware with a simple secret key for development
app.add_middleware(SessionMiddleware, secret_key="my-simple-secret-key-for-development")

# Enable CORS - UPDATE THE PORT HERE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],  # <-- Changed from 3000 to 5174
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(email.router)
app.include_router(event.router)
app.include_router(auth.router)

@app.get("/health")
def health_check(db=Depends(get_db)):
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "API is running"}