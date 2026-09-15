import calendar
import hashlib
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import extra_streamlit_components as stx
import pandas as pd
import pytz
import streamlit as st
from notion_client import Client


def setup_page():
    """Configure Streamlit page settings"""
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
        .block-container {padding-top: 2rem;}
        [data-testid="stMetricValue"] {font-size: 1.15rem;}
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
    st.title("🔑 Hexz Budget Tracker Login")

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


EXPENSE_CATEGORIES = [
    "Rent", "Bills & Utilities", "Food & Dining", "Transportation", "Shopping",
    "Entertainment", "Healthcare", "Education", "Savings", "Physical Investments",
    "Stocks", "Mutual Funds", "Other"
]

INCOME_CATEGORIES = [
    "Salary", "Freelance", "Bonus", "Investment", "Gift", "Other"
]

SAVINGS_DEBIT_CATEGORIES = [
    "Shopping", "Food & Dining", "Transportation", "Entertainment",
    "Healthcare", "Education", "Travel", "Electronics", "Clothing", "Other"
]

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# ---------- Budget Allocation Plan ----------
# Share of monthly salary assigned to each bucket
BUDGET_ALLOCATIONS = {
    "Bills & Rent": 0.55,
    "Daily Life": 0.25,
    "Pro Investments": 0.10,
    "Savings": 0.10,
}

# Which spending categories count toward each bucket
BUCKET_CATEGORIES = {
    "Bills & Rent": ["Rent", "Bills & Utilities"],
    "Daily Life": [
        "Food & Dining", "Transportation", "Shopping", "Entertainment",
        "Healthcare", "Education", "Other"
    ],
    "Pro Investments": ["Physical Investments", "Stocks", "Mutual Funds"],
    "Savings": ["Savings"],
}

BUCKET_EMOJIS = {
    "Bills & Rent": "🏠",
    "Daily Life": "🛒",
    "Pro Investments": "📈",
    "Savings": "💳",
}


# ---------------------------------------------------------------------------
# Self-contained finance core (no cross-file imports so each tracker runs standalone
# on Streamlit Cloud as a single file).
# Why Decimal: Python float cannot represent currency exactly (0.1 + 0.2 != 0.3)
# and drifts over hundreds of transactions. All money is coerced via to_currency()
# at ingestion, all arithmetic happens in Decimal, float/str only at display.
# ---------------------------------------------------------------------------
PKT_TZ_NAME = "Asia/Karachi"
CENT = Decimal("0.01")
DEFAULT_SAVINGS_RATE_TARGET = 0.20


def to_currency(value) -> Decimal:
    """Convert to Decimal rounded to 2 places (ROUND_HALF_UP).

    Why it matters: float stores numbers in binary, so sums of float amounts
    drift by paisa. Converting via str() + quantize keeps totals exact.
    None/empty/invalid -> Decimal("0.00") so one bad row never poisons a month.
    """
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, bool):
        dec = Decimal(int(value))
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, float):
        dec = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip().replace(",", "").replace("PKR", "").strip()
        if not text:
            return Decimal("0.00")
        try:
            dec = Decimal(text)
        except InvalidOperation:
            return Decimal("0.00")
    else:
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0.00")
    if not dec.is_finite():
        return Decimal("0.00")
    return dec.quantize(CENT, rounding=ROUND_HALF_UP)


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, float) and pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_ratio(numerator, denominator) -> float:
    """Guarded division: numerator/denominator, 0.0 on zero/negative/missing denom.

    Why it matters: denominators (income, salary, target, prior-month spend)
    come from user data and are routinely zero. One helper avoids scattered
    inline ternaries that inevitably miss a spot (ZeroDivisionError / inf%).
    """
    denom = _to_float(denominator, default=0.0)
    if denom is None or denom <= 0:
        return 0.0
    num = _to_float(numerator, default=0.0)
    if num is None or pd.isna(num):
        return 0.0
    return num / denom


def _series_decimal_sum(series) -> Decimal:
    if series is None or len(series) == 0:
        return Decimal("0.00")
    total = Decimal("0.00")
    for v in series.tolist():
        try:
            if v is None:
                continue
            if isinstance(v, float) and pd.isna(v):
                continue
            if v is pd.NA:
                continue
        except Exception:
            pass
        total += to_currency(v)
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def format_pkr(value) -> str:
    return f"PKR {to_currency(value):,.2f}"


def compute_bucket_actuals(df):
    """Actual spend per bucket in Decimal; empty/missing cols -> zeros (no crash)."""
    result = {name: Decimal("0.00") for name in BUCKET_CATEGORIES}
    if df is None or len(df) == 0:
        return result
    if "type" not in df.columns or "category" not in df.columns or "amount" not in df.columns:
        return result
    for bucket, cats in BUCKET_CATEGORIES.items():
        try:
            mask = (df["type"] == "Expense") & (df["category"].isin(list(cats)))
            result[bucket] = _series_decimal_sum(df.loc[mask, "amount"])
        except Exception:
            result[bucket] = Decimal("0.00")
    try:
        gross = result.get("Savings", Decimal("0.00"))
        debits = _series_decimal_sum(df.loc[df["type"] == "Savings Debit", "amount"])
        result["Savings"] = (to_currency(gross) - to_currency(debits)).quantize(
            CENT, rounding=ROUND_HALF_UP)
    except Exception:
        pass
    return result


def build_allocation_frame(salary, actuals):
    """Allocation summary; Decimal arithmetic, floats only for display compat."""
    salary_dec = to_currency(salary)
    rows = []
    for name, pct in BUDGET_ALLOCATIONS.items():
        target = (salary_dec * to_currency(pct)).quantize(CENT, rounding=ROUND_HALF_UP)
        actual = to_currency(actuals.get(name, 0) if actuals else 0)
        remaining = (target - actual).quantize(CENT, rounding=ROUND_HALF_UP)
        ratio = safe_ratio(actual, target)
        rows.append({
            "Bucket": name,
            "Allocation": f"{_to_float(pct) * 100:.0f}%",
            "Target (PKR)": float(target),
            "Actual (PKR)": float(actual),
            "Remaining (PKR)": float(remaining),
            "Utilized": f"{ratio * 100:.1f}%" if _to_float(target) > 0 else "—",
        })
    return pd.DataFrame(rows, columns=[
        "Bucket", "Allocation", "Target (PKR)", "Actual (PKR)",
        "Remaining (PKR)", "Utilized",
    ])


# --- Spending pace / forecasting (YNAB-style "trending over") ---
def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(int(year), int(month))[1]


def pace_info(year: int, month: int, today=None) -> dict:
    """days_elapsed/days_in_month pace ratio; past=1.0, future=0.0, current=day/dim."""
    dim = days_in_month(year, month)
    if today is None:
        today = datetime.now(pytz.timezone(PKT_TZ_NAME)).date()
    if isinstance(today, datetime):
        today = today.date()
    if today.year == year and today.month == month:
        elapsed = max(1, min(today.day, dim))
        return {"days_elapsed": elapsed, "days_in_month": dim,
                "pace_ratio": elapsed / dim, "is_current_month": True}
    if (today.year, today.month) > (year, month):
        return {"days_elapsed": dim, "days_in_month": dim,
                "pace_ratio": 1.0, "is_current_month": False}
    return {"days_elapsed": 0, "days_in_month": dim,
            "pace_ratio": 0.0, "is_current_month": False}


def project_month_end_spend(actual_so_far, pace_ratio):
    """Projected month-end: actual / pace_ratio (Decimal); None if pace <= 0."""
    try:
        pace = float(pace_ratio)
    except (TypeError, ValueError):
        return None
    if pace <= 0:
        return None
    return (to_currency(actual_so_far) / Decimal(str(pace))).quantize(
        CENT, rounding=ROUND_HALF_UP)


def is_overshoot_projected(actual_so_far, target, pace_ratio,
                           is_current_month: bool = True) -> bool:
    """True when burn rate guarantees overshoot even though actual < target today.

    Why it matters: 80% of budget spent by day 12 looks "on track" on a plain
    ratio but is already doomed. Flagging projected > target is what separates
    a tracker from a real budgeting tool. Current month only.
    """
    if not is_current_month:
        return False
    try:
        pace = float(pace_ratio)
    except (TypeError, ValueError):
        return False
    if pace <= 0:
        return False
    target_dec = to_currency(target)
    if target_dec <= 0:
        return False
    projected = project_month_end_spend(actual_so_far, pace)
    if projected is None:
        return False
    return projected > target_dec


# --- Rolling trends / health / timezone helpers ---
def monthly_totals(df, value_col: str = "amount", type_filter="Expense"):
    if df is None or len(df) == 0 or "date" not in df.columns:
        return pd.Series(dtype=float)
    work = df.copy()
    work["_mk"] = pd.to_datetime(work["date"], errors="coerce").dt.strftime("%Y-%m")
    if type_filter is not None and "type" in work.columns:
        work = work[work["type"] == type_filter]
    work = work.dropna(subset=["_mk"])
    if work.empty:
        return pd.Series(dtype=float)
    return work.groupby("_mk")[value_col].apply(
        lambda s: float(_series_decimal_sum(s))).sort_index()


def rolling_average(monthly, window: int):
    if monthly is None or len(monthly) == 0:
        return pd.Series(dtype=float)
    return monthly.sort_index().rolling(window=int(window), min_periods=1).mean()


def mom_pct_change(current, previous):
    try:
        prev, cur = float(previous), float(current)
    except (TypeError, ValueError):
        return None
    if prev is None or prev <= 0:
        return None
    return (cur - prev) / prev


def yoy_comparison(df, year: int, type_filter="Expense") -> dict:
    """This year vs last year on the same months only (like-for-like)."""
    if df is None or len(df) == 0 or "date" not in df.columns:
        return {"months": [], "current": 0.0, "previous": 0.0,
                "delta": 0.0, "pct_change": None}
    work = df.copy()
    work["_dt"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["_dt"])
    if type_filter is not None and "type" in work.columns:
        work = work[work["type"] == type_filter]
    work["_y"] = work["_dt"].dt.year
    work["_m"] = work["_dt"].dt.month
    cur = work[work["_y"] == int(year)]
    prev = work[work["_y"] == int(year) - 1]
    months = sorted(set(cur["_m"].tolist()) & set(prev["_m"].tolist()))
    if not months:
        return {"months": [], "current": 0.0, "previous": 0.0,
                "delta": 0.0, "pct_change": None}
    cur_total = float(_series_decimal_sum(cur[cur["_m"].isin(months)]["amount"]))
    prev_total = float(_series_decimal_sum(prev[prev["_m"].isin(months)]["amount"]))
    return {"months": months, "current": cur_total, "previous": prev_total,
            "delta": cur_total - prev_total,
            "pct_change": mom_pct_change(cur_total, prev_total)}


def savings_rate(net_savings, total_income) -> float:
    return safe_ratio(net_savings, total_income)


def emergency_runway(total_savings_balance, avg_monthly_expense):
    try:
        avg = float(avg_monthly_expense)
    except (TypeError, ValueError):
        return None
    if avg is None or avg <= 0:
        return None
    try:
        bal = float(total_savings_balance)
    except (TypeError, ValueError):
        return None
    return bal / avg


def compute_financial_health(df, savings_target: float = DEFAULT_SAVINGS_RATE_TARGET) -> dict:
    empty = {"total_income": Decimal("0.00"), "total_expense": Decimal("0.00"),
             "gross_savings": Decimal("0.00"), "savings_debits": Decimal("0.00"),
             "net_savings": Decimal("0.00"), "net_balance": Decimal("0.00"),
             "savings_rate": 0.0, "savings_on_track": False,
             "avg_monthly_expense": Decimal("0.00"),
             "emergency_runway_months": None}
    if df is None or len(df) == 0 or "amount" not in df.columns:
        return empty
    types = df["type"] if "type" in df.columns else pd.Series(dtype=object)
    cats = df["category"] if "category" in df.columns else pd.Series(dtype=object)
    total_income = _series_decimal_sum(df.loc[types == "Income", "amount"])
    total_expense = _series_decimal_sum(df.loc[types == "Expense", "amount"])
    gross_savings = _series_decimal_sum(
        df.loc[(types == "Expense") & (cats == "Savings"), "amount"])
    if gross_savings == 0 and "Savings" in cats.tolist():
        gross_savings = _series_decimal_sum(df.loc[cats == "Savings", "amount"])
    savings_debits = _series_decimal_sum(df.loc[types == "Savings Debit", "amount"])
    net_savings = (gross_savings - savings_debits).quantize(CENT, rounding=ROUND_HALF_UP)
    rate = savings_rate(net_savings, total_income)
    avg_exp = Decimal("0.00")
    try:
        monthly = monthly_totals(df, type_filter="Expense")
        if len(monthly) > 0:
            avg_exp = to_currency(float(monthly.mean()))
    except Exception:
        avg_exp = Decimal("0.00")
    runway = emergency_runway(net_savings if net_savings > 0 else gross_savings, avg_exp)
    return {"total_income": total_income, "total_expense": total_expense,
            "gross_savings": gross_savings, "savings_debits": savings_debits,
            "net_savings": net_savings,
            "net_balance": (total_income - total_expense).quantize(CENT, rounding=ROUND_HALF_UP),
            "savings_rate": rate, "savings_on_track": bool(rate >= float(savings_target)),
            "avg_monthly_expense": avg_exp, "emergency_runway_months": runway}


def pkt_now() -> datetime:
    return datetime.now(pytz.timezone(PKT_TZ_NAME))


def month_str_for_date(value) -> str:
    """Month label from any date-like, always PKT-local (avoids 11:58 PM drift)."""
    tz = pytz.timezone(PKT_TZ_NAME)
    try:
        if isinstance(value, datetime):
            dt = value if value.tzinfo else tz.localize(value)
            return dt.astimezone(tz).strftime("%B %Y")
        if isinstance(value, date):
            return value.strftime("%B %Y")
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return pkt_now().strftime("%B %Y")
        dt = ts.to_pydatetime()
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        return dt.astimezone(tz).strftime("%B %Y")
    except Exception:
        return pkt_now().strftime("%B %Y")


# --- Carryover / rollover (zero-based budgeting; derived from existing data, no schema change) ---
ROLLOVER_FRESH = "fresh"
ROLLOVER_ROLL = "roll"


def compute_carryover_adjustments(prev_actuals, prev_targets, modes):
    """Last month's leftover (target - actual) per bucket for mode == "roll"."""
    adjustments = {}
    for bucket, target in (prev_targets or {}).items():
        if (modes or {}).get(bucket, ROLLOVER_FRESH) != ROLLOVER_ROLL:
            adjustments[bucket] = Decimal("0.00")
            continue
        carry = to_currency(target) - to_currency(
            prev_actuals.get(bucket, 0) if prev_actuals else 0)
        adjustments[bucket] = carry.quantize(CENT, rounding=ROUND_HALF_UP)
    return adjustments


def apply_carryover(base_targets, adjustments):
    effective = {}
    for bucket, base in (base_targets or {}).items():
        adj = to_currency(adjustments.get(bucket, 0) if adjustments else 0)
        effective[bucket] = (to_currency(base) + adj).quantize(
            CENT, rounding=ROUND_HALF_UP)
    return effective


# --- Debt-to-income + net worth (keyword detection; no schema change) ---
DEBT_KEYWORDS = ("loan", "debt", "emi", "mortgage", "credit", "financing", "markup")


def is_debt_category(category) -> bool:
    if category is None:
        return False
    text = str(category).strip().lower()
    return any(kw in text for kw in DEBT_KEYWORDS)


def total_debt_payments(df) -> Decimal:
    if df is None or len(df) == 0:
        return Decimal("0.00")
    if "type" not in df.columns or "category" not in df.columns \
            or "amount" not in df.columns:
        return Decimal("0.00")
    try:
        mask = (df["type"] == "Expense") & (df["category"].apply(is_debt_category))
        return _series_decimal_sum(df.loc[mask, "amount"])
    except Exception:
        return Decimal("0.00")


def debt_to_income(df) -> float:
    if df is None or len(df) == 0 or "amount" not in df.columns:
        return 0.0
    income = _series_decimal_sum(df.loc[df["type"] == "Income", "amount"]) \
        if "type" in df.columns else Decimal("0.00")
    return safe_ratio(total_debt_payments(df), income)


def compute_net_worth(total_assets, total_liabilities) -> Decimal:
    return (to_currency(total_assets) - to_currency(total_liabilities)).quantize(
        CENT, rounding=ROUND_HALF_UP)


def render_bucket_progress(name, pct, target, actual, year=None, month=None, today=None):
    """Render bucket with progress bar, status, and pace/forecast warning badge."""
    target_dec, actual_dec = to_currency(target), to_currency(actual)
    ratio = safe_ratio(actual_dec, target_dec)

    if year is not None and month is not None:
        info = pace_info(int(year), int(month), today=today)
        projected = project_month_end_spend(actual_dec, info["pace_ratio"]) \
            if info["is_current_month"] else actual_dec
        overshoot = is_overshoot_projected(actual_dec, target_dec,
                                           info["pace_ratio"], info["is_current_month"])
    else:
        info = {"pace_ratio": 0.0, "is_current_month": False,
                "days_elapsed": 0, "days_in_month": 0}
        projected, overshoot = actual_dec, False

    if _to_float(target_dec) <= 0:
        status = "⚪ No target"
    elif ratio > 1.0:
        status = "🔴 Over budget"
    elif overshoot:
        status = "🟠 On pace to overshoot ⚠️"
    elif ratio >= 0.9:
        status = "🟡 Near limit"
    else:
        status = "🟢 On track"

    remaining = (target_dec - actual_dec).quantize(CENT, rounding=ROUND_HALF_UP)

    with st.container(border=True):
        col_1, col_2, col_3 = st.columns([2, 3, 2])
        col_1.metric(
            f"{BUCKET_EMOJIS.get(name, '🎯')} {name}",
            f"{_to_float(pct) * 100:.0f}% of salary",
            f"Target PKR {_to_float(target_dec):,.0f}"
        )
        col_2.write(f"**Spent:** PKR {_to_float(actual_dec):,.2f} ({ratio * 100:.1f}% of target)")
        col_2.progress(min(ratio, 1.0))
        if info["is_current_month"] and projected is not None:
            col_2.caption(
                f"📈 Day {info['days_elapsed']}/{info['days_in_month']} · "
                f"projected {format_pkr(projected)}"
                + (" ⚠️ trending over target" if overshoot else "")
            )
        col_3.metric(
            "Remaining",
            f"PKR {_to_float(remaining):,.2f}",
            delta=f"{'over' if remaining < 0 else 'left'}",
            delta_color="inverse" if remaining < 0 else "normal",
        )
        st.caption(status)


class NotionService:
    """Handle all Notion API interactions"""

    def __init__(self):
        self.notion_token = st.secrets["notion_token_3"]
        self.database_id = st.secrets["database_id_3"]
        self.datasource_id = st.secrets["data_source_id_3"]
        self.client = self._get_client()

    @staticmethod
    @st.cache_resource
    def _get_client():
        """Create and cache Notion client"""
        try:
            return Client(auth=st.secrets["notion_token_3"])
        except Exception as e:
            st.error(f"Failed to initialize Notion client: {e}")
            return None

    @st.cache_data(ttl=300)
    def get_transactions(_self, month=None):
        """
        Fetch transactions from Notion with optional month filter.

        Args:
            month: Filter by month string (e.g., "January 2026"). If None, fetches all transactions.
        """
        transactions = []
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
                    transactions.append({
                        "id": row["id"],
                        "date": props["Date"]["date"]["start"] if props["Date"]["date"] else None,
                        "time": props["Time"]["rich_text"][0]["text"]["content"] if props["Time"][
                            "rich_text"] else "Unknown",
                        "type": props["Type"]["select"]["name"] if props["Type"]["select"] else "Unknown",
                        "category": props["Category"]["rich_text"][0]["text"]["content"] if props["Category"][
                            "rich_text"] else "Unknown",
                        # Decimal-at-ingestion: quantize once so float drift never enters totals.
                        "amount": float(to_currency(props["Amount"]["number"] if props["Amount"]["number"] else 0)),
                        "month": props["Month"]["rich_text"][0]["text"]["content"] if props["Month"][
                            "rich_text"] else "Unknown",
                        "description": props["Description"]["rich_text"][0]["text"]["content"] if
                        props["Description"]["rich_text"] else ""
                    })

                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")

            return transactions
        except Exception as e:
            st.error(f"Error fetching transactions: {e}")
            return []

    def save_transaction(self, transaction_type, category, date_obj, time_obj, amount, description):
        """Save transaction to Notion (PKT-aware month label, quantized amount)."""
        # Timezone edge case: a transaction at 11:58 PM PKT saved with a naive
        # date could be labelled into the wrong month. Derive the Month string
        # from the PKT-local date, never the naive input.
        pkt = pytz.timezone(PKT_TZ_NAME)
        try:
            if isinstance(date_obj, datetime):
                base = date_obj if date_obj.tzinfo else pkt.localize(date_obj)
            else:
                base = pkt.localize(datetime.combine(date_obj, time_obj)
                                    if isinstance(date_obj, date) and hasattr(time_obj, "hour")
                                    else datetime.combine(date_obj, datetime.min.time()))
            pkt_date = base.astimezone(pkt).date()
        except Exception:
            pkt_date = date_obj if isinstance(date_obj, date) else pkt_now().date()
        month = pkt_date.strftime("%B %Y")
        formatted_time = time_obj.strftime("%I:%M %p")
        amount = float(to_currency(amount))

        try:
            self.client.pages.create(
                parent={"data_source_id": self.datasource_id},
                properties={
                    "Name": {"title": [{"text": {"content": f"{transaction_type} - {category} ({date_obj})"}}]},
                    "Type": {"select": {"name": transaction_type}},
                    "Category": {"rich_text": [{"text": {"content": category}}]},
                    "Date": {"date": {"start": date_obj.isoformat()}},
                    "Time": {"rich_text": [{"text": {"content": formatted_time}}]},
                    "Amount": {"number": amount},
                    "Month": {"rich_text": [{"text": {"content": month}}]},
                    "Description": {"rich_text": [{"text": {"content": description or ""}}]},
                },
            )
            st.success(
                f"{transaction_type} - {category} for PKR {amount:,.2f} @ {date_obj} - {formatted_time} saved! ✅")
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error saving transaction: {e}")
            return False

    def delete_transaction(self, transaction_id):
        """Archive a transaction in Notion"""
        try:
            self.client.pages.update(transaction_id, archived=True)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Error deleting transaction: {e}")
            return False


def render_add_transaction_tab(notion_service):
    """Render the Add Transaction tab"""
    st.header("💸 Add a Transaction")

    pkt = pytz.timezone("Asia/Karachi")
    now_pkt = datetime.now(pkt)

    transaction_type = st.selectbox("Type", ["Expense", "Income", "Savings Debit"])
    if transaction_type == "Expense":
        category = st.selectbox("Category", EXPENSE_CATEGORIES)
    elif transaction_type == "Income":
        category = st.selectbox("Category", INCOME_CATEGORIES)
    else:
        transaction_type = "Savings Debit"
        st.info("💡 This will be deducted from your Savings balance.")
        category = st.selectbox("Spending Category", SAVINGS_DEBIT_CATEGORIES)

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
        emoji = "➖" if transaction_type == "Expense" else "➕" if transaction_type == "Income" else "➖"
        st.info(f"Preview {emoji} {transaction_type}: {category} | {formatted_dt} | PKR {amount:,}")

    if submitted:
        if amount > 0 and category and transaction_type:
            notion_service.save_transaction(transaction_type, category, transaction_date, transaction_time, amount,
                                            description)
        else:
            st.warning("⚠️ Missing or Invalid Data Detected!")


def render_dashboard(df):
    """Render dashboard view"""
    st.subheader("Financial Dashboard")

    if df is None or len(df) == 0:
        st.info("No transactions recorded yet.")
        return

    health = compute_financial_health(df)
    total_income = health["total_income"]
    total_expense = health["total_expense"]
    savings = health["gross_savings"]
    savings_debit = health["savings_debits"]
    net_savings = health["net_savings"]
    physical_investments = _series_decimal_sum(
        df.loc[df["category"] == "Physical Investments", "amount"])
    stocks = _series_decimal_sum(df.loc[df["category"] == "Stocks", "amount"])
    mutual_funds = _series_decimal_sum(df.loc[df["category"] == "Mutual Funds", "amount"])
    net_balance = health["net_balance"]

    # Headline health metrics first (Mint/YNAB-style): savings rate + runway.
    st.subheader("💚 Financial Health")
    h1, h2, h3 = st.columns(3)
    h1.metric("💰 Savings Rate", f"{health['savings_rate'] * 100:.1f}%",
              delta="on track ✅" if health["savings_on_track"] else "below 20% target",
              delta_color="normal" if health["savings_on_track"] else "inverse")
    runway = health["emergency_runway_months"]
    h2.metric("🛟 Emergency Runway",
              f"{runway:.1f} months" if runway is not None else "—",
              delta=f"avg spend {format_pkr(health['avg_monthly_expense'])}/mo" if runway is not None else "no spend history")
    h3.metric("🤑 Net Savings", format_pkr(net_savings),
              delta=f"{safe_ratio(net_savings, total_income) * 100:.1f}% of income")

    # Rolling trends (3m/6m) + MoM change for expenses.
    try:
        monthly = monthly_totals(df, type_filter="Expense")
        if len(monthly) >= 2:
            r3 = rolling_average(monthly, 3).iloc[-1]
            r6 = rolling_average(monthly, 6).iloc[-1]
            mom = mom_pct_change(monthly.iloc[-1], monthly.iloc[-2])
            mom_txt = ("—" if mom is None
                       else f"{'up' if mom > 0 else ('down' if mom < 0 else 'flat')} {abs(mom) * 100:.1f}% vs last month")
            st.caption(f"📊 Expense trend — 3m avg PKR {r3:,.0f} · 6m avg PKR {r6:,.0f} · {mom_txt}")
    except Exception:
        pass

    # Debt-to-income + net worth (manual inputs; no Notion schema change).
    dti = debt_to_income(df)
    debt_total = total_debt_payments(df)
    nw_assets = float(st.session_state.get("net_worth_assets", 0.0) or 0.0)
    nw_liab = float(st.session_state.get("net_worth_liab", 0.0) or 0.0)
    nw = compute_net_worth(nw_assets, nw_liab)
    d1, d2 = st.columns(2)
    d1.metric("🧾 Debt-to-Income", f"{dti * 100:.1f}%",
              delta=format_pkr(debt_total) + " debt payments" if debt_total > 0 else "no debt payments found")
    d2.metric("🏦 Net Worth", format_pkr(nw) if (nw_assets or nw_liab) else "— set below")

    with st.expander("🏦 Net Worth setup (manual — Notion has no Assets/Liabilities yet)"):
        st.caption("Enter totals once per session; kept in session state, never written to Notion.")
        n1, n2 = st.columns(2)
        with n1:
            st.number_input("Total assets (PKR)", min_value=0.0, step=1000.0,
                            value=0.0, key="net_worth_assets")
        with n2:
            st.number_input("Total liabilities (PKR)", min_value=0.0, step=1000.0,
                            value=0.0, key="net_worth_liab")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("💰 Total Income", format_pkr(total_income))
    col_b.metric("💸 Total Expenses", format_pkr(total_expense))
    col_c.metric("💵 Net Balance", format_pkr(net_balance), delta_arrow="off")

    col_a.metric("💳 Total Savings", format_pkr(savings),
                 delta=f"{safe_ratio(savings, total_income) * 100:.1f}%")
    col_b.metric("🤑 Net Savings", format_pkr(net_savings),
                 delta=f"{safe_ratio(net_savings, total_income) * 100:.1f}%")
    col_c.metric("😔 Savings Debits", format_pkr(savings_debit))

    st.subheader("📈 Investments")
    col_a.metric("🥇 Physical Investments", format_pkr(physical_investments),
                 delta=f"{safe_ratio(physical_investments, total_income) * 100:.1f}%")
    col_b.metric("📈 Stocks", format_pkr(stocks),
                 delta=f"{safe_ratio(stocks, total_income) * 100:.1f}%")
    col_c.metric("💹 Mutual Funds", format_pkr(mutual_funds),
                 delta=f"{safe_ratio(mutual_funds, total_income) * 100:.1f}%")

    st.subheader("Income vs Expenses by Month")
    month_summary = df.groupby(["month", "type"])["amount"].sum().reset_index()
    month_pivot = month_summary.pivot(index="month", columns="type", values="amount").fillna(0)
    st.bar_chart(month_pivot)

    month_summary.index = range(1, len(month_summary) + 1)
    month_summary["amount"] = month_summary["amount"].map("PKR {:,.2f}".format)
    st.dataframe(month_summary)

    expense_df = df[df["type"] == "Expense"]
    if not expense_df.empty:
        category_totals = expense_df.groupby("category")["amount"].sum().reset_index().sort_values("amount",
                                                                                                   ascending=False)
        st.subheader("Expenses by Category")
        st.bar_chart(category_totals.set_index("category"))

        st.subheader("Expense Breakdown")
        exp_cols = st.columns(min(len(category_totals), 3))
        for i, (_, row) in enumerate(category_totals.iterrows()):
            exp_cols[i % len(exp_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")
    else:
        st.info("No expenses recorded yet.")

    income_df = df[df["type"] == "Income"]
    if not income_df.empty:
        category_totals = income_df.groupby("category")["amount"].sum().reset_index().sort_values("amount",
                                                                                                  ascending=False)
        st.subheader("Income by Category")
        st.bar_chart(category_totals.set_index("category"))

        st.subheader("Income Breakdown")
        inc_cols = st.columns(min(len(category_totals), 3))
        for i, (_, row) in enumerate(category_totals.iterrows()):
            inc_cols[i % len(inc_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")
    else:
        st.info("No income recorded yet.")


def render_by_month(notion_service):
    """Render by month view with separate Month and Year selectors"""
    st.subheader("Filter by Month")

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

    month_str = f"{selected_month_name} {selected_year}"

    with st.spinner(f"Loading transactions for {month_str}..."):
        transactions = notion_service.get_transactions(month=month_str)

    if not transactions:
        st.info(f"No transactions found for {month_str}.")
        return

    filtered_df = pd.DataFrame(transactions)
    filtered_df.index = range(1, len(filtered_df) + 1)

    df_show = filtered_df.copy()
    df_show["amount"] = df_show["amount"].map("PKR {:,.2f}".format)
    st.write(df_show.drop(columns=["id"]))

    income = filtered_df[filtered_df["type"] == "Income"]["amount"].sum()
    expense = filtered_df[filtered_df["type"] == "Expense"]["amount"].sum()
    savings = filtered_df[filtered_df["category"] == "Savings"]["amount"].sum()
    savings_debit = filtered_df[filtered_df["type"] == "Savings Debit"]["amount"].sum()
    net_savings = savings - savings_debit
    physical_investments = filtered_df[filtered_df["category"] == "Physical Investments"]["amount"].sum()
    stocks = filtered_df[filtered_df["category"] == "Stocks"]["amount"].sum()
    mutual_funds = filtered_df[filtered_df["category"] == "Mutual Funds"]["amount"].sum()
    balance = income - expense

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("💰 Income", f"PKR {income:,.2f}")
    col_c.metric("💸 Expenses", f"PKR {expense:,.2f}")
    col_c.metric("💵 Balance", f"PKR {balance:,.2f}")
    col_a.metric("💳 Savings", f"PKR {savings:,.2f}")
    col_a.metric("🥇 Physical Investments", f"PKR {physical_investments:,.2f}")
    col_a.metric("📈 Stocks", f"PKR {stocks:,.2f}")
    col_a.metric("💹 Mutual Funds", f"PKR {mutual_funds:,.2f}")
    col_c.metric("😔 Debit Savings", f"PKR {savings_debit:,.2f}")


def render_all_data(df):
    """Render all data view"""
    st.subheader("All Transactions")
    df_show = df.copy()
    df_show["amount"] = df_show["amount"].map("PKR {:,.2f}".format)
    st.dataframe(df_show.drop(columns=["id"]))


def render_by_category(df):
    """Render by category view"""
    st.subheader("Expenses by Category")
    expense_df = df[df["type"] == "Expense"]

    if not expense_df.empty:
        category_totals = expense_df.groupby("category")["amount"].sum().reset_index().sort_values("amount",
                                                                                                   ascending=False)
        st.bar_chart(category_totals.set_index("category"))
    else:
        st.info("No expenses recorded yet.")

    st.subheader("Income by Category")
    income_df = df[df["type"] == "Income"]

    if not income_df.empty:
        income_category_totals = income_df.groupby("category")["amount"].sum().reset_index().sort_values("amount",
                                                                                                         ascending=False)
        st.bar_chart(income_category_totals.set_index("category"))
    else:
        st.info("No income recorded yet.")

    if not expense_df.empty:
        st.subheader("Expense Breakdown")
        exp_cols = st.columns(min(len(category_totals), 3))
        for i, (_, row) in enumerate(category_totals.iterrows()):
            exp_cols[i % len(exp_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")

    if not income_df.empty:
        st.subheader("Income Breakdown")
        inc_cols = st.columns(min(len(income_category_totals), 3))
        for i, (_, row) in enumerate(income_category_totals.iterrows()):
            inc_cols[i % len(inc_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")


def render_delete(transactions, notion_service):
    """Render delete transactions view"""
    st.subheader("Delete Transactions")

    def parse_date(date_value):
        if isinstance(date_value, datetime):
            return date_value
        return pd.to_datetime(date_value, errors="coerce")

    with st.expander("💸 Expenses", expanded=True):
        expense_transactions = [{**t, "parsed_date": parse_date(t["date"])} for t in transactions if
                                t["type"] == "Expense"]

        if expense_transactions:
            expense_df = pd.DataFrame(expense_transactions)
            expense_df["month"] = expense_df["parsed_date"].dt.to_period("M")
            expense_df = expense_df.sort_values("parsed_date", ascending=False)

            for month, month_df in expense_df.groupby("month"):
                with st.expander(f"📅 {month.strftime('%B %Y')}"):
                    for idx, transaction in month_df.iterrows():
                        st.markdown(
                            f"**➖ {transaction['parsed_date'].strftime('%d %B %Y')} - {transaction['time']}**  \n"
                            f"Category: {transaction['category']}  |  "
                            f"Amount: PKR {transaction['amount']:,} | "
                            f"Description: {transaction['description']} "
                        )
                        if st.button("🗑 Delete Expense", key=f"delete_exp_{transaction['id']}"):
                            notion_service.delete_transaction(transaction["id"])
                            st.success("Expense deleted successfully")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("No expenses recorded yet.")

    with st.expander("🤑 Income", expanded=True):
        income_transactions = [{**t, "parsed_date": parse_date(t["date"])} for t in transactions if
                               t["type"] == "Income"]

        if income_transactions:
            income_df = pd.DataFrame(income_transactions)
            income_df["month"] = income_df["parsed_date"].dt.to_period("M")
            income_df = income_df.sort_values("parsed_date", ascending=False)

            for month, month_df in income_df.groupby("month"):
                with st.expander(f"📅 {month.strftime('%B %Y')}"):
                    for idx, transaction in month_df.iterrows():
                        st.markdown(
                            f"**➕ {transaction['parsed_date'].strftime('%d %B %Y')} - {transaction['time']}**  \n"
                            f"Category: {transaction['category']}  |  "
                            f"Amount: PKR {transaction['amount']:,} | "
                            f"Description: {transaction['description']} "
                        )
                        if st.button("🗑 Delete Income", key=f"delete_inc_{transaction['id']}"):
                            notion_service.delete_transaction(transaction["id"])
                            st.success("Income deleted successfully")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("No income recorded yet.")


def render_budget_overview_tab(notion_service):
    """Render the Budget Overview tab"""
    st.header("📊 Budget Overview")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    view = st.radio("Select View", ["📅 By Month", "📊 Dashboard", "📋 All Data", "📈 By Category", "❌ Delete"],
                    horizontal=True)

    if view == "📅 By Month":
        render_by_month(notion_service)
    else:
        transactions = notion_service.get_transactions()

        if transactions:
            df = pd.DataFrame(transactions)
            df.index = range(1, len(transactions) + 1)

            if view == "📊 Dashboard":
                render_dashboard(df)
            elif view == "📋 All Data":
                render_all_data(df)
            elif view == "📈 By Category":
                render_by_category(df)
            elif view == "❌ Delete":
                render_delete(transactions, notion_service)
        else:
            st.info("❌ No transactions recorded yet.")


def render_budget_stats_tab(notion_service):
    """Render the Budget Allocation Stats tab"""
    st.header("🎯 Budget Allocation Stats")

    if st.button("🔄 Refresh Data", key="refresh_stats"):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "See how your salary splits across the four budget buckets. "
        "🏠 Bills & Rent 55% · 🛒 Daily Life 25% · 📈 Pro Investments 10% · 💳 Savings 10%"
    )

    pkt = pytz.timezone("Asia/Karachi")
    now_pkt = datetime.now(pkt)

    transactions = notion_service.get_transactions()

    if not transactions:
        st.info("❌ No transactions recorded yet.")
        return

    df = pd.DataFrame(transactions)

    col1, col2 = st.columns(2)
    with col1:
        selected_month_name = st.selectbox(
            "Month",
            MONTHS,
            index=now_pkt.month - 1,
            key="stats_month"
        )
    with col2:
        years = list(range(2025, now_pkt.year + 1))
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(now_pkt.year),
            key="stats_year"
        )

    month_str = f"{selected_month_name} {selected_year}"
    month_df = df[df["month"] == month_str]

    if month_df.empty:
        st.info(f"No transactions found for {month_str}.")
        return

    salary_income = month_df[(month_df["type"] == "Income") & (month_df["category"] == "Salary")]["amount"].sum()
    default_salary = float(to_currency(salary_income))

    salary_key = f"salary_{month_str}"
    if salary_key not in st.session_state:
        st.session_state[salary_key] = default_salary

    st.write("**Monthly Salary (PKR)**")
    salary = st.number_input(
        "Monthly Salary",
        min_value=0.0,
        step=1000.0,
        key=salary_key,
        label_visibility="collapsed",
    )

    if salary <= 0:
        st.info(
            "💡 Enter your monthly salary above (or record a **Salary** income for this month) "
            "to unlock allocation stats."
        )
        return

    actuals = compute_bucket_actuals(month_df)

    st.subheader("📊 Salary Allocation Overview")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("💰 Monthly Salary", f"PKR {salary:,.0f}")
    col_b.metric("🎯 Total Targeted", f"PKR {salary:,.0f}")
    spent_total = sum((_to_float(v) for v in actuals.values()), 0.0)
    col_c.metric("💸 Total Bucket Spend", f"PKR {spent_total:,.0f}")
    col_d.metric("🧮 Utilization", f"{safe_ratio(spent_total, salary) * 100:.1f}%")

    try:
        _mnum = MONTHS.index(selected_month_name) + 1
    except ValueError:
        _mnum = pkt_now().month

    # Rollover settings (per-bucket toggle; deltas derived from last month's
    # already-fetched data — nothing stored in Notion).
    _midx = MONTHS.index(selected_month_name)
    _pm_idx = (_midx - 1) % 12
    _py = int(selected_year) - (1 if _midx == 0 else 0)
    prev_month_str = f"{MONTHS[_pm_idx]} {_py}"
    prev_df = df[df["month"] == prev_month_str]
    prev_salary = float(to_currency(
        prev_df[(prev_df["type"] == "Income") & (prev_df["category"] == "Salary")]["amount"].sum()
    )) if not prev_df.empty else 0.0

    with st.expander("🔁 Rollover / carryover (zero-based budgeting)"):
        st.caption(f"Carry last month's leftover ({prev_month_str}) into this month's targets. "
                   "Fresh start = reset · Roll = surplus adds, deficit subtracts.")
        modes = {}
        rcols = st.columns(len(BUDGET_ALLOCATIONS))
        for i, bname in enumerate(BUDGET_ALLOCATIONS):
            with rcols[i]:
                modes[bname] = st.radio(
                    bname, [ROLLOVER_FRESH, ROLLOVER_ROLL],
                    format_func=lambda m: "Fresh start" if m == ROLLOVER_FRESH else "Roll ↔",
                    key=f"rollover_mode_{bname}_{month_str}", horizontal=True)
    base_targets = {n: (to_currency(salary) * to_currency(p)).quantize(CENT, rounding=ROUND_HALF_UP)
                    for n, p in BUDGET_ALLOCATIONS.items()}
    if prev_salary > 0 and not prev_df.empty:
        prev_targets = {n: (to_currency(prev_salary) * to_currency(p)).quantize(CENT, rounding=ROUND_HALF_UP)
                        for n, p in BUDGET_ALLOCATIONS.items()}
        adjustments = compute_carryover_adjustments(
            compute_bucket_actuals(prev_df), prev_targets, modes)
    else:
        adjustments = {n: Decimal("0.00") for n in BUDGET_ALLOCATIONS}
        if any(m == ROLLOVER_ROLL for m in modes.values()):
            st.caption(f"⚠️ No Salary income found for {prev_month_str} — rollover needs last month's salary.")
    effective_targets = apply_carryover(base_targets, adjustments)

    for name, pct in BUDGET_ALLOCATIONS.items():
        target = float(effective_targets[name])
        actual = actuals.get(name, Decimal("0.00"))
        adj = adjustments.get(name, Decimal("0.00"))
        if adj != 0:
            st.caption(f"🔁 {name}: {format_pkr(adj)} carried from {prev_month_str}")
        render_bucket_progress(name, pct, target, actual,
                               year=int(selected_year), month=int(_mnum))

    st.subheader("📋 Allocation Breakdown")
    alloc_frame = build_allocation_frame(salary, actuals)
    if any(adjustments.get(n, 0) != 0 for n in BUDGET_ALLOCATIONS):
        for idx, row in alloc_frame.iterrows():
            adj = float(to_currency(adjustments.get(row["Bucket"], 0)))
            alloc_frame.at[idx, "Target (PKR)"] = row["Target (PKR)"] + adj
            alloc_frame.at[idx, "Remaining (PKR)"] = (
                alloc_frame.at[idx, "Target (PKR)"] - row["Actual (PKR)"])
            tgt = alloc_frame.at[idx, "Target (PKR)"]
            alloc_frame.at[idx, "Utilized"] = (
                f"{safe_ratio(row['Actual (PKR)'], tgt) * 100:.1f}%" if tgt > 0 else "—")
        st.caption("Targets include the rollover adjustments above.")
    st.dataframe(
        alloc_frame,
        hide_index=True,
        column_config={
            "Target (PKR)": st.column_config.NumberColumn(format="PKR %.0f"),
            "Actual (PKR)": st.column_config.NumberColumn(format="PKR %.0f"),
            "Remaining (PKR)": st.column_config.NumberColumn(format="PKR %.0f"),
        },
    )

    st.subheader("🗂️ What Counts in Each Bucket")
    for name, cats in BUCKET_CATEGORIES.items():
        with st.expander(f"{BUCKET_EMOJIS.get(name, '🎯')} {name} — {', '.join(cats)}"):
            cat_df = month_df[(month_df["type"] == "Expense") & (month_df["category"].isin(cats))]
            if name == "Savings":
                debits = month_df[month_df["type"] == "Savings Debit"]["amount"].sum()
                st.caption(f"Savings Debits this month: PKR {debits:,.2f}")
            if cat_df.empty:
                st.caption("No spending in this bucket yet.")
            else:
                cat_totals = cat_df.groupby("category")["amount"].sum().reset_index().sort_values(
                    "amount", ascending=False)
                cat_totals["amount"] = cat_totals["amount"].map("PKR {:,.2f}".format)
                st.dataframe(cat_totals, hide_index=True)


def render_search_filter_tab(notion_service):
    """Render the Search & Filter tab"""
    st.header("🔍 Search & Filter Transactions")

    if st.button("🔄 Refresh Data", key="refresh_search"):
        st.cache_data.clear()
        st.rerun()

    transactions = notion_service.get_transactions()

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
                date_from = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date,
                                          key="date_from")
                date_to = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date, key="date_to")

            st.write("**Transaction Type**")
            selected_type = st.selectbox("Select Type", ["All", "Income", "Expense", "Savings Debit"])

        with filter_col2:
            st.write("**Amount Range**")
            use_amount_range = st.checkbox("Filter by amount")
            if use_amount_range:
                min_amount = int(df["amount"].min())
                max_amount = int(df["amount"].max())
                amount_range = st.slider("Select amount range (PKR)", min_value=min_amount, max_value=max_amount,
                                         value=(min_amount, max_amount), step=50)

            st.write("**Category**")
            categories = ["All"] + sorted(df["category"].unique().tolist())
            selected_category = st.selectbox("Select Category", categories)

        filtered_df = df.copy()
        if use_date_range:
            filtered_df = filtered_df[
                (filtered_df["date"].dt.date >= date_from) & (filtered_df["date"].dt.date <= date_to)]
        if use_amount_range:
            filtered_df = filtered_df[
                (filtered_df["amount"] >= amount_range[0]) & (filtered_df["amount"] <= amount_range[1])]
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
            debit_savings = filtered_df[filtered_df["type"] == "Savings Debit"]["amount"].sum()
            net_savings = total_savings - debit_savings
            net_balance = total_income - total_expense

            with col1:
                st.metric("💰 Total Income", f"PKR {total_income:,.2f}")
                st.metric("💸 Total Expenses", f"PKR {total_expense:,.2f}")
                st.metric("🤑 Total Savings", f"PKR {net_savings:,.2f}")

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
                category_chart = filtered_df.groupby("category")["amount"].sum().reset_index().sort_values("amount",
                                                                                                           ascending=False)
                st.bar_chart(category_chart.set_index("category"))

            if selected_type == "All":
                st.subheader("Income vs Expenses vs Savings Debit")
                type_summary = filtered_df.groupby("type")["amount"].sum().reset_index()
                st.bar_chart(type_summary.set_index("type"))
        else:
            st.info("No transactions match your filters.")
    else:
        st.info("❌ No transactions recorded yet.")


def render_yearly_summary_tab(notion_service):
    """Render the Yearly Summary tab"""
    st.header("📈 Yearly Summary")

    if st.button("🔄 Refresh Data", key="refresh_yearly"):
        st.cache_data.clear()
        st.rerun()

    transactions = notion_service.get_transactions()

    if transactions:
        df = pd.DataFrame(transactions)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year

        # Drop missing years (undated transactions) and cast to plain int:
        # NaN options crash st.selectbox serialization ("bad argument type").
        years = sorted({int(y) for y in df["year"].dropna().unique()}, reverse=True)

        if not years:
            st.info("No dated transactions yet — yearly summary needs transaction dates.")
            return

        selected_year = st.selectbox("Select Year", years)

        yearly_df = df[df["year"] == selected_year]

        if not yearly_df.empty:
            st.subheader(f"Summary for {selected_year}")

            total_income = yearly_df[yearly_df["type"] == "Income"]["amount"].sum()
            total_expense = yearly_df[yearly_df["type"] == "Expense"]["amount"].sum()
            total_savings = yearly_df[yearly_df["category"] == "Savings"]["amount"].sum()
            savings_debit = yearly_df[yearly_df["type"] == "Savings Debit"]["amount"].sum()
            net_savings = total_savings - savings_debit
            physical_investments = yearly_df[yearly_df["category"] == "Physical Investments"]["amount"].sum()
            stocks = yearly_df[yearly_df["category"] == "Stocks"]["amount"].sum()
            mutual_funds = yearly_df[yearly_df["category"] == "Mutual Funds"]["amount"].sum()
            net_balance = total_income - total_expense

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("💰 Total Income", f"PKR {total_income:,.2f}")
            col_b.metric("💸 Total Expenses", f"PKR {total_expense:,.2f}")
            col_c.metric("💵 Net Balance", f"PKR {net_balance:,.2f}")

            col_a.metric("💳 Total Savings", f"PKR {total_savings:,.2f}",
                         delta=f"{safe_ratio(total_savings, total_income) * 100:.1f}%")
            col_b.metric("🥇 Physical Investments", f"PKR {physical_investments:,.2f}",
                         delta=f"{safe_ratio(physical_investments, total_income) * 100:.1f}%")
            col_c.metric("🤑 Net Savings", f"PKR {net_savings:,.2f}",
                         delta=f"{safe_ratio(net_savings, total_income) * 100:.1f}%")

            col_a.metric("📈 Total Stocks", f"PKR {stocks:,.2f}",
                         delta=f"{safe_ratio(stocks, total_income) * 100:.1f}%")
            col_b.metric("💹 Total Mutual Funds", f"PKR {mutual_funds:,.2f}",
                         delta=f"{safe_ratio(mutual_funds, total_income) * 100:.1f}%")

            salary_income = yearly_df[(yearly_df["type"] == "Income") & (yearly_df["category"] == "Salary")][
                "amount"].sum()
            if salary_income > 0:
                annual_actuals = compute_bucket_actuals(yearly_df)
                st.subheader("🎯 Annual Allocation Check")
                alloc_cols = st.columns(len(BUDGET_ALLOCATIONS))
                for i, (name, pct) in enumerate(BUDGET_ALLOCATIONS.items()):
                    target = salary_income * pct
                    actual = annual_actuals.get(name, 0.0)
                    ratio = safe_ratio(actual, target)
                    with alloc_cols[i]:
                        st.metric(
                            f"{BUCKET_EMOJIS.get(name, '🎯')} {name}",
                            f"{ratio * 100:.0f}%",
                            delta="Over" if ratio > 1.0 else "OK",
                            delta_color="inverse" if ratio > 1.0 else "normal",
                        )
                        st.progress(min(ratio, 1.0))
                        st.caption(f"PKR {actual:,.0f} / {target:,.0f}")

            st.subheader("Monthly Breakdown")
            month_pivot = yearly_df.groupby([yearly_df["date"].dt.to_period("M"), "type"])["amount"].sum().reset_index()
            month_pivot["date"] = month_pivot["date"].astype(str)
            month_pivot = month_pivot.pivot(index="date", columns="type", values="amount").fillna(0)
            st.bar_chart(month_pivot)

            expense_df = yearly_df[yearly_df["type"] == "Expense"]
            if not expense_df.empty:
                st.subheader("Expenses by Category")
                category_totals = expense_df.groupby("category")["amount"].sum().reset_index().sort_values(
                    "amount", ascending=False)
                st.bar_chart(category_totals.set_index("category"))

                st.subheader("Expense Breakdown")
                exp_cols = st.columns(min(len(category_totals), 3))
                for i, (_, row) in enumerate(category_totals.iterrows()):
                    exp_cols[i % len(exp_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")

            income_df = yearly_df[yearly_df["type"] == "Income"]
            if not income_df.empty:
                st.subheader("Income by Category")
                income_category_totals = income_df.groupby("category")["amount"].sum().reset_index().sort_values(
                    "amount", ascending=False)
                st.bar_chart(income_category_totals.set_index("category"))

                st.subheader("Income Breakdown")
                inc_cols = st.columns(min(len(income_category_totals), 3))
                for i, (_, row) in enumerate(income_category_totals.iterrows()):
                    inc_cols[i % len(inc_cols)].metric(label=row["category"], value=f"PKR {row['amount']:,.2f}")

            st.subheader("Investment Summary")
            inv_col1, inv_col2, inv_col3 = st.columns(3)
            inv_col1.metric("🥇 Physical Investments", f"PKR {physical_investments:,.2f}")
            inv_col2.metric("📈 Stocks", f"PKR {stocks:,.2f}")
            inv_col3.metric("💹 Mutual Funds", f"PKR {mutual_funds:,.2f}")

            # Year-over-year: this year vs last year, same months only.
            try:
                yoy = yoy_comparison(df, int(selected_year), type_filter="Expense")
                st.subheader(f"🪞 Year over Year (vs {int(selected_year) - 1}, same months)")
                if yoy["months"]:
                    c1, c2, c3 = st.columns(3)
                    c1.metric(f"{selected_year} spend", f"PKR {yoy['current']:,.0f}")
                    c2.metric(f"{int(selected_year) - 1} spend", f"PKR {yoy['previous']:,.0f}")
                    pct = yoy["pct_change"]
                    c3.metric("Change",
                              ("—" if pct is None else f"{pct * 100:+.1f}%"),
                              delta=(f"{len(yoy['months'])} mo. compared" if pct is not None else "no overlap"))
                else:
                    st.caption("Not enough overlapping months with last year yet.")
            except Exception:
                pass

        else:
            st.info(f"No transactions found for {selected_year}.")
    else:
        st.info("❌ No transactions recorded yet.")


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
    main_tabs = st.tabs(
        ["💸 Add Transaction", "📊 View Budget", "🎯 Allocation Stats", "🔍 Search & Filter", "📈 Yearly Summary"]
    )

    with main_tabs[0]:
        render_add_transaction_tab(notion_service)

    with main_tabs[1]:
        render_budget_overview_tab(notion_service)

    with main_tabs[2]:
        render_budget_stats_tab(notion_service)

    with main_tabs[3]:
        render_search_filter_tab(notion_service)

    with main_tabs[4]:
        render_yearly_summary_tab(notion_service)


if __name__ == "__main__":
    main()
