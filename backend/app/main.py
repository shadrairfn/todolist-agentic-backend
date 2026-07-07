import sys
import os

# Tambahkan direktori 'backend' ke Python path agar modul 'app' terdeteksi secara otomatis
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import create_db_and_tables
from app.api.label_api import router as labels_router
from app.api.project_api import router as projects_router
from app.api.todo_api import router as todos_router 
from app.api.user_api import router as user_router
from app.api.agentic_ai_api import router as agentic_ai_router

app = FastAPI(
    title="Premium ToDo List API",
    description="FastAPI + SQLModel + PostgreSQL ToDo List Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Sesuaikan dengan port yang digunakan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    from app.core.config import settings

    if settings.AUTO_CREATE_TABLES:
        create_db_and_tables()

@app.get("/api/health")
def read_root():
    return {
        "status": "online",
        "message": "FastAPI is successfully connected to your PostgreSQL database!"
    }

app.include_router(todos_router)
app.include_router(projects_router)
app.include_router(labels_router)
app.include_router(user_router)
app.include_router(agentic_ai_router)

# app.mount("/", StaticFiles(directory="frontend-react", html=True), name="frontend") # Sesuaikan direktori frontendnya
