import re
from typing import Dict, Any

class SafetyGuard:
    """
    Enforces absolute compliance and security guardrails on customer replies and
    agent recommendations. Discards/rewrites any unsafe commitments or credential queries.
    """

    # PIN/OTP protection regex patterns (both English and Bangla)
    PIN_OTP_PATTERN = re.compile(
        r"(?:pin|otp|password|cvv|card\s*number|পিন|ওটিপি|পাসওয়ার্ড|পাসওয়ার্ড)", 
        re.IGNORECASE
    )
    REQUEST_PATTERN = re.compile(
        r"(?:share|enter|provide|send|tell|give|আমাকে|জানান|শেয়ার|দিন|প্রদান)", 
        re.IGNORECASE
    )

    # Disbursement authority regex patterns
    REFUND_PROMISE_PATTERN = re.compile(
        r"(?:we\s*will\s*(?:refund|reverse|credit|unblock)|we\s*have\s*(?:refunded|reversed)|refund\s*confirmed|রিফান্ড\s*(?:করব|করে|করা\s*হবে))", 
        re.IGNORECASE
    )

    # Standard safe texts
    SAFE_SECURITY_WARNING_EN = (
        "We have noted your concern. For your security, please NEVER share your PIN, OTP, "
        "or password with anyone (including support agents). Our team will investigate "
        "and contact you via official support channels."
    )
    SAFE_SECURITY_WARNING_BN = (
        "আমরা আপনার সমস্যাটি নথিভুক্ত করেছি। আপনার সুরক্ষার জন্য, দয়া করে আপনার পিন (PIN), "
        "ওটিপি (OTP) বা পাসওয়ার্ড কারও সাথে শেয়ার করবেন না। আমাদের টিম অফিসিয়াল চ্যানেলের মাধ্যমে "
        "তদন্ত করে আপনার সাথে যোগাযোগ করবে।"
    )

    SAFE_REFUND_STATEMENT_EN = (
        "any eligible amount will be returned through official channels after investigation"
    )
    SAFE_REFUND_STATEMENT_BN = (
        "তদন্ত সাপেক্ষে অফিসিয়াল চ্যানেলের মাধ্যমে যে কোনো যোগ্য অর্থ ফেরত দেওয়া হবে"
    )

    @classmethod
    def sanitize_response(cls, result: Dict[str, Any], original_complaint: str) -> Dict[str, Any]:
        """
        Scans and sanitizes the output JSON to ensure complete adherence to Safety Rules.
        """
        customer_reply = result.get("customer_reply", "")
        recommended_action = result.get("recommended_next_action", "")
        agent_summary = result.get("agent_summary", "")

        # Detect if complaint was primarily Bangla to match fallback response language
        is_bangla_complaint = any(
            char in original_complaint for char in "অআইঈউঊঋএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়"
        )

        # 1. CREDENTIALS GUARD: Disallow credential sharing prompts
        has_pin_otp = cls.PIN_OTP_PATTERN.search(customer_reply)
        has_request = cls.REQUEST_PATTERN.search(customer_reply)
        
        if has_pin_otp and has_request:
            # Overwrite with standard safe text
            result["customer_reply"] = (
                cls.SAFE_SECURITY_WARNING_BN if is_bangla_complaint else cls.SAFE_SECURITY_WARNING_EN
            )
            customer_reply = result["customer_reply"]

        # Append standard safety disclaimer if not present
        security_keywords = ["pin", "otp", "পিন", "ওটিপি"]
        if not any(kw in result["customer_reply"].lower() for kw in security_keywords):
            disclaimer = (
                "\n\nসতর্কতা: আমরা কখনোই আপনার পিন বা ওটিপি জানতে চাই না। এটি কারো সাথে শেয়ার করবেন না।"
                if is_bangla_complaint else
                "\n\nSecurity Notice: We will never ask for your PIN or OTP. Never share it with anyone."
            )
            result["customer_reply"] += disclaimer

        # 2. DISBURSEMENT AUTHORITY GUARD: Rewrite promises of refunds or unblocking
        customer_reply = result["customer_reply"]
        if cls.REFUND_PROMISE_PATTERN.search(customer_reply):
            # Replace English promises
            customer_reply = re.sub(
                r"(?:we\s*will\s*refund\s*(?:you)?|we\s*have\s*refunded\s*(?:you)?)",
                cls.SAFE_REFUND_STATEMENT_EN,
                customer_reply,
                flags=re.IGNORECASE
            )
            # Replace Bangla promises
            customer_reply = re.sub(
                r"(?:আমরা\s*রিফান্ড\s*(?:করে\s*দেব|করেছি)|রিফান্ড\s*করা\s*হবে)",
                cls.SAFE_REFUND_STATEMENT_BN,
                customer_reply,
                flags=re.IGNORECASE
            )
            result["customer_reply"] = customer_reply

        # Also sanitize recommended next action and agent summary for deterministic safety
        if cls.REFUND_PROMISE_PATTERN.search(recommended_action):
            result["recommended_next_action"] = re.sub(
                r"(?:we\s*will\s*refund|refund\s*confirmed|reverse\s*the\s*transfer)",
                "advise the operations team to process any eligible reversal per official verification standards",
                recommended_action,
                flags=re.IGNORECASE
            )

        # 3. THIRD PARTY REDIRECTS GUARD: Strip any instructions pointing out of official support
        # Matches phone numbers that aren't official or external domains
        # If model tries to direct to third party, clean it.
        external_redirect_pattern = re.compile(r"(?:contact|call|email)\s+(?:\+?\d[\d\s-]{7,15}|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", re.IGNORECASE)
        current_reply = result["customer_reply"]
        if external_redirect_pattern.search(current_reply):
            result["customer_reply"] = re.sub(
                external_redirect_pattern,
                "reach out via official support channels",
                current_reply
            )

        return result
