# 💰✨ Hexz Finance & Events Suite

**Personal Budget Trackers • Ride Expense Tracker • Investment Calculator • Itinerary Planner**

A unified personal finance and planning suite built with **Streamlit** and **Notion**. It combines financial tracking, salary allocation analytics, and event planning into a single, cohesive ecosystem — with a dedicated budget tracker per user.

---

## 🚀 Overview

The suite currently consists of **five** applications:

| # | Application | File | Users |
| - | ----------- | ---- | ----- |
| 1 | Hexz Personal Budget Tracker | `BudgetHexz.py` | Hexz |
| 2 | Toobsz Personal Budget Tracker | `ToobszBudget.py` | Tooba |
| 3 | Hexz Ride Expense Tracker | `HexzRideLog.py` | Hexz |
| 4 | Investment Calculator | `InvestmentCalculator.py` | Anyone |
| 5 | Itinerary Planner | `ItineraryPlanner.py` | Anyone |

All apps follow a consistent design philosophy, share cookie-based authentication, and use **Notion as a backend database** — each user's budget app is wired to its own Notion data source.

---

## 🔐 Core Architecture

### Authentication

* Secure login via **SHA-256 hashed credentials**
* Cookie-based session management (default 30-day expiry)
* Per-user credentials managed via `secrets.toml`

### Backend (Notion)

* Structured data storage using Notion data sources
* Soft deletion via page archiving (non-destructive)
* Pagination + caching (`@st.cache_data` TTL 300s)

---

## 💸 Personal Budget Trackers (`BudgetHexz.py` / `ToobszBudget.py`)

Two personalized budget apps — identical features, separate Notion backends and credentials.

### Add Transaction

* Track **Expense**, **Income**, and **Savings Debit** entries
* Category-based financial organization (incl. **Rent**, Bills & Utilities, Food, Transport, Shopping, Investments…)
* PKT timezone-aware (Asia/Karachi) date & time capture
* Preview before saving

### 🎯 Budget Allocation Stats

Track how your monthly salary is split across **four budget buckets**:

| Bucket | Share | What counts |
| ------ | ----- | ----------- |
| 🏠 Bills & Rent | **55%** | Rent, Bills & Utilities |
| 🛒 Daily Life | **25%** | Food, Transport, Shopping, Entertainment, Healthcare, Education, Other |
| 📈 Pro Investments | **10%** | Physical Investments, Stocks, Mutual Funds |
| 💳 Savings | **10%** | Savings (minus Savings Debits) |

* Salary auto-detects from **Salary** income for the selected month (manually editable)
* Per-bucket progress bars with 🟢 On track / 🟡 Near limit / 🔴 Over budget status
* Remaining-budget metrics and full breakdown table
* Expanders showing exactly which categories count toward each bucket

### Analytics

* Financial dashboard (income, expenses, net balance, net savings, investments)
* Income vs Expense comparison by month
* Category-level breakdowns and charts
* **Yearly Summary** with monthly breakdown + 🎯 Annual Allocation Check
* Filter by month & year

### Filtering & Search

* Date range, amount range, category & transaction-type filters
* Spending-over-time line charts and category bar charts

### Data Safety

* Soft delete (archival only)
* Refresh controls with cache invalidation

---

## 🚕 Ride Expense Tracker (`HexzRideLog.py`)

### Features

* Log rides with **date, time, and amount**
* Monthly and yearly summaries
* Quick daily entry optimization

### Insights

* Total ride spend
* Average cost per ride
* Spending trends over time

### Filtering

* Date range
* Amount range

### Data Handling

* Safe deletion by month/year (archival)

---

## 📈 Investment Calculator (`InvestmentCalculator.py`)

* ROI / SIP calculation based on principal and interest rate
* **Alternating SIP strategy** — mutual funds (70% equity / 30% balanced) in odd months, stocks in even months
* Multi-year return projections with Plotly charts
* PKR formatting in Cr / Lac / thousands
* Investment options comparison & portfolio growth visualization

---

## 📅 Itinerary Planner (`ItineraryPlanner.py`)

* Create event or occasion-based itineraries
* Send full itinerary via email (`smtplib`)
* Multiple theme options with custom CSS (Inter font, hero cards)
* PKT timezone-aware scheduling

---

## 🛠 Tech Stack

| Layer         | Technology                 |
| ------------- | -------------------------- |
| Language      | Python 3.13+               |
| Frontend      | Streamlit 1.53             |
| Data          | Pandas, Altair, Plotly     |
| Backend       | Notion API (notion-client) |
| Auth          | SHA-256 + cookies (extra-streamlit-components) |
| Time Handling | pytz / zoneinfo            |
| Emails        | smtplib (Itinerary Planner) |

---

## 📂 Project Structure

```text
.
├── BudgetHexz.py               # Hexz personal budget tracker
├── ToobszBudget.py             # Tooba personal budget tracker
├── HexzRideLog.py              # Ride expense tracker
├── InvestmentCalculator.py     # SIP / ROI calculator
├── ItineraryPlanner.py         # Event itinerary planner
├── scripts/
│   ├── wakeup.py               # Keep-alive ping (UptimeRobot)
│   ├── send_summary.py         # Ride summary email
│   └── send_budget_summary.py  # Budget summary email
├── requirements.txt
├── .streamlit/
│   └── secrets.toml            # NEVER commit this
└── README.md
```

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/Iamhuzaifasabahuddin/Hexz_Automations.git
cd Hexz_Automations
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Secrets Configuration

Hash your password first:

```python
import hashlib
password = "Your Password"
print(hashlib.sha256(password.encode()).hexdigest())
```

Create `.streamlit/secrets.toml`:

```toml
# Notion — Ride Tracker
notion_token = "YOUR_NOTION_API_KEY"
data_source_id = "RIDE_DATA_SOURCE_ID"
database_id = "RIDE_DATABASE_ID"

# Notion — Toobsz Budget
notion_token_2 = "YOUR_NOTION_API_KEY_2"
data_source_id_2 = "TOOBA_DATA_SOURCE_ID"
database_id_2 = "TOOBA_DATABASE_ID"

# Notion — Hexz Budget
notion_token_3 = "YOUR_NOTION_API_KEY_3"
data_source_id_3 = "HEXZ_DATA_SOURCE_ID"
database_id_3 = "HEXZ_DATABASE_ID"

# Notion — Invoices
invoice_notion_token = "YOUR_INVOICE_NOTION_API_KEY"
invoice_data_source_id = "INVOICE_DATA_SOURCE_ID"

# Authentication
auth_username_hexz = "your_username"
auth_name_hexz = "Your Name"
auth_email_hexz = "you@email.com"
auth_password_hexz = "hashed_password"

auth_username_tooba = "tooba"
auth_name_tooba = "Tooba"
auth_email_tooba = "tooba@email.com"
auth_password_tooba = "hashed_password"

# Cookies
cookie_key = "secure_random_key"
cookie_expiry_days = 30

# Email (Itinerary Planner / summary scripts)
SENDER_EMAIL = "sender@gmail.com"
SENDER_PASSWORD = "app_password"
```


⚠️ **Important:** Never commit `secrets.toml` to version control.

---

## ▶️ Running the Applications

```bash
streamlit run BudgetHexz.py
streamlit run ToobszBudget.py
streamlit run HexzRideLog.py
streamlit run InvestmentCalculator.py
streamlit run ItineraryPlanner.py
```

---

## 🧾 Notion Database Schema

### Budget Tracker (one per user)

| Property    | Type                      |
| ----------- | ------------------------- |
| Name        | Title                     |
| Type        | Select (Income / Expense / Savings Debit) |
| Category    | Rich Text                 |
| Date        | Date                      |
| Time        | Rich Text                 |
| Amount      | Number                    |
| Month       | Rich Text                 |
| Description | Rich Text                 |

### Ride Tracker

| Property | Type      |
| -------- | --------- |
| Name     | Title     |
| Date     | Date      |
| Time     | Rich Text |
| Amount   | Number    |
| Month    | Rich Text |

---

## ⚡ Performance Optimization

* `@st.cache_resource` → Notion client
* `@st.cache_data (TTL=300s)` → Data caching
* Manual refresh controls included

---

## 🔒 Data Safety

* All deletions are **non-destructive (archived)**
* No permanent data loss unless manually removed in Notion
* Secrets are fully isolated from source code

---

## 🧠 Roadmap

* 📤 CSV / Excel export
* 📈 Financial forecasting & predictive analytics
* 👥 Multi-user collaboration
* 🧮 Ride expense vs income correlation insights
* ⚙️ Customizable allocation percentages per bucket

---

## 📜 License

Private Software License Agreement

---

## 👤 Author

**Hexz** — built by [Huzaifa Sabah Uddin](https://iamhuzaifasabahuddin.github.io/Portfolio/)

---

<div align="center">
  <a href="https://iamhuzaifasabahuddin.github.io/Portfolio/"><strong>About the author →</strong></a>
</div>
