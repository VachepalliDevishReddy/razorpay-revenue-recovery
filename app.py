import streamlit as st
import json
import os
from recovery_engine import process_recoveries

st.set_page_config(
    page_title="RecoverAI - Autonomous Revenue Recovery Engine",
    page_icon="⚡",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fb;
        border-radius: 12px;
        padding: 20px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .badge-recoverable {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-unrecoverable {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .decision-box {
        background: #f1f5f9;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        border-left: 4px solid #3b82f6;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to safely extract amount
def get_safe_amount(txn):
    raw_val = txn.get("amount") or txn.get("amount_inr") or txn.get("value") or txn.get("txn_amount") or 0
    try:
        return float(raw_val)
    except (ValueError, TypeError):
        return 0.0

# State Management
if "processed_transactions" not in st.session_state:
    st.session_state.processed_transactions = None

# Sidebar Controls
with st.sidebar:
    st.title("⚡ RecoverAI Engine")
    st.caption("Track 3: AI Revenue Recovery (Razorpay Buildathon)")
    st.markdown("---")
    st.markdown("**Core Architecture Flow:**")
    st.markdown("""
    1. Ingestion (Webhook Telemetry)
    2. Contextual AI Diagnosis
    3. Probability Prediction
    4. AI Orchestration Strategy
    5. Razorpay Dynamic Links
    6. Settlement & Feedback Loop
    """)
    st.markdown("---")
    
    if st.button("🚀 Run Recovery Orchestrator", use_container_width=True, type="primary"):
        with st.spinner("AI analyzing failure telemetry & generating Razorpay links..."):
            st.session_state.processed_transactions = process_recoveries("mock_data.json")
            st.success("Orchestration pipeline execution complete!")

# Main Dashboard View
st.title("Autonomous AI Revenue Recovery Dashboard")
st.subheader("Intelligent transaction failure diagnosis, automated orchestration & Razorpay recovery")

if st.session_state.processed_transactions:
    data = st.session_state.processed_transactions
    
    total_txns = len(data)
    total_at_risk = sum(get_safe_amount(item["transaction"]) for item in data)
    
    recoverable_items = [item for item in data if item["diagnosis"].get("classification") == "RECOVERABLE"]
    recoverable_count = len(recoverable_items)
    gross_recoverable_value = sum(get_safe_amount(item["transaction"]) for item in recoverable_items)
    
    # Calculate Total Expected Recovery Value (Probability-Weighted)
    total_expected_recovery = sum(
        get_safe_amount(item["transaction"]) * (item["diagnosis"].get("recovery_probability", 75) / 100.0)
        for item in recoverable_items
    )
    
    # Track simulated customer settlements
    settled_items = [item for item in data if item.get("payment_status") == "Paid"]
    settled_value = sum(get_safe_amount(item["transaction"]) for item in settled_items)
    
    rec_rate = (gross_recoverable_value / total_at_risk * 100) if total_at_risk > 0 else 0

    # Top-Level Executive KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Failed (At Risk)", f"₹{total_at_risk:,.0f}", f"{total_txns} txns")
    with col2:
        st.metric("Gross Recoverable", f"₹{gross_recoverable_value:,.0f}", f"{recoverable_count} viable txns")
    with col3:
        st.metric("Expected Recovery (EV)", f"₹{total_expected_recovery:,.0f}", "Probability weighted")
    with col4:
        st.metric("Potential Recovery Rate", f"{rec_rate:.1f}%", f"{settled_value:,.0f} settled live")

    if settled_items:
        st.info(f"🔄 **Live Settlement Outcome Loop:** {len(settled_items)} transactions settled by customers! **₹{settled_value:,.0f} directly converted into merchant revenue.**")

    st.markdown("---")
    st.markdown("### 📋 Real-Time AI Orchestration & Recovery Log")

    for idx, item in enumerate(data):
        txn = item["transaction"]
        diag = item["diagnosis"]
        status = diag.get("classification", "UNRECOVERABLE")
        prob = diag.get("recovery_probability", 75)
        strategy = diag.get("action_strategy", "SEND_PAYMENT_LINK")
        link = item.get("payment_link")
        payment_status = item.get("payment_status", "Pending")

        # Safe amount and EV computation
        txn_amount = get_safe_amount(txn)
        expected_value = txn_amount * (prob / 100.0)

        txn_id = txn.get("id", f"TXN_{idx+1}")
        cust_name = txn.get("customer_name", "Customer")
        err_code = txn.get("error_code", "UNKNOWN_ERROR")
        err_desc = txn.get("error_description", "No description provided")
        cust_email = txn.get("email", "customer@example.com")
        method = txn.get("payment_method", "Payment")

        icon = "🟢" if status == "RECOVERABLE" else "🔴"

        header_title = f"{icon} {txn_id} - {cust_name} (₹{txn_amount:,.0f}) | {err_code} | EV: ₹{expected_value:,.0f} ({prob}%) | Strategy: {strategy}"
        
        with st.expander(header_title):
            c1, c2 = st.columns([1.8, 1.2])
            with c1:
                st.markdown(f"**Customer:** {cust_name} (`{cust_email}`) | **Method:** {method}")
                st.markdown(f"**Failure Telemetry:** `{err_code}` — *{err_desc}*")
                
                st.markdown("##### 🧠 AI Contextual Diagnosis")
                st.markdown(f"> **Technical Justification:** {diag.get('reasoning', 'N/A')}")
                st.markdown(f"> **Customer Note:** *\"{diag.get('recovery_note', 'N/A')}\"*")
            
            with c2:
                st.markdown("##### ⚙️ Decision & Financial Impact")
                st.markdown(f"• **Classification:** `{status}`")
                st.markdown(f"• **Confidence / Probability:** `{prob}%`")
                st.markdown(f"• **Expected Value (EV):** `₹{expected_value:,.0f}`")
                st.markdown(f"• **Orchestration Action:** `{strategy}`")
                st.markdown(f"• **Settlement Status:** `{payment_status}`")

                st.markdown("---")
                if link and status == "RECOVERABLE":
                    st.link_button("💳 Pay via Razorpay Link", link, use_container_width=True)
                    if payment_status == "Pending":
                        if st.button(f"✅ Simulate Customer Payment", key=f"pay_{idx}", use_container_width=True):
                            st.session_state.processed_transactions[idx]["payment_status"] = "Paid"
                            st.rerun()
                else:
                    st.caption("🔒 **Action:** Retries suppressed to safeguard merchant from chargeback and fraud penalty.")

else:
    st.info("👈 Click **'🚀 Run Recovery Orchestrator'** in the sidebar to ingest transaction webhooks and start the recovery engine.")