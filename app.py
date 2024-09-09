from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('base.html')

if __name__ == '__main__':
    # Run the app on port 5000
    app.run(host='0.0.0.0', port=8000, debug=True)
