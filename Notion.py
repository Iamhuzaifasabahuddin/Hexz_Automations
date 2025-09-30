import time
from datetime import datetime

import pandas as pd
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
    st.title("🔑 Login")
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


main_tabs = st.tabs(["🚖 Add Ride", "📊 View Rides"])

with main_tabs[0]:
    st.header("🚖 Add a Ride")

    with st.form("ride_form", clear_on_submit=False):
        ride_date = st.date_input("Date", datetime.today())
        ride_time = st.time_input("Time", datetime.now().time())
        amount = st.number_input("Amount", min_value=0, step=50)

        preview = st.form_submit_button("Preview Ride")
        submitted = st.form_submit_button("Save Ride")

    if preview:
        st.info(f"Preview → {ride_date} at {ride_time.strftime('%I:%M %p')} | Amount: PKR{amount}")

    if submitted:
        month = ride_date.strftime("%B")
        formatted_time = ride_time.strftime("%I:%M %p")
        try:
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Name": {
                        "title": [
                            {"text": {"content": f"Ride {ride_date} {ride_time.strftime('%H:%M')}"}}
                        ]
                    },
                    "Date": {"date": {"start": ride_date.isoformat()}},
                    "Time": {"rich_text": [{"text": {"content": formatted_time}}]},
                    "Amount": {"number": amount},
                    "Month": {"rich_text": [{"text": {"content": month}}]},
                },
            )
            st.success("Ride saved to Notion! ✅")
        except Exception as e:
            st.error(f"Error: {e}")

with main_tabs[1]:
    st.header("📊 Ride Stats")

    @st.cache_data(ttl=120)
    def get_rides():
        data = notion.databases.query(database_id=database_id)
        rides = []
        for row in data["results"]:
            props = row["properties"]

            ride_date = props["Date"]["date"]["start"] if props["Date"]["date"] else None
            amount = props["Amount"]["number"] if props["Amount"]["number"] else 0
            month = (
                props["Month"]["rich_text"][0]["text"]["content"]
                if props["Month"]["rich_text"] else "Unknown"
            )
            rides.append({"date": ride_date, "amount": amount, "month": month})
        return rides

    rides = get_rides()

    if rides:
        df = pd.DataFrame(rides)
        df.index = range(1, len(rides) + 1)

        subtabs = st.tabs(["📋 All Data", "📅 By Month", "📊 Summary"])

        with subtabs[0]:
            st.subheader("All Ride Data")
            st.dataframe(df)

            month_totals = df.groupby("month")["amount"].sum().reset_index()
            st.subheader("Total per Month")
            st.bar_chart(month_totals.set_index("month"))

        with subtabs[1]:
            st.subheader("Filter by Month")
            unique_months = sorted(df["month"].unique())
            selected_month = st.selectbox("Choose a month", ["All"] + list(unique_months))

            if selected_month == "All":
                filtered_df = df
            else:
                filtered_df = df[df["month"] == selected_month]

            st.write(filtered_df)

            total = filtered_df["amount"].sum()
            avg = filtered_df["amount"].mean() if not filtered_df.empty else 0

            st.metric("💲 Total Spend", f"PKR{total:,.2f}")
            st.metric("💸 Average Spend", f"PKR{avg:,.2f}")

        with subtabs[2]:
            st.subheader("Overall Summary")
            total_spend = df["amount"].sum()
            avg_spend = df["amount"].mean()

            st.metric("💲 Total Spend (All Time)", f"PKR{total:,.2f}")
            st.metric("💸 Average Spend per Ride", f"PKR{avg_spend:,.2f}")

            month_totals = df.groupby("month")["amount"].sum().reset_index()
            st.bar_chart(month_totals.set_index("month"))

    else:
        st.info("❌ No rides recorded yet.")
