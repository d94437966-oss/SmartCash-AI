
import streamlit as st
import sqlite3
import hashlib
from datetime import date

st.set_page_config(
    page_title="SmartCash AI",
    page_icon="💰",
    layout="wide"
)

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

st.title("💰 SmartCash AI")
st.subheader("Intelligent Financial Management")

# AUTHENTICATION
if "company_id" not in st.session_state:
    st.session_state.company_id = None

if st.session_state.company_id is None:

    choice = st.radio(
        "Welcome",
        ["Login", "Create Account"]
    )

    if choice == "Create Account":

        company = st.text_input("Company Name")
        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

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

# MAIN DASHBOARD
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

    st.success(f"Welcome, {company_name}!")

    if st.button("Logout"):
        st.session_state.company_id = None
        st.rerun()

    st.divider()
    st.header("Financial Dashboard")

    # ADD TRANSACTION
    st.subheader("Add Transaction")

    with st.form("transaction_form"):

        description = st.text_input("Description")

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Revenue", "Expense"]
        )

        amount = st.number_input(
            "Amount",
            min_value=0.0
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
            "Add Transaction"
        )

        if submitted:

            if description.strip() and amount > 0:

                cursor.execute(
                    """INSERT INTO transactions
                    (company_id, description, transaction_type,
                    amount, currency, transaction_date)
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

    # FINANCIAL SUMMARY
    st.divider()
    st.subheader("Financial Summary")

    cursor.execute(
        """SELECT currency, transaction_type, SUM(amount)
        FROM transactions
        WHERE company_id=?
        GROUP BY currency, transaction_type""",
        (company_id,)
    )

    totals = cursor.fetchall()

    currencies = sorted(set(row[0] for row in totals))

    if currencies:

        for curr in currencies:

            revenue = sum(
                row[2] or 0
                for row in totals
                if row[0] == curr and row[1] == "Revenue"
            )

            expense = sum(
                row[2] or 0
                for row in totals
                if row[0] == curr and row[1] == "Expense"
            )

            net_cash_flow = revenue - expense

            st.markdown(f"### {curr}")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Total Revenues",
                f"{revenue:,.2f} {curr}"
            )

            col2.metric(
                "Total Expenses",
                f"{expense:,.2f} {curr}"
            )

            col3.metric(
                "Net Cash Flow",
                f"{net_cash_flow:,.2f} {curr}"
            )

    else:
        st.info("No financial data yet.")

    # TRANSACTION HISTORY
    st.divider()
    st.subheader("Transaction History")

    cursor.execute(
        """SELECT id, description, transaction_type,
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
                0: "ID",
                1: "Description",
                2: "Type",
                3: "Amount",
                4: "Currency",
                5: "Date"
            },
            use_container_width=True,
            hide_index=True
        )

        # SELECT TRANSACTION
        st.divider()
        st.subheader("Manage Transactions")

        selected_id = st.selectbox(
            "Select Transaction",
            [r[0] for r in records],
            format_func=lambda tid: next(
                f"{r[1]} - {r[3]:,.2f} {r[4]} ({r[5]})"
                for r in records if r[0] == tid
            )
        )

        selected_record = next(
            r for r in records if r[0] == selected_id
        )

        # EDIT TRANSACTION
        st.markdown("### Edit Transaction")

        with st.form("edit_form"):

            new_description = st.text_input(
                "Description",
                value=selected_record[1]
            )

            new_type = st.selectbox(
                "Transaction Type",
                ["Revenue", "Expense"],
                index=(
                    0 if selected_record[2] == "Revenue" else 1
                )
            )

            new_amount = st.number_input(
                "Amount",
                min_value=0.0,
                value=float(selected_record[3])
            )

            new_currency = st.selectbox(
                "Currency",
                ["DZD", "EUR", "USD"],
                index=["DZD", "EUR", "USD"].index(
                    selected_record[4]
                )
            )

            new_date = st.date_input(
                "Date",
                value=date.fromisoformat(selected_record[5])
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
                            selected_id,
                            company_id
                        )
                    )

                    conn.commit()

                    st.success("Transaction updated!")
                    st.rerun()

                else:
                    st.warning("Enter valid information.")

        # DELETE TRANSACTION
        st.markdown("### Delete Transaction")

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
                (selected_id, company_id)
            )

            conn.commit()

            st.success("Transaction deleted!")
            st.rerun()

    else:
        st.info("No transactions yet.")

conn.close()
