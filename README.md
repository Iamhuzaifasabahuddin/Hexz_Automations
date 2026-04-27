# 💰✨ Hexz Finance & Events Suite

**Personal Budget Tracker • Ride Expense Tracker • Investment Calculator • Itinerary Planner**

Hexz Finance & Event Suite is a unified personal finance and planning system built with **Streamlit** and **Notion**. It combines financial tracking, analytics, and event planning into a single, cohesive ecosystem.

---

## 🚀 Overview

The suite consists of four integrated applications:

1. **Hexz Personal Budget Tracker**
2. **Hexz Ride Expense Tracker**
3. **Investment Calculator**
4. **Itinerary Planner**

All apps follow a consistent design philosophy, share authentication, and use **Notion as a backend database**.

---

## 🔐 Core Architecture

### Authentication

* Secure login via **custom authenticator**
* Cookie-based session management
* Credentials managed via secrets

### Backend (Notion)

* Structured data storage using Notion databases
* Soft deletion via page archiving
* Efficient pagination with caching

---

## 💸 Personal Budget Tracker

### Key Capabilities

* Track **income and expenses**
* Category-based financial organization
* Real-time **savings and net balance calculation**

### Analytics Dashboard

* Income vs Expense comparison
* Category-level breakdowns
* Monthly & yearly summaries

### Filtering & Search

* Date range filtering
* Amount-based filtering
* Category & transaction type filters

### Data Safety

* Soft delete (archival)
* Timezone-aware (Asia/Karachi)

---

## 🚕 Ride Expense Tracker

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

## 📅 Itinerary Planner

* Create event or occasion-based itineraries
* Send full itinerary via email
* Calendar integration support
* Multiple theme options for customization

---

## 📈 Investment Calculator

* ROI calculation based on principal and interest rate
* SIP growth visualization over time
* Multi-year return projections
* Graphical representation of investment growth

---

## 🛠 Tech Stack

| Layer         | Technology              |
| ------------- | ----------------------- |
| Language      | Python 3.13+            |
| Frontend      | Streamlit               |
| Data          | Pandas                  |
| Backend       | Notion API              |
| Auth          | custom authenticator    |
| Time Handling | pytz                    |

---

## 📂 Project Structure

```text
.
├── BudgetHexz.py 
├── HexzRideLog.py
├── InvestmentCalculator.py 
├── ItinearyPlanner.py        
├── requirements.txt
├── .streamlit/
│   └── secrets.toml
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
```python
import hashlib
password = "Your Password"
print(hashlib.sha256(password.encode()).hexdigest())
```

Create `.streamlit/secrets.toml`:

```toml
# Notion
notion_token = "YOUR_NOTION_API_KEY"
datasource_id = "RIDE_DATA_SOURCE_ID"

# Authentication
auth_username_hexz = "your_username"
auth_name_hexz = "Your Name"
auth_email_hexz = "you@email.com"
auth_password_hexz = "hashed_password"

# Cookies
cookie_key = "secure_random_key"
cookie_name = "hexz_cookie"
cookie_expiry_days = 30
```


⚠️ **Important:** Never commit `secrets.toml` to version control.

---

## ▶️ Running the Applications

```bash
streamlit run BudgetHexz.py
streamlit run HexzRideLog.py
streamlit run InvestmentCalculator.py
streamlit run ItinearyPlanner.py
```

---

## 🧾 Notion Database Schema

### Budget Tracker

| Property    | Type                      |
| ----------- | ------------------------- |
| Name        | Title                     |
| Type        | Select (Income / Expense) |
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

---

## 📜 License

Private Software License Agreement

---

## 👤 Author

**Hexz**
