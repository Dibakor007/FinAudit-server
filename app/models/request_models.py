from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class Transaction(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ledger reference")
    timestamp: str = Field(..., description="ISO-8601 transaction execution time")
    type: str = Field(..., description="Type of transaction, e.g., transfer, payment, cash_in")
    amount: float = Field(..., description="Financial amount of transaction")
    counterparty: str = Field(..., description="Destination account or party of transaction")
    status: str = Field(..., description="Ledger status of transaction (completed, failed, pending)")

class TicketRequest(BaseModel):
    ticket_id: str = Field(..., description="Customer-facing ticket or case reference")
    complaint: str = Field(..., description="Raw natural language text complaint from the user")
    language: Optional[str] = Field("en", description="Detected or declared customer language")
    channel: Optional[str] = Field("in_app_chat", description="Submission channel (e.g., in_app_chat, email, web)")
    user_type: Optional[str] = Field("customer", description="User segment (e.g., customer, merchant, agent)")
    campaign_context: Optional[str] = Field(None, description="Campaign identifier context if applicable")
    transaction_history: Optional[List[Transaction]] = Field(default_factory=list, description="Array of ledger entries")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional contextual metadata key-values")

    @field_validator("complaint")
    @classmethod
    def validate_complaint_not_blank(cls, val: str) -> str:
        """Enforces HTTP 422 for semantically empty complaints."""
        if not val or not val.strip():
            raise ValueError("complaint cannot be empty or blank.")
        return val
