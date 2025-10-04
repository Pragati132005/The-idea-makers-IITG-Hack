# import streamlit as st
# import mysql.connector
# from datetime import date

# # Database connection
# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="",  # Replace with your actual password
#         database="expense_management"
#     )

# # Sidebar login
# st.sidebar.title("Login")
# username = st.sidebar.text_input("Username")
# password = st.sidebar.text_input("Password", type="password")
# login_button = st.sidebar.button("Login")

# if login_button:
#     conn = get_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT * FROM Users WHERE username=%s AND password=%s", (username, password))
#     user = cursor.fetchone()

#     if user:
#         st.success(f"Welcome {user['username']} ({user['role']})")

#         # Employee View
#         if user['role'] == 'Employee':
#             st.header("Submit Expense")
#             amount = st.number_input("Amount", min_value=0.0)
#             currency = st.selectbox("Currency", ["INR", "USD", "EUR"])
#             category = st.text_input("Category")
#             description = st.text_area("Description")

#             if st.button("Submit"):
#                 cursor.execute("""
#                     INSERT INTO Expenses (employee_id, amount, currency, category, description, expense_date, status)
#                     VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
#                 """, (user['user_id'], amount, currency, category, description, date.today()))
#                 conn.commit()
#                 st.success("Expense submitted!")

#             st.subheader("My Expenses")
#             cursor.execute("SELECT * FROM Expenses WHERE employee_id=%s", (user['user_id'],))
#             for row in cursor.fetchall():
#                 st.write(row)

#         # Manager/Admin View
#         else:
#             st.header("Pending Approvals")
#             cursor.execute("""
#                 SELECT a.approval_id, e.expense_id, e.amount, e.currency, e.category, e.description, e.status
#                 FROM Approvals a
#                 JOIN Expenses e ON a.expense_id = e.expense_id
#                 WHERE a.approver_id = %s AND a.decision = 'Pending'
#             """, (user['user_id'],))
#             approvals = cursor.fetchall()

#             for app in approvals:
#                 st.write(f"Expense ID: {app['expense_id']}, Amount: {app['amount']} {app['currency']}, Category: {app['category']}")
#                 comment = st.text_input(f"Comment for Expense {app['expense_id']}", key=f"cmt{app['approval_id']}")
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     if st.button(f"Approve {app['approval_id']}"):
#                         cursor.execute("""
#                             UPDATE Approvals SET decision='Approved', comments=%s, decided_at=NOW()
#                             WHERE approval_id=%s
#                         """, (comment, app['approval_id']))
#                         cursor.execute("UPDATE Expenses SET status='Approved' WHERE expense_id=%s", (app['expense_id'],))
#                         conn.commit()
#                         st.success(f"Expense {app['expense_id']} approved")
#                 with col2:
#                     if st.button(f"Reject {app['approval_id']}"):
#                         cursor.execute("""
#                             UPDATE Approvals SET decision='Rejected', comments=%s, decided_at=NOW()
#                             WHERE approval_id=%s
#                         """, (comment, app['approval_id']))
#                         cursor.execute("UPDATE Expenses SET status='Rejected' WHERE expense_id=%s", (app['expense_id'],))
#                         conn.commit()
#                         st.error(f"Expense {app['expense_id']} rejected")

#             st.header("Approval Percentage")
#             exp_id = st.number_input("Enter Expense ID", min_value=1)
#             if st.button("Calculate"):
#                 cursor.execute("""
#                     SELECT 
#                         (SUM(CASE WHEN decision='Approved' THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS approval_percentage
#                     FROM Approvals
#                     WHERE expense_id=%s
#                 """, (exp_id,))
#                 result = cursor.fetchone()
#                 st.write(f"Approval Percentage: {result['approval_percentage']:.2f}%")

#     else:
#         st.error("Invalid credentials")

#     cursor.close()
#     conn.close()

from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "expense_secret_key"

# ✅ Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",             # your MySQL username
    password="",# your MySQL password
    database="expense_management"
)
cursor = db.cursor(dictionary=True)

# ------------------------------------------------------------
# 🔐 LOGIN PAGE
# ------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cursor.execute("SELECT * FROM Users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            session['username'] = user['username']

            # ✅ Make sure to COMMIT session data before redirect
            db.commit()

            # ✅ Explicit redirect based on role
            if user['role'] == 'Employee':
                return redirect(url_for('dashboard'))
            elif user['role'] == 'Manager' or user['role'] == 'Admin':
                return redirect(url_for('approvals'))
            else:
                return render_template('login.html', error="Admin role not supported yet.")

        # if login fails
        return render_template('login.html', error="Invalid username or password.")
    
    #✅ If already logged in, skip login page
    if 'user_id' in session:
        if session['role'] == 'Employee':
            return redirect(url_for('dashboard'))
        elif session['role'] == 'Manager':
            return redirect(url_for('approvals'))

    return render_template('login.html')

# ------------------------------------------------------------
# 🧾 EMPLOYEE DASHBOARD
# ------------------------------------------------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session['role'] != 'Employee':
        return redirect(url_for('login'))

    employee_id = session['user_id']

    # when employee submits new expense
    if request.method == 'POST':
        amount = request.form.get('amount')
        currency = request.form.get('currency')
        category = request.form.get('category')
        description = request.form.get('description')
        expense_date = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT INTO Expenses (employee_id, amount, currency, category, description, expense_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
        """, (employee_id, amount, currency, category, description, expense_date))
        db.commit()

        expense_id = cursor.lastrowid

        # link to manager for approval
        cursor.execute("SELECT manager_id FROM Users WHERE user_id=%s", (employee_id,))
        manager = cursor.fetchone()
        if manager and manager['manager_id']:
            cursor.execute("""
                INSERT INTO Approvals (expense_id, approver_id, step_order)
                VALUES (%s, %s, 1)
            """, (expense_id, manager['manager_id']))
            db.commit()

        return redirect(url_for('dashboard'))

    # fetch all employee expenses
    cursor.execute("""
        SELECT * FROM Expenses WHERE employee_id=%s ORDER BY expense_date DESC
    """, (employee_id,))
    expenses = cursor.fetchall()

    # Pass data so your existing dashboard.html can display
    return render_template('dashboard.html', expenses=expenses)

# ------------------------------------------------------------
# ✅ MANAGER APPROVAL PAGE
# ------------------------------------------------------------
@app.route('/approvals')
def approvals():
    if 'user_id' not in session or session['role'] != 'Manager':
        return redirect(url_for('login'))

    manager_id = session['user_id']

    cursor.execute("""
        SELECT 
            a.approval_id,
            e.expense_id,
            u.username AS employee,
            e.amount, e.currency, e.category, e.description, e.expense_date
        FROM Approvals a
        JOIN Expenses e ON a.expense_id = e.expense_id
        JOIN Users u ON e.employee_id = u.user_id
        WHERE a.approver_id=%s AND a.decision='Pending'
        ORDER BY e.expense_date DESC
    """, (manager_id,))
    approvals = cursor.fetchall()

    return render_template('approvals.html', approvals=approvals)

# ------------------------------------------------------------
# 🟢 APPROVE / REJECT ACTIONS
# ------------------------------------------------------------
@app.route('/update/<int:approval_id>/<string:action>', methods=['POST'])
def update_approval(approval_id, action):
    if 'user_id' not in session or session['role'] != 'Manager':
        return redirect(url_for('login'))

    decision = 'Approved' if action == 'approve' else 'Rejected'

    cursor.execute("""
        UPDATE Approvals 
        SET decision=%s, decided_at=NOW() 
        WHERE approval_id=%s
    """, (decision, approval_id))
    db.commit()

    # find related expense
    cursor.execute("SELECT expense_id FROM Approvals WHERE approval_id=%s", (approval_id,))
    expense = cursor.fetchone()

    if expense:
        expense_id = expense['expense_id']
        cursor.execute("UPDATE Expenses SET status=%s WHERE expense_id=%s", (decision, expense_id))
        db.commit()

    return redirect(url_for('approvals'))

# ------------------------------------------------------------
# 🚪 LOGOUT
# ------------------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------------------------------------------------
# 🚀 RUN FLASK APP
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
