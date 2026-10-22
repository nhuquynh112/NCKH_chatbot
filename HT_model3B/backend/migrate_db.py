import os
from dotenv import load_dotenv
import psycopg2

# Tải cấu hình từ .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    print("Không tìm thấy DATABASE_URL trong file .env")
    exit(1)

try:
    # Kết nối đến DB
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Kiểm tra xem cột title đã tồn tại chưa
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='chat_sessions' AND column_name='title';
    """)
    result = cursor.fetchone()
    
    if not result:
        print("Adding column 'title' to table 'chat_sessions'...")
        cursor.execute("ALTER TABLE chat_sessions ADD COLUMN title VARCHAR(255) DEFAULT 'New Chat';")
        print("Column added successfully!")
    else:
        print("Column 'title' already exists in 'chat_sessions'.")
        
except Exception as e:
    print(f"Error occurred: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
