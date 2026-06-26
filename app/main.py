from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.routes import router as api_router
from app.core.logging import logger

app = FastAPI(
    title="FinAudit Investigator API",
    description="AI-Powered Fintech Support Ticket Analysis & Automated Ledger Audit API",
    version="1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Root endpoint
@app.get("/")
def root():
    return {
        "name": "FinAudit Investigator API",
        "version": "1.0",
        "docs": "/docs",
        "endpoints": ["GET /health", "POST /analyze-ticket"]
    }

# Register API routers
app.include_router(api_router)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Standardizes request validation exceptions to output clean 422 JSON objects
    while maintaining logging oversight.
    """
    errors = exc.errors()
    log_msg = f"Request validation failed for {request.url.path}: {errors}"
    logger.warning(log_msg)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Unprocessable Entity",
            "detail": errors,
            "message": "Input validation failed. Check request schema parameters."
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled system exceptions to prevent secret exposure
    or raw traceback leaks.
    """
    logger.critical(f"Unhandled critical system error at {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An internal system error occurred. Please try again later."
        }
    )
