# ⚡ RecoverAI — Autonomous Revenue Recovery Engine
> Built for the **Razorpay AI Buildathon 2026** (Track 3: AI Revenue Recovery)

RecoverAI is an intelligent payment recovery and orchestration system designed to salvage failed e-commerce transactions without blind, repetitive retries. By analyzing granular failure telemetry using Google Gemini Flash, RecoverAI predicts recovery viability, calculates probability-weighted financial impact, suppresses fraud risks, and dynamically generates actionable Razorpay checkout links.

---

## 🚀 Key Architectural Pillars

* **Contextual AI Diagnosis:** Evaluates telemetry (`error_code`, `error_description`, payment method, customer history) to differentiate transient gateway drops from hard permanent failures.
* **Dynamic Orchestration Strategies:**
  * `SEND_PAYMENT_LINK`: Issues an active Razorpay checkout link for frictionless customer completion.
  * `RETRY_NOW`: Recommended for instantaneous transient gateway drops.
  * `RETRY_LATER`: Scheduled retries for temporary bank downtime or insufficient balance states.
  * `SUPPRESS_FRAUD`: Blocks retries on high-risk errors (`FRAUD_SUSPECTED`, `CARD_EXPIRED`) to protect merchants from chargeback penalties and gateway fees.
* **Probability-Weighted Financial Modeling:** Computes **Expected Recoverable Value (EV)** ($Amount \times \text{Probability}\%$) alongside gross values for clear merchant impact visibility.
* **Live Razorpay Integration:** Dynamically generates active payment links via the Razorpay Python SDK (`short_url`).
* **Settlement Outcome Tracking Loop:** Captures asynchronous payment completion events in real time, converting pending recovery value directly into confirmed merchant revenue.

---

## 🛠️ System Architecture

```text
       Failed Transaction Webhook Telemetry
                        ↓
         Contextual AI Diagnosis (Gemini Flash)
                        ↓
         ┌──────────────┴──────────────┐
         ↓                             ↓
   🟢 RECOVERABLE                🔴 UNRECOVERABLE / HIGH RISK
 (Gateway Timeouts, Drops)        (Card Expired, Fraud Suspected)
         ↓                             ↓
 EV Calculation & Strategy      Suppress Retries & Protect Merchant
         ↓
  Dynamic Razorpay Link
         ↓
 Customer Payment Settlement → Real-Time Ledger Update