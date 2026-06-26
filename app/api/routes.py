import time
import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.models.request_models import TicketRequest
from app.models.response_models import TicketResponse
from app.services.ai_service import AIService

router = APIRouter()

# Simple Dependency Injector for AIService
def get_ai_service() -> AIService:
    try:
        return AIService()
    except Exception as e:
        logger.error(f"Failed to initialize AIService: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Fintech analysis service credentials are misconfigured on the server."
        )

@router.get("/health", status_code=200)
def health_check():
    """Endpoint for continuous deployment readiness/liveness checks."""
    return {"status": "ok"}

@router.post(
    "/analyze-ticket", 
    response_model=TicketResponse, 
    status_code=200,
    responses={
        400: {"description": "Malformed JSON structure"},
        422: {"description": "Validation errors or blank complaints"},
        500: {"description": "Internal server/model errors"}
    }
)
def analyze_ticket(
    payload: TicketRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Ingests and audits natural language digital finance complaints, cross-referencing
    against transaction histories to produce structured, safe Operational JSON answers.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Received ticket analysis request for ticket {payload.ticket_id}",
        extra={
            "request_id": request_id,
            "ticket_id": payload.ticket_id,
            "complaint_len": len(payload.complaint)
        }
    )

    try:
        # Run combined deterministic & AI assessment
        result = ai_service.analyze_complaint(payload)
        
        latency = time.time() - start_time
        logger.info(
            f"Successfully processed ticket {payload.ticket_id}",
            extra={
                "request_id": request_id,
                "ticket_id": payload.ticket_id,
                "latency": f"{latency:.3f}s"
            }
        )
        return result
        
    except HTTPException as http_exc:
        # Re-raise standard FastAPI HTTP exceptions
        raise http_exc
    except Exception as exc:
        latency = time.time() - start_time
        logger.error(
            f"Unexpected error processing ticket {payload.ticket_id}: {str(exc)}",
            extra={
                "request_id": request_id,
                "ticket_id": payload.ticket_id,
                "latency": f"{latency:.3f}s"
            }
        )
        # Protect internal stack traces per Section 1 specifications
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while analyzing the ticket evidence."
        )
