from contextlib import asynccontextmanager
import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.routers import products, faqs, tickets, chat, auth
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.rag.embedding import OllamaClient, OllamaError
from app.middleware.rate_limit import RateLimitMiddleware
import app.models  # Ensure models are loaded before creating tables
from seed import seed

# Tự động tạo bảng trong DB nếu chưa có
Base.metadata.create_all(bind=engine)
if settings.AUTO_SEED:
    seed()

logger = logging.getLogger(__name__)


def _warm_ai_model() -> None:
    try:
        OllamaClient(
            settings.ollama_base_url,
            settings.chat_model,
            settings.embedding_model,
        ).warm_up()
        logger.info("Ollama chat model is warm")
    except OllamaError as exc:
        logger.warning("Could not warm Ollama model: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.WARM_AI_ON_STARTUP:
        threading.Thread(target=_warm_ai_model, daemon=True).start()
    yield


app = FastAPI(title="AI Customer Service Chatbot", lifespan=lifespan)

app.add_middleware(
    RateLimitMiddleware,
    chat_limit=settings.CHAT_RATE_LIMIT_PER_MINUTE,
    login_limit=settings.LOGIN_RATE_LIMIT_PER_MINUTE,
)
# Add CORS last so even rate-limit errors include browser CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],  # Cho phép mọi method (GET, POST, PUT, DELETE,...)
    allow_headers=["*"],  # Cho phép mọi header
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(faqs.router)
app.include_router(tickets.router)
app.include_router(chat.router)

@app.get("/")
def home():
    return {
        "message": "Chatbot backend is running"
    }


@app.get("/health")
def health():
    return {"status": "ok", "vector_store": settings.vector_store_backend}


@app.get("/ready")
def readiness():
    """Report dependency health without making the lightweight liveness check slow."""
    database_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database_ok = True
    except Exception as exc:
        logger.error("Database readiness check failed: %s", exc)

    ai_ok = OllamaClient(
        settings.ollama_base_url,
        settings.chat_model,
        settings.embedding_model,
    ).is_available()
    return {
        "status": "ready" if database_ok and ai_ok else "degraded",
        "database": "ok" if database_ok else "unavailable",
        "ai": "ok" if ai_ok else "unavailable",
        "deterministic_answers_available": database_ok,
        "vector_store": settings.vector_store_backend,
    }
