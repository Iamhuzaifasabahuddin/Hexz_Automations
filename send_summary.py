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


def get_all_rides():
    """Fetch all rides from Notion with pagination"""
    rides = []
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
                "month": month
            })

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return rides


def get_previous_month_summary(rides):
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

    month_rides = [r for r in rides if r["month"] == prev_month_name]

    if not month_rides:
        return None

    total_spent = sum(r["amount"] for r in month_rides)
    total_rides = len(month_rides)
    avg_cost = total_spent / total_rides if total_rides > 0 else 0
    most_expensive = max(month_rides, key=lambda x: x["amount"])
    cheapest = min(month_rides, key=lambda x: x["amount"])

    time_breakdown = {}
    for ride in month_rides:
        time = ride["time"]
        time_breakdown[time] = time_breakdown.get(time, 0) + 1

    most_common_time = max(time_breakdown, key=time_breakdown.get) if time_breakdown else "N/A"

    return {
        "month": prev_month_year,
        "total_spent": total_spent,
        "total_rides": total_rides,
        "avg_cost": avg_cost,
        "most_expensive": most_expensive,
        "cheapest": cheapest,
        "most_common_time": most_common_time,
        "time_breakdown": time_breakdown
    }


def send_email(summary):
    """Send monthly summary via Gmail SMTP"""
    sender_email = os.environ["SENDER_EMAIL"]
    sender_password = os.environ["SENDER_PASSWORD"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]

    message = MIMEMultipart("alternative")
    message["Subject"] = f"🚗 Your Ride Summary for {summary['month']}"
    message["From"] = sender_email
    message["To"] = recipient_email

    time_html = ""
    for time, count in summary['time_breakdown'].items():
        percentage = (count / summary['total_rides']) * 100
        time_html += f"<li><strong>{time}:</strong> {count} rides ({percentage:.1f}%)</li>"

    html = f"""
	<html>
		<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f9f9f9;">
			<div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
				<h2 style="color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px;">
					🚗 Your {summary['month']} Ride Summary
				</h2>

				<div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
					<h3 style="color: #4CAF50; margin-top: 0;">📊 Overall Statistics</h3>
					<ul style="font-size: 16px; line-height: 2;">
						<li><strong>Total Rides:</strong> {summary['total_rides']}</li>
						<li><strong>Total Spent:</strong> <span style="color: #e74c3c; font-size: 18px;">PKR {summary['total_spent']:.2f}</span></li>
						<li><strong>Average Cost:</strong> PKR {summary['avg_cost']:.2f}</li>
					</ul>
				</div>

				<div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
					<h3 style="color: #856404; margin-top: 0;">💰 Ride Details</h3>
					<ul style="font-size: 16px; line-height: 2;">
						<li><strong>Most Expensive:</strong> PKR {summary['most_expensive']['amount']:.2f} on {summary['most_expensive']['date']} at {summary['most_expensive']['time']}</li>
						<li><strong>Cheapest:</strong> PKR {summary['cheapest']['amount']:.2f} on {summary['cheapest']['date']} at {summary['cheapest']['time']}</li>
						<li><strong>Most Common Time:</strong> {summary['most_common_time']}</li>
					</ul>
				</div>

				<div style="background-color: #d1ecf1; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #17a2b8;">
					<h3 style="color: #0c5460; margin-top: 0;">⏰ Time Breakdown</h3>
					<ul style="font-size: 16px; line-height: 2;">
						{time_html}
					</ul>
				</div>

				<div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
					<p style="color: #666; font-size: 14px;">
						Keep tracking your rides to stay on budget! 💪
					</p>
					<p style="color: #999; font-size: 12px;">
						Sent automatically by Hexz Drive Log
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
        print(f"✅ Monthly summary sent successfully for {summary['month']}!")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def main():
    """Main function to generate and send monthly summary"""
    print("🔄 Fetching rides from Notion...")
    rides = get_all_rides()
    print(f"📊 Found {len(rides)} total rides")

    print("📅 Generating previous month summary...")
    summary = get_previous_month_summary(rides)

    if not summary:
        print("⚠️ No rides found for previous month")
        return

    print(f"📧 Sending summary for {summary['month']}...")
    send_email(summary)


if __name__ == "__main__":
    main()