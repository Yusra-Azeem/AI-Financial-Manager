from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Financial Manager API",
    version="1.0.0"
)

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to AI Financial Manager API",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {
        "success": True,
        "service": "Backend",
        "status": "Healthy"
    }


@app.get("/api/v1")
def api_info():
    return {
        "project": "AI Financial Manager",
        "theme": "Agentic AI & Emerging Tech",
        "version": "1.0.0"
    }

 //remove dummy code