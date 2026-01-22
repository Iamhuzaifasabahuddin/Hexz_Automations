# 💰🚕 Hexz Finance Suite  
**Personal Budget Tracker & Ride Expense Tracker (Streamlit + Notion)**

Hexz Finance Suite is a unified personal finance system built with **Streamlit** and **Notion**.  
It consists of two tightly related apps:

1. **Hexz Personal Budget Tracker** – track income, expenses, savings, and financial health  
2. **Hexz Ride Tracker** – track ride/taxi expenses with monthly and yearly insights  

Both apps share the same design philosophy, authentication system, and Notion-backed storage.

---

## 🚀 Core Features (Combined)

### 🔐 Authentication
- Secure login using **streamlit-authenticator**
- Cookie-based sessions
- Secrets-managed credentials

### ☁️ Notion as Backend
- All data stored in Notion databases
- Soft delete via page archiving
- Paginated querying with caching

---

## 💸 Hexz Personal Budget Tracker

### Features
- Add **Income & Expenses**
- Category-based tracking
- Savings calculation
- Monthly & yearly summaries
- Interactive dashboard:
  - Income vs Expenses
  - Category breakdowns
  - Net balance
- Advanced search & filters:
  - Date range
  - Amount range
  - Category & type
- Safe delete (archive) for transactions
- Timezone-aware (Asia/Karachi)

---

## 🚕 Hexz Ride Tracker

### Features
- Log ride expenses with date, time, and amount
- Monthly & yearly views
- Ride summaries:
  - Total spend
  - Average per ride
- Visual analytics:
  - Spending over time
  - Monthly totals
- Search & filter:
  - Date range
  - Amount range
- Safe deletion by month/year
- Optimized for daily quick entry

---

## 🛠 Tech Stack

- **Python 3.13+**
- **Streamlit**
- **Pandas**
- **Notion API**
- **streamlit-authenticator**
- **pytz**

---

## 📂 Project Structure

```text
.
├── budget_app.py          # Personal Budget Tracker
├── ride_app.py            # Ride Expense Tracker
├── requirements.txt
├── .streamlit/
│   └── secrets.toml       # Environment secrets
└── README.md
````

---

## 📦 Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Iamhuzaifasabahuddin/Hexz_Automations.git
cd Hexz_Automations
```

### 2️⃣ Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Secrets Configuration

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

> ⚠️ Never commit `secrets.toml`

---

## ▶️ Running the Apps

### Budget Tracker

```bash
streamlit run budget_app.py
```

### Ride Tracker

```bash
streamlit run ride_app.py
```

---

## 🧾 Notion Database Requirements

### Budget Tracker Database

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

### Ride Tracker Database

| Property | Type      |
| -------- | --------- |
| Name     | Title     |
| Date     | Date      |
| Time     | Rich Text |
| Amount   | Number    |
| Month    | Rich Text |

---

## ⚡ Performance & Caching

* `@st.cache_resource` → Notion client
* `@st.cache_data (TTL=300s)` → Transactions & rides
* Manual refresh buttons included

---

## 🔒 Data Safety

* Deletes are **archival**, not permanent
* No data loss unless removed directly in Notion
* Secrets fully isolated from source code

---

## 🧠 Future Enhancements

* 📤 CSV / Excel export
* 📱 Mobile-first UI
* 🔔 Monthly budget alerts
* 📈 Forecasting & trends
* 👥 Multi-user support
* 🧮 Ride cost analytics vs income

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 🙌 Author

**Hexz**
Streamlit • Notion • Personal Finance Automation

---

