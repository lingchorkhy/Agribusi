import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Ling Farmer Dashboard",
    page_icon="🌱",
    layout="wide"
)

DB_PATH = Path(__file__).parent / "farm.db"


# ==========================================
# 2. DATABASE FUNCTIONS
# ==========================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS farm_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                crop TEXT NOT NULL,
                acres REAL NOT NULL,
                trees INTEGER NOT NULL,
                harvest_kg REAL NOT NULL,
                revenue REAL NOT NULL,
                expenses REAL NOT NULL
            )
        """)


def load_records():
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT *
            FROM farm_records
            ORDER BY date DESC, id DESC
            """,
            conn
        )


def save_record(
    date,
    crop,
    acres,
    trees,
    harvest_kg,
    revenue,
    expenses
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO farm_records (
                date, crop, acres, trees,
                harvest_kg, revenue, expenses
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                crop,
                acres,
                trees,
                harvest_kg,
                revenue,
                expenses
            )
        )


initialize_database()


# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🌱 Ling Farm")
st.sidebar.caption("Farm Management System")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Farm Record",
        "Crop Records",
        "Farm Finance",
        "Export Data"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Version 1.0 | Local Application")


# Load records from the database.
df = load_records()


# ==========================================
# 4. DASHBOARD
# ==========================================

if page == "Dashboard":

    st.title("Farmer Dashboard")
    st.write(
        "Monitor plantation, harvest, revenue and expenses."
    )

    total_acres = df["acres"].sum()
    total_trees = df["trees"].sum()
    total_harvest = df["harvest_kg"].sum()
    total_revenue = df["revenue"].sum()
    total_expenses = df["expenses"].sum()
    total_profit = total_revenue - total_expenses

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Land",
        f"{total_acres:,.2f} acres"
    )

    col2.metric(
        "Recorded Trees",
        f"{total_trees:,.0f}"
    )

    col3.metric(
        "Harvest",
        f"{total_harvest:,.2f} kg"
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "Revenue",
        f"₹{total_revenue:,.2f}"
    )

    col5.metric(
        "Expenses",
        f"₹{total_expenses:,.2f}"
    )

    col6.metric(
        "Operating Surplus",
        f"₹{total_profit:,.2f}"
    )

    st.divider()

    if df.empty:

        st.info(
            "No farm records found. "
            "Open 'Add Farm Record' to get started."
        )

    else:

        st.subheader("Harvest by Crop")

        harvest_chart = (
            df.groupby("crop", as_index=False)["harvest_kg"]
            .sum()
        )

        fig = px.bar(
            harvest_chart,
            x="crop",
            y="harvest_kg",
            color="crop",
            title="Total Harvest by Crop",
            labels={
                "crop": "Crop",
                "harvest_kg": "Harvest (kg)"
            }
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Revenue and Expenses")

        finance_chart = df.melt(
            id_vars=["crop"],
            value_vars=["revenue", "expenses"],
            var_name="Category",
            value_name="Amount"
        )

        finance_chart = (
            finance_chart.groupby(
                ["crop", "Category"],
                as_index=False
            )["Amount"].sum()
        )

        fig = px.bar(
            finance_chart,
            x="crop",
            y="Amount",
            color="Category",
            barmode="group",
            title="Crop-wise Financial Performance"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("Recent Records")

        st.dataframe(
            df.head(10),
            use_container_width=True,
            hide_index=True
        )


# ==========================================
# 5. ADD FARM RECORD
# ==========================================

elif page == "Add Farm Record":

    st.title("Add Farm Record")

    st.write(
        "Enter the details of your plantation or harvest."
    )

    with st.form("farm_record_form"):

        date = st.date_input(
            "Record Date"
        )

        crop = st.selectbox(
            "Select Crop",
            [
                "Betel Nut",
                "Banana",
                "Papaya",
                "Pineapple",
                "Jackfruit",
                "Mango",
                "Guava",
                "Ginger",
                "Turmeric",
                "Other"
            ]
        )

        if crop == "Other":
            crop = st.text_input(
                "Enter Crop Name"
            )

        col1, col2 = st.columns(2)

        with col1:

            acres = st.number_input(
                "Land Area (acres)",
                min_value=0.0,
                step=0.5
            )

            trees = st.number_input(
                "Number of Trees",
                min_value=0,
                step=10
            )

            harvest_kg = st.number_input(
                "Harvest (kg)",
                min_value=0.0,
                step=10.0
            )

        with col2:

            revenue = st.number_input(
                "Revenue (₹)",
                min_value=0.0,
                step=100.0
            )

            expenses = st.number_input(
                "Expenses (₹)",
                min_value=0.0,
                step=100.0
            )

        submitted = st.form_submit_button(
            "Save Farm Record"
        )

        if submitted:

            if not crop or not crop.strip():

                st.error(
                    "Please enter a valid crop name."
                )

            else:

                save_record(
                    date.isoformat(),
                    crop.strip(),
                    acres,
                    int(trees),
                    harvest_kg,
                    revenue,
                    expenses
                )

                st.success(
                    "Farm record saved successfully!"
                )

                st.rerun()


# ==========================================
# 6. CROP RECORDS
# ==========================================

elif page == "Crop Records":

    st.title("Crop Records")

    if df.empty:

        st.info("No crop records available.")

    else:

        crops = ["All Crops"] + sorted(
            df["crop"].unique().tolist()
        )

        selected_crop = st.selectbox(
            "Filter by Crop",
            crops
        )

        filtered_df = df.copy()

        if selected_crop != "All Crops":

            filtered_df = filtered_df[
                filtered_df["crop"] == selected_crop
            ]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Crop Summary")

        summary = (
            filtered_df.groupby("crop")
            .agg(
                Total_Acres=("acres", "sum"),
                Total_Trees=("trees", "sum"),
                Total_Harvest_kg=("harvest_kg", "sum"),
                Total_Revenue=("revenue", "sum"),
                Total_Expenses=("expenses", "sum")
            )
            .reset_index()
        )

        summary["Operating_Surplus"] = (
            summary["Total_Revenue"]
            - summary["Total_Expenses"]
        )

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True
        )


# ==========================================
# 7. FARM FINANCE
# ==========================================

elif page == "Farm Finance":

    st.title("Farm Financial Management")

    if df.empty:

        st.info(
            "Add farm records to calculate your finances."
        )

    else:

        total_revenue = df["revenue"].sum()
        total_expenses = df["expenses"].sum()
        profit = total_revenue - total_expenses

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Revenue",
            f"₹{total_revenue:,.2f}"
        )

        col2.metric(
            "Total Expenses",
            f"₹{total_expenses:,.2f}"
        )

        col3.metric(
            "Operating Surplus",
            f"₹{profit:,.2f}"
        )

        if total_revenue > 0:

            margin = (
                profit / total_revenue
            ) * 100

            st.metric(
                "Operating Margin",
                f"{margin:.2f}%"
            )

        st.caption(
            "Operating surplus here means recorded revenue "
            "minus recorded expenses. It is not necessarily "
            "net profit after taxes, depreciation, financing "
            "costs or other unrecorded expenses."
        )

        st.subheader("Financial Records by Date")

        daily_finance = (
            df.groupby("date", as_index=False)
            .agg(
                Revenue=("revenue", "sum"),
                Expenses=("expenses", "sum")
            )
            .sort_values("date")
        )

        fig = px.line(
            daily_finance,
            x="date",
            y=["Revenue", "Expenses"],
            markers=True,
            title="Revenue and Expenses Over Time"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ==========================================
# 8. EXPORT DATA
# ==========================================

elif page == "Export Data":

    st.title("Export Farm Data")

    if df.empty:

        st.info("No data available for export.")

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download Farm Records (CSV)",
            data=csv_data,
            file_name="farm_records.csv",
            mime="text/csv"
        )


# ==========================================
# 9. FOOTER
# ==========================================

st.sidebar.divider()
st.sidebar.caption(
    "Ling Farmer Dashboard © 2026"
)