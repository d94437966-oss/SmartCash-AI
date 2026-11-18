import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(
    page_title="SmartCash AI",
    page_icon="💰",
    layout="wide"
)

# DESIGN
st.markdown("""
<style>
.stApp {
    background-color: #F5F7FA;
}
h1, h2, h3 {
    color: #173B35;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #E5E7EB;
}
</style>
""", unsafe_allow_html=True)

# DATABASE
conn = sqlite3.connect("smartcash.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT,
    username TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    description TEXT,
    transaction_type TEXT,
    amount REAL,
    currency TEXT,
    transaction_date TEXT
)
""")
conn.commit()

# HEADER
st.title("💰 SmartCash AI")
st.caption("Intelligent Financial Management Platform")

# LOGIN
if "company_id" not in st.session_state:
    st.session_state.company_id = None

if st.session_state.company_id is None:

    st.markdown("### Welcome")

    choice = st.radio(
        "Account",
        ["Login", "Create Account"],
        horizontal=True
    )

    if choice == "Create Account":

        company = st.text_input("Company Name")
        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Register", use_container_width=True):

            if company and username and password:

                hashed = hashlib.sha256(
                    password.encode()
                ).hexdigest()

                try:
                    cursor.execute(
                        """INSERT INTO companies
                        (company_name, username, password)
                        VALUES (?, ?, ?)""",
                        (company, username, hashed)
                    )
                    conn.commit()
                    st.success(
                        "Account created! Please Login."
                    )

                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

            else:
                st.warning("Complete all fields.")

    else:

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login", use_container_width=True):

            hashed = hashlib.sha256(
                password.encode()
            ).hexdigest()

            cursor.execute(
                """SELECT id FROM companies
                WHERE username=? AND password=?""",
                (username, hashed)
            )

            result = cursor.fetchone()

            if result:
                st.session_state.company_id = result[0]
                st.rerun()
            else:
                st.error("Invalid username or password.")

# DASHBOARD
else:

    company_id = st.session_state.company_id

    cursor.execute(
        "SELECT company_name FROM companies WHERE id=?",
        (company_id,)
    )
    company_result = cursor.fetchone()

    if not company_result:
        st.session_state.company_id = None
        st.rerun()

    company_name = company_result[0]

    # SIDEBAR
    st.sidebar.title("💰 SmartCash AI")
    st.sidebar.success(company_name)

    if st.sidebar.button("Logout"):
        st.session_state.company_id = None
        st.rerun()

    st.sidebar.divider()
    st.sidebar.caption("Financial Management System")

    st.success(f"Welcome, {company_name}!")

    # ADD TRANSACTION
    st.header("➕ Add Transaction")

    with st.form("transaction_form"):

        description = st.text_input("Description")

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Revenue", "Expense"]
        )

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0
        )

        currency = st.selectbox(
            "Currency",
            ["DZD", "EUR", "USD"]
        )

        transaction_date = st.date_input(
            "Date",
            value=date.today()
        )

        submitted = st.form_submit_button(
            "Add Transaction",
            use_container_width=True
        )

        if submitted:

            if description.strip() and amount > 0:

                cursor.execute(
                    """INSERT INTO transactions
                    (company_id, description,
                    transaction_type, amount,
                    currency, transaction_date)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        company_id,
                        description,
                        transaction_type,
                        amount,
                        currency,
                        str(transaction_date)
                    )
                )

                conn.commit()
                st.success("Transaction added!")
                st.rerun()

            else:
                st.warning(
                    "Enter a description and a valid amount."
                )

    # LOAD DATA
    cursor.execute(
        """SELECT id, description, transaction_type,
        amount, currency, transaction_date
        FROM transactions
        WHERE company_id=?
        ORDER BY id DESC""",
        (company_id,)
    )

    records = cursor.fetchall()

    df = pd.DataFrame(
        records,
        columns=[
            "ID",
            "Description",
            "Type",
            "Amount",
            "Currency",
            "Date"
        ]
    )

    # FILTERS
    st.divider()
    st.header("📊 Financial Dashboard")

    if not df.empty:

        available_currencies = sorted(
            df["Currency"].dropna().unique().tolist()
        )

        selected_currency = st.selectbox(
            "Choose Currency",
            available_currencies
        )

        currency_df = df[
            df["Currency"] == selected_currency
        ].copy()

        months = sorted(
            currency_df["Date"].str[:7].unique().tolist(),
            reverse=True
        )

        selected_month = st.selectbox(
            "Choose Period",
            ["All Months"] + months
        )

        if selected_month != "All Months":
            filtered_df = currency_df[
                currency_df["Date"].str[:7] == selected_month
            ].copy()
        else:
            filtered_df = currency_df.copy()

    else:

        selected_currency = "DZD"
        filtered_df = df.copy()

    # FINANCIAL SUMMARY
    revenues = filtered_df.loc[
        filtered_df["Type"] == "Revenue",
        "Amount"
    ].sum()

    expenses = filtered_df.loc[
        filtered_df["Type"] == "Expense",
        "Amount"
    ].sum()

    net_cash_flow = revenues - expenses

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Revenues",
        f"{revenues:,.2f} {selected_currency}"
    )

    col2.metric(
        "Total Expenses",
        f"{expenses:,.2f} {selected_currency}"
    )

    col3.metric(
        "Net Cash Flow",
        f"{net_cash_flow:,.2f} {selected_currency}"
    )

    # CHARTS
    st.divider()
    st.header("📈 Financial Analytics")

    if not filtered_df.empty:

        chart_data = filtered_df.copy()

        # REVENUE VS EXPENSES
        st.subheader("Revenue vs Expenses")

        comparison = (
            chart_data.groupby("Type")["Amount"]
            .sum()
            .reset_index()
        )

        comparison_chart = px.bar(
            comparison,
            x="Type",
            y="Amount",
            color="Type",
            color_discrete_map={
                "Revenue": "#16A34A",
                "Expense": "#EF4444"
            },
            title="Revenue and Expenses"
        )

        comparison_chart.update_layout(
            template="plotly_white",
            showlegend=False
        )

        st.plotly_chart(
            comparison_chart,
            use_container_width=True
        )

        # MONTHLY CHART
        st.subheader("Monthly Financial Performance")

        chart_data["Month"] = (
            chart_data["Date"].str[:7]
        )

        monthly = (
            chart_data.groupby(
                ["Month", "Type"]
            )["Amount"]
            .sum()
            .unstack(fill_value=0)
        )

        monthly = monthly.reindex(
            columns=["Revenue", "Expense"],
            fill_value=0
        )

        monthly["Net Cash Flow"] = (
            monthly["Revenue"] - monthly["Expense"]
        )

        monthly = monthly.reset_index()

        monthly_long = monthly.melt(
            id_vars=["Month"],
            value_vars=["Revenue", "Expense"],
            var_name="Type",
            value_name="Amount"
        )

        monthly_chart = px.bar(
            monthly_long,
            x="Month",
            y="Amount",
            color="Type",
            barmode="group",
            color_discrete_map={
                "Revenue": "#16A34A",
                "Expense": "#EF4444"
            },
            title="Monthly Revenues and Expenses"
        )

        monthly_chart.update_layout(
            template="plotly_white"
        )

        st.plotly_chart(
            monthly_chart,
            use_container_width=True
        )

        # CASH FLOW
        st.subheader("Net Cash Flow Trend")

        cash_chart = px.line(
            monthly,
            x="Month",
            y="Net Cash Flow",
            markers=True,
            title="Monthly Net Cash Flow"
        )

        cash_chart.update_traces(
            line=dict(color="#2563EB", width=3)
        )

        cash_chart.update_layout(
            template="plotly_white"
        )

        st.plotly_chart(
            cash_chart,
            use_container_width=True
        )

    else:
        st.info("No transactions available for charts.")

    # TRANSACTION HISTORY
    st.divider()
    st.header("📋 Transaction History")

    if not filtered_df.empty:

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.header("⚙️ Manage Transactions")

        selected_id = st.selectbox(
            "Select Transaction",
            filtered_df["ID"].tolist(),
            format_func=lambda tid: next(
                f"{r['Description']} - "
                f"{r['Amount']:,.2f} {r['Currency']} "
                f"({r['Date']})"
                for _, r in filtered_df.iterrows()
                if r["ID"] == tid
            )
        )

        selected_record = filtered_df[
            filtered_df["ID"] == selected_id
        ].iloc[0]

        # EDIT
        st.subheader("✏️ Edit Transaction")

        with st.form("edit_form"):

            new_description = st.text_input(
                "Description",
                value=selected_record["Description"]
            )

            new_type = st.selectbox(
                "Transaction Type",
                ["Revenue", "Expense"],
                index=(
                    0 if selected_record["Type"] == "Revenue"
                    else 1
                )
            )

            new_amount = st.number_input(
                "Amount",
                min_value=0.0,
                value=float(selected_record["Amount"])
            )

            new_currency = st.selectbox(
                "Currency",
                ["DZD", "EUR", "USD"],
                index=["DZD", "EUR", "USD"].index(
                    selected_record["Currency"]
                )
            )

            new_date = st.date_input(
                "Date",
                value=date.fromisoformat(
                    selected_record["Date"]
                )
            )

            update_button = st.form_submit_button(
                "Save Changes"
            )

            if update_button:

                if new_description.strip() and new_amount > 0:

                    cursor.execute(
                        """UPDATE transactions
                        SET description=?,
                        transaction_type=?,
                        amount=?,
                        currency=?,
                        transaction_date=?
                        WHERE id=? AND company_id=?""",
                        (
                            new_description,
                            new_type,
                            new_amount,
                            new_currency,
                            str(new_date),
                            int(selected_id),
                            company_id
                        )
                    )

                    conn.commit()
                    st.success("Transaction updated!")
                    st.rerun()

                else:
                    st.warning("Enter valid information.")

        # DELETE
        st.subheader("🗑️ Delete Transaction")

        confirm_delete = st.checkbox(
            "I confirm that I want to delete this transaction."
        )

        if st.button(
            "Delete Transaction",
            disabled=not confirm_delete
        ):

            cursor.execute(
                """DELETE FROM transactions
                WHERE id=? AND company_id=?""",
                (int(selected_id), company_id)
            )

            conn.commit()
            st.success("Transaction deleted!")
            st.rerun()

    else:
        st.info("No transactions yet.")

conn.close()
