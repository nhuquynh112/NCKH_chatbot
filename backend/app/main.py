from fastapi import FastAPI

app = FastAPI(
    title="AI Customer Service Chatbot"
)


@app.get("/")
def home():

    return {
        "message": "Chatbot backend is running"
    }