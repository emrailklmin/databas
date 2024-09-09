from flask import Flask, render_template, request, redirect, url_for, flash
import pyodbc
import pickle
from credentials import SQL_SERVER  # Import hidden credentials

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Database connection settings using credentials from the hidden file
connection_string = f'Driver={SQL_SERVER["driver"]};Server=tcp:{SQL_SERVER["server"]},1433;Database={SQL_SERVER["database"]};Uid={SQL_SERVER["username"]};Pwd={SQL_SERVER["password"]};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

def get_db_connection():
    conn = pyodbc.connect(connection_string)
    return conn

incomes = {}
expenses = {}
savings = {}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')  # Placeholder for username input
        password = request.form.get('password')  # Placeholder for password input

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the user already exists
        query = "SELECT * FROM users WHERE username = ?"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        if user:
            flash("User already exists. Please login.", "warning")
        else:
            # Add user to the database
            insert_query = "INSERT INTO users (username, password) VALUES (?, ?)"
            cursor.execute(insert_query, (username, password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))

        conn.close()

    return render_template('register.html')

@app.route('/finance', methods=['GET', 'POST'])
def finance_page():
    global incomes, expenses, savings
    
    # Handle form submission
    if request.method == 'POST':
        type_of_entry = request.form['type']
        description = request.form['description']
        amount = float(request.form['amount'])

        # Add to the appropriate dictionary
        if type_of_entry == 'income':
            incomes[description] = amount
        elif type_of_entry == 'expense':
            expenses[description] = amount
        elif type_of_entry == 'savings':
            savings[description] = amount

    # Calculate total income and expenses
    total_income = sum(incomes.values())
    total_expenses = sum(expenses.values())
    total_savings = sum(savings.values())
    net_result = total_income - total_expenses
    net_result_after_savings = net_result - total_savings

    return render_template('finance.html', incomes=incomes, expenses=expenses, savings=savings, total_income=total_income, total_expenses=total_expenses, total_savings=total_savings, net_result=net_result, net_result_after_savings=net_result_after_savings)

if __name__ == '__main__':
    # Run the app on port 8000
    app.run(host='0.0.0.0', port=8000, debug=True)
