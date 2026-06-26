from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from app.models.request_models import TicketRequest, Transaction
from app.services.transaction_matcher import TransactionMatcher

class ReasoningEngine:
    """
    Core deterministic rule executor. This is the single source of truth for
    classification, severity, department, evidence_verdict, and human_review_required.
    """

    @classmethod
    def evaluate(
        cls, 
        payload: TicketRequest
    ) -> Tuple[str, Optional[str], bool, List[str]]:
        """
        Calculates the consistency verdict and checks for human routing criteria.
        Returns:
            evidence_verdict: "consistent" | "inconsistent" | "insufficient_data"
            relevant_transaction_id: str | None
            human_review_required: bool
            reason_codes: list of strings
        """
        history = payload.transaction_history or []
        complaint = payload.complaint.lower()
        
        # 1. Map target transaction
        matched_tx, matcher_codes = TransactionMatcher.match_transaction(complaint, history)
        
        verdict = "insufficient_data"
        relevant_tx_id = matched_tx.transaction_id if matched_tx else None
        human_review = False
        reason_codes = list(matcher_codes)

        # 2. Insufficient Data Cases
        if not matched_tx:
            verdict = "insufficient_data"
            # Ambiguity or empty history means we must require human eyes
            if "ambiguous_multiple_matches" in reason_codes:
                human_review = True
                reason_codes.append("ambiguity_requires_review")
            else:
                reason_codes.append("empty_or_no_matching_ledger")
                
            # If complaint indicates phishing or fraud, escalate immediately regardless of history
            if any(term in complaint for term in ["otp", "pin", "password", "hack", "phish", "পিন", "ওটিপি", "পাসওয়ার্ড"]):
                human_review = True
                reason_codes.append("suspicious_phishing_context")
                
            return verdict, relevant_tx_id, human_review, reason_codes

        # 3. Established Pattern Checker (Wrong Transfer Inconsistencies)
        # If user claims they sent money to a wrong number, but ledger shows multiple
        # successful prior transactions to this exact counterparty, it is inconsistent.
        is_dispute = any(term in complaint for term in ["wrong", "ভুল", "dispute", "অন্য নাম্বারে"])
        if is_dispute:
            target_party = matched_tx.counterparty
            past_txs = [
                tx for tx in history 
                if tx.counterparty == target_party 
                and tx.transaction_id != matched_tx.transaction_id
                and tx.status == "completed"
            ]
            if len(past_txs) >= 2:
                verdict = "inconsistent"
                human_review = True
                reason_codes.append("established_recipient_pattern_found")
                return verdict, relevant_tx_id, human_review, reason_codes

        # 4. Failed Transaction Claims
        is_failed_claim = any(term in complaint for term in ["failed", "not received", "deducted", "ব্যর্থ", "কেটে নিয়েছে", "পৌঁছায়নি"])
        if is_failed_claim:
            if matched_tx.status in ["failed", "pending"]:
                verdict = "consistent"
                reason_codes.append("claim_matches_failed_status")
            elif matched_tx.status == "completed":
                # User claims failed payment, but ledger shows completed success
                verdict = "inconsistent"
                human_review = True
                reason_codes.append("claim_contradicts_completed_status")
            return verdict, relevant_tx_id, human_review, reason_codes

        # 5. Duplicate Payment Checks
        # User claims double charging. Let's look for transactions to same counterparty
        # with matching amount within 15 minutes of the matched transaction.
        is_duplicate_claim = any(term in complaint for term in ["duplicate", "double", "দুইবার", "ডাবল"])
        if is_duplicate_claim:
            duplicates = []
            try:
                # Approximate parsing of standard ISO datetime formats
                t1 = datetime.fromisoformat(matched_tx.timestamp.replace("Z", "+00:00"))
                for tx in history:
                    if tx.transaction_id == matched_tx.transaction_id:
                        continue
                    if tx.counterparty == matched_tx.counterparty and abs(tx.amount - matched_tx.amount) < 0.01:
                        t2 = datetime.fromisoformat(tx.timestamp.replace("Z", "+00:00"))
                        if abs((t1 - t2).total_seconds()) <= 900:  # 15 minutes
                            duplicates.append(tx)
            except Exception:
                pass

            if duplicates:
                verdict = "consistent"
                reason_codes.append("duplicate_transactions_detected")
            else:
                verdict = "inconsistent"
                human_review = True
                reason_codes.append("no_duplicate_found_in_timeframe")
            return verdict, relevant_tx_id, human_review, reason_codes

        # 6. Default Fallback
        # If we matched a clean transaction with no contradictions, it is consistent.
        verdict = "consistent"
        reason_codes.append("basic_transaction_match")
        
        # Wrong transfer dispute tickets always require manual review per rule 1
        if is_dispute:
            human_review = True
            reason_codes.append("dispute_requires_human_negotiation")

        return verdict, relevant_tx_id, human_review, reason_codes


    @classmethod
    def determine_routing(
        cls, 
        case_type: str, 
        verdict: str
    ) -> Tuple[str, str]:
        """
        Determines the appropriate severity and department routing.
        """
        # Default mapping logic
        severity = "medium"
        department = "customer_support"

        if case_type == "phishing_or_social_engineering":
            severity = "critical"
            department = "fraud_risk"
        elif case_type == "wrong_transfer":
            severity = "high"
            department = "dispute_resolution"
        elif case_type in ["payment_failed", "duplicate_payment"]:
            severity = "high"
            department = "payments_ops"
        elif case_type == "merchant_settlement_delay":
            severity = "medium"
            department = "merchant_operations"
        elif case_type == "agent_cash_in_issue":
            severity = "high"
            department = "agent_operations"
        elif case_type == "refund_request":
            severity = "low"
            department = "customer_support"

        # Escalate department/severity if verdict is contradictory
        if verdict == "inconsistent" and severity != "critical":
            severity = "high"
            if case_type == "phishing_or_social_engineering":
                department = "fraud_risk"
            elif case_type not in ("wrong_transfer", "payment_failed", "duplicate_payment",
                                   "merchant_settlement_delay", "agent_cash_in_issue"):
                department = "customer_support"
            # else: keep the department already determined above

        return severity, department
