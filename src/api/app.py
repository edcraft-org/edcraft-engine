from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import question_generation

# Create FastAPI app
app = FastAPI(
    title="EdCraft Backend API",
    description="API for EdCraft Backend Services",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(question_generation.router)

@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "Edcraft API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
