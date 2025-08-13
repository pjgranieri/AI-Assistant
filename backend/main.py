import dotenv
dotenv.load_dotenv()
import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import email, event, auth, ai_assistant, gmail  # Add gmail import
from app.deps import get_db
from app.api.planner import router as planner_router

app = FastAPI()

# Add SessionMiddleware with a simple secret key for development
app.add_middleware(SessionMiddleware, secret_key="my-simple-secret-key-for-development")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(email.router, prefix="/api", tags=["emails"])
app.include_router(gmail.router, prefix="/api", tags=["gmail"])  # Add Gmail router
app.include_router(event.router, tags=["events"])
app.include_router(ai_assistant.router, prefix="/ai", tags=["ai"])
app.include_router(planner_router, prefix="/planner", tags=["planner"])

@app.get("/health")
def health_check(db=Depends(get_db)):
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to see all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods)
            })
    return {"routes": routes}