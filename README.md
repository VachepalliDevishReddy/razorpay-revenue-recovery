# ⚡ Autonomous AI Revenue Recovery Engine

An intelligent payment recovery pipeline built for the **Razorpay AI Buildathon (Track 3: AI Revenue Recovery)**. It autonomously analyzes failed transaction webhooks, categorizes transient vs hard failures using Google Gemini, and generates frictionless Razorpay Payment Links to recover dropped revenue.

---

## 🎯 Key Features

* **Intelligent Error Categorization:** Uses Gemini 3.6 Flash structured JSON output to analyze failure metadata.
* **Automated Dynamic Payment Links:** Automatically generates instant Razorpay checkout links for recoverable transactions.
* **Fraud & Hard Failure Protection:** Flags expired cards and suspected fraud to avoid spamming customers or creating redundant payment requests.
* **Interactive Executive Dashboard:** Visualizes recovered revenue, recovery percentages, and per-transaction AI diagnostics.

---

## 🏗️ Architecture & Data Flow

1. **Ingestion:** Transaction failure payload received (simulated via `mock_data.json`).
2. **AI Reasoning:** Gemini diagnoses error classification (`RECOVERABLE` vs `UNRECOVERABLE`) and crafts a personalized recovery note.
3. **Razorpay Action:** For recoverable errors, a Razorpay Payment Link (`short_url`) is generated via the Razorpay Python SDK.
4. **Presentation:** Real-time Streamlit dashboard calculates business KPIs (Recovered Amount, Recovery Rate %).

---

## 🚀 Quickstart

### 1. Clone Repository & Enter Directory
```bash
git clone [https://github.com/VachepalliDevishReddy/razorpay-revenue-recovery.git](https://github.com/VachepalliDevishReddy/razorpay-revenue-recovery.git)
cd razorpay-revenue-recovery
