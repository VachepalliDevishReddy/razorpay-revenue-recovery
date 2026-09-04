import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
import razorpay

# Force reload .env
load_dotenv(override=True)

gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
rzp_key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
rzp_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

# Initialize API clients
rzp_client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
ai_client = genai.Client(api_key=gemini_key)

def analyze_and_recover(transaction: dict) -> dict:
    """
    Analyzes a failed transaction with Gemini and creates a Razorpay Payment Link if recoverable.
    Falls back gracefully to deterministic rule classification if API rate limits are encountered.
    """
    code = transaction.get("error_code", "")
    is_hard_fail = code in ["FRAUD_SUSPECTED", "CARD_EXPIRED"]
    
    # 1. AI Diagnostic Attempt
    diagnosis = None
    try:
        time.sleep(0.5)
        prompt = f"""
        You are an expert fintech payment recovery engine.
        Analyze this failed transaction:
        {json.dumps(transaction)}

        Business Rules:
        1. RECOVERABLE: Timeouts, network drops, temporary bank downtime, cancelled UPI prompts, or minor user input errors.
           -> Set should_recover=True, recovery_channel="PAYMENT_LINK".
        2. UNRECOVERABLE: Expired cards, suspected fraud, permanently blocked accounts.
           -> Set should_recover=False, recovery_channel="DO_NOT_RETRY".
        3. Generate a polite, 1-sentence recovery note explaining how the customer can retry.

        Return ONLY a JSON object with:
        {{
          "should_recover": boolean,
          "recovery_channel": "PAYMENT_LINK" | "DO_NOT_RETRY",
          "reasoning": "1 sentence technical justification",
          "customer_note": "1 sentence polite customer message"
        }}
        """
        response = ai_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        diagnosis = json.loads(response.text)
    except Exception:
        # 2. Automated Diagnostic Fallback
        if is_hard_fail:
            diagnosis = {
                "should_recover": False,
                "recovery_channel": "DO_NOT_RETRY",
                "reasoning": f"Hard failure ({code}) identified. Automated retry blocked to prevent redundant charges and risk flags.",
                "customer_note": "Your transaction could not be processed. Please try using a different payment instrument."
            }
        else:
            diagnosis = {
                "should_recover": True,
                "recovery_channel": "PAYMENT_LINK",
                "reasoning": f"Transient error ({code}) detected. Successfully eligible for frictionless recovery link.",
                "customer_note": f"Hi {transaction.get('customer_name')}, your payment encountered a temporary network delay. You can complete it securely using the payment link below."
            }

    # 3. Dynamic Razorpay Payment Link Generation
    payment_url = None
    if diagnosis.get("should_recover") and diagnosis.get("recovery_channel") == "PAYMENT_LINK":
        try:
            link_data = {
                "amount": transaction["amount_inr"] * 100,  # paise
                "currency": "INR",
                "description": f"Recovery for {transaction['transaction_id']}",
                "customer": {
                    "name": transaction["customer_name"],
                    "email": transaction["customer_email"],
                },
                "notify": {"sms": False, "email": False},
            }
            rzp_link = rzp_client.payment_link.create(link_data)
            payment_url = rzp_link.get("short_url")
        except Exception as e:
            print(f"Razorpay API Error for {transaction['transaction_id']}: {e}")

    return {
        "transaction_id": transaction["transaction_id"],
        "customer_name": transaction["customer_name"],
        "amount_inr": transaction["amount_inr"],
        "error_code": transaction["error_code"],
        "ai_should_recover": diagnosis.get("should_recover"),
        "ai_reasoning": diagnosis.get("reasoning"),
        "customer_note": diagnosis.get("customer_note"),
        "payment_link": payment_url,
        "status": "RECOVERED" if payment_url else "ABORTED",
    }