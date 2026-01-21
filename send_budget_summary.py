import os
from notion_client import Client
from datetime import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz

pkt = pytz.timezone("Asia/Karachi")
notion = Client(auth=os.environ["NOTION_TOKEN"])
datasource_id = os.environ["NOTION_DATASOURCE_ID"]


def get_all_transactions():
    """Fetch all transactions from Notion with pagination"""
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


def get_previous_month_summary(transactions):
    """Generate summary for the previous month"""
    today = datetime.now(pkt)

    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year

    prev_month_name = calendar.month_name[prev_month]
    prev_month_year = f"{prev_month_name} {prev_year}"

    month_transactions = [t for t in transactions if t["month"] == prev_month_year]

    if not month_transactions:
        return None

    income_transactions = [t for t in month_transactions if t["type"] == "Income"]
    expense_transactions = [t for t in month_transactions if t["type"] == "Expense"]

    total_income = sum(t["amount"] for t in income_transactions)
    total_expenses = sum(t["amount"] for t in expense_transactions)
    total_savings = sum(t["amount"] for t in expense_transactions if t["category"] == "Savings")
    net_balance = total_income - total_expenses


    income_by_category = {}
    for t in income_transactions:
        category = t["category"]
        income_by_category[category] = income_by_category.get(category, 0) + t["amount"]

    expense_by_category = {}
    for t in expense_transactions:
        category = t["category"]
        expense_by_category[category] = expense_by_category.get(category, 0) + t["amount"]

    biggest_expense = max(expense_transactions, key=lambda x: x["amount"]) if expense_transactions else None
    biggest_income = max(income_transactions, key=lambda x: x["amount"]) if income_transactions else None

    most_common_expense_category = max(expense_by_category,
                                       key=expense_by_category.get) if expense_by_category else "N/A"

    return {
        "month": prev_month_year,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_savings": total_savings,
        "net_balance": net_balance,
        "income_count": len(income_transactions),
        "expense_count": len(expense_transactions),
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "biggest_expense": biggest_expense,
        "biggest_income": biggest_income,
        "most_common_expense_category": most_common_expense_category,
        "savings_rate": (total_savings / total_income * 100) if total_income > 0 else 0
    }


def send_email(summary):
    """Send monthly summary via Gmail SMTP"""
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
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px;">
                    💰 Your {summary['month']} Budget Summary
                </h2>

                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #4CAF50; margin-top: 0;">📊 Financial Overview</h3>
                    <ul style="font-size: 16px; line-height: 2;">
                        <li><strong>Total Income:</strong> <span style="color: #27ae60; font-size: 18px;">PKR {summary['total_income']:,.2f}</span></li>
                        <li><strong>Total Expenses:</strong> <span style="color: #e74c3c; font-size: 18px;">PKR {summary['total_expenses']:,.2f}</span></li>
                        <li><strong>Net Balance:</strong> <span style="color: {balance_color}; font-size: 18px; font-weight: bold;">PKR {summary['net_balance']:,.2f} {balance_emoji}</span></li>
                        <li><strong>Total Savings:</strong> <span style="color: #3498db; font-size: 18px;">PKR {summary['total_savings']:,.2f}</span></li>
                        <li><strong>Savings Rate:</strong> {summary['savings_rate']:.1f}%</li>
                    </ul>
                </div>

                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="color: #155724; margin-top: 0;">💵 Income Breakdown</h3>
                    <p style="font-size: 16px;"><strong>Total Income Transactions:</strong> {summary['income_count']}</p>
                    <ul style="font-size: 16px; line-height: 2;">
                        {income_html if income_html else "<li>No income recorded</li>"}
                    </ul>
                    {f'<p style="margin-top: 15px; padding: 10px; background-color: #fff; border-radius: 5px;"><strong>💰 Biggest Income:</strong> PKR {summary["biggest_income"]["amount"]:,.2f} from {summary["biggest_income"]["category"]} on {summary["biggest_income"]["date"]}</p>' if summary['biggest_income'] else ''}
                </div>

                <div style="background-color: #f8d7da; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="color: #721c24; margin-top: 0;">💸 Expense Breakdown</h3>
                    <p style="font-size: 16px;"><strong>Total Expense Transactions:</strong> {summary['expense_count']}</p>
                    <ul style="font-size: 16px; line-height: 2;">
                        {expense_html if expense_html else "<li>No expenses recorded</li>"}
                    </ul>
                    {f'<p style="margin-top: 15px; padding: 10px; background-color: #fff; border-radius: 5px;"><strong>💳 Biggest Expense:</strong> PKR {summary["biggest_expense"]["amount"]:,.2f} for {summary["biggest_expense"]["category"]} on {summary["biggest_expense"]["date"]}</p>' if summary['biggest_expense'] else ''}
                    <p style="margin-top: 10px; padding: 10px; background-color: #fff; border-radius: 5px;"><strong>🔝 Most Common Category:</strong> {summary['most_common_expense_category']}</p>
                </div>

                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <p style="color: #666; font-size: 14px;">
                        Keep tracking your finances to reach your goals! 💪
                    </p>
                    <p style="color: #999; font-size: 12px;">
                        Sent automatically by Hexz Budget Tracker
                    </p>
                </div>
            </div>
        </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"✅ Monthly budget summary sent successfully for {summary['month']}!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def main():
    """Main function to generate and send monthly summary"""
    print("🔄 Fetching transactions from Notion...")
    transactions = get_all_transactions()
    print(f"📊 Found {len(transactions)} total transactions")

    print("📅 Generating previous month summary...")
    summary = get_previous_month_summary(transactions)

    if not summary:
        print("⚠️ No transactions found for previous month")
        return

    print(f"📧 Sending summary for {summary['month']}...")
    send_email(summary)


if __name__ == "__main__":
    main()