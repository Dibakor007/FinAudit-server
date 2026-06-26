import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from app.models.request_models import Transaction

class TransactionMatcher:
    """
    Helper to deterministically parse customer complaint text for financial entities
    (amounts, phone numbers) and map them against ledger history.
    """
    
    @staticmethod
    def extract_amounts(text: str) -> List[float]:
        """Extracts potential monetary amounts from English and Bengali text."""
        # Standard English decimals/numbers and Bengali numerals
        # Matches numbers like 5000, 5,000, 500.50, etc.
        cleaned_text = text.replace(",", "")
        
        # Translate Bengali numerals to English numerals for parsing
        bengali_digits = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}
        for b_char, e_char in bengali_digits.items():
            cleaned_text = cleaned_text.replace(b_char, e_char)
            
        # Regex to find numbers
        matches = re.findall(r'\b\d+(?:\.\d+)?\b', cleaned_text)
        amounts = []
        for m in matches:
            try:
                val = float(m)
                # Ignore very small numbers like times, hours, dates, or small fractions
                if val >= 10.0:
                    amounts.append(val)
            except ValueError:
                continue
        return list(set(amounts))

    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extracts potential 11-digit or international formatted mobile numbers."""
        # Matches standard Bangladeshi numbers like 01712345678, +88017... etc.
        # Also supports Bengali digits
        cleaned_text = text
        bengali_digits = {'০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'}
        for b_char, e_char in bengali_digits.items():
            cleaned_text = cleaned_text.replace(b_char, e_char)
            
        # Clean spacing around symbols
        cleaned_text = re.sub(r'[\s\-()]+', '', cleaned_text)
        
        # Match pattern: 013-019 (11 digits) or with +88 prefix (13/14 digits)
        matches = re.findall(r'(?:\+?88)?01[3-9]\d{8}\b', cleaned_text)
        
        # Standardize matching to the last 11 digits to ensure easy comparisons
        standardized = []
        for m in matches:
            if len(m) >= 11:
                standardized.append(m[-11:])
        return list(set(standardized))

    @classmethod
    def match_transaction(
        cls, 
        complaint: str, 
        history: List[Transaction]
    ) -> Tuple[Optional[Transaction], List[str]]:
        """
        Main matching engine.
        Returns the matched transaction and list of matching reason codes.
        """
        if not history:
            return None, ["no_transaction_history"]

        amounts = cls.extract_amounts(complaint)
        phones = cls.extract_phone_numbers(complaint)
        
        matches = []
        reason_codes = []
        
        # Strategy 1: Exact Amount and Phone Number Match
        for tx in history:
            tx_amount = float(tx.amount)
            # Normalize tx counterparty phone
            tx_phone = re.sub(r'\D', '', tx.counterparty)
            if len(tx_phone) >= 11:
                tx_phone = tx_phone[-11:]
                
            amount_match = any(abs(tx_amount - amt) < 1.0 for amt in amounts)
            phone_match = any(tx_phone == p for p in phones)
            
            if amount_match and phone_match:
                matches.append((tx, 3))  # Weight 3 for both matching
                
        # Strategy 2: Match by exact amount only
        if not matches:
            for tx in history:
                tx_amount = float(tx.amount)
                if any(abs(tx_amount - amt) < 1.0 for amt in amounts):
                    matches.append((tx, 2))  # Weight 2 for amount match
                    
        # Strategy 3: Match by counterparty phone only
        if not matches:
            for tx in history:
                tx_phone = re.sub(r'\D', '', tx.counterparty)
                if len(tx_phone) >= 11:
                    tx_phone = tx_phone[-11:]
                if any(tx_phone == p for p in phones):
                    matches.append((tx, 1))  # Weight 1 for phone match

        if not matches:
            return None, ["no_transaction_match_found"]

        # Sort matches by weight (highest score first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Ambiguity check: if multiple distinct transactions have the same highest weight,
        # we cannot safely auto-resolve, and must flag it as ambiguous.
        highest_weight = matches[0][1]
        candidates = [m[0] for m in matches if m[1] == highest_weight]
        
        if len(candidates) > 1:
            return None, ["ambiguous_multiple_matches"]

        best_tx = candidates[0]
        
        # Gather matching reasons
        if highest_weight == 3:
            reason_codes.append("exact_amount_and_recipient_match")
        elif highest_weight == 2:
            reason_codes.append("amount_only_match")
        elif highest_weight == 1:
            reason_codes.append("recipient_only_match")
            
        return best_tx, reason_codes
