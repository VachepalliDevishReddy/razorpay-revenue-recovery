import streamlit as st
import json
from recovery_engine import analyze_and_recover

st.set_page_config(
    page_title="AI Revenue Recovery Engine",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Autonomous AI Revenue Recovery Dashboard")
st.markdown("Track 3: AI-driven transaction failure diagnosis & recovery via Razorpay.")

# Load failure dataset
@st.cache_data
def load_data():
    with open("mock_data.json", "r") as f:
        return json.load(f)

failures = load_data()

# Sidebar controls
st.sidebar.header("Pipeline Control")
st.sidebar.write(f"Total Failed Ingestion Queue: **{len(failures)} Transactions**")

if "results" not in st.session_state:
    st.session_state.results = []

if st.sidebar.button("🚀 Run Autonomous Recovery Engine", type="primary"):
    with st.spinner("Processing failure queue with Gemini & Razorpay API..."):
        recovered_list = []
        for txn in failures:
            res = analyze_and_recover(txn)
            recovered_list.append(res)
        st.session_state.results = recovered_list
    st.sidebar.success("Recovery pipeline executed successfully!")

# Main Dashboard View
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    
    # Calculate Summary Metrics
    total_txns = len(df)
    recovered_df = df[df["status"] == "RECOVERED"]
    recovered_count = len(recovered_df)
    total_val = df["amount_inr"].sum()
    recovered_val = recovered_df["amount_inr"].sum()
    recovery_rate = (recovered_val / total_val) * 100 if total_val > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Failed Transactions", f"{total_txns}")
    col2.metric("Total At-Risk Value", f"₹{total_val:,}")
    col3.metric("Recovered Transactions", f"{recovered_count}")
    col4.metric("Recovered Revenue", f"₹{recovered_val:,}", f"{recovery_rate:.1f}% Rate")

    st.markdown("---")
    st.subheader("Transaction Recovery Log")
    
    # Render interactive data view
    for _, row in df.iterrows():
        status_color = "🟢" if row["status"] == "RECOVERED" else "🔴"
        with st.expander(f"{status_color} {row['transaction_id']} - {row['customer_name']} (₹{row['amount_inr']:,}) | Error: {row['error_code']}"):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(f"**AI Reasoning:** {row['ai_reasoning']}")
                st.markdown(f"**Generated Customer Notification:** _{row['customer_note']}_")
            with c2:
                if row["payment_link"]:
                    st.success(f"**Payment Link Generated:** [Open Checkout]({row['payment_link']})")
                    st.code(row["payment_link"], language="text")
                else:
                    st.error("**Recovery Status:** ABORTED (Unrecoverable Error / Fraud Prevention)")
else:
    st.info("Click **'Run Autonomous Recovery Engine'** in the sidebar to process the failure backlog.")