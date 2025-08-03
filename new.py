import streamlit as st
import pandas as pd
import numpy as np
import io
import numpy_financial as npf

st.set_page_config(page_title="Smart Home Loan Planner", layout="wide")
st.title("🏠 Smart Home Loan + Parallel Funding Planner")

st.sidebar.header("User Inputs")

# Loan slab disbursement inputs
loan_slabs = st.sidebar.text_area("Loan Slabs (comma-separated, ₹)", "750000,1500000,1500000,1200000,1200000,1200000")
slab_months = st.sidebar.text_area("Slab Disbursement Months (comma-separated)", "1,2,6,12,18,24")

loan_slabs = [float(x.strip()) for x in loan_slabs.split(",")]
slab_months = [int(x.strip()) for x in slab_months.split(",")]
disbursement_dict = dict(zip(slab_months, loan_slabs))

# Inputs
tenure_years = st.sidebar.number_input("Loan Tenure (Years)", value=20)
months = tenure_years * 12
interest_rate = st.sidebar.number_input("Interest Rate (Annual %)", value=7.5)
monthly_salary = st.sidebar.number_input("Initial Monthly Salary (₹)", value=150000)
inflation_rate = st.sidebar.number_input("Annual Inflation %", value=6.0)
expenses = st.sidebar.number_input("Monthly Fixed Expenses (₹)", value=30000)
sip_percent = st.sidebar.slider("SIP % of Salary", 0, 50, 20)
emi_limit_percent = st.sidebar.slider("Max EMI % of Salary", 0, 100, 50)

# Derived values
monthly_interest = interest_rate / 12 / 100
principal = 0
prepayment_total = 0
disbursed_amount = 0
data = []

for i in range(1, months + 1):
    # Handle slab disbursement
    if i in disbursement_dict:
        principal += disbursement_dict[i]
        disbursed_amount += disbursement_dict[i]

    year = (i - 1) // 12
    adjusted_salary = monthly_salary * ((1 + inflation_rate / 100) ** year)
    sip = (sip_percent / 100) * adjusted_salary
    max_emi = (emi_limit_percent / 100) * adjusted_salary
    emi = 0
    interest_paid = 0
    principal_paid = 0

    if principal > 0:
        emi = npf.pmt(monthly_interest, months - i + 1, -principal)
        emi = min(emi, max_emi)  # Clamp EMI to max EMI based on income
        interest_paid = principal * monthly_interest
        principal_paid = emi - interest_paid
        principal -= principal_paid

    budget_left = adjusted_salary - expenses - sip - emi
    prepayment = 0
    if budget_left > 5000 and principal > 0:
        prepayment = 0.8 * budget_left
        prepayment_total += prepayment
        principal -= prepayment

    principal = max(principal, 0)

    data.append({
        "Month": i,
        "Adjusted Salary": round(adjusted_salary),
        "SIP": round(sip),
        "EMI": round(emi),
        "Interest Paid": round(interest_paid),
        "Principal Paid": round(principal_paid),
        "Prepayment": round(prepayment),
        "Remaining Principal": round(principal)
    })

    if principal <= 0:
        break

df = pd.DataFrame(data)

# Output section
st.subheader("📊 Loan Amortization Schedule")
st.dataframe(df, use_container_width=True)

st.subheader("📈 Summary Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Total Interest Paid", f"₹{df['Interest Paid'].sum():,.0f}")
col2.metric("Total Prepayments", f"₹{prepayment_total:,.0f}")
col3.metric("Loan Closed In", f"{len(df)} months")

st.subheader("📉 Trends Over Time")
st.line_chart(df[["EMI", "Interest Paid", "Prepayment"]])

# File download
csv = df.to_csv(index=False)
excel = io.BytesIO()
with pd.ExcelWriter(excel, engine='xlsxwriter') as writer:
    df.to_excel(writer, index=False, sheet_name='Schedule')
excel.seek(0)

st.subheader("📥 Download")
st.download_button("Download CSV", csv, "loan_schedule.csv", "text/csv")
st.download_button("Download Excel", excel.read(), "loan_schedule.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
