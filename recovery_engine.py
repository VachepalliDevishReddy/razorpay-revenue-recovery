import json
import os
import time
import razorpay
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Initialize API Clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

try:
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
except Exception:
    razorpay_client = None


def diagnose_failure(txn):
    """
    Evaluates failure telemetry, predicts recovery probability,
    and assigns an orchestration strategy (SEND_LINK, RETRY_NOW, RETRY_LATER, SUPPRESS).
    """
    prompt = f"""
You are an expert AI Payment Operations and Revenue Recovery Agent.
Analyze the following failed transaction telemetry and predict recovery viability:
Transaction ID: {txn.get('id')}
Customer: {txn.get('customer_name')} ({txn.get('email')})
Amount: INR {txn.get('amount')}
Payment Method: {txn.get('payment_method')}
Error Code: {txn.get('error_code')}
Error Description: {txn.get('error_description')}
Attempts: {txn.get('attempts')}

Determine:
1. classification: "RECOVERABLE" (transient/soft errors) or "UNRECOVERABLE" (fraud, card expired, wrong credentials).
2. recovery_probability: Integer score from 0 to 100 representing confidence in successful recovery.
3. action_strategy: One of ["SEND_PAYMENT_LINK", "RETRY_NOW", "RETRY_LATER", "SUPPRESS_FRAUD"].
4. reasoning: Clear technical justification.
5. recovery_note: Polite, actionable message explaining the next step to the customer.
"""

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "classification": {"type": "STRING", "enum": ["RECOVERABLE", "UNRECOVERABLE"]},
            "recovery_probability": {"type": "INTEGER"},
            "action_strategy": {
                "type": "STRING", 
                "enum": ["SEND_PAYMENT_LINK", "RETRY_NOW", "RETRY_LATER", "SUPPRESS_FRAUD"]
            },
            "reasoning": {"type": "STRING"},
            "recovery_note": {"type": "STRING"}
        },
        "required": ["classification", "recovery_probability", "action_strategy", "reasoning", "recovery_note"]
    }

    if client:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.1
                    )
                )
                return json.loads(response.text)
            except Exception:
                time.sleep(2)
                continue

    return _fallback_diagnosis(txn)


def _fallback_diagnosis(txn):
    """Safety heuristic fallback for rate limits or offline runs."""
    error = txn.get("error_code", "").upper()
    unrec_errors = ["CARD_EXPIRED", "FRAUD_SUSPECTED", "INVALID_CVV"]
    
    if error in unrec_errors:
        return {
            "classification": "UNRECOVERABLE",
            "recovery_probability": 5,
            "action_strategy": "SUPPRESS_FRAUD",
            "reasoning": f"Critical permanent failure: {error}. Retries blocked to prevent fraud and merchant risk.",
            "recovery_note": "Payment could not be processed due to invalid or restricted card details."
        }
    elif error == "NETWORK_TIMEOUT":
        return {
            "classification": "RECOVERABLE",
            "recovery_probability": 85,
            "action_strategy": "RETRY_NOW",
            "reasoning": "Transient gateway network glitch. Immediate retry recommended.",
            "recovery_note": "A network timeout occurred. Please retry your payment."
        }
    elif error == "INSUFFICIENT_FUNDS":
        return {
            "classification": "RECOVERABLE",
            "recovery_probability": 65,
            "action_strategy": "RETRY_LATER",
            "reasoning": "Account balance insufficient. Delayed retry or alternative payment link recommended.",
            "recovery_note": "Please ensure sufficient funds or select an alternative payment method."
        }
    else:
        return {
            "classification": "RECOVERABLE",
            "recovery_probability": 80,
            "action_strategy": "SEND_PAYMENT_LINK",
            "reasoning": f"Transient error: {error}. Issuing Razorpay Payment Link for frictionless completion.",
            "recovery_note": "We noticed a temporary issue with your transaction. Use the secure link below to complete your order."
        }


def create_payment_link(txn, recovery_note):
    """Generates an active Razorpay payment link or mock short_url."""
    if razorpay_client:
        try:
            payload = {
                "amount": int(txn.get("amount", 0) * 100),
                "currency": "INR",
                "description": f"Recovery for {txn.get('id')} - {recovery_note[:100]}",
                "customer": {
                    "name": txn.get("customer_name", "Customer"),
                    "email": txn.get("email", "customer@example.com"),
                    "contact": "+919876543210"
                },
                "notify": {"sms": True, "email": True}
            }
            link = razorpay_client.payment_link.create(data=payload)
            return link.get("short_url")
        except Exception:
            pass
            
    return f"https://rzp.io/i/mock_{txn.get('id')}"


def process_recoveries(data_file="mock_data.json"):
    """Main pipeline processing each failed transaction webhook."""
    with open(data_file, "r") as f:
        transactions = json.load(f)

    results = []
    for txn in transactions:
        diagnosis = diagnose_failure(txn)
        
        payment_link = None
        if diagnosis["classification"] == "RECOVERABLE":
            payment_link = create_payment_link(txn, diagnosis["recovery_note"])

        results.append({
            "transaction": txn,
            "diagnosis": diagnosis,
            "payment_link": payment_link,
            "payment_status": "Pending"
        })

    return results