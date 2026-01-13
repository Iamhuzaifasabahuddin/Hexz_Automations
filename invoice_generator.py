import pytz
import streamlit as st
from notion_client import Client
from datetime import datetime
import pandas as pd
from io import BytesIO

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch


pkst_timezone = pytz.timezone('Asia/Karachi')
now_pkt = datetime.now(pkst_timezone)

st.set_page_config(page_title="Invoice Generator", page_icon="🧾", layout="wide")

# @st.cache_resource
# def init_notion(api_key):
#     return Client(auth=api_key)


def create_invoice_pdf(invoice_data, items):
    """Generate PDF invoice"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    centered_h3 = styles['Heading3'].clone('centered_h3')
    centered_h3.alignment = TA_CENTER
    title = Paragraph(f"<b>INVOICE #{invoice_data['invoice_number']}</b>", styles['Title'])
    generated = Paragraph(f"<b>generated on {now_pkt.strftime("%d-%B-%Y @ %I:%m %p")}</b>",centered_h3)
    elements.append(title)
    elements.append(generated)
    elements.append(Spacer(1, 0.3 * inch))

    details = f"""
    <b>Date:</b> {invoice_data['date']}<br/>
    <b>Due Date:</b> {invoice_data['due_date']}<br/>
    <b>Client:</b> {invoice_data['client_name']}<br/>
    <b>Email:</b> {invoice_data['client_email']}
    """
    details_para = Paragraph(details, styles['Normal'])
    elements.append(details_para)
    elements.append(Spacer(1, 0.3 * inch))

    # Items table
    table_data = [['Item', 'Description', 'Quantity', 'Rate', 'Amount']]
    for item in items:
        table_data.append([
            item['name'],
            item['description'],
            str(item['quantity']),
            f"PKR {item['rate']:,.2f}",
            f"PKR {item['amount']:,.2f}"
        ])

    # Add totals
    table_data.append(['', '', '', 'Subtotal:', f"PKR {invoice_data['subtotal']:,.2f}"])
    table_data.append(['', '', '', 'Tax:', f"PKR {invoice_data['tax']:,.2f}"])
    table_data.append(['', '', '', 'Total:', f"PKR {invoice_data['total']:,.2f}"])

    table = Table(table_data, colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 1 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (3, -3), (-1, -1), 'RIGHT'),
    ]))


    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


# def add_invoice_to_notion(notion, datasource_id, invoice_data, items):
#     """Add invoice to Notion database"""
#     try:
#         properties = {
#             "Invoice Number": {"title": [{"text": {"content": invoice_data['invoice_number']}}]},
#             "Client Name": {"rich_text": [{"text": {"content": invoice_data['client_name']}}]},
#             "Client Email": {"email": invoice_data['client_email']},
#             "Date": {"date": {"start": invoice_data['date']}},
#             "Due Date": {"date": {"start": invoice_data['due_date']}},
#             "Subtotal": {"number": invoice_data['subtotal']},
#             "Tax": {"number": invoice_data['tax']},
#             "Total": {"number": invoice_data['total']},
#             "Status": {"select": {"name": invoice_data['status']}}
#         }
#
#         page = notion.pages.create(
#             parent={"data_source_id": datasource_id},
#             properties=properties
#         )
#
#         blocks = []
#         blocks.append({
#             "object": "block",
#             "type": "heading_2",
#             "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Invoice Items"}}]}
#         })
#
#         for item in items:
#             blocks.append({
#                 "object": "block",
#                 "type": "bulleted_list_item",
#                 "bulleted_list_item": {
#                     "rich_text": [{
#                         "type": "text",
#                         "text": {
#                             "content": f"{item['name']} - {item['description']} | Qty: {item['quantity']} | Rate: ${item['rate']:.2f} | Amount: ${item['amount']:.2f}"}
#                     }]
#                 }
#             })
#
#         notion.blocks.children.append(block_id=page['id'], children=blocks)
#         return True, page['id']
#     except Exception as e:
#         return False, str(e)



st.title("🧾 Invoice Generator")
notion_api_key = st.secrets.get("invoice_notion_token")
data_source_id = st.secrets.get("invoice_data_source_id")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Invoice Details")
    invoice_number = st.text_input("Invoice Number", value=f"INV-{now_pkt.date().strftime('%Y%m%d')}")
    client_name = st.text_input("Client Name", placeholder="E.g John Doe")
    client_email = st.text_input("Client Email", placeholder="Joh@example.com")
    client_phone = st.text_input("Client Phone", placeholder="+91-99-99")


with col2:
    st.subheader("Dates & Status")
    invoice_date = st.date_input("Invoice Date", value=now_pkt.now())
    due_date = st.date_input("Due Date")
    tax_rate = st.number_input("Tax Rate (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
    status = st.selectbox("Status", ["Draft", "Sent", "Paid"])

def validate_invoice_details(invoice_data):
    errors = []

    # Required text fields
    if not invoice_data['invoice_number'].strip():
        errors.append("Invoice Number is required.")
    if not invoice_data['client_name'].strip():
        errors.append("Client Name is required.")
    if not invoice_data['client_email'].strip():
        errors.append("Client Email is required.")

    # Basic email format check
    import re
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if invoice_data['client_email'] and not re.match(email_regex, invoice_data['client_email']):
        errors.append("Client Email is invalid.")

    # Date checks
    from datetime import datetime
    try:
        inv_date = datetime.strptime(invoice_data['date'], "%d-%B-%Y")
        due_date = datetime.strptime(invoice_data['due_date'], "%d-%B-%Y")
        if due_date < inv_date:
            errors.append("Due Date cannot be before Invoice Date.")
    except Exception:
        errors.append("Invalid dates provided.")

    # Totals
    if invoice_data['subtotal'] < 0 or invoice_data['total'] < 0:
        errors.append("Subtotal or Total cannot be negative.")

    return errors

st.subheader("Invoice Items")

if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = []

with st.form("add_item_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        item_name = st.text_input("Item Name")
    with col2:
        item_description = st.text_input("Description")
    with col3:
        quantity = st.number_input("Quantity", min_value=1, value=1)
    with col4:
        rate = st.number_input("Rate (PKR)", min_value=0, value=0, step=10)

    if st.form_submit_button("Add Item"):
        if item_name and rate > 0:
            st.session_state.invoice_items.append({
                'name': item_name,
                'description': item_description,
                'quantity': quantity,
                'rate': rate,
                'amount': quantity * rate
            })
            st.rerun()


if st.session_state.invoice_items:
    df = pd.DataFrame(st.session_state.invoice_items)
    df.index = range(1, len(df) + 1)
    st.dataframe(df, width="stretch")

    if st.button("Clear All Items"):
        st.session_state.invoice_items = []
        st.rerun()

    subtotal = sum(item['amount'] for item in st.session_state.invoice_items)
    tax = subtotal * (tax_rate / 100)
    total = subtotal + tax

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Subtotal", f"PKR {subtotal:,.2f}")
    with col2:
        st.metric("Tax", f"PKR {tax:,.2f}")
    with col3:
        st.metric("Total", f"PKR {total:,.2f}")


    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:

        if st.button("📄 Generate PDF", type="primary", width="stretch"):
            invoice_data = {
                'invoice_number': invoice_number,
                'client_name': client_name,
                'client_email': client_email,
                'date': str(invoice_date.strftime("%d-%B-%Y")),
                'due_date': str(due_date.strftime("%d-%B-%Y")),
                'subtotal': subtotal,
                'tax': tax,
                'total': total,
                'status': status
            }
            errors = validate_invoice_details(invoice_data)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                pdf_buffer = create_invoice_pdf(invoice_data, st.session_state.invoice_items)
                st.download_button(
                    label="Download Invoice PDF",
                    data=pdf_buffer,
                    file_name=f"invoice_{invoice_number}.pdf",
                    mime="application/pdf"
                )

    # with col2:
    #     if st.button("💾 Save to Notion", type="primary", use_container_width=True):
    #         if not notion_api_key or not data_source_id:
    #             st.error("Please provide Notion API Key and Database ID in the sidebar")
    #         elif not client_name or not client_email:
    #             st.error("Please fill in client name and email")
    #         else:
    #             notion = init_notion(notion_api_key)
    #             invoice_data = {
    #                 'invoice_number': invoice_number,
    #                 'client_name': client_name,
    #                 'client_email': client_email,
    #                 'date': str(invoice_date),
    #                 'due_date': str(due_date),
    #                 'subtotal': subtotal,
    #                 'tax': tax,
    #                 'total': total,
    #                 'status': status
    #             }
    #
    #             success, result = add_invoice_to_notion(notion, data_source_id, invoice_data, st.session_state.items)
    #             if success:
    #                 st.success(f"✅ Invoice saved to Notion! Page ID: {result}")
    #             else:
    #                 st.error(f"❌ Error saving to Notion: {result}")
else:
    st.info("👆 Add items to your invoice using the form above")


# def fetch_invoices_from_notion(notion, data_source_id):
#     """Fetch all invoices from a Notion database"""
#     try:
#         results = []
#         response = notion.data_sources.query(data_source_id=data_source_id, page_size=100)
#         for page in response['results']:
#             props = page['properties']
#             invoice = {
#                 'page_id': page['id'],
#                 'invoice_number': props.get('Invoice Number', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
#                 'client_name': props.get('Client Name', {}).get('rich_text', [{}])[0].get('text', {}).get('content', ''),
#                 'client_email': props.get('Client Email', {}).get('email', ''),
#                 'date': props.get('Date', {}).get('date', {}).get('start', ''),
#                 'due_date': props.get('Due Date', {}).get('date', {}).get('start', ''),
#                 'subtotal': props.get('Subtotal', {}).get('number', 0),
#                 'tax': props.get('Tax', {}).get('number', 0),
#                 'total': props.get('Total', {}).get('number', 0),
#                 'status': props.get('Status', {}).get('select', {}).get('name', ''),
#             }
#             results.append(invoice)
#         return results
#     except Exception as e:
#         st.error(f"Error fetching invoices: {e}")
#         return []
#
#
# def download_invoice_from_notion(notion, page_id):
#     """Fetch page details including items and generate PDF"""
#     try:
#         # Fetch page properties
#         page = notion.pages.retrieve(page_id=page_id)
#         props = page['properties']
#         invoice_data = {
#             'invoice_number': props.get('Invoice Number', {}).get('title', [{}])[0].get('text', {}).get('content', ''),
#             'client_name': props.get('Client Name', {}).get('rich_text', [{}])[0].get('text', {}).get('content', ''),
#             'client_email': props.get('Client Email', {}).get('email', ''),
#             'date': props.get('Date', {}).get('date', {}).get('start', ''),
#             'due_date': props.get('Due Date', {}).get('date', {}).get('start', ''),
#             'subtotal': props.get('Subtotal', {}).get('number', 0),
#             'tax': props.get('Tax', {}).get('number', 0),
#             'total': props.get('Total', {}).get('number', 0),
#             'status': props.get('Status', {}).get('select', {}).get('name', ''),
#         }
#
#         # Fetch invoice items from blocks
#         children = notion.blocks.children.list(block_id=page_id)
#         items = []
#         for block in children['results']:
#             if block['type'] == 'bulleted_list_item':
#                 text_content = block['bulleted_list_item']['rich_text'][0]['text']['content']
#                 # Parse item string: "name - desc | Qty: X | Rate: Y | Amount: Z"
#                 try:
#                     name_desc, qty_part, rate_part, amount_part = [x.strip() for x in text_content.split('|')]
#                     name, description = [x.strip() for x in name_desc.split('-', 1)]
#                     qty = int(qty_part.replace('Qty:', '').strip())
#                     rate = float(rate_part.replace('Rate: $', '').strip())
#                     amount = float(amount_part.replace('Amount: $', '').strip())
#                     items.append({
#                         'name': name,
#                         'description': description,
#                         'quantity': qty,
#                         'rate': rate,
#                         'amount': amount
#                     })
#                 except Exception:
#                     continue
#
#         pdf_buffer = create_invoice_pdf(invoice_data, items)
#         return pdf_buffer
#     except Exception as e:
#         st.error(f"Error generating PDF: {e}")
#         return None
#
#
# if notion_api_key and data_source_id:
#     st.markdown("---")
#     st.subheader("💾 Saved Invoices in Notion")
#     notion = init_notion(notion_api_key)
#     invoices = fetch_invoices_from_notion(notion, data_source_id)
#
#     if invoices:
#         for inv in invoices:
#             col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
#             with col1:
#                 st.text(inv['invoice_number'])
#             with col2:
#                 st.text(inv['client_name'])
#             with col3:
#                 st.text(inv['total'])
#             with col4:
#                 if st.button(f"📄 Download {inv['invoice_number']}", key=inv['page_id']):
#                     pdf_buffer = download_invoice_from_notion(notion, inv['page_id'])
#                     if pdf_buffer:
#                         st.download_button(
#                             label=f"Download PDF - {inv['invoice_number']}",
#                             data=pdf_buffer,
#                             file_name=f"{inv['invoice_number']}.pdf",
#                             mime="application/pdf"
#                         )
#     else:
#         st.info("No invoices found in Notion database.")
