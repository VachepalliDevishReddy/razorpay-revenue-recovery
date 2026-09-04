import streamlit as st
import json
import webbrowser
import os
from recovery_engine import analyze_and_recover

st.set_page_config(page_title="RecoverAI Engine", page_icon="⚡", layout="wide")

@st.cache_data
def load_data():
    with open("mock_data.json", "r") as f:
        return json.load(f)

failures = load_data()

if "results" not in st.session_state:
    st.session_state.results = []

st.sidebar.title("⚡ RecoverAI Engine")
st.sidebar.caption("Autonomous Revenue Recovery Engine")
st.sidebar.write(f"Failed Telemetry Queue: **{len(failures)} Transactions**")

if st.sidebar.button("🚀 Run Autonomous Recovery Engine", type="primary", use_container_width=True):
    with st.spinner("Triaging telemetry via Gemini 2.5 Flash..."):
        recovered = []
        for raw_txn in failures:
            res = analyze_and_recover(raw_txn)
            recovered.append({
                "transaction": raw_txn,
                "classification": res["classification"],
                "confidence": res["recovery_probability"],
                "strategy": res["action_strategy"],
                "rail": res["recommended_rail"],
                "ai_reasoning": res["ai_reasoning"],
                "customer_note": res["customer_note"],
                "checkout_html": res["checkout_html"],
                "payment_status": "Pending"
            })
        st.session_state.results = recovered
    st.sidebar.success("Triage & Recovery Mapping Complete!")

filter_tier = "ALL"
if st.session_state.results:
    st.sidebar.markdown("---")
    filter_tier = st.sidebar.selectbox("Filter Operational Tiers", ["ALL", "RECOVERABLE", "CUSTOMER_ACTION_REQUIRED", "HIGH_RISK"])

st.title("Autonomous AI Revenue Recovery Dashboard")
st.caption("Contextual failure triage, intelligent routing, and Razorpay dynamic checkout")

if st.session_state.results:
    data = st.session_state.results
    total_at_risk = sum(item["transaction"]["amount_inr"] for item in data)
    settled_items = [item for item in data if item["payment_status"] == "Paid"]
    settled_value = sum(item["transaction"]["amount_inr"] for item in settled_items)
    
    # Expected Value (Probability-Weighted)
    actionable_items = [item for item in data if item["classification"] in ["RECOVERABLE", "CUSTOMER_ACTION_REQUIRED"]]
    gross_actionable = sum(item["transaction"]["amount_inr"] for item in actionable_items)
    ev_total = sum(item["transaction"]["amount_inr"] * (item["confidence"] / 100.0) for item in actionable_items)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gross Pipeline At Risk", f"₹{total_at_risk:,.0f}", f"{len(data)} txns")
    col2.metric("Actionable Recovery Pool", f"₹{gross_actionable:,.0f}", f"{len(actionable_items)} viable txns")
    col3.metric("Expected Recovery (EV)", f"₹{ev_total:,.0f}", "Probability weighted")
    col4.metric("Realized Settlement", f"₹{settled_value:,.0f}", f"{len(settled_items)} settled")

    st.markdown("---")
    filtered = [item for item in data if filter_tier == "ALL" or item["classification"] == filter_tier]

    for idx, item in enumerate(filtered):
        orig_idx = data.index(item)
        txn = item["transaction"]
        tier = item["classification"]
        prob = item["confidence"]
        status = item["payment_status"]

        icons = {"RECOVERABLE": "🟢", "CUSTOMER_ACTION_REQUIRED": "🟡", "HIGH_RISK": "🔴"}
        icon = icons.get(tier, "⚪")

        header = f"{icon} [{tier}] {txn['id']} - {txn['customer_name']} (₹{txn['amount_inr']:,}) | {txn['error_code']} | EV: ₹{(txn['amount_inr'] * prob / 100):,.0f} ({prob}%) | [{status}]"

        with st.expander(header, expanded=(orig_idx == 0)):
            c1, c2 = st.columns([1.6, 1.4])
            with c1:
                st.markdown(f"**Error Telemetry:** `{txn['error_code']}` — *{txn['error_description']}*")
                st.markdown(f"**Customer Profile:** Preferred: `{txn.get('customer_history', {}).get('preferred_method', 'N/A')}` | Historical Successes: `{txn.get('customer_history', {}).get('successful_attempts', 0)}`")
                st.markdown(f"> **Technical Root Cause:** {item['ai_reasoning']}")
                st.markdown(f"> **Contextual Recovery Prompt:** *\"{item['customer_note']}\"*")
            with c2:
                st.markdown(f"• **Recommended Action:** `{item['strategy']}`")
                st.markdown(f"• **Recommended Rail:** `{item['rail']}`")
                st.markdown(f"• **Recovery Probability:** `{prob}%`")

                if item["checkout_html"]:
                    if st.button(f"🌐 Launch Dynamic Checkout Session", key=f"btn_{orig_idx}", use_container_width=True):
                        path = os.path.abspath("live_checkout.html")
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(item["checkout_html"])
                        webbrowser.open(f"file:///{path}")
                    if status == "Pending":
                        if st.button(f"✅ Record Settlement Outcome", key=f"settle_{orig_idx}", use_container_width=True):
                            st.session_state.results[orig_idx]["payment_status"] = "Paid"
                            st.rerun()
                else:
                    st.caption("🔒 Automated recovery suppressed to mitigate chargeback risk.")
else:
    st.info("👈 Click **'Run Autonomous Recovery Engine'** in the sidebar to process failed transactions.")