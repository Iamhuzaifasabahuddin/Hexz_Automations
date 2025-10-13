import time
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
from notion_client import Client

notion = Client(auth=st.secrets["notion_token"])
database_id = st.secrets["database_id"]
APP_PASSWORD = st.secrets["app_password"]

st.set_page_config(
    page_title="Hexz Ride App",
    page_icon="🚕",
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
    st.title("🔑 Hexz Drive Log Login")
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
    main_tabs = st.tabs(["🚖 Add Ride", "📊 View Rides"])

    with main_tabs[0]:
        st.header("🚖 Add a Ride")

        pkt = pytz.timezone("Asia/Karachi")
        now_pkt = datetime.now(pkt)

        with st.form("ride_form", clear_on_submit=False):
            ride_date = st.date_input("Date", now_pkt.date())
            ride_time = st.time_input("Time", now_pkt.time(), key="ride_time")
            amount = st.number_input("Amount", min_value=0, step=50)

            preview = st.form_submit_button("Preview Ride")
            submitted = st.form_submit_button("Save Ride")

        if preview:
            ride_dt = datetime.combine(ride_date, ride_time)
            ride_dt_pkt = pkt.localize(ride_dt)
            formatted_dt = ride_dt_pkt.strftime("%d-%m-%Y at %I:%M %p")
            st.info(f"Preview → {formatted_dt} | Amount: PKR {amount:,}")
        if submitted:
            if not ride_date or not ride_time or amount <= 0:
                st.warning("⚠️ Please provide a valid date, time, and amount before saving.")
            else:
                month = ride_date.strftime("%B")
                formatted_time = ride_time.strftime("%I:%M %p")
                page_title = f"Ride {ride_date} {ride_time.strftime('%H:%M')}"

                try:
                    response = notion.pages.create(
                        parent={"database_id": database_id},
                        properties={
                            "Name": {
                                "title": [
                                    {"text": {"content": page_title}}
                                ]
                            },
                            "Date": {"date": {"start": ride_date.isoformat()}},
                            "Time": {"rich_text": [{"text": {"content": formatted_time}}]},
                            "Amount": {"number": amount},
                            "Month": {"rich_text": [{"text": {"content": month}}]},
                        },
                    )
                    if response and response.get("id"):
                        st.success(f"✅ Ride saved to Notion successfully!\n\n**Title:** {page_title} for PKR {amount}")
                    else:
                        st.warning("⚠️ Ride creation request sent, but no confirmation received from Notion.")
                except Exception as e:
                    st.error(f"Error: {e}")
    with main_tabs[1]:
        st.header("📊 Ride Stats")

        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()


        @st.cache_data(ttl=120)
        def get_rides():
            rides = []
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

                    ride_date = props["Date"]["date"]["start"] if props["Date"]["date"] else None
                    amount = props["Amount"]["number"] if props["Amount"]["number"] else 0
                    month = (
                        props["Month"]["rich_text"][0]["text"]["content"]
                        if props["Month"]["rich_text"] else "Unknown"
                    )
                    ride_time = (
                        props["Time"]["rich_text"][0]["text"]["content"]
                        if props["Time"]["rich_text"] else "Unknown"
                    )

                    rides.append({
                        "id": row["id"],
                        "date": ride_date,
                        "time": ride_time,
                        "amount": amount,
                    })
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

            return rides


        rides = get_rides()

        if rides:
            df = pd.DataFrame(rides)

            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["month"] = df["date"].dt.strftime("%B")
            df["year"] = df["date"].dt.year

            df = df.sort_values(by="date", ascending=True)
            df["date"] = df["date"].dt.strftime("%d-%B-%Y")
            df.index = range(1, len(df) + 1)
            unique_years = sorted(df["year"].dropna().unique(), reverse=True)
            unique_months = sorted(df["month"].dropna().unique())

            view = st.radio(
                "Select View",
                ["📅 By Month", "📋 All Data", "📊 Summary", "❌ Delete"],
                horizontal=True
            )

            if view == "📋 All Data":
                st.subheader("All Ride Data")
                st.dataframe(df.drop(columns=["id"]))

                month_totals = df.groupby(["year", "month"])["amount"].sum().reset_index()
                st.subheader("Total per Month")
                st.bar_chart(month_totals.set_index("month"))

                month_totals = month_totals.sort_values(by="amount", ascending=False)
                month_totals.index = range(1, len(month_totals) + 1)
                st.dataframe(month_totals)

            elif view == "📅 By Month":
                st.subheader("Filter by Month and Year")


                current_month = datetime.now(pkt).strftime("%B")
                current_year = datetime.now(pkt).year

                months = ["All"] + unique_months
                default_month_idx = unique_months.index(current_month) + 1 if current_month in unique_months else 0
                selected_month = st.selectbox("Select Month", months, index=default_month_idx)

                selected_year = st.number_input("Select Year", value=current_year, min_value=2025, max_value=current_year)

                if selected_month == "All":
                    filtered_df = df[df["year"] == selected_year]
                else:
                    filtered_df = df[(df["year"] == selected_year) & (df["month"] == selected_month)]

                st.write(filtered_df.drop(columns=["id"]))

                total = filtered_df["amount"].sum()
                avg = filtered_df["amount"].mean() if not filtered_df.empty else 0

                st.metric("💲 Total Spend", f"PKR{total:,.2f}")
                st.metric("💸 Average Spend", f"PKR{avg:,.2f}")

            elif view == "📊 Summary":
                st.subheader("Overall Summary")
                total_spend = df["amount"].sum()
                avg_spend = df["amount"].mean()

                st.metric("💲 Total Spend (All Time)", f"PKR {total_spend:,.2f}")
                st.metric("💸 Average Spend per Ride", f"PKR {avg_spend:,.2f}")

                month_totals = df.groupby(["year", "month"])["amount"].sum().reset_index()
                st.bar_chart(month_totals.set_index("month"))

            elif view == "❌ Delete":
                st.subheader("Delete Rides by Month/Year")

                current_month = datetime.now(pkt).strftime("%B")
                current_year = datetime.now(pkt).year


                months = ["All"] + unique_months
                default_month_idx = unique_months.index(current_month) + 1 if current_month in unique_months else 0
                selected_month = st.selectbox("Select Month", months, index=default_month_idx, key="delete_box")
                selected_year = st.number_input("Select Year", value=current_year, min_value=2025, max_value=current_year)
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                if selected_month == "All":
                    filtered_df = df[df["year"] == selected_year]
                else:
                    filtered_df = df[(df["year"] == selected_year) & (df["month"] == selected_month)]

                if filtered_df.empty:
                    st.info("No rides found for the selected filters.")
                else:
                    for idx, (_, ride) in enumerate(filtered_df.iterrows(), start=1):
                        with st.expander(
                                f"{ride['date'].strftime('%d-%b-%Y')} @ {ride['time']}| PKR{ride['amount']} | {ride['month']} {ride['year']}"):
                            if st.button("🗑 Delete Ride", key=f"delete_{ride['id']}"):
                                try:
                                    notion.pages.update(ride["id"], archived=True)
                                    st.success(f"Deleted ride from {ride['date'].strftime('%d-%b-%Y')} @ {ride['time']}")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting ride: {e}")

        else:
            st.info("❌ No rides recorded yet.")

        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.success("Logged out successfully! 👋")
            time.sleep(2)
            st.rerun()