import streamlit as st
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, time, timedelta
import json

try:
    from zoneinfo import ZoneInfo

    PKT = ZoneInfo("Asia/Karachi")
except ImportError:
    import pytz

    PKT = pytz.timezone("Asia/Karachi")

st.set_page_config(
    page_title="✨ Itinerary Planner",
    page_icon="🗓️",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    text-align: center;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(102,126,234,0.35);
}
.hero h1 { font-size: 2.4rem; margin: 0 0 .4rem; font-weight: 700; }
.hero p  { font-size: 1.05rem; margin: 0; opacity: .88; }

.event-card {
    background: white;
    border: 1.5px solid #e8eaed;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
    transition: box-shadow .2s;
}
.event-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); }
.event-card h4   { margin: 0 0 .3rem; font-size: 1.05rem; color: #1a1a2e; }
.event-card p    { margin: 0; color: #555; font-size: .92rem; }

.preview-box {
    background: #f8f9ff;
    border: 1.5px solid #d0d7ff;
    border-radius: 14px;
    padding: 1.8rem;
    font-family: 'Inter', sans-serif;
    white-space: pre-wrap;
    line-height: 1.7;
    font-size: .95rem;
    color: #222;
    max-height: 520px;
    overflow-y: auto;
}

.pill {
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    border-radius: 999px;
    padding: .18rem .7rem;
    font-size: .78rem;
    font-weight: 600;
    margin-right: .3rem;
}

.recipient-chip {
    display: inline-block;
    background: #ede9fe;
    color: #5b21b6;
    border-radius: 999px;
    padding: .22rem .75rem;
    font-size: .78rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
    word-break: break-all;
}

.stButton>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all .2s !important;
}
.stButton>button:hover { transform: translateY(-1px); }

.success-banner {
    background: linear-gradient(90deg,#d1fae5,#a7f3d0);
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    color: #065f46;
    font-weight: 600;
    margin-top: 1rem;
}

# section[data-testid="stSidebar"] { background: #fafbff; }
</style>
""", unsafe_allow_html=True)

# ── Muslim-friendly occasions ──────────────────────────────────────────────
OCCASIONS = {
    "🎂 Birthday Party":          {"color": "#ff6b9d", "template": "birthday"},
    "💍 Nikah / Walima":          {"color": "#f59e0b", "template": "wedding"},
    "🎓 Graduation":              {"color": "#6366f1", "template": "graduation"},
    "🌙 Eid Celebration":         {"color": "#06b6d4", "template": "eid"},
    "🕌 Ramadan Gathering":       {"color": "#0ea5e9", "template": "ramadan"},
    "🍽️ Iftar / Dinner Party":   {"color": "#ef4444", "template": "dinner"},
    "👶 Aqiqah / Baby Shower":    {"color": "#f9a8d4", "template": "baby"},
    "🏢 Corporate Event":         {"color": "#374151", "template": "corporate"},
    "🏖️ Vacation / Holiday":     {"color": "#10b981", "template": "vacation"},
    "📿 Quran Khatam / Dua":      {"color": "#7c3aed", "template": "quran"},
    "🤲 Milad / Religious Event": {"color": "#d97706", "template": "milad"},
    "🎉 Custom Event":            {"color": "#8b5cf6", "template": "custom"},
}

# ── Muslim-friendly emojis ─────────────────────────────────────────────────
EMOJIS = {
    "🌙 Crescent":      "🌙",
    "⭐ Star":           "⭐",
    "🤲 Dua / Prayer":  "🤲",
    "🕌 Mosque":        "🕌",
    "📿 Tasbih":        "📿",
    "🍽️ Dining":       "🍽️",
    "🎵 Nasheed":       "🎵",
    "🥤 Drinks":        "🥤",
    "🏃 Activity":      "🏃",
    "📸 Photos":        "📸",
    "🎮 Games":         "🎮",
    "🚗 Travel":        "🚗",
    "🛍️ Shopping":     "🛍️",
    "🌿 Nature":        "🌿",
    "🎬 Entertainment": "🎬",
    "🧘 Wellness":      "🧘",
    "🏊 Swimming":      "🏊",
    "🎨 Creative":      "🎨",
    "🔥 Hot":           "🔥",
    "✨ Magic":          "✨",
    "💫 Sparkle":       "💫",
    "🌟 Star":          "🌟",
    "🎁 Gift":          "🎁",
    "🎉 Celebration":   "🎉",
    "🌸 Flowers":       "🌸",
}

if "events" not in st.session_state:
    st.session_state.events = []
if "email_sent" not in st.session_state:
    st.session_state.email_sent = False
if "recipients" not in st.session_state:
    st.session_state.recipients = []


def is_valid_email(email: str) -> bool:
    parts = email.split("@")
    return len(parts) == 2 and "." in parts[1] and len(parts[1]) > 2


def build_itinerary_text(meta: dict, events: list) -> str:
    lines = []
    occ = meta.get("occasion", "Event").replace("_", " ")
    title = meta.get("title", "Our Event")
    host = meta.get("host", "")
    loc = meta.get("location", "")
    ev_date = meta.get("date", "")
    note = meta.get("note", "")

    lines.append(f"{'═' * 52}")
    lines.append(f"  {occ}")
    lines.append(f"  {title}")
    lines.append(f"{'═' * 52}")
    if host:     lines.append(f"👤 Hosted by : {host}")
    if loc:      lines.append(f"📍 Location  : {loc}")
    if ev_date:  lines.append(f"📅 Date (PKT): {ev_date}")
    lines.append("")

    if events:
        lines.append("🗓️  SCHEDULE")
        lines.append("─" * 40)
        # ── Display in order added (no sorting) ──
        for e in events:
            emoji = e.get("emoji", "•")
            t = e.get("time", "")
            name = e.get("name", "")
            detail = e.get("detail", "")
            dur = e.get("duration", "")
            tag = f"  [{dur}]" if dur else ""
            lines.append(f"{emoji}  {t:<7} {name}{tag}")
            if detail:
                lines.append(f"          ↳ {detail}")
    lines.append("")

    if note:
        lines.append("📝 NOTES")
        lines.append("─" * 40)
        lines.append(note)
        lines.append("")

    lines.append("─" * 52)
    lines.append("   Created with ✨ Itinerary Planner")
    lines.append("─" * 52)
    return "\n".join(lines)


def build_html_email(meta: dict, events: list) -> str:
    occ = meta.get("occasion", "Event")
    title = meta.get("title", "Our Event")
    host = meta.get("host", "")
    loc = meta.get("location", "")
    ev_date = meta.get("date", "")
    note = meta.get("note", "")

    occ_color = "#667eea"
    for k, v in OCCASIONS.items():
        if occ in k or k in occ:
            occ_color = v["color"]
            break

    def darken(hex_col, factor=0.75):
        h = hex_col.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"

    dark_color = darken(occ_color)

    event_rows = ""
    # ── Display in order added (no sorting) ──
    for e in events:
        emoji = e.get("emoji", "•")
        t = e.get("time", "")
        name = e.get("name", "")
        detail = e.get("detail", "")
        dur = e.get("duration", "")

        detail_html = f"""<tr><td colspan='4' style='padding:0 12px 14px 64px;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:13px;color:#888;font-style:italic;line-height:1.5;'>↳ {detail}</td></tr>""" if detail else ""
        dur_badge = f"""<span style='background:{occ_color}18;color:{dark_color};border-radius:99px;padding:3px 12px;font-size:11px;font-weight:700;font-family:"Plus Jakarta Sans",Arial,sans-serif;letter-spacing:0.04em;text-transform:uppercase;white-space:nowrap;'>{dur}</span>""" if dur else ""

        event_rows += f"""
        <tr>
          <td style='padding:14px 10px 4px 12px;font-size:22px;width:40px;vertical-align:top;'>{emoji}</td>
          <td style='padding:14px 8px 4px;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:12px;font-weight:800;color:{occ_color};letter-spacing:0.08em;text-transform:uppercase;white-space:nowrap;vertical-align:top;'>{t} <span style="font-size:9px;font-weight:600;opacity:0.6;">PKT</span></td>
          <td style='padding:14px 8px 4px;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:15px;font-weight:700;color:#1a1a2e;vertical-align:top;line-height:1.3;'>{name}</td>
          <td style='padding:14px 12px 4px;text-align:right;vertical-align:top;'>{dur_badge}</td>
        </tr>
        {detail_html}"""

    def meta_chip(icon, label, value):
        return f"""<div style='display:inline-block;background:#f5f5fa;border-radius:10px;padding:10px 16px;margin:0 8px 8px 0;font-family:"Plus Jakarta Sans",Arial,sans-serif;'>
          <span style='font-size:16px;'>{icon}</span>
          <span style='display:block;font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#aaa;margin-top:2px;'>{label}</span>
          <span style='display:block;font-size:14px;font-weight:700;color:#1a1a2e;margin-top:1px;'>{value}</span>
        </div>"""

    meta_chips = ""
    if host:     meta_chips += meta_chip("👤", "Hosted by", host)
    if loc:      meta_chips += meta_chip("📍", "Location", loc)
    if ev_date:  meta_chips += meta_chip("📅", "Date (PKT)", ev_date)

    meta_section = f"<div style='margin-bottom:28px;'>{meta_chips}</div>" if meta_chips else ""
    note_section = f"""<div style='margin-top:28px;background:linear-gradient(135deg,{occ_color}12,{occ_color}06);border-left:5px solid {occ_color};border-radius:12px;padding:20px 24px;'>
      <p style='margin:0 0 6px;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:11px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:{occ_color};'>📝 Notes</p>
      <p style='margin:0;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:14px;color:#444;line-height:1.75;'>{note}</p>
    </div>""" if note else ""

    occ_emoji = occ.split()[0]
    occ_label = " ".join(occ.split()[1:])

    now_pkt = datetime.now(PKT)
    pkt_stamp = now_pkt.strftime("%d-%B-%Y · %I:%M %p PKT")

    return f"""<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <link href='https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap' rel='stylesheet'>
</head>
<body style='margin:0;padding:0;background:#eef0f8;'>
  <div style='max-width:640px;margin:36px auto;font-family:"Plus Jakarta Sans",Arial,sans-serif;'>
    <div style='background:linear-gradient(145deg,{occ_color}f0 0%,{dark_color} 100%);border-radius:20px 20px 0 0;padding:52px 40px 44px;text-align:center;position:relative;overflow:hidden;'>
      <div style='position:absolute;top:-40px;right:-40px;width:180px;height:100px;background:rgba(255,255,255,0.08);border-radius:50%;'></div>
      <div style='position:absolute;bottom:-60px;left:-30px;width:220px;height:100px;background:rgba(255,255,255,0.05);border-radius:50%;'></div>
      <div style='font-size:56px;line-height:1;margin-bottom:14px;'>{occ_emoji}</div>
      <p style='margin:0 0 8px;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:11px;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.7);'>{occ_label}</p>
      <h1 style='margin:0;font-family:"Playfair Display",Georgia,serif;font-size:38px;font-weight:900;color:#ffffff;line-height:1.15;text-shadow:0 2px 12px rgba(0,0,0,0.18);letter-spacing:-0.01em;'>{title}</h1>
    </div>
   <div style='background:#ffffff;padding:36px 40px 32px;border-radius:0 0 20px 20px;box-shadow:0 8px 40px rgba(0,0,0,0.10);'>

    <div style="text-align:center; gap:20px;">
      {meta_section}
    </div>

    <h2 style='margin:0 0 6px;font-family:"Playfair Display",Georgia,serif;font-size:22px;font-weight:700;color:#1a1a2e;letter-spacing:-0.01em;'>🗓️ Schedule</h2>

    <div style='height:3px;background:linear-gradient(90deg,{occ_color},{occ_color}00);border-radius:2px;margin-bottom:18px;'></div>

    <table style='width:100%;border-collapse:collapse;'>
      {event_rows if event_rows else "<tr><td style='padding:16px;font-family:Plus Jakarta Sans,Arial,sans-serif;color:#bbb;font-size:14px;'>No events added yet.</td></tr>"}
    </table>

    {note_section}
</div>
    <div style='text-align:center;padding:20px;'>
      <p style='margin:0;font-family:"Plus Jakarta Sans",Arial,sans-serif;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#bbb;'>✨ Created with Hexz Itinerary Planner &nbsp;·&nbsp; {pkt_stamp}</p>
    </div>
  </div>
</body>
</html>"""


def send_email(sender_email, sender_password, recipients: list, subject, plain_text, html_body):
    """Send individual emails to every recipient in the list."""
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, sender_password)
        for addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = addr
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            server.sendmail(sender_email, addr, msg.as_string())


with st.sidebar:
    st.markdown("### 📧 Recipients")

    new_email = st.text_input(
        "Email address",
        placeholder="guest@example.com",
        key="new_recipient_input",
        label_visibility="collapsed",
    )

    col_add, col_paste = st.columns(2)
    with col_add:
        if st.button("➕ Add one", use_container_width=True):
            cleaned = new_email.strip().lower()
            if not cleaned:
                st.warning("Type an email first.")
            elif not is_valid_email(cleaned):
                st.error("Invalid email.")
            elif cleaned in st.session_state.recipients:
                st.warning("Already in list.")
            else:
                st.session_state.recipients.append(cleaned)
                st.rerun()

    with col_paste:
        if st.button("📋 Paste many", use_container_width=True,
                     help="Paste comma- or newline-separated emails above, then click here"):
            raw = new_email.strip()
            added, dupes, bad = [], [], []
            for part in raw.replace("\n", ",").replace(";", ",").split(","):
                addr = part.strip().lower()
                if not addr:
                    continue
                if not is_valid_email(addr):
                    bad.append(addr)
                elif addr in st.session_state.recipients:
                    dupes.append(addr)
                else:
                    st.session_state.recipients.append(addr)
                    added.append(addr)
            msgs = []
            if added:  msgs.append(f"✅ Added {len(added)}")
            if dupes:  msgs.append(f"⚠️ {len(dupes)} duplicate(s) skipped")
            if bad:    msgs.append(f"❌ {len(bad)} invalid skipped")
            if msgs:
                st.toast(" · ".join(msgs))
                st.rerun()
            else:
                st.warning("No valid new addresses found.")

    if st.session_state.recipients:
        st.markdown(f"**{len(st.session_state.recipients)} recipient(s):**")
        for i, addr in enumerate(list(st.session_state.recipients)):
            col_chip, col_x = st.columns([5, 1])
            with col_chip:
                st.markdown(f"<span class='recipient-chip'>✉️ {addr}</span>", unsafe_allow_html=True)
            with col_x:
                if st.button("✕", key=f"rm_{i}", help=f"Remove {addr}"):
                    st.session_state.recipients.pop(i)
                    st.rerun()

        st.markdown("")
        if st.button("🗑️ Clear all recipients", use_container_width=True):
            st.session_state.recipients = []
            st.rerun()
    else:
        st.caption("No recipients yet — add above.")

    st.markdown("---")
    st.markdown("### 📋 Event Summary")
    if st.session_state.events:
        # ── Display in order added (no sorting) ──
        for e in st.session_state.events:
            st.markdown(f"**{e.get('emoji', '•')} {e.get('time', '')}** – {e.get('name', '')}")
        st.markdown(f"**Total:** {len(st.session_state.events)} event(s)")
        if st.button("🗑️ Clear All Events", use_container_width=True):
            st.session_state.events = []
            st.rerun()
    else:
        st.caption("No events added yet.")

st.markdown("""
<div class="hero">
  <h1>✨ Itinerary Planner</h1>
  <p>Build beautiful event itineraries & send them instantly by email</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Event Details", "➕ Add Schedule Items", "📤 Preview & Send"])

with tab1:
    st.subheader("🎯 Occasion & Basic Info")
    col_a, col_b = st.columns(2)
    with col_a:
        occasion = st.selectbox("Occasion Type", list(OCCASIONS.keys()), key="occasion")
        event_title = st.text_input("Event Title", placeholder="e.g. Sarah's 30th Surprise Party", key="event_title")
        host_name = st.text_input("Host / Organiser", placeholder="John & Jane Doe", key="host_name")
    with col_b:
        event_date = st.date_input("Event Date", value=date.today() + timedelta(days=7), key="event_date")
        event_location = st.text_input("Venue / Location", placeholder="The Grand Ballroom, NYC", key="event_location")
        dress_code = st.selectbox("Dress Code",
                                  ["Not specified", "Casual 👕", "Smart Casual 👔", "Formal 🤵", "Black Tie 🎩",
                                   "Traditional / Desi 👘", "Modest Dress 🧕", "Costume 🎭", "Beach / Tropical 🌴"],
                                  key="dress_code")

    additional_notes = st.text_area("Additional Notes / RSVP Info", placeholder="RSVP by Jan 15 | Contact: 555-1234",
                                    height=100, key="additional_notes")
    st.subheader("🏷️ Event Tags / Vibe")
    tag_options = [
        "🎊 Fun", "💖 Warm & Welcoming", "👨‍👩‍👧 Family", "🍸 Classy",
        "🌈 Colourful", "🔇 Intimate", "🎭 Themed", "🌍 Outdoor",
        "🏠 Indoor", "🌙 Evening", "☀️ Daytime", "🎁 Gifts Welcome",
        "🤲 Barakah & Blessings", "🕌 Islamic Theme",
    ]
    selected_tags = st.multiselect("Select tags (optional)", tag_options, key="selected_tags")

with tab2:
    st.subheader("➕ Add a Schedule Item")
    with st.form("add_event_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            emoji_label = st.selectbox("Emoji", list(EMOJIS.keys()), key="emoji_select")
            item_time = st.time_input("Time", value=time(12, 0), key="item_time")
        with col2:
            item_name = st.text_input("Activity / Item Name *", placeholder="e.g. Welcome Guests", key="item_name")
            item_detail = st.text_input("Details / Notes", placeholder="Dates & juice served at entrance",
                                        key="item_detail")
        with col3:
            duration_options = ["", "15 min", "30 min", "45 min", "1 hr", "1.5 hr", "2 hr", "2.5 hr", "3 hr", "All day"]
            item_duration = st.selectbox("Duration", duration_options, key="item_duration")

        submitted = st.form_submit_button("➕ Add to Schedule", use_container_width=True, type="primary")
        if submitted:
            if not item_name.strip():
                st.error("Please enter an activity name.")
            else:
                st.session_state.events.append({
                    "emoji": EMOJIS[emoji_label],
                    "time": item_time.strftime("%I:%M %p"),
                    "name": item_name.strip(),
                    "detail": item_detail.strip(),
                    "duration": item_duration,
                })
                st.success(f"✅ Added: {EMOJIS[emoji_label]} {item_name}")
                st.rerun()

    if st.session_state.events:
        st.markdown("---")
        st.subheader("📋 Current Schedule")
        # ── Display in order added (no sorting) ──
        for i, e in enumerate(st.session_state.events):
            col_l, col_r = st.columns([5, 1])
            with col_l:
                st.markdown(f"""
                <div class="event-card">
                  <h4>{e.get('emoji', '•')} {e.get('time', '')} — {e.get('name', '')}</h4>
                  <p>{e.get('detail', '') or '&nbsp;'} {'<span class="pill">' + e.get("duration") + '</span>' if e.get("duration") else ''}</p>
                </div>""", unsafe_allow_html=True)
            with col_r:
                if st.button("🗑️", key=f"del_{i}", help="Remove this event"):
                    st.session_state.events.pop(i)
                    st.rerun()
    else:
        st.info("No schedule items yet. Add some above! 👆")

with tab3:
    meta = {
        "occasion": st.session_state.get("occasion", "🎉 Custom Event"),
        "title": st.session_state.get("event_title", "Our Event"),
        "host": st.session_state.get("host_name", ""),
        "location": st.session_state.get("event_location", ""),
        "date": st.session_state.get("event_date", date.today()).strftime("%d-%B-%Y"),
        "note": (
                (f"👗 Dress Code: {st.session_state.get('dress_code', '')}\n"
                 if st.session_state.get("dress_code", "") not in ["", "Not specified"] else "")
                + (" | ".join(st.session_state.get("selected_tags", [])) + "\n"
                   if st.session_state.get("selected_tags") else "")
                + st.session_state.get("additional_notes", "")
        ).strip(),
    }

    plain_text = build_itinerary_text(meta, st.session_state.events)
    html_body = build_html_email(meta, st.session_state.events)

    col_pre, col_act = st.columns([3, 2])

    st.markdown("---")
    st.subheader("🌐 HTML Email Preview")
    st.components.v1.html(html_body, height=600, scrolling=True)

    st.subheader("📧 Send by Email")

    recipients = st.session_state.recipients
    if recipients:
        chips = " ".join(f"<span class='recipient-chip'>✉️ {r}</span>" for r in recipients)
        st.markdown(f"**Sending to {len(recipients)} recipient(s):**<br>{chips}",
                    unsafe_allow_html=True)
    else:
        st.info("👈 Add recipients in the sidebar before sending.")

    subject_default = f"🗓️ Itinerary: {meta.get('title', 'Our Event')}"
    email_subject = st.text_input("Email Subject", value=subject_default, key="email_subject")

    send_btn = st.button("🚀 Send Email Now", type="primary",
                         use_container_width=True, disabled=(len(recipients) == 0))

    if send_btn:
        s_email = st.secrets.get("SENDER_EMAIL")
        s_pass = st.secrets.get("SENDER_PASSWORD")

        if not s_email or not s_pass:
            st.error("⚠️ Set SENDER_EMAIL and SENDER_PASSWORD in your Streamlit secrets.")
        else:
            with st.spinner(f"Sending to {len(recipients)} recipient(s)…"):
                try:
                    send_email(s_email, s_pass, recipients, email_subject, plain_text, html_body)
                    st.session_state.email_sent = True
                    st.markdown(
                        f'<div class="success-banner">✅ Sent to {len(recipients)} recipient(s)!</div>',
                        unsafe_allow_html=True)
                except smtplib.SMTPAuthenticationError:
                    st.error("❌ Auth failed — check your Gmail App Password in Streamlit secrets.")
                except smtplib.SMTPException as ex:
                    st.error(f"❌ SMTP Error: {ex}")
                except Exception as ex:
                    st.error(f"❌ Error: {ex}")

    if st.session_state.email_sent:
        st.balloons()
        st.session_state.email_sent = False