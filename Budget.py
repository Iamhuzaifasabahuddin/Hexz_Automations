import time
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
from notion_client import Client

notion = Client(auth=st.secrets["notion_token_2"])
database_id = st.secrets["database_id_2"]
APP_PASSWORD = st.secrets["app_password_2"]

st.set_page_config(
    page_title="Personal Budget Tracker",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔑 Budget Tracker Login")
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.success("Login successful! 🎉")
            time.sleep(2)
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

col1, col2 = st.columns([8, 2])

with col1:
    main_tabs = st.tabs(["💸 Add Transaction", "📊 View Budget"])

    with main_tabs[0]:
        st.header("💸 Add a Transaction")

        pkt = pytz.timezone("Asia/Karachi")
        now_pkt = datetime.now(pkt)

        with st.form("transaction_form", clear_on_submit=False):
            transaction_type = st.selectbox("Type", ["Expense", "Income"])

            if transaction_type == "Expense":
                category = st.selectbox("Category", [
                    "Food & Dining",
                    "Transportation",
                    "Shopping",
                    "Entertainment",
                    "Bills & Utilities",
                    "Healthcare",
                    "Education",
                    "Other"
                ])
            else:
                category = st.selectbox("Category", [
                    "Salary",
                    "Freelance",
                    "Business",
                    "Investment",
                    "Gift",
                    "Other"
                ])

            transaction_date = st.date_input("Date", now_pkt.date())
            transaction_time = st.time_input("Time", now_pkt.time(), key="transaction_time")
            amount = st.number_input("Amount (PKR)", min_value=0, step=50)
            description = st.text_input("Description (Optional)")

            preview = st.form_submit_button("Preview Transaction")
            submitted = st.form_submit_button("Save Transaction")

        if preview:
            transaction_dt = datetime.combine(transaction_date, transaction_time)
            transaction_dt_pkt = pkt.localize(transaction_dt)
            formatted_dt = transaction_dt_pkt.strftime("%d-%m-%Y at %I:%M %p")
            emoji = "➖" if transaction_type == "Expense" else "➕"
            st.info(f"Preview {emoji} {transaction_type}: {category} | {formatted_dt} | PKR {amount:,}")

        if submitted:
            month = transaction_date.strftime("%B %Y")
            formatted_time = transaction_time.strftime("%I:%M %p")
            try:
                notion.pages.create(
                    parent={"database_id": database_id},
                    properties={
                        "Name": {
                            "title": [
                                {"text": {"content": f"{transaction_type} - {category} ({transaction_date})"}}
                            ]
                        },
                        "Type": {"select": {"name": transaction_type}},
                        "Category": {"rich_text": [{"text": {"content": category}}]},
                        "Date": {"date": {"start": transaction_date.isoformat()}},
                        "Time": {"rich_text": [{"text": {"content": formatted_time}}]},
                        "Amount": {"number": amount},
                        "Month": {"rich_text": [{"text": {"content": month}}]},
                        "Description": {"rich_text": [{"text": {"content": description if description else ""}}]},
                    },
                )
                st.success(f"{transaction_type} saved to Notion! ✅")
            except Exception as e:
                st.error(f"Error: {e}")

    with main_tabs[1]:
        st.header("📊 Budget Overview")

        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()


        @st.cache_data(ttl=120)
        def get_transactions():
            transactions = []
            has_more = True
            start_cursor = None

            while has_more:
                if start_cursor:
                    data = notion.databases.query(
                        database_id=database_id,
                        start_cursor=start_cursor
                    )
                else:
                    data = notion.databases.query(database_id=database_id)

                for row in data["results"]:
                    props = row["properties"]

                    transaction_date = props["Date"]["date"]["start"] if props["Date"]["date"] else None
                    amount = props["Amount"]["number"] if props["Amount"]["number"] else 0
                    month = (
                        props["Month"]["rich_text"][0]["text"]["content"]
                        if props["Month"]["rich_text"] else "Unknown"
                    )
                    transaction_time = (
                        props["Time"]["rich_text"][0]["text"]["content"]
                        if props["Time"]["rich_text"] else "Unknown"
                    )
                    transaction_type = (
                        props["Type"]["select"]["name"]
                        if props["Type"]["select"] else "Unknown"
                    )
                    category = (
                        props["Category"]["rich_text"][0]["text"]["content"]
                        if props["Category"]["rich_text"] else "Unknown"
                    )
                    description = (
                        props["Description"]["rich_text"][0]["text"]["content"]
                        if props["Description"]["rich_text"] else ""
                    )

                    transactions.append({
                        "id": row["id"],
                        "date": transaction_date,
                        "time": transaction_time,
                        "type": transaction_type,
                        "category": category,
                        "amount": amount,
                        "month": month,
                        "description": description
                    })
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

            return transactions


        transactions = get_transactions()

        if transactions:
            df = pd.DataFrame(transactions)
            df.index = range(1, len(transactions) + 1)

            view = st.radio(
                "Select View",
                ["📊 Dashboard", "📅 By Month", "📋 All Data", "📈 By Category", "❌ Delete"],
                horizontal=True
            )

            if view == "📊 Dashboard":
                st.subheader("Financial Dashboard")

                total_income = df[df["type"] == "Income"]["amount"].sum()
                total_expense = df[df["type"] == "Expense"]["amount"].sum()
                net_balance = total_income - total_expense

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("💰 Total Income", f"PKR {total_income:,.2f}")
                col_b.metric("💸 Total Expenses", f"PKR {total_expense:,.2f}")
                col_c.metric("💵 Net Balance", f"PKR {net_balance:,.2f}",
                             delta=f"{net_balance:,.2f}", delta_color="normal")

                st.subheader("Income vs Expenses by Month")
                month_summary = df.groupby(["month", "type"])["amount"].sum().reset_index()
                month_pivot = month_summary.pivot(index="month", columns="type", values="amount").fillna(0)
                st.bar_chart(month_pivot)
                month_summary.index = range(1, len(month_summary) + 1)
                st.dataframe(month_summary)

            elif view == "📅 By Month":
                st.subheader("Filter by Month")

                unique_months = sorted(df["month"].unique())
                months = ["All"] + list(unique_months)
                current_month = datetime.now(pkt).strftime("%B")
                if current_month in unique_months:
                    default_index = unique_months.index(current_month) + 1
                else:
                    default_index = 0
                selected_month = st.selectbox("Choose a month", months, index=default_index)
                if selected_month == "All":
                    filtered_df = df
                else:
                    filtered_df = df[df["month"] == selected_month]

                st.write(filtered_df.drop(columns=["id"]))

                income = filtered_df[filtered_df["type"] == "Income"]["amount"].sum()
                expense = filtered_df[filtered_df["type"] == "Expense"]["amount"].sum()
                balance = income - expense

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("💰 Income", f"PKR {income:,.2f}")
                col_b.metric("💸 Expenses", f"PKR {expense:,.2f}")
                col_c.metric("💵 Balance", f"PKR {balance:,.2f}")

            elif view == "📋 All Data":
                st.subheader("All Transactions")
                st.dataframe(df.drop(columns=["id"]))

            elif view == "📈 By Category":
                st.subheader("Expenses by Category")
                expense_df = df[df["type"] == "Expense"]

                if not expense_df.empty:
                    category_totals = expense_df.groupby("category")["amount"].sum().reset_index()
                    category_totals = category_totals.sort_values("amount", ascending=False)

                    st.bar_chart(category_totals.set_index("category"))

                    st.subheader("Category Breakdown")
                    for _, row in category_totals.iterrows():
                        st.write(f"**{row['category']}**: PKR {row['amount']:,.2f}")
                else:
                    st.info("No expenses recorded yet.")

                st.subheader("Income by Category")
                income_df = df[df["type"] == "Income"]

                if not income_df.empty:
                    income_category_totals = income_df.groupby("category")["amount"].sum().reset_index()
                    income_category_totals = income_category_totals.sort_values("amount", ascending=False)

                    for _, row in income_category_totals.iterrows():
                        st.write(f"**{row['category']}**: PKR {row['amount']:,.2f}")
                else:
                    st.info("No income recorded yet.")

            elif view == "❌ Delete":
                for idx, transaction in enumerate(transactions, start=1):
                    emoji = "➖" if transaction['type'] == "Expense" else "➕"
                    st.write(
                        f"{emoji} {transaction['date']} | {transaction['type']} | {transaction['category']} | PKR {transaction['amount']:,}")
                    if st.button(f"🗑 Delete Transaction {idx}", key=f"delete_{transaction['id']}"):
                        notion.pages.update(transaction["id"], archived=True)
                        st.success(f"Deleted transaction from {transaction['date']}")
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()
        else:
            st.info("❌ No transactions recorded yet.")

with col2:
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.success("Logged out successfully! 👋")
        time.sleep(2)
        st.rerun()