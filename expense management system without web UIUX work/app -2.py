from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "expense_secret_key"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="expense_management"
)
cursor = db.cursor(dictionary=True)

# -------------------------------
# 🔐 LOGIN
# -------------------------------
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

            if user['role'] == 'Employee':
                return redirect(url_for('dashboard'))
            elif user['role'] == 'Manager':
                return redirect(url_for('approvals'))
            else:
                return render_template('login.html', error="Admin role not supported yet.")

        return render_template('login.html', error="Invalid username or password.")

    if 'user_id' in session:
        if session['role'] == 'Employee':
            return redirect(url_for('dashboard'))
        elif session['role'] == 'Manager':
            return redirect(url_for('approvals'))

    return render_template('login.html')

# -------------------------------
# 🧾 EMPLOYEE DASHBOARD
# -------------------------------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session['role'] != 'Employee':
        return redirect(url_for('login'))

    employee_id = session['user_id']

    if request.method == 'POST':
        amount = request.form.get('amount')
        currency = request.form.get('currency')
        category = request.form.get('category')
        description = request.form.get('description')
        expense_date = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT INTO Expenses (employee_id, amount, currency, category, description, expense_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (employee_id, amount, currency, category, description, expense_date))
        db.commit()

        expense_id = cursor.lastrowid

        cursor.execute("SELECT manager_id FROM Users WHERE user_id=%s", (employee_id,))
        manager = cursor.fetchone()
        if manager and manager['manager_id']:
            cursor.execute("""
                INSERT INTO Approvals (expense_id, approver_id, step_order)
                VALUES (%s, %s, 1)
            """, (expense_id, manager['manager_id']))
            db.commit()

        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM Expenses WHERE employee_id=%s ORDER BY expense_date DESC", (employee_id,))
    expenses = cursor.fetchall()

    return render_template('dashboard.html', expenses=expenses)

# -------------------------------
# ✅ MANAGER APPROVALS
# -------------------------------
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

# -------------------------------
# 🟢 APPROVE / REJECT
# -------------------------------
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

    cursor.execute("SELECT expense_id FROM Approvals WHERE approval_id=%s", (approval_id,))
    expense = cursor.fetchone()

    if expense:
        expense_id = expense['expense_id']
        cursor.execute("UPDATE Expenses SET status=%s WHERE expense_id=%s", (decision, expense_id))
        db.commit()

    return redirect(url_for('approvals'))

# -------------------------------
# 🚪 LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------------
# 🚀 RUN
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)