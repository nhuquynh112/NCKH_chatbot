# TechCare Electronics Customer Support Chatbot

Đây là đồ án xây dựng chatbot hỗ trợ chăm sóc khách hàng cho website bán thiết bị điện tử.

## System Architecture

```text
                         Người dùng
                              │
                              ▼
                    Website (React Frontend)
                              │
                              ▼
                    FastAPI Backend Server
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
 PostgreSQL             ChromaDB              Ollama
(Data Server)      (Vector Database)     (AI Server - Qwen2.5:3B)
        │                     ▲                     │
        │                     │                     │
        └──────────────┐      │      ┌──────────────┘
                       ▼      │      ▼
                 Export dữ liệu      Embedding
            (Product, FAQ, KB)       (nomic-embed-text)
                       │             │
                       └─────────────┘
                             RAG Pipeline
```

---

# Hướng dẫn cài đặt và chạy hệ thống

## Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Ollama

---

## 1. Clone project

```bash
git clone <repository_url>
cd <project_folder>
```

---

## 2. Cài đặt Backend

```bash
cd backend
pip install -r requirements.txt
```

---

## 3. Cài đặt Frontend

```bash
cd frontend
npm install
```

---

## 4. Cấu hình môi trường

Sao chép file `.env.example` thành `.env`.

### Backend

```bash
cp backend/.env.example backend/.env
```

### Frontend

```bash
cp frontend/.env.example frontend/.env
```

Sau đó cập nhật các giá trị phù hợp với môi trường của bạn.

## 5. Cài đặt AI Models

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Khởi động Ollama trước khi chạy Backend.

---

## 6. Xây dựng cơ sở dữ liệu RAG

```bash
python export_rag.py
python rebuild_rag.py
```

---

## 7. Chạy Backend

```bash
cd backend
uvicorn app.main:app --reload
```

Backend mặc định:

```
http://127.0.0.1:8000
```

---

## 8. Chạy Frontend

```bash
cd frontend
npm run dev
```

Frontend mặc định:

```
http://localhost:5173
```

---

# Lưu ý

- Sau khi thay đổi dữ liệu trong thư mục `rag_data`, cần rebuild lại cơ sở dữ liệu vector:

```bash
python export_rag.py
python rebuild_rag.py
```

- Đảm bảo Ollama đang chạy trước khi khởi động Backend.

- Nếu đây là lần chạy đầu tiên, hãy pull đầy đủ hai model:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

## License

This project is developed for academic purposes.
