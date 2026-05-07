import os
from notion_client import Client
from datetime import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart




notion = Client(auth=os.environ["NOTION_TOKEN"])
datasource_id = os.environ["NOTION_DATASOURCE_ID"]




def get_all_transactions(month=None):
    """Fetch transactions from Notion with optional Month filter + pagination"""

    transactions = []
    has_more = True
    start_cursor = None

    base_params = {
        "data_source_id": datasource_id
    }

    if month:
        base_params["filter"] = {
            "property": "Month",
            "rich_text": {
                "equals": month
            }
        }

    while has_more:

        params = base_params.copy()

        if start_cursor:
            params["start_cursor"] = start_cursor

        data = notion.data_sources.query(**params)

        for row in data["results"]:
            props = row["properties"]

            transactions.append({
                "id": row["id"],
                "date": props["Date"]["date"]["start"] if props["Date"]["date"] else None,
                "time": props["Time"]["rich_text"][0]["text"]["content"] if props["Time"]["rich_text"] else "Unknown",
                "type": props["Type"]["select"]["name"] if props["Type"]["select"] else "Unknown",
                "category": props["Category"]["rich_text"][0]["text"]["content"] if props["Category"]["rich_text"] else "Unknown",
                "amount": props["Amount"]["number"] or 0,
                "month": props["Month"]["rich_text"][0]["text"]["content"] if props["Month"]["rich_text"] else "Unknown",
                "description": props["Description"]["rich_text"][0]["text"]["content"] if props["Description"]["rich_text"] else ""
            })

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return transactions



def get_previous_month_name():
    """Return previous month in 'Month Year' format"""

    today = datetime.now()

    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year

    return f"{calendar.month_name[prev_month]} {prev_year}"



def get_previous_month_summary():
    """Generate financial summary for previous month"""

    prev_month = get_previous_month_name()

    transactions = get_all_transactions(month=prev_month)

    if not transactions:
        return None

    income = [t for t in transactions if t["type"] == "Income"]
    expenses = [t for t in transactions if t["type"] == "Expense"]

    total_income = sum(t["amount"] for t in income)
    total_expenses = sum(t["amount"] for t in expenses)
    total_savings = sum(t["amount"] for t in expenses if t["category"] == "Savings")
    net_balance = total_income - total_expenses

    income_by_category = {}
    expense_by_category = {}

    for t in income:
        income_by_category[t["category"]] = income_by_category.get(t["category"], 0) + t["amount"]

    for t in expenses:
        expense_by_category[t["category"]] = expense_by_category.get(t["category"], 0) + t["amount"]

    biggest_expense = max(expenses, key=lambda x: x["amount"], default=None)
    biggest_income = max(income, key=lambda x: x["amount"], default=None)

    most_common_expense_category = (
        max(expense_by_category, key=expense_by_category.get)
        if expense_by_category else "N/A"
    )

    return {
        "month": prev_month,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_savings": total_savings,
        "net_balance": net_balance,
        "income_count": len(income),
        "expense_count": len(expenses),
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "biggest_expense": biggest_expense,
        "biggest_income": biggest_income,
        "most_common_expense_category": most_common_expense_category,
        "savings_rate": (total_savings / total_income * 100) if total_income > 0 else 0
    }



def send_email(summary):
    """Send monthly financial summary via Gmail SMTP"""

    sender_email = os.environ["SENDER_EMAIL"]
    sender_password = os.environ["SENDER_PASSWORD"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]

    message = MIMEMultipart("alternative")
    message["Subject"] = f"💰 Your Budget Summary for {summary['month']}"
    message["From"] = sender_email
    message["To"] = recipient_email

    income_html = ""
    for category, amount in sorted(summary['income_by_category'].items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / summary['total_income']) * 100 if summary['total_income'] > 0 else 0
        income_html += f"<li><strong>{category}:</strong> PKR {amount:,.2f} ({percentage:.1f}%)</li>"

    expense_html = ""
    for category, amount in sorted(summary['expense_by_category'].items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / summary['total_expenses']) * 100 if summary['total_expenses'] > 0 else 0
        expense_html += f"<li><strong>{category}:</strong> PKR {amount:,.2f} ({percentage:.1f}%)</li>"

    balance_color = "#27ae60" if summary['net_balance'] >= 0 else "#e74c3c"
    balance_emoji = "✅" if summary['net_balance'] >= 0 else "⚠️"

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">

                <h2>💰 {summary['month']} Budget Summary</h2>

                <h3>📊 Overview</h3>
                <ul>
                    <li>Total Income: PKR {summary['total_income']:,.2f}</li>
                    <li>Total Expenses: PKR {summary['total_expenses']:,.2f}</li>
                    <li>Net Balance: <span style="color:{balance_color}">PKR {summary['net_balance']:,.2f} {balance_emoji}</span></li>
                    <li>Savings Rate: {summary['savings_rate']:.1f}%</li>
                </ul>

                <h3>💵 Income</h3>
                <ul>{income_html or "<li>No income recorded</li>"}</ul>

                <h3>💸 Expenses</h3>
                <ul>{expense_html or "<li>No expenses recorded</li>"}</ul>

                <p><strong>Most Common Expense:</strong> {summary['most_common_expense_category']}</p>

            </div>
        </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())

        print(f"✅ Email sent for {summary['month']}")
        return True

    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False



def main():
    print("📅 Generating previous month report...")

    summary = get_previous_month_summary()

    if not summary:
        print("⚠️ No data found for previous month")
        return

    print("📧 Sending email...")
    send_email(summary)


if __name__ == "__main__":
    main()
