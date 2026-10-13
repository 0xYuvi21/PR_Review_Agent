from fastapi import FastAPI
import uvicorn
from src.webhook_receiver.router import router as webhook_router

app = FastAPI(title="PR Review Agent API")

app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
