import os
from notion_client import Client
from datetime import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart



notion = Client(auth=os.environ["NOTION_TOKEN"])
datasource_id = os.environ["NOTION_DATASOURCE_ID"]



def get_all_rides(month=None):
    """Fetch rides from Notion with optional Month filter + pagination"""

    rides = []
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

            rides.append({
                "id": row["id"],
                "date": props["Date"]["date"]["start"] if props["Date"]["date"] else None,
                "time": props["Time"]["rich_text"][0]["text"]["content"] if props["Time"]["rich_text"] else "Unknown",
                "amount": props["Amount"]["number"] or 0,
                "month": props["Month"]["rich_text"][0]["text"]["content"] if props["Month"]["rich_text"] else "Unknown"
            })

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return rides



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
    """Generate ride summary for previous month (filtered at source)"""

    prev_month = get_previous_month_name()

    rides = get_all_rides(month=prev_month)

    if not rides:
        return None

    total_spent = sum(r["amount"] for r in rides)
    total_rides = len(rides)
    avg_cost = total_spent / total_rides if total_rides > 0 else 0

    most_expensive = max(rides, key=lambda x: x["amount"], default=None)
    cheapest = min(rides, key=lambda x: x["amount"], default=None)

    time_breakdown = {}

    for r in rides:
        time_breakdown[r["time"]] = time_breakdown.get(r["time"], 0) + 1

    most_common_time = (
        max(time_breakdown, key=time_breakdown.get)
        if time_breakdown else "N/A"
    )

    return {
        "month": prev_month,
        "total_spent": total_spent,
        "total_rides": total_rides,
        "avg_cost": avg_cost,
        "most_expensive": most_expensive,
        "cheapest": cheapest,
        "most_common_time": most_common_time,
        "time_breakdown": time_breakdown
    }



def send_email(summary):
    """Send monthly ride summary via Gmail SMTP"""

    sender_email = os.environ["SENDER_EMAIL"]
    sender_password = os.environ["SENDER_PASSWORD"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]

    message = MIMEMultipart("alternative")
    message["Subject"] = f"🚗 Your Ride Summary for {summary['month']}"
    message["From"] = sender_email
    message["To"] = recipient_email

    time_html = ""

    for time, count in summary["time_breakdown"].items():
        percentage = (count / summary["total_rides"]) * 100 if summary["total_rides"] > 0 else 0
        time_html += f"<li><strong>{time}:</strong> {count} rides ({percentage:.1f}%)</li>"

    html = f"""
    <html>
        <body style="font-family: Arial; padding:20px; background:#f9f9f9;">
            <div style="max-width:600px;margin:auto;background:white;padding:25px;border-radius:10px;">

                <h2>🚗 {summary['month']} Ride Summary</h2>

                <h3>📊 Overview</h3>
                <ul>
                    <li>Total Rides: {summary['total_rides']}</li>
                    <li>Total Spent: PKR {summary['total_spent']:.2f}</li>
                    <li>Average Cost: PKR {summary['avg_cost']:.2f}</li>
                </ul>

                <h3>💰 Details</h3>
                <ul>
                    <li>Most Expensive: PKR {summary['most_expensive']['amount']:.2f} on {summary['most_expensive']['date']} at {summary['most_expensive']['time']}</li>
                    <li>Cheapest: PKR {summary['cheapest']['amount']:.2f} on {summary['cheapest']['date']} at {summary['cheapest']['time']}</li>
                    <li>Most Common Time: {summary['most_common_time']}</li>
                </ul>

                <h3>⏰ Time Breakdown</h3>
                <ul>
                    {time_html}
                </ul>

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
    print("📅 Generating ride summary...")

    summary = get_previous_month_summary()

    if not summary:
        print("⚠️ No rides found for previous month")
        return

    print("📧 Sending email...")
    send_email(summary)


if __name__ == "__main__":
    main()
