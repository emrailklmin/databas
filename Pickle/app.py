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
# Skapa kalkyl för sparande sidan. Utgå från savings_graph.html
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

def generate_total_savings_graph(savings_per_month):
    max_savings = max(savings_per_month.values()) if savings_per_month else 0  # Hämta maximal sparande
    y_max = max_savings + 500 
    
    # Skapa en Plotly-graf
    fig = go.Figure(data=[
        go.Scatter(
            x=list(savings_per_month.keys()), 
            y=list(savings_per_month.values()), 
            mode='lines+markers',  # För linjediagram med markörer
            name='Savings'
        )
    ])
    
    fig.update_layout(
        title='Total Savings Overview',
        xaxis_title='Months',
        yaxis_title='Total Savings (kr)',
        yaxis=dict(range=[0, y_max]),
        template='plotly_white'  # Valfritt: Lägg till en vit bakgrund
    )
    # Konvertera grafen till JSON-format
    savings_graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return savings_graph_json

def generate_savings_forecast_graph(savings_per_month):
    # Skapa en lista med ackumulerade sparanden
    months = list(range(1, len(savings_per_month) + 1))
    savings = list(savings_per_month.values())

    # Beräkna ackumulerade besparingar
    cumulative_savings = np.cumsum(savings)  # Cumulative sum of savings

    # Om det finns tillräckligt med data, gör en linjär regression för prognos
    if len(months) >= 2:
        # Linjär regression baserad på ackumulerat sparande
        coef, intercept = np.polyfit(months, cumulative_savings, 1)  # Linjär regression: y = coef*x + intercept

        # Prognos för kommande 3 månader (ackumulerad)
        future_months = list(range(len(months) + 1, len(months) + 4))  # Nästa 3 månader
        forecast_savings = [coef * month + intercept for month in future_months]

        # Beräkna ackumulerade prognosvärden (baserat på senaste ackumulerade värdet)
        last_cumulative_saving = cumulative_savings[-1]
        cumulative_forecast_savings = [last_cumulative_saving + (forecast - last_cumulative_saving) 
                                       for forecast in forecast_savings]
    else:
        # Om vi inte har tillräckligt med data för att göra en prognos
        future_months = []
        cumulative_forecast_savings = []

    # Skapa en Plotly-graf
    fig = go.Figure()

    # Historisk data (solid linje)
    fig.add_trace(go.Scatter(
        x=list(savings_per_month.keys()), 
        y=np.append(cumulative_savings, cumulative_forecast_savings),  # Append forecasted savings to cumulative savings
        mode='lines+markers', 
        name='Cumulative Savings',
        line=dict(color='blue')
    ))

    # Prognosdata (streckad linje för ackumulerad prognos)
    if future_months:
        # Använd månatliga etiketter för prognosen
        forecast_months = list(savings_per_month.keys()) + [f"Month {i}" for i in future_months]
        
        # Prognos y-värden
        y_forecast = list(cumulative_savings) + cumulative_forecast_savings  # Starta prognosen med det senaste ackumulerade värdet

        fig.add_trace(go.Scatter(
            x=forecast_months,  # Den sista månadens etikett och prognosetiketter
            y=y_forecast,  # Det sista ackumulerade värdet och prognosvärden
            mode='lines',
            name='Forecast',
            line=dict(color='red', dash='dash')  # Streckad linje för prognos
        ))

    # Justera y-axeln för att ha en marginal på 500 kr mer än högsta värdet
    max_savings = max(np.append(cumulative_savings, cumulative_forecast_savings)) if len(cumulative_savings) > 0 else 0
    y_max = max_savings + 500
    
    fig.update_layout(
        title='Savings Forecast',
        xaxis_title='Months',
        yaxis_title='Total Savings (kr)',
        yaxis=dict(range=[0, y_max]),  # Sätt intervallet för y-axeln
        template='plotly_white'
    )

    # Konvertera grafen till JSON-format
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json

# Route for displaying the savings graph
@app.route('/savings_graph', methods=['GET'])
def savings_graph():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = load_data()
    username = session['username']

    # Samla in besparingar per månad
    savings_per_month = {}
    total_savings = 0 
    accumulated_savings = 0 
    months = ['January', 'February', 'March', 'April', 'May', 
              'June', 'July', 'August', 'September', 'October', 
              'November', 'December']

    for month in months:
        if username in data['finances'] and month in data['finances'][username]:
            month_data = data['finances'][username][month]
            month_savings = sum(month_data.get('Savings', {}).values())
            accumulated_savings += month_savings  # Lägg till månadens sparande till ackumulerat värde
            savings_per_month[month] = accumulated_savings
        else:
            savings_per_month[month] = accumulated_savings  # Om ingen sparing för denna månad, använd föregående ackumulerade

    # Kontrollera om `total_savings` har ett värde
    total_savings = accumulated_savings  # Totala sparandet blir ackumulerat sparande vid årets slut

    # Generera grafen
    savings_graph_json = generate_total_savings_graph(savings_per_month)
    forecast_graph_json = generate_savings_forecast_graph(savings_per_month)

    # Rendera den nya HTML-sidan för att visa grafen
    return render_template('savings_graph.html', savings_graph_json=savings_graph_json, total_savings=total_savings, forecast_graph_json=forecast_graph_json)


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