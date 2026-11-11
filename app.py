import streamlit as st
import sqlite3
import pandas as pd
import datetime
import json
import hashlib
import os

# ==========================================
# 1. PAGE CONFIG & DATABASE INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Farm Management System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "farm.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Users table (Role: farmer, admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'farmer',
            plan TEXT DEFAULT 'Free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Farm records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS farm_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            crop_name TEXT NOT NULL,
            land_acres REAL NOT NULL,
            harvest_kg REAL NOT NULL,
            revenue_inr REAL NOT NULL,
            expense_inr REAL NOT NULL,
            record_date DATE NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # AI Chat History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Seed default admin user if not existing
    admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, email, password_hash, name, role, plan)
        VALUES (1, 'admin@farmsystem.com', ?, 'System Administrator', 'admin', 'Pro')
    ''', (admin_pass,))
    
    conn.commit()
    conn.close()

init_db()

# Helper hash function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if "user" not in st.session_state:
    st.session_state["user"] = None

# ==========================================
# 3. AUTHENTICATION MODULE (LOGIN / GOOGLE)
# ==========================================
def render_auth_page():
    st.markdown("<h2 style='text-align: center;'>🌱 Welcome to Farm System</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Manage plantation, yields, financial records, and AI advisory.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["📧 Email Login", "📝 Sign Up"])
        
        with tab1:
            st.subheader("Sign In")
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True):
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT id, email, name, role, plan FROM users WHERE email=? AND password_hash=?",
                               (email, hash_password(password)))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    st.session_state["user"] = {
                        "id": row[0], "email": row[1], "name": row[2], "role": row[3], "plan": row[4]
                    }
                    st.success(f"Welcome back, {row[2]}!")
                    st.rerun()
                else:
                    st.error("Invalid Email or Password.")
            
            st.divider()
            st.markdown("#### Or continue with Social Auth")
            if st.button("🌐 Sign in with Google", use_container_width=True):
                # Simulated Google SSO Callback Response
                st.info("Google OAuth SSO redirected. Setting up session...")
                st.session_state["user"] = {
                    "id": 999, "email": "farmer.google@gmail.com", 
                    "name": "Google Agri User", "role": "farmer", "plan": "Free"
                }
                st.rerun()

        with tab2:
            st.subheader("Create New Account")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Password", type="password")
            
            if st.button("Create Account", use_container_width=True):
                if new_name and new_email and new_password:
                    try:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                                       (new_email, hash_password(new_password), new_name))
                        conn.commit()
                        conn.close()
                        st.success("Account created successfully! Please login.")
                    except sqlite3.IntegrityError:
                        st.error("Email already registered.")
                else:
                    st.warning("Please fill in all fields.")

# ==========================================
# 4. MAIN DASHBOARD PANELS
# ==========================================
if st.session_state["user"] is None:
    render_auth_page()
else:
    user = st.session_state["user"]
    
    # ----------------------------------
    # SIDEBAR NAVIGATION
    # ----------------------------------
    st.sidebar.title("🌱 Farm System")
    st.sidebar.caption(f"Logged in as: **{user['name']}** ({user['role'].capitalize()})")
    st.sidebar.markdown(f"**Current Plan:** `{user['plan']}`")
    
    nav_options = [
        "Dashboard", 
        "Add Farm Record", 
        "Crop Records", 
        "Farm Finance", 
        "AI Agronomist Chat",
        "Export Reports", 
        "Notifications", 
        "Subscription & Billing"
    ]
    
    if user["role"] == "admin":
        nav_options.append("Admin Panel")
        
    page = st.sidebar.radio("Navigation", nav_options)
    st.sidebar.divider()
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()
        
    st.sidebar.caption("Version 2.0 | Local Application")

    # ----------------------------------
    # PAGE: USER DASHBOARD
    # ----------------------------------
    if page == "Dashboard":
        st.title("Farmer Dashboard")
        st.caption("Monitor plantation, harvest, revenue, and expenses.")
        
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM farm_records WHERE user_id=?", conn, params=(user["id"],))
        conn.close()
        
        total_land = df["land_acres"].sum() if not df.empty else 0.0
        total_harvest = df["harvest_kg"].sum() if not df.empty else 0.0
        total_rev = df["revenue_inr"].sum() if not df.empty else 0.0
        total_exp = df["expense_inr"].sum() if not df.empty else 0.0
        surplus = total_rev - total_exp
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Land", f"{total_land:.2f} acres")
        col2.metric("Harvest Output", f"{total_harvest:.2f} kg")
        col3.metric("Operating Surplus", f"₹{surplus:,.2f}")
        
        col4, col5 = st.columns(2)
        col4.metric("Total Revenue", f"₹{total_rev:,.2f}")
        col5.metric("Total Expenses", f"₹{total_exp:,.2f}")
        
        st.divider()
        if not df.empty:
            st.subheader("Yield & Revenue Overview")
            st.line_chart(df.set_index("record_date")[["revenue_inr", "expense_inr"]])
        else:
            st.info("No farm records found. Open 'Add Farm Record' to get started.")

    # ----------------------------------
    # PAGE: ADD FARM RECORD
    # ----------------------------------
    elif page == "Add Farm Record":
        st.title("Add Farm Record")
        
        with st.form("record_form"):
            crop_name = st.selectbox("Crop Type", ["Rice / Paddy", "Wheat", "Sugarcane", "Cotton", "Maize", "Vegetables", "Other"])
            land_acres = st.number_input("Land Area (Acres)", min_value=0.1, step=0.1)
            harvest_kg = st.number_input("Harvest Produced (Kg)", min_value=0.0, step=10.0)
            revenue_inr = st.number_input("Revenue Earned (₹)", min_value=0.0, step=100.0)
            expense_inr = st.number_input("Total Expense (₹)", min_value=0.0, step=100.0)
            record_date = st.date_input("Date of Entry", datetime.date.today())
            
            submit = st.form_submit_button("Save Farm Record")
            
            if submit:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO farm_records (user_id, crop_name, land_acres, harvest_kg, revenue_inr, expense_inr, record_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user["id"], crop_name, land_acres, harvest_kg, revenue_inr, expense_inr, record_date))
                conn.commit()
                conn.close()
                st.success("Record added successfully!")

    # ----------------------------------
    # PAGE: CROP RECORDS
    # ----------------------------------
    elif page == "Crop Records":
        st.title("Crop Production Logs")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT crop_name, land_acres, harvest_kg, record_date FROM farm_records WHERE user_id=?", conn, params=(user["id"],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No crop records registered yet.")

    # ----------------------------------
    # PAGE: FARM FINANCE
    # ----------------------------------
    elif page == "Farm Finance":
        st.title("Farm Financial Statement")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT record_date, revenue_inr, expense_inr, (revenue_inr - expense_inr) as net_profit FROM farm_records WHERE user_id=?", conn, params=(user["id"],))
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No financial records to display.")

    # ----------------------------------
    # PAGE: AI AGRONOMIST CHAT & HISTORY
    # ----------------------------------
    elif page == "AI Agronomist Chat":
        st.title("🤖 AI Agronomist Advisor")
        st.caption("Ask questions about crop diseases, pest control, fertilizer application, and weather planning.")
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        chat_df = pd.read_sql_query("SELECT role, content FROM ai_chat_history WHERE user_id=? ORDER BY id ASC", conn, params=(user["id"],))
        
        for _, msg in chat_df.iterrows():
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        user_prompt = st.chat_input("Ask advice (e.g. 'How to protect paddy crops from stem borer?')")
        
        if user_prompt:
            with st.chat_message("user"):
                st.write(user_prompt)
            cursor.execute("INSERT INTO ai_chat_history (user_id, role, content) VALUES (?, 'user', ?)", (user["id"], user_prompt))
            
            ai_reply = f"AI Advisory for '{user_prompt}': Ensure balanced NPK fertilization. For pest outbreaks, inspect under leaf surfaces and apply recommended organic bio-pesticides or Neem oil emulsion."
            
            with st.chat_message("assistant"):
                st.write(ai_reply)
            cursor.execute("INSERT INTO ai_chat_history (user_id, role, content) VALUES (?, 'assistant', ?)", (user["id"], ai_reply))
            
            conn.commit()
            conn.close()

    # ----------------------------------
    # PAGE: EXPORT REPORTS
    # ----------------------------------
    elif page == "Export Reports":
        st.title("Export Reports & Statements")
        st.caption("Download reports for agricultural bank loans or tax submissions.")
        
        if user["plan"] == "Free":
            st.warning("🔒 Pro Feature: Upgrade to Pro Plan to download bank-ready PDF & Excel reports.")
        else:
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query("SELECT * FROM farm_records WHERE user_id=?", conn, params=(user["id"],))
            conn.close()
            
            if not df.empty:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Complete Farm Data (CSV)",
                    data=csv_data,
                    file_name=f"farm_report_{user['id']}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No data available to export.")

    # ----------------------------------
    # PAGE: NOTIFICATIONS
    # ----------------------------------
    elif page == "Notifications":
        st.title("🔔 Alert & Advisory Center")
        
        conn = sqlite3.connect(DB_FILE)
        notifs = pd.read_sql_query("SELECT title, message, created_at FROM notifications WHERE user_id=? OR user_id IS NULL ORDER BY id DESC", conn, params=(user["id"],))
        conn.close()
        
        if notifs.empty:
            st.info("📌 System Broadcast: Heavy rain expected next week. Secure harvested crops in dry storage.")
            st.success("📌 Subscription: Your account is active on the Free Tier.")
        else:
            for _, row in notifs.iterrows():
                with st.expander(f"{row['title']} - {row['created_at']}"):
                    st.write(row['message'])

    # ----------------------------------
    # PAGE: SUBSCRIPTION & PAYMENT GATEWAY
    # ----------------------------------
    elif page == "Subscription & Billing":
        st.title("👑 Subscription Plans & Payments")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Free Plan")
            st.write("• Basic manual land & harvest logs\n• Dashboard metrics\n• Standard 3-day weather alerts")
            st.button("Current Active Plan", disabled=True if user['plan'] == 'Free' else False)
            
        with col2:
            st.subheader("Pro Farmer Plan (₹299/month)")
            st.write("• Unlimited land & crop records\n• AI Agronomist support & history\n• Export CSV/PDF reports for Bank Loans\n• Automated P&L Statements")
            
            if user["plan"] == "Pro":
                st.success("✅ Pro Plan Active")
            else:
                if st.button("💳 Upgrade to Pro (Razorpay / UPI)"):
                    st.markdown("---")
                    st.subheader("Checkout with Payment Gateway")
                    st.components.v1.html("""
                        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                        <script>
                        function payNow() {
                            var options = {
                                "key": "rzp_test_dummy_key", 
                                "amount": "29900", // ₹299 in paise
                                "currency": "INR",
                                "name": "Farm Management System",
                                "description": "Pro Tier Subscription",
                                "handler": function (response){
                                    alert("Payment Successful! Ref: " + response.razorpay_payment_id);
                                },
                                "prefill": {
                                    "name": "Farmer User",
                                    "email": "farmer@farmsystem.com"
                                },
                                "theme": { "color": "#15803d" }
                            };
                            var rzp1 = new Razorpay(options);
                            rzp1.open();
                        }
                        </script>
                        <button onclick="payNow()" style="background-color:#15803d;color:white;padding:12px 24px;border:none;border-radius:6px;font-size:16px;cursor:pointer;">
                            Pay ₹299 with UPI / PhonePe / Card
                        </button>
                    """, height=100)

    # ----------------------------------
    # PAGE: ADMIN DASHBOARD
    # ----------------------------------
    elif page == "Admin Panel" and user["role"] == "admin":
        st.title("🛡️ System Administration")
        
        conn = sqlite3.connect(DB_FILE)
        users_df = pd.read_sql_query("SELECT id, name, email, role, plan, created_at FROM users", conn)
        conn.close()
        
        st.subheader("Registered Users")
        st.dataframe(users_df, use_container_width=True)
        
        st.divider()
        st.subheader("Broadcast System Notification")
        with st.form("broadcast_form"):
            notif_title = st.text_input("Notice Title")
            notif_msg = st.text_area("Notice Message")
            send_btn = st.form_submit_button("Send Broadcast Alert")
            
            if send_btn and notif_title and notif_msg:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO notifications (user_id, title, message) VALUES (NULL, ?, ?)", (notif_title, notif_msg))
                conn.commit()
                conn.close()
                st.success("Broadcast alert dispatched to all farmers!")