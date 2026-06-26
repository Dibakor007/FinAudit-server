from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# Strict literal definitions matching API specifications
EvidenceVerdict = Literal["consistent", "inconsistent", "insufficient_data"]

CaseType = Literal[
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "duplicate_payment",
    "merchant_settlement_delay",
    "agent_cash_in_issue",
    "phishing_or_social_engineering",
    "other"
]

Severity = Literal["low", "medium", "high", "critical"]

Department = Literal[
    "customer_support",
    "dispute_resolution",
    "payments_ops",
    "merchant_operations",
    "agent_operations",
    "fraud_risk"
]

class TicketResponse(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket ID matching the request payload")
    relevant_transaction_id: Optional[str] = Field(None, description="The matching transaction ID from the ledger, or null")
    evidence_verdict: EvidenceVerdict = Field(..., description="Calculated consistency verdict")
    case_type: CaseType = Field(..., description="Categorized case classification type")
    severity: Severity = Field(..., description="Triage priority level")
    department: Department = Field(..., description="Target routing operations department")
    agent_summary: str = Field(..., description="1-2 sentences precise summary of the ticket in English")
    recommended_next_action: str = Field(..., description="Operational instruction in English for the human agent")
    customer_reply: str = Field(..., description="Polite, secure response matched to customer's input language")
    human_review_required: bool = Field(..., description="Flag indicating if a human agent must verify the result")
    confidence: float = Field(0.9, description="AI/Reasoning confidence rating between 0.0 and 1.0")
    reason_codes: List[str] = Field(default_factory=list, description="Descriptive labels identifying analysis grounds")
