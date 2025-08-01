from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api import email, event, user
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
app.include_router(email.router, prefix="/email", tags=["email"])
app.include_router(event.router, prefix="/event", tags=["event"])
app.include_router(user.router, prefix="/user", tags=["user"])

# Example endpoint using DB session dependency
@app.get("/health")
def health_check(db=Depends(get_db)):
    return {"status": "ok"} 