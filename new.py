import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import io

st.set_page_config(page_title="Smart Home Loan Planner", layout="wide")
st.title("🏠 Smart Home Loan & Salary Planner with Parallel Funding & Smart Prepayment")

# Sidebar: User Inputs
st.sidebar.header("Basic Details")
monthly_salary = st.sidebar.number_input("Monthly Salary (₹)", value=150000)
expenses = st.sidebar.number_input("Fixed Monthly Expenses (₹)", value=30000)
sip_percent = st.sidebar.slider("SIP % of Salary", 0, 50, 20)
emergency_percent = st.sidebar.slider("Emergency Buffer % of Salary", 0, 50, 10)

loan_tenure = st.sidebar.number_input("Loan Tenure (Years)", value=20)
interest_rate = st.sidebar.number_input("Loan Interest Rate (% Annual)", value=7.5)
inflation = st.sidebar.slider("Inflation Rate %", 0.0, 10.0, 6.0)

# Prepayment or reinvest surplus
surplus_strategy = st.sidebar.radio("What to do with surplus?", ["Prepay Loan", "Reinvest Surplus"])

# Dynamic Slab Entry
st.sidebar.markdown("## 🧮 Slabwise Loan Disbursement")
num_slabs = st.sidebar.number_input("Number of Slabs", min_value=1, max_value=12, value=6)
loan_slabs = []
slab_months = []
for i in range(num_slabs):
    col1, col2 = st.sidebar.columns(2)
    with col1:
        amt = st.number_input(f"Slab {i+1} Amount (₹)", key=f"amt_{i}", value=1200000)
    with col2:
        mon = st.number_input(f"Month {i+1}", key=f"mon_{i}", min_value=1, value=(i + 1) * 3)
    loan_slabs.append(amt)
    slab_months.append(mon)

# Derived
total_loan = sum(loan_slabs)
months = loan_tenure * 12
monthly_interest = interest_rate / 12 / 100
disbursement_dict = dict(zip(slab_months, loan_slabs))

# Init vars
principal = 0
data = []
prepayment_total = 0
emergency_fund = 0

# Simulation
for month in range(1, months + 1):
    # Disbursement
    if month in disbursement_dict:
        principal += disbursement_dict[month]

    # Adjusted salary
    year = (month - 1) // 12
    adj_salary = monthly_salary * ((1 + inflation / 100) ** year)
    sip = sip_percent / 100 * adj_salary
    emergency = emergency_percent / 100 * adj_salary
    surplus = adj_salary - expenses - sip - emergency

    # EMI
    if principal > 0:
        emi = npf.pmt(monthly_interest, months - month + 1, -principal)
        interest_paid = principal * monthly_interest
        principal_paid = emi - interest_paid
    else:
        emi = 0
        interest_paid = 0
        principal_paid = 0

    surplus -= emi
    prepayment = 0
    reinvested = 0

    if surplus > 5000:
        if surplus_strategy == "Prepay Loan":
            prepayment = 0.8 * surplus
            principal -= prepayment
            prepayment_total += prepayment
        else:
            reinvested = 0.8 * surplus

        emergency_fund += 0.2 * surplus

    # Update principal
    principal -= principal_paid
    principal = max(principal, 0)

    data.append({
        "Month": month,
        "Adjusted Salary": round(adj_salary),
        "Expenses": round(expenses),
        "SIP": round(sip),
        "Emergency Fund": round(emergency_fund),
        "Surplus": round(surplus),
        "Reinvested" if surplus_strategy == "Reinvest Surplus" else "Prepayment": round(reinvested if surplus_strategy == "Reinvest Surplus" else prepayment),
        "EMI": round(emi),
        "Interest Paid": round(interest_paid),
        "Principal Paid": round(principal_paid),
        "Remaining Principal": round(principal)
    })

    if principal <= 0:
        break

# DataFrame
df = pd.DataFrame(data)

# Layout
st.subheader("📊 Loan Amortization Schedule")
st.dataframe(df, use_container_width=True)

# Summary
st.subheader("📈 Summary")
c1, c2, c3 = st.columns(3)
c1.metric("Total Interest Paid", f"₹{df['Interest Paid'].sum():,.0f}")
c2.metric("Total Prepayments" if surplus_strategy == "Prepay Loan" else "Total Reinvested", f"₹{df.iloc[-1]['Prepayment' if surplus_strategy == 'Prepay Loan' else 'Reinvested']:,.0f}")
c3.metric("Loan Closed In", f"{len(df)} months")

# Visuals
st.subheader("📉 Trend Charts")
st.line_chart(df[["EMI", "Interest Paid", "Principal Paid"]])
st.area_chart(df[["Emergency Fund"]])
if surplus_strategy == "Prepay Loan":
    st.line_chart(df[["Prepayment"]])
else:
    st.line_chart(df[["Reinvested"]])

# Downloads
st.subheader("📥 Download Schedule")
csv = df.to_csv(index=False).encode()
st.download_button("Download CSV", csv, "loan_schedule.csv", "text/csv")
