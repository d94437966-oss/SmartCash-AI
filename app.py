
import streamlit as st
import sqlite3
import hashlib
from datetime import date

st.set_page_config(
    page_title="SmartCash AI",
    page_icon="💰",
    layout="wide"
)

# Database
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

st.title("💰 SmartCash AI")
st.subheader("Intelligent Financial Management")

# Authentication
if "company_id" not in st.session_state:
    st.session_state.company_id = None

if st.session_state.company_id is None:
    choice = st.radio("Welcome", ["Login", "Create Account"])

    if choice == "Create Account":
        company = st.text_input("Company Name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Register"):
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
                    st.success("Account created! Please Login.")
                except sqlite3.IntegrityError:
                    st.error("Username already exists.")
            else:
                st.warning("Complete all fields.")

    else:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
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

else:
    company_id = st.session_state.company_id

    cursor.execute(
        "SELECT company_name FROM companies WHERE id=?",
        (company_id,)
    )
    company_name = cursor.fetchone()[0]

    st.success(f"Welcome, {company_name}!")

    if st.button("Logout"):
        st.session_state.company_id = None
        st.rerun()

    st.divider()
    st.header("Financial Dashboard")

    with st.form("transaction_form"):
        description = st.text_input("Description")
        transaction_type = st.selectbox(
            "Transaction Type",
            ["Revenue", "Expense"]
        )
        amount = st.number_input(
            "Amount", min_value=0.0
        )
        currency = st.selectbox(
            "Currency", ["DZD", "EUR", "USD"]
        )
        transaction_date = st.date_input(
            "Date", value=date.today()
        )

        submitted = st.form_submit_button(
            "Add Transaction"
        )

        if submitted and description and amount > 0:
            cursor.execute(
                """INSERT INTO transactions
                (company_id, description, transaction_type,
                amount, currency, transaction_date)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    company_id, description,
                    transaction_type, amount,
                    currency, str(transaction_date)
                )
            )
            conn.commit()
            st.success("Transaction added!")
            st.rerun()

    cursor.execute(
        """SELECT transaction_type, SUM(amount)
        FROM transactions
        WHERE company_id=?
        GROUP BY transaction_type""",
        (company_id,)
    )
    totals = dict(cursor.fetchall())

    st.subheader("Financial Summary")
    col1, col2 = st.columns(2)

    col1.metric(
        "Total Revenues",
        f"{totals.get('Revenue', 0) or 0:,.2f}"
    )
    col2.metric(
        "Total Expenses",
        f"{totals.get('Expense', 0) or 0:,.2f}"
    )

    st.divider()
    st.subheader("Transaction History")

    cursor.execute(
        """SELECT description, transaction_type,
        amount, currency, transaction_date
        FROM transactions
        WHERE company_id=?
        ORDER BY id DESC""",
        (company_id,)
    )

    records = cursor.fetchall()

    if records:
        st.dataframe(
            records,
            column_config={
                0: "Description",
                1: "Type",
                2: "Amount",
                3: "Currency",
                4: "Date"
            },
            use_container_width=True
        )
    else:
        st.info("No transactions yet.")

conn.close()
