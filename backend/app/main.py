from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import products, faqs, tickets, chat, auth
from app.database import engine, Base
import app.models  # Ensure models are loaded before creating tables

# Tự động tạo bảng trong DB nếu chưa có
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Customer Service Chatbot"
)

# Thêm CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi domain (cần sửa lại lúc deploy)
    allow_credentials=True,
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