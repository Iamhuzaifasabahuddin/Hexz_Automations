import time
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
import streamlit_authenticator as stauth
from notion_client import Client

# Initialize Notion client
notion = Client(auth=st.secrets["notion_token_3"])
database_id = st.secrets["database_id_3"]
datasource_id = st.secrets["data_source_id_3"]

st.set_page_config(
    page_title="Hexz Personal Budget Tracker",
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

config = {
    'credentials': {
        'usernames': {
            st.secrets["auth_username_hexz"]: {
                'name': st.secrets["auth_name_hexz"],
                'email': st.secrets["auth_email_hexz"],
                'password': st.secrets["auth_password_hexz"]
            }
        }
    },
    'cookie': {
        'name': st.secrets.get("cookie_name", "hexz_budget_cookie"),
        'key': st.secrets["cookie_key"],
        'expiry_days': st.secrets.get("cookie_expiry_days", 30)
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

if st.session_state.get('authentication_status') is None:
    st.title("🔑 Hexz Budget Tracker Login")
authenticator.login()

if st.session_state.get('authentication_status') is True:

    st.title(f"💰 Welcome {st.session_state.get('name')}!")


    main_tabs = st.tabs(["💸 Add Transaction", "📊 View Budget", "🔍 Search & Filter"])

    with main_tabs[0]:
        st.header("💸 Add a Transaction")

        pkt = pytz.timezone("Asia/Karachi")
        now_pkt = datetime.now(pkt)

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
                "Savings",
                "Other"
            ])
        else:
            category = st.selectbox("Category", [
                "Salary",
                "Freelance",
                "Bonus",
                "Investment",
                "Gift",
                "Other"
            ])

        with st.form("transaction_form", clear_on_submit=False):
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
            if amount > 0 and category and transaction_type:
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
                    st.success(
                        f"{transaction_type} - {category} @ {transaction_date} - {formatted_time} saved to Notion! ✅")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Missing or Invalid Data Detected!")

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
                    data = notion.data_sources.query(
                        data_source_id=datasource_id,
                        start_cursor=start_cursor
                    )
                else:
                    data = notion.data_sources.query(data_source_id=datasource_id)

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
                ["📅 By Month", "📊 Dashboard", "📋 All Data", "📈 By Category", "❌ Delete"],
                horizontal=True
            )

            if view == "📊 Dashboard":
                st.subheader("Financial Dashboard")
                total_income = df[df["type"] == "Income"]["amount"].sum()
                total_expense = df[df["type"] == "Expense"]["amount"].sum()
                savings = df[df["category"] == "Savings"]["amount"].sum()
                net_balance = total_income - total_expense

                expense_df = df[df["type"] == "Expense"]
                income_df = df[df["type"] == "Income"]

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("💰 Total Income", f"PKR {total_income:,.2f}")
                col_b.metric("💸 Total Expenses", f"PKR {total_expense:,.2f}")
                col_a.metric("💹 Total Savings", f"PKR {savings:,.2f}",
                             delta=f"{savings / total_income * 100:.1f}%" if total_income > 0 else "0%")
                col_c.metric(
                    "💵 Net Balance",
                    f"PKR {net_balance:,.2f}",
                    delta=f"{net_balance:,.2f}",
                    delta_arrow="off"
                )

                st.subheader("Income vs Expenses by Month")
                month_summary = df.groupby(["month", "type"])["amount"].sum().reset_index()
                month_pivot = month_summary.pivot(index="month", columns="type", values="amount").fillna(0)
                st.bar_chart(month_pivot)
                month_summary.index = range(1, len(month_summary) + 1)
                month_summary["amount"] = month_summary["amount"].map("PKR {:,.2f}".format)
                st.dataframe(month_summary)

                if not expense_df.empty:
                    category_totals_expense = (
                        expense_df.groupby("category")["amount"]
                        .sum()
                        .reset_index()
                        .sort_values("amount", ascending=False)
                    )
                    st.subheader("Expenses by Category")
                    st.bar_chart(category_totals_expense.set_index("category"))

                    st.subheader("Expense Breakdown")
                    exp_cols = st.columns(min(len(category_totals_expense), 3))
                    for i, (_, row) in enumerate(category_totals_expense.iterrows()):
                        col = exp_cols[i % len(exp_cols)]
                        col.metric(
                            label=row["category"],
                            value=f"PKR {row['amount']:,.2f}"
                        )
                else:
                    st.info("No expenses recorded yet.")

                if not income_df.empty:
                    category_totals_income = (
                        income_df.groupby("category")["amount"]
                        .sum()
                        .reset_index()
                        .sort_values("amount", ascending=False)
                    )
                    st.subheader("Income by Category")
                    st.bar_chart(category_totals_income.set_index("category"))

                    st.subheader("Income Breakdown")
                    inc_cols = st.columns(min(len(category_totals_income), 3))
                    for i, (_, row) in enumerate(category_totals_income.iterrows()):
                        col = inc_cols[i % len(inc_cols)]
                        col.metric(
                            label=row["category"],
                            value=f"PKR {row['amount']:,.2f}"
                        )
                else:
                    st.info("No income recorded yet.")

            elif view == "📅 By Month":
                st.subheader("Filter by Month")

                pkt = pytz.timezone("Asia/Karachi")
                unique_months = sorted(df["month"].unique())
                months = ["All"] + list(unique_months)
                current_month = datetime.now(pkt).strftime("%B %Y")
                if current_month in unique_months:
                    default_index = unique_months.index(current_month) + 1
                else:
                    default_index = 0
                selected_month = st.selectbox("Choose a month", months, index=default_index)
                if selected_month == "All":
                    filtered_df = df
                else:
                    filtered_df = df[df["month"] == selected_month]

                filtered_df.index = range(1, len(filtered_df) + 1)
                df_show = filtered_df.copy()

                df_show["amount"] = df_show["amount"].map("PKR {:,.2f}".format)
                st.write(df_show.drop(columns=["id"]))

                income = filtered_df[filtered_df["type"] == "Income"]["amount"].sum()
                expense = filtered_df[filtered_df["type"] == "Expense"]["amount"].sum()
                savings = filtered_df[filtered_df["category"] == "Savings"]["amount"].sum()
                balance = income - expense

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("💰 Income", f"PKR {income:,.2f}")
                col_b.metric("💸 Expenses", f"PKR {expense:,.2f}")
                col_c.metric("💵 Balance", f"PKR {balance:,.2f}")
                col_a.metric("💹 Savings", f"PKR {savings:,.2f}")

            elif view == "📋 All Data":
                st.subheader("All Transactions")
                df_show = df.copy()
                df_show["amount"] = df_show["amount"].map("PKR {:,.2f}".format)
                st.dataframe(df_show.drop(columns=["id"]))

            elif view == "📈 By Category":
                st.subheader("Expenses by Category")

                expense_df = df[df["type"] == "Expense"]

                if not expense_df.empty:
                    category_totals = (
                        expense_df.groupby("category")["amount"]
                        .sum()
                        .reset_index()
                        .sort_values("amount", ascending=False)
                    )
                    st.bar_chart(category_totals.set_index("category"))
                else:
                    st.info("No expenses recorded yet.")

                st.subheader("Income by Category")

                income_df = df[df["type"] == "Income"]

                if not income_df.empty:
                    income_category_totals = (
                        income_df.groupby("category")["amount"]
                        .sum()
                        .reset_index()
                        .sort_values("amount", ascending=False)
                    )
                    st.bar_chart(income_category_totals.set_index("category"))
                else:
                    st.info("No income recorded yet.")

                if not expense_df.empty:
                    st.subheader("Expense Breakdown")
                    exp_cols = st.columns(min(len(category_totals), 3))
                    for i, (_, row) in enumerate(category_totals.iterrows()):
                        col = exp_cols[i % len(exp_cols)]
                        col.metric(
                            label=row["category"],
                            value=f"PKR {row['amount']:,.2f}"
                        )

                if not income_df.empty:
                    st.subheader("Income Breakdown")
                    inc_cols = st.columns(min(len(income_category_totals), 3))
                    for i, (_, row) in enumerate(income_category_totals.iterrows()):
                        col = inc_cols[i % len(inc_cols)]
                        col.metric(
                            label=row["category"],
                            value=f"PKR {row['amount']:,.2f}"
                        )

            elif view == "❌ Delete":
                st.subheader("Delete Transactions")


                def parse_date(date_value):
                    if isinstance(date_value, datetime):
                        return date_value
                    return pd.to_datetime(date_value, errors="coerce")


                with st.expander("💸 Expenses", expanded=True):
                    expense_transactions = [
                        {**t, "parsed_date": parse_date(t["date"])}
                        for t in transactions if t["type"] == "Expense"
                    ]

                    if expense_transactions:
                        expense_df = pd.DataFrame(expense_transactions)
                        expense_df["month"] = expense_df["parsed_date"].dt.to_period("M")
                        expense_df = expense_df.sort_values("parsed_date", ascending=False)

                        for month, month_df in expense_df.groupby("month"):
                            with st.expander(f"📅 {month.strftime('%B %Y')}"):
                                for idx, transaction in month_df.iterrows():
                                    with st.container():
                                        st.markdown(
                                            f"**➖ {transaction['parsed_date'].strftime('%d %B %Y')}**  \n"
                                            f"Category: {transaction['category']}  |  "
                                            f"Amount: PKR {transaction['amount']:,}"
                                        )

                                        if st.button(
                                                "🗑 Delete Expense",
                                                key=f"delete_exp_{transaction['id']}"
                                        ):
                                            notion.pages.update(transaction["id"], archived=True)
                                            st.success("Expense deleted successfully")
                                            st.cache_data.clear()
                                            time.sleep(1)
                                            st.rerun()
                    else:
                        st.info("No expenses recorded yet.")

                with st.expander("🤑 Income", expanded=True):
                    income_transactions = [
                        {**t, "parsed_date": parse_date(t["date"])}
                        for t in transactions if t["type"] == "Income"
                    ]

                    if income_transactions:
                        income_df = pd.DataFrame(income_transactions)
                        income_df["month"] = income_df["parsed_date"].dt.to_period("M")
                        income_df = income_df.sort_values("parsed_date", ascending=False)
                        for month, month_df in income_df.groupby("month"):
                            with st.expander(f"📅 {month.strftime('%B %Y')}"):
                                for idx, transaction in month_df.iterrows():
                                    with st.container():
                                        st.markdown(
                                            f"**➕ {transaction['parsed_date'].strftime('%d %B %Y')}**  \n"
                                            f"Category: {transaction['category']}  |  "
                                            f"Amount: PKR {transaction['amount']:,}"
                                        )

                                        if st.button(
                                                "🗑 Delete Income",
                                                key=f"delete_inc_{transaction['id']}"
                                        ):
                                            notion.pages.update(transaction["id"], archived=True)
                                            st.success("Income deleted successfully")
                                            st.cache_data.clear()
                                            time.sleep(1)
                                            st.rerun()
                    else:
                        st.info("No income recorded yet.")
        else:
            st.info("❌ No transactions recorded yet.")

    with main_tabs[2]:
        st.header("🔍 Search & Filter Transactions")

        if st.button("🔄 Refresh Data", key="refresh_search"):
            st.cache_data.clear()
            st.rerun()

        transactions = get_transactions()

        if transactions:
            df = pd.DataFrame(transactions)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.sort_values(by="date", ascending=False)

            st.subheader("Filter Options")

            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:

                st.write("**Date Range**")
                use_date_range = st.checkbox("Filter by date range")

                if use_date_range:
                    min_date = df["date"].min().date()
                    max_date = df["date"].max().date()

                    date_from = st.date_input(
                        "From",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="date_from"
                    )
                    date_to = st.date_input(
                        "To",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="date_to"
                    )


                st.write("**Transaction Type**")
                transaction_types = ["All", "Income", "Expense"]
                selected_type = st.selectbox("Select Type", transaction_types)

            with filter_col2:

                st.write("**Amount Range**")
                use_amount_range = st.checkbox("Filter by amount")

                if use_amount_range:
                    min_amount = int(df["amount"].min())
                    max_amount = int(df["amount"].max())

                    amount_range = st.slider(
                        "Select amount range (PKR)",
                        min_value=min_amount,
                        max_value=max_amount,
                        value=(min_amount, max_amount),
                        step=50
                    )


                st.write("**Category**")
                categories = ["All"] + sorted(df["category"].unique().tolist())
                selected_category = st.selectbox("Select Category", categories)


            filtered_df = df.copy()

            if use_date_range:
                filtered_df = filtered_df[
                    (filtered_df["date"].dt.date >= date_from) &
                    (filtered_df["date"].dt.date <= date_to)
                    ]

            if use_amount_range:
                filtered_df = filtered_df[
                    (filtered_df["amount"] >= amount_range[0]) &
                    (filtered_df["amount"] <= amount_range[1])
                    ]

            if selected_type != "All":
                filtered_df = filtered_df[filtered_df["type"] == selected_type]

            if selected_category != "All":
                filtered_df = filtered_df[filtered_df["category"] == selected_category]


            st.subheader(f"Results ({len(filtered_df)} transactions found)")

            if not filtered_df.empty:

                col1, col2 = st.columns(2)

                total_income = filtered_df[filtered_df["type"] == "Income"]["amount"].sum()
                total_expense = filtered_df[filtered_df["type"] == "Expense"]["amount"].sum()
                total_savings = filtered_df[filtered_df["category"] == "Savings"]["amount"].sum()
                net_balance = total_income - total_expense

                with col1:
                    st.metric("💰 Total Income", f"PKR {total_income:,.2f}")
                    st.metric("💸 Total Expenses", f"PKR {total_expense:,.2f}")
                    st.metric("🤑 Total Savings", f"PKR {total_savings:,.2f}")

                with col2:
                    st.metric("💵 Net Balance", f"PKR {net_balance:,.2f}")
                    st.metric("📊 Count", len(filtered_df))


                filtered_df["date_display"] = filtered_df["date"].dt.strftime("%d-%B-%Y")
                display_df = filtered_df[["date_display", "time", "type", "category", "amount", "description"]].copy()
                display_df.columns = ["Date", "Time", "Type", "Category", "Amount (PKR)", "Description"]
                display_df.index = range(1, len(display_df) + 1)

                st.dataframe(display_df, width="stretch")


                st.subheader("Visual Analysis")

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    st.write("**Spending Over Time**")
                    chart_df = filtered_df.groupby(filtered_df["date"].dt.date)["amount"].sum().reset_index()
                    chart_df.columns = ["Date", "Amount"]
                    st.line_chart(chart_df.set_index("Date"))

                with chart_col2:
                    st.write("**Amount by Category**")
                    category_chart = filtered_df.groupby("category")["amount"].sum().reset_index()
                    category_chart = category_chart.sort_values("amount", ascending=False)
                    st.bar_chart(category_chart.set_index("category"))


                if selected_type == "All":
                    st.subheader("Income vs Expenses")
                    type_summary = filtered_df.groupby("type")["amount"].sum().reset_index()
                    st.bar_chart(type_summary.set_index("type"))

            else:
                st.info("No transactions match your filters.")
        else:
            st.info("❌ No transactions recorded yet.")

elif st.session_state.get('authentication_status') is False:
    st.error('Username/password is incorrect')
    st.stop()
elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
    st.stop()