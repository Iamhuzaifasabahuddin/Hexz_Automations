# 🚕 Hexz Drive Log 

This project helps you **log, view, and analyze your rides or commute data** with full integration into **Notion**, **Streamlit**, and **Gmail**.  
It runs on a scheduled **GitHub Actions workflow** to automatically send you monthly summaries by email.

---

## ✨ Features
- 📒 **Notion Integration** – Store all ride/commute data in a Notion database for easy access and organization.  
- 🌐 **Streamlit App** – View and analyze your rides anywhere, on the go, with interactive charts and dashboards.  
- 📧 **Gmail Integration** – Automatically email yourself (or others) monthly summaries of your ride activity.  
- ⏰ **GitHub Actions Scheduler** – Run background jobs to generate and send summaries without manual work.  

---

## 🛠️ Tech Stack
- **Python 3.13**  
- **Notion API (`notion-client`)**  
- **Streamlit**  
- **smtplib / Gmail SMTP** for email summaries  
- **GitHub Actions** for automated scheduling  