import json
import os
import time
import logging
import warnings
from dotenv import load_dotenv
from google import genai
from google.genai import types
import razorpay

# Suppress standard Python and GenAI internal warnings
warnings.filterwarnings("ignore")
logging.getLogger("google.genai").setLevel(logging.ERROR)

load_dotenv(override=True)

gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
rzp_key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
rzp_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

# Initialize Razorpay Client
rzp_client = None
if rzp_key_id and rzp_key_secret:
    try:
        rzp_client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
    except Exception as e:
        pass

# Initialize Gemini Client
ai_client = None
if gemini_key:
    try:
        ai_client = genai.Client(api_key=gemini_key)
    except Exception as e:
        pass


def _safe_get_amount(txn: dict) -> float:
    val = txn.get("amount_inr") or txn.get("amount") or txn.get("value") or txn.get("txn_amount") or 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def analyze_and_recover(transaction: dict, call_ai: bool = True) -> dict:
    """
    Triages failure telemetry into 3 operational buckets:
    - RECOVERABLE (transient timeouts)
    - CUSTOMER_ACTION_REQUIRED (expired cards, wrong CVV/OTP, limits)
    - HIGH_RISK (fraud, blocked accounts)
    Uses client.chats to avoid AFC warnings.
    """
    txn_id = transaction.get("id") or transaction.get("transaction_id") or "TXN_UNKNOWN"
    customer_name = transaction.get("customer_name") or transaction.get("name") or "Customer"
    customer_email = transaction.get("customer_email") or transaction.get("email") or "customer@example.com"
    customer_contact = transaction.get("customer_phone") or transaction.get("phone") or "9676265757"
    code = transaction.get("error_code") or "UNKNOWN_ERROR"
    amount_inr = _safe_get_amount(transaction)
    history = transaction.get("customer_history", {})

    high_risk_codes = ["FRAUD_SUSPECTED", "ACCOUNT_BLOCKED", "STOLEN_CARD"]
    customer_action_codes = ["CARD_EXPIRED", "INVALID_CVV", "INSUFFICIENT_FUNDS", "OTP_VERIFICATION_FAILED", "TRANSACTION_LIMIT_EXCEEDED"]

    diagnosis = None

    # Call Gemini via Chat interface (avoids AFC warning entirely)
    if call_ai and ai_client:
        try:
            prompt = f"""
            You are an autonomous fintech revenue recovery engine.
            Analyze this failed transaction telemetry and customer profile:
            {json.dumps(transaction)}

            Classify into EXACTLY one of these 3 tiers:
            1. RECOVERABLE: Transient system drops, network timeouts, bank temporary downtime.
               - action_strategy: "AUTO_RETRY" or "SEND_CHECKOUT"
               - recovery_probability: 65 to 95
            2. CUSTOMER_ACTION_REQUIRED: Fixable user errors (expired cards, wrong CVV/OTP, limits).
               - action_strategy: "SWITCH_PAYMENT_METHOD" or "UPDATE_CREDENTIALS"
               - recovery_probability: 30 to 60
               - Recommend an instrument based on customer_history.
            3. HIGH_RISK: Suspected fraud, stolen cards, blocked accounts.
               - action_strategy: "SUPPRESS_FRAUD"
               - recovery_probability: 0 to 5

            Return ONLY raw valid JSON (no markdown ticks):
            {{
              "classification": "RECOVERABLE" | "CUSTOMER_ACTION_REQUIRED" | "HIGH_RISK",
              "action_strategy": "AUTO_RETRY" | "SEND_CHECKOUT" | "SWITCH_PAYMENT_METHOD" | "UPDATE_CREDENTIALS" | "SUPPRESS_FRAUD",
              "recovery_probability": integer,
              "recommended_rail": "UPI" | "NETBANKING" | "CARD" | "NONE",
              "reasoning": "1-sentence technical root cause",
              "customer_note": "1-sentence clear customer recovery prompt"
            }}
            """
            
            chat = ai_client.chats.create(model="gemini-2.0-flash")
            response = chat.send_message(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            diagnosis = json.loads(clean_text)
        except Exception:
            pass

    # Instant deterministic rule-based fallback
    if not diagnosis:
        if code in high_risk_codes:
            diagnosis = {
                "classification": "HIGH_RISK",
                "action_strategy": "SUPPRESS_FRAUD",
                "recovery_probability": 0,
                "recommended_rail": "NONE",
                "reasoning": f"Security restriction ({code}). Retries suppressed to safeguard gateway health.",
                "customer_note": "Transaction declined by security policies. Please use an alternative card."
            }
        elif code in customer_action_codes:
            pref = history.get("preferred_method", "UPI")
            diagnosis = {
                "classification": "CUSTOMER_ACTION_REQUIRED",
                "action_strategy": "SWITCH_PAYMENT_METHOD",
                "recovery_probability": 45,
                "recommended_rail": pref,
                "reasoning": f"Customer validation error ({code}). Switch payment rail to resolve.",
                "customer_note": f"Hi {customer_name}, your payment encountered an issue. Please complete using your verified {pref}."
            }
        else:
            diagnosis = {
                "classification": "RECOVERABLE",
                "action_strategy": "SEND_CHECKOUT",
                "recovery_probability": 85,
                "recommended_rail": "UPI",
                "reasoning": f"Transient timeout ({code}). Eligible for pre-filled recovery session.",
                "customer_note": f"Hi {customer_name}, checkout was interrupted. Tap below to finish your order."
            }

    classification = diagnosis.get("classification", "HIGH_RISK")
    action_strategy = diagnosis.get("action_strategy", "SUPPRESS_FRAUD")
    rec_rail = diagnosis.get("recommended_rail", "UPI").lower()
    can_open_checkout = classification in ["RECOVERABLE", "CUSTOMER_ACTION_REQUIRED"]

    checkout_html = None
    if can_open_checkout:
        paise = int(amount_inr * 100)
        checkout_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>RecoverAI Dynamic Checkout</title>
          <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
          <style>
            * {{ box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #090d16; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
            .card {{ background: #131b2e; padding: 28px; border-radius: 16px; box-shadow: 0 20px 45px rgba(0,0,0,0.7); max-width: 440px; width: 100%; border: 1px solid #1e293b; }}
            .badge {{ display: inline-block; background: #064e3b; color: #34d399; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
            .amount {{ font-size: 32px; font-weight: 800; color: #38bdf8; margin: 8px 0; }}
            .input-box {{ width: 100%; background: #0a0f1d; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; color: #f8fafc; font-size: 14px; margin-top: 6px; }}
            .status-box {{ margin-top: 14px; padding: 12px; border-radius: 8px; font-size: 13px; line-height: 1.5; display: none; }}
            .btn {{ background: #2563eb; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-weight: 600; font-size: 15px; cursor: pointer; width: 100%; margin-top: 14px; }}
            .btn-pay {{ background: #059669; display: none; }}
            .disclaimer {{ font-size: 11px; color: #64748b; margin-top: 14px; text-align: center; }}
          </style>
        </head>
        <body>
          <div class="card">
            <span class="badge">⚡ RecoverAI Dynamic Session</span>
            <div class="amount">₹{amount_inr:,.2f}</div>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 10px 0;">Customer: <b>{customer_name}</b> | Action: <b>{action_strategy}</b></p>
            
            <label style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 600;">Payment Method</label>
            <select id="method-selector" class="input-box" onchange="handleMethodChange()">
              <option value="upi" {"selected" if rec_rail == "upi" else ""}>UPI (Recommended from History)</option>
              <option value="netbanking" {"selected" if rec_rail == "netbanking" else ""}>Netbanking</option>
              <option value="card" {"selected" if rec_rail == "card" else ""}>Card (Alternate)</option>
            </select>

            <div id="upi-section" style="margin-top: 12px; display: {'block' if rec_rail == 'upi' else 'none'};">
              <label style="font-size: 12px; color: #94a3b8;">Customer VPA</label>
              <input type="text" id="upi-input" class="input-box" value="aarav@okhdfcbank">
            </div>

            <div id="verify-status" class="status-box"></div>

            <button id="validate-btn" class="btn" onclick="verifyAccount()">🔍 Run Simulated Pre-Flight Check</button>
            <button id="pay-btn" class="btn btn-pay" onclick="openRazorpay()">💳 Proceed to Razorpay Checkout</button>
            
            <div class="disclaimer">Demo Environment: Account checks are simulated to demonstrate pre-flight routing.</div>
          </div>

          <script>
            function handleMethodChange() {{
              var m = document.getElementById('method-selector').value;
              document.getElementById('upi-section').style.display = (m === 'upi') ? 'block' : 'none';
              document.getElementById('verify-status').style.display = 'none';
              document.getElementById('pay-btn').style.display = 'none';
              document.getElementById('validate-btn').style.display = 'block';
            }}

            function verifyAccount() {{
              var statusBox = document.getElementById('verify-status');
              statusBox.style.display = 'block';
              statusBox.style.background = '#1e293b';
              statusBox.style.color = '#38bdf8';
              statusBox.innerHTML = '⏳ Simulating pre-flight account status check...';

              setTimeout(function() {{
                var m = document.getElementById('method-selector').value;
                var vpa = document.getElementById('upi-input').value;
                if (m === 'upi' && (vpa.includes('invalid') || vpa === '')) {{
                  statusBox.style.background = '#450a0a';
                  statusBox.style.color = '#f87171';
                  statusBox.innerHTML = '❌ <b>Simulated VPA Check Failed:</b> VPA not registered. Please enter a valid UPI address.';
                  document.getElementById('pay-btn').style.display = 'none';
                }} else {{
                  statusBox.style.background = '#064e3b';
                  statusBox.style.color = '#34d399';
                  statusBox.innerHTML = '✅ <b>Account Verified:</b> Active payment instrument confirmed. Ready for authorization.';
                  document.getElementById('validate-btn').style.display = 'none';
                  document.getElementById('pay-btn').style.display = 'block';
                }}
              }}, 400);
            }}

            function openRazorpay() {{
              var options = {{
                "key": "{rzp_key_id}",
                "amount": "{paise}",
                "currency": "INR",
                "name": "RecoverAI Checkout",
                "description": "Order Recovery for {txn_id}",
                "prefill": {{
                  "name": "{customer_name}",
                  "email": "{customer_email}",
                  "contact": "{customer_contact}"
                }},
                "theme": {{ "color": "#2563eb" }}
              }};
              var rzp = new Razorpay(options);
              rzp.open();
            }}
          </script>
        </body>
        </html>
        """

    return {
        "transaction_id": txn_id,
        "customer_name": customer_name,
        "amount_inr": amount_inr,
        "error_code": code,
        "classification": classification,
        "action_strategy": action_strategy,
        "recovery_probability": int(diagnosis.get("recovery_probability", 50)),
        "recommended_rail": diagnosis.get("recommended_rail", "UPI"),
        "ai_reasoning": diagnosis.get("reasoning", ""),
        "customer_note": diagnosis.get("customer_note", ""),
        "checkout_html": checkout_html,
        "status": classification,
    }


def process_recoveries(mock_file_path: str = "mock_data.json") -> list:
    if not os.path.exists(mock_file_path):
        return []

    with open(mock_file_path, "r") as f:
        transactions = json.load(f)

    results = []
    for txn in transactions:
        res = analyze_and_recover(txn)
        results.append({
            "transaction": txn,
            "diagnosis": {
                "classification": res["classification"],
                "action_strategy": res["action_strategy"],
                "recovery_probability": res["recovery_probability"],
                "reasoning": res["ai_reasoning"],
                "recovery_note": res["customer_note"],
            },
            "checkout_html": res["checkout_html"],
            "payment_status": "Pending"
        })

    return results