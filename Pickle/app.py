import os
import pickle
import plotly
import plotly.graph_objs as go
import json
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Ändra home page till Title, två boxes: 1 för budgetering och 1 för sparande kalkyl. (ta bort "choose month" --> goto budget)
# Flytta över månadsvalet till budegeteringssidan, där default månad plockas via import Time.
# Omstrukturera Summary (siffrorna och förklaringerna så att de är linjärt ovanför varandra).
# Lägg till barchart höger om summary, kanske resultat + savings för varje månad.
# Skapa kalkyl för sparande sidan. Utgå från savings_graph.html, Trine
# Lägg till CSS för att göra sidan snyggare.

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Path to store the database file
DATABASE_PATH = 'database.pkl'

# Function to load data from the pickle database
def load_data():
    if not os.path.exists(DATABASE_PATH):
        return {'users': {}, 'finances': {}}
    with open(DATABASE_PATH, 'rb') as f:
        return pickle.load(f)

# Function to save data to the pickle database
def save_data(data):
    with open(DATABASE_PATH, 'wb') as f:
        pickle.dump(data, f)

@app.route('/')
def home():
    return redirect(url_for('login'))

# Route for Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data = load_data()

        if username in data['users'] and data['users'][username] == password:
            session['username'] = username
            return redirect(url_for('month'))  # Redirect to month selection after login
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# Route for Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        data = load_data()

        if username in data['users']:
            flash('Username already exists', 'error')
        else:
            data['users'][username] = password
            save_data(data)
            flash('Registration successful', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


# Route for selecting month
@app.route('/month', methods=['GET', 'POST'])
def month():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    data = load_data()
    username = session['username']
    
    if request.method == 'POST':
        selected_month = request.form['month']
        session['month'] = selected_month
        return redirect(url_for('finance'))
    
    # Display a list of months to choose from
    months = ['January', 'February', 'March', 'April', 'May', 
              'June', 'July', 'August', 'September', 'October', 
              'November', 'December']
    
    savings_per_month = {}
    for month in months:
        if username in data['finances'] and month in data['finances'][username]:
            month_data = data['finances'][username][month]
            total_savings = sum(month_data.get('Savings', {}).values())
            savings_per_month[month] = total_savings
        else:
            # If no data exists for this month, set savings to 0
            savings_per_month[month] = 0

    if 'total_savings' in session:
        current_month = session.get('month')
        savings_per_month[current_month] = session['total_savings']
    
    return render_template('month.html', months=months, savings_per_month=savings_per_month)

@app.route('/savings_calculator')
def savings_calculator():
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template('kalkylator.html')

# Route for Finance Tracker page
@app.route('/finance', methods=['GET', 'POST'])
def finance():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'month' not in session:
        return redirect(url_for('month'))

    data = load_data()
    username = session['username']
    month = session['month']

    # Create structure for user if it doesn't exist
    if username not in data['finances']:
        data['finances'][username] = {}

    # Create structure for the month if it doesn't exist
    if month not in data['finances'][username]:
        data['finances'][username][month] = {'Income': {}, 'Expense': {}, 'Savings': {}}

    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        type = request.form['type']

        # Save transaction under the correct month
        data['finances'][username][month][type][description] = amount
        save_data(data)

    # Retrieve financial data for the selected month
    finances = data['finances'][username][month]
    total_income = sum(finances['Income'].values())
    total_expenses = sum(finances['Expense'].values())
    total_savings = sum(finances['Savings'].values())
    net_result = total_income - total_expenses
    net_result_after_savings = net_result - total_savings

    session['total_savings'] = total_savings 

    return render_template('finance.html', 
                           incomes=finances['Income'], 
                           expenses=finances['Expense'], 
                           savings=finances['Savings'], 
                           total_income=total_income, 
                           total_expenses=total_expenses,
                           net_result=net_result,
                           total_savings=total_savings,
                           net_result_after_savings=net_result_after_savings,
                           month=month)


# Route for deleting an entry
@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = load_data()
    username = session['username']
    month = session['month']  # Get the current month from the session
    type = request.form['type']
    description = request.form['description']

    if username in data['finances'] and month in data['finances'][username]:
        if description in data['finances'][username][month][type]:
            del data['finances'][username][month][type][description]
            save_data(data)

    return redirect(url_for('finance'))

# Route for Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('month', None)  # Clear selected month on logout
    return redirect(url_for('login'))

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    print(f"Starting Flask server on http://{host}:{port}")
    app.run(debug=True, host=host, port=port)  # Specify host and port
    print(f"Server running on http://{host}:{port}")