import pytest
from app.models.request_models import TicketRequest, Transaction
from app.services.transaction_matcher import TransactionMatcher
from app.services.reasoning_engine import ReasoningEngine
from app.services.safety_guard import SafetyGuard

def test_extract_amounts():
    # Test English and Bengali numbers
    text_en = "I lost 5000 Taka and another 250.50 amount."
    text_bn = "আমি ৫০০০ টাকা এবং ২৫০.৫০ টাকা হারিয়েছি।"
    
    assert 5000.0 in TransactionMatcher.extract_amounts(text_en)
    assert 250.50 in TransactionMatcher.extract_amounts(text_en)
    
    assert 5000.0 in TransactionMatcher.extract_amounts(text_bn)
    assert 250.50 in TransactionMatcher.extract_amounts(text_bn)

def test_extract_phone_numbers():
    text = "Please refund to my wrong send recipient 01712345678 or +8801987654321."
    phones = TransactionMatcher.extract_phone_numbers(text)
    
    assert "01712345678" in phones
    assert "01987654321" in phones

def test_transaction_matcher_exact_match():
    history = [
        Transaction(
            transaction_id="TXN-001",
            timestamp="2026-06-26T12:00:00Z",
            type="transfer",
            amount=1500.0,
            counterparty="+8801711112222",
            status="completed"
        )
    ]
    # Complaint mentions both amount and number
    complaint = "Sent 1500 to 01711112222 but it was wrong"
    tx, codes = TransactionMatcher.match_transaction(complaint, history)
    
    assert tx is not None
    assert tx.transaction_id == "TXN-001"
    assert "exact_amount_and_recipient_match" in codes

def test_reasoning_engine_empty_history():
    payload = TicketRequest(
        ticket_id="TKT-ENG-001",
        complaint="I lost my money on a payment.",
        transaction_history=[]
    )
    verdict, tx_id, review, codes = ReasoningEngine.evaluate(payload)
    
    assert verdict == "insufficient_data"
    assert tx_id is None
    assert "empty_or_no_matching_ledger" in codes

def test_reasoning_engine_established_pattern_inconsistent():
    # Regular past payments to this recipient contradicts "wrong transfer" claim
    history = [
        Transaction(transaction_id="TXN-1", timestamp="2026-06-01T10:00:00Z", type="transfer", amount=1000.0, counterparty="01711112222", status="completed"),
        Transaction(transaction_id="TXN-2", timestamp="2026-06-15T10:00:00Z", type="transfer", amount=2000.0, counterparty="01711112222", status="completed"),
        Transaction(transaction_id="TXN-3", timestamp="2026-06-26T10:00:00Z", type="transfer", amount=1500.0, counterparty="01711112222", status="completed")
    ]
    payload = TicketRequest(
        ticket_id="TKT-002",
        complaint="ভুল করে ০১৭১১১১২২২২ নাম্বারে ১৫০০ টাকা পাঠিয়েছি। ফেরত দিন।",
        transaction_history=history
    )
    verdict, tx_id, review, codes = ReasoningEngine.evaluate(payload)
    
    assert verdict == "inconsistent"
    assert tx_id == "TXN-3"
    assert review is True
    assert "established_recipient_pattern_found" in codes

def test_reasoning_engine_duplicate_payment():
    # Two identical transactions within 10 minutes (duplicate)
    history = [
        Transaction(transaction_id="TXN-1", timestamp="2026-06-26T14:00:00Z", type="payment", amount=500.0, counterparty="01811112222", status="completed"),
        Transaction(transaction_id="TXN-2", timestamp="2026-06-26T14:05:00Z", type="payment", amount=500.0, counterparty="01811112222", status="completed")
    ]
    payload = TicketRequest(
        ticket_id="TKT-003",
        complaint="I was double charged! 500 taka was sent twice.",
        transaction_history=history
    )
    verdict, tx_id, review, codes = ReasoningEngine.evaluate(payload)
    
    assert verdict == "consistent"
    assert tx_id in ["TXN-1", "TXN-2"]
    assert "duplicate_transactions_detected" in codes

def test_safety_guard_pin_otp_leak():
    unsafe_response = {
        "customer_reply": "Please send us your OTP or enter your PIN to verify this refund request.",
        "recommended_next_action": "Ask for verification code.",
        "agent_summary": "User needs verification."
    }
    sanitized = SafetyGuard.sanitize_response(unsafe_response, "I want a refund")
    
    # Assert credentials are secure and standard warning is injected
    assert "NEVER share" in sanitized["customer_reply"]
    assert "OTP" in sanitized["customer_reply"]

def test_safety_guard_unauthorized_promise():
    unsafe_response = {
        "customer_reply": "We will refund you immediately for this duplicate charge.",
        "recommended_next_action": "refund the transfer",
        "agent_summary": "Charge refunded"
    }
    sanitized = SafetyGuard.sanitize_response(unsafe_response, "I was double charged")
    
    assert "any eligible amount will be returned through official channels after investigation" in sanitized["customer_reply"]
    assert "advise the operations team to process" in sanitized["recommended_next_action"]

def test_safety_guard_third_party_redirect():
    unsafe_response = {
        "customer_reply": "Please contact the merchant immediately at help@merchant.com or call +8801234567.",
        "recommended_next_action": "Refer client to merchant.",
        "agent_summary": "Redirect to external support."
    }
    sanitized = SafetyGuard.sanitize_response(unsafe_response, "The merchant didn't deliver my product.")
    
    assert "reach out via official support channels" in sanitized["customer_reply"]
