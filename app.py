from flask import Flask, render_template, request
app = Flask(__name__)

incomes = {}
expenses = {}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/finance', methods=['GET', 'POST'])
def finance_page():
    global incomes, expenses
    
    # Handle form submission
    if request.method == 'POST':
        type_of_entry = request.form['type']
        description = request.form['description']
        amount = float(request.form['amount'])

        # Add to the appropriate dictionary
        if type_of_entry == 'income':
            incomes[description] = amount
        else:
            expenses[description] = amount

    # Calculate total income and expenses
    total_income = sum(incomes.values())
    total_expenses = sum(expenses.values())
    net_result = total_income - total_expenses

    return render_template('finance.html', incomes=incomes, expenses=expenses, total_income=total_income, total_expenses=total_expenses, net_result=net_result)

if __name__ == '__main__':
    # Run the app on port 8000
    app.run(host='0.0.0.0', port=8000, debug=True)
