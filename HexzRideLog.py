import time
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st
import extra_streamlit_components as stx
from notion_client import Client
import hashlib


def setup_page():
    """Configure Streamlit page settings"""
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


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


class CookieAuth:
    """Handle cookie-based passwordless authentication with password fallback"""

    def __init__(self):
        self.cookie_manager = stx.CookieManager()
        self.cookie_name = st.secrets.get("cookie_name", "hexz_budget_cookie")
        self.cookie_key = st.secrets.get("cookie_key", "secret_key")
        self.expiry_days = int(st.secrets.get("cookie_expiry_days", 30))
        self.username = st.secrets.get("auth_username_hexz", "hexz")
        self.user_name = st.secrets.get("auth_name_hexz", "Hexz User")
        self.password_hash = st.secrets.get("auth_password_hexz", "")

    def generate_token(self):
        """Generate a secure token"""
        timestamp = datetime.now().isoformat()
        data = f"{self.username}:{self.cookie_key}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_token(self, token):
        """Verify if token is valid"""
        return len(token) == 64 and token.isalnum()

    def verify_password(self, password):
        """Verify password against hash"""
        return hash_password(password) == self.password_hash

    def set_auth_cookie(self):
        """Set authentication cookie"""
        token = self.generate_token()
        expiry = datetime.now() + timedelta(days=self.expiry_days)

        self.cookie_manager.set(
            self.cookie_name,
            token,
            expires_at=expiry
        )

        st.session_state.authentication_status = True
        st.session_state.username = self.username
        st.session_state.name = self.user_name

    def check_cookie(self):
        """Check if valid cookie exists"""
        cookies = self.cookie_manager.get_all()

        if self.cookie_name in cookies:
            token = cookies[self.cookie_name]

            if self.verify_token(token):
                st.session_state.authentication_status = True
                st.session_state.username = self.username
                st.session_state.name = self.user_name
                return True

        return False

    def is_authenticated(self):
        """Check if user is authenticated"""
        if st.session_state.get('authentication_status') is False:
            return False

        if st.session_state.get('authentication_status') is True:
            return True
        return self.check_cookie()

    def logout(self):
        """Clear authentication"""
        self.cookie_manager.delete(self.cookie_name)
        st.session_state.authentication_status = False
        st.session_state.username = None
        st.session_state.name = None


def login_page(auth):
    """Display login page"""
    st.title("🔑 Hexz Ride Tracker Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if username == auth.username and auth.verify_password(password):
                auth.set_auth_cookie()
                st.success("✅ Login successful!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


class NotionService:
    """Handle all Notion API interactions"""

    def __init__(self):
        self.notion_token = st.secrets["notion_token"]
        self.datasource_id = st.secrets["datasource_id"]
        self.client = self._get_client()

    @staticmethod
    @st.cache_resource
    def _get_client():
        """Create and cache Notion client"""
        try:
            return Client(auth=st.secrets["notion_token"])
        except Exception as e:
            st.error(f"Failed to initialize Notion client: {e}")
            return None

    @st.cache_data(ttl=300)
    def get_rides(_self, month=None):
        """
        Fetch rides from Notion with optional month filter.

        Args:
            month: Filter by month name only (e.g., "January"). If None, fetches all rides.
        """
        rides = []
        has_more = True
        start_cursor = None

        try:
            while has_more:
                query_params = {"data_source_id": _self.datasource_id}

                if month:
                    query_params["filter"] = {
                        "property": "Month",
                        "rich_text": {
                            "equals": month
                        }
                    }

                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                data = _self.client.data_sources.query(**query_params)

                for row in data["results"]:
                    props = row["properties"]
                    rides.append({
                        "id": row["id"],
                        "date": props["Date"]["date"]["start"] if props["Date"]["date"] else None,
                        "time": props["Time"]["rich_text"][0]["text"]["content"] if props["Time"][
                            "rich_text"] else "Unknown",
                        "amount": props["Amount"]["number"] if props["Amount"]["number"] else 0,
                    })

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

            return rides
        except Exception as e:
            st.error(f"Error fetching rides: {e}")
            return []

    def save_ride(self, ride_date, ride_time, amount):
        """Save ride to Notion"""
        month = ride_date.strftime("%B %Y")
        formatted_time = ride_time.strftime("%I:%M %p")
        page_title = f"Ride {ride_date} {ride_time.strftime('%H:%M')}"

        try:
            response = self.client.pages.create(
                parent={"data_source_id": self.datasource_id},
                properties={
                    "Name": {"title": [{"text": {"content": page_title}}]},
                    "Date": {"date": {"start": ride_date.isoformat()}},
                    "Time": {"rich_text": [{"text": {"content": formatted_time}}]},
                    "Amount": {"number": amount},
                    "Month": {"rich_text": [{"text": {"content": month}}]},
                },
            )
            if response and response.get("id"):
                st.success(f"✅ Ride saved to Notion successfully!\n\n**Title:** {page_title} for PKR {amount:,.2f}")
                st.cache_data.clear()
                return True
            else:
                st.warning("⚠️ Ride creation request sent, but no confirmation received from Notion.")
                return False
        except Exception as e:
            st.error(f"Error: {e}")
            return False

    def delete_ride(self, ride_id):
        """Archive a ride in Notion"""
        try:
            self.client.pages.update(ride_id, archived=True)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error deleting ride: {e}")
            return False


def render_add_ride_tab(notion_service):
    """Render the Add Ride tab"""
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
        formatted_dt = ride_dt_pkt.strftime("%d-%B-%Y at %I:%M %p")
        st.info(f"Preview → {formatted_dt} | Amount: PKR {amount:,}")

    if submitted:
        if not ride_date or not ride_time or amount <= 0:
            st.warning("⚠️ Please provide a valid date, time, and amount before saving.")
        else:
            notion_service.save_ride(ride_date, ride_time, amount)


def render_all_data(df):
    """Render all data view"""
    st.subheader("All Ride Data")
    display_df = df.drop(columns=["id", "date"]).rename(columns={"date_display": "date"})
    st.dataframe(display_df)

    month_totals = df.groupby(["year", "month"])["amount"].sum().reset_index()
    st.subheader("Total per Month")
    st.bar_chart(month_totals.set_index("month"))

    month_totals = month_totals.sort_values(by="amount", ascending=False)
    month_totals.index = range(1, len(month_totals) + 1)
    st.dataframe(month_totals)


def render_by_month(notion_service):
    """Render by month view with separate Month and Year selectors, fetching filtered data from Notion"""
    st.subheader("Filter by Month and Year")

    pkt = pytz.timezone("Asia/Karachi")
    now_pkt = datetime.now(pkt)

    current_year = now_pkt.year
    years = list(range(2025, current_year + 1))

    col1, col2 = st.columns(2)
    with col1:
        selected_month_name = st.selectbox(
            "Month",
            MONTHS,
            index=now_pkt.month - 1
        )
    with col2:
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(current_year)
        )

    with st.spinner(f"Loading rides for {selected_month_name} {selected_year}..."):
        rides = notion_service.get_rides(month=f"{selected_month_name} {selected_year}")

    if not rides:
        st.info(f"No rides found for {selected_month_name} {selected_year}.")
        return

    df = pd.DataFrame(rides)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.strftime("%B")
    df["year"] = df["date"].dt.year
    df["date_display"] = df["date"].dt.strftime("%d-%B-%Y")

    filtered_df = df[df["year"] == selected_year]

    if filtered_df.empty:
        st.info(f"No rides found for {selected_month_name} {selected_year}.")
        return

    filtered_df = filtered_df.sort_values(by="date", ascending=True)
    filtered_df.index = range(1, len(filtered_df) + 1)

    display_df = filtered_df.drop(columns=["id", "date"]).rename(columns={"date_display": "date"})
    st.write(display_df)

    total = filtered_df["amount"].sum()
    avg = filtered_df["amount"].mean() if not filtered_df.empty else 0

    st.metric("💲 Total Spend", f"PKR {total:,.2f}")
    st.metric("💸 Average Spend", f"PKR {avg:,.2f}")


def render_summary(df):
    """Render summary view"""
    st.subheader("Overall Summary")
    total_spend = df["amount"].sum()
    avg_spend = df["amount"].mean()

    st.metric("💲 Total Spend (All Time)", f"PKR {total_spend:,.2f}")
    st.metric("💸 Average Spend per Ride", f"PKR {avg_spend:,.2f}")

    month_totals = df.groupby(["year", "month"])["amount"].sum().reset_index()
    st.bar_chart(month_totals.set_index("month"))


def render_delete(notion_service):
    """Render delete rides view with separate Month and Year selectors"""
    st.subheader("Delete Rides by Month/Year")

    pkt = pytz.timezone("Asia/Karachi")
    now_pkt = datetime.now(pkt)

    current_year = now_pkt.year
    years = list(range(2025, current_year + 1))

    col1, col2 = st.columns(2)
    with col1:
        selected_month_name = st.selectbox(
            "Month",
            MONTHS,
            index=now_pkt.month - 1,
            key="delete_month"
        )
    with col2:
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(current_year),
            key="delete_year"
        )

    with st.spinner(f"Loading rides for {selected_month_name} {selected_year}..."):
        rides = notion_service.get_rides(month=f"{selected_month_name} {selected_year}")

    if not rides:
        st.info(f"No rides found for {selected_month_name} {selected_year}.")
        return

    df = pd.DataFrame(rides)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.strftime("%B")
    df["year"] = df["date"].dt.year
    df["date_display"] = df["date"].dt.strftime("%d-%B-%Y")

    filtered_df = df[df["year"] == selected_year]

    if filtered_df.empty:
        st.info(f"No rides found for {selected_month_name} {selected_year}.")
        return

    for _, ride in filtered_df.iterrows():
        with st.expander(
                f"{ride['date'].strftime('%d-%b-%Y')} @ {ride['time']} | PKR {ride['amount']} | {ride['month']} {ride['year']}"):
            if st.button("🗑 Delete Ride", key=f"delete_{ride['id']}"):
                if notion_service.delete_ride(ride["id"]):
                    st.success(f"Deleted ride from {ride['date'].strftime('%d-%b-%Y')} @ {ride['time']}")
                    time.sleep(1)
                    st.rerun()


def render_view_rides_tab(notion_service):
    """Render the View Rides tab"""
    st.header("📊 Ride Stats")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    view = st.radio("Select View", ["📅 By Month", "📋 All Data", "📊 Summary", "❌ Delete"], horizontal=True)

    if view == "📅 By Month":
        render_by_month(notion_service)
    elif view == "❌ Delete":
        render_delete(notion_service)
    else:
        rides = notion_service.get_rides()

        if rides:
            df = pd.DataFrame(rides)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["month"] = df["date"].dt.strftime("%B")
            df["year"] = df["date"].dt.year
            df = df.sort_values(by="date", ascending=True)
            df["date_display"] = df["date"].dt.strftime("%d-%B-%Y")
            df.index = range(1, len(df) + 1)

            if view == "📋 All Data":
                render_all_data(df)
            elif view == "📊 Summary":
                render_summary(df)
        else:
            st.info("❌ No rides recorded yet.")


def render_search_filter_tab(notion_service):
    """Render the Search & Filter tab"""
    st.header("🔍 Search & Filter Rides")

    if st.button("🔄 Refresh Data", key="refresh_search"):
        st.cache_data.clear()
        st.rerun()

    rides = notion_service.get_rides()

    if rides:
        df = pd.DataFrame(rides)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month"] = df["date"].dt.strftime("%B")
        df["year"] = df["date"].dt.year
        df = df.sort_values(by="date", ascending=False)

        st.subheader("Filter Options")
        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            st.write("**Date Range**")
            use_date_range = st.checkbox("Filter by date range")
            if use_date_range:
                min_date = df["date"].min().date()
                max_date = df["date"].max().date()
                date_from = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date,
                                          key="date_from")
                date_to = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date, key="date_to")

        with filter_col2:
            st.write("**Amount Range**")
            use_amount_range = st.checkbox("Filter by amount")
            if use_amount_range:
                min_amount = int(df["amount"].min())
                max_amount = int(df["amount"].max())
                amount_range = st.slider("Select amount range (PKR)", min_value=min_amount, max_value=max_amount,
                                         value=(min_amount, max_amount), step=50)

        filtered_df = df.copy()
        if use_date_range:
            filtered_df = filtered_df[
                (filtered_df["date"].dt.date >= date_from) & (filtered_df["date"].dt.date <= date_to)]
        if use_amount_range:
            filtered_df = filtered_df[
                (filtered_df["amount"] >= amount_range[0]) & (filtered_df["amount"] <= amount_range[1])]

        st.subheader(f"Results ({len(filtered_df)} rides found)")

        if not filtered_df.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Amount", f"PKR {filtered_df['amount'].sum():,.2f}")
                st.metric("Average Amount", f"PKR {filtered_df['amount'].mean():,.2f}")
            with col3:
                st.metric("Number of Rides", len(filtered_df))

            filtered_df["date_display"] = filtered_df["date"].dt.strftime("%d-%B-%Y")
            display_df = filtered_df[["date_display", "time", "amount", "month", "year"]].copy()
            display_df.columns = ["Date", "Time", "Amount (PKR)", "Month", "Year"]
            display_df.index = range(1, len(display_df) + 1)
            st.dataframe(display_df, width="stretch")

            st.subheader("Spending Over Time")
            chart_df = filtered_df.groupby(filtered_df["date"].dt.date)["amount"].sum().reset_index()
            chart_df.columns = ["Date", "Amount"]
            st.line_chart(chart_df.set_index("Date"))
        else:
            st.info("No rides match your filters.")
    else:
        st.info("❌ No rides recorded yet.")


def main():
    """Main application entry point"""
    setup_page()

    auth = CookieAuth()

    if not auth.is_authenticated():
        with st.spinner("🔄 Initializing secure session..."):
            time.sleep(1.5)
        login_page(auth)
        return

    st.title(f"💰 Welcome {st.session_state.get('name')}!")

    if st.button("🚪 Logout"):
        auth.logout()
        st.rerun()

    notion_service = NotionService()
    main_tabs = st.tabs(["🚖 Add Ride", "📊 View Rides", "🔍 Search & Filter"])

    with main_tabs[0]:
        render_add_ride_tab(notion_service)

    with main_tabs[1]:
        render_view_rides_tab(notion_service)

    with main_tabs[2]:
        render_search_filter_tab(notion_service)


if __name__ == "__main__":
    main()