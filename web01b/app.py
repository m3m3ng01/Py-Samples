#NOTE 
#this version using API
#input param from FE: number1, number2, operation

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    # Render the index.html template
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    # Get data from the JSON request
    data = request.get_json()
    number1 = float(data['number1'])
    number2 = float(data['number2'])
    operation = data['operation']

    # Perform the calculation
    result = None
    if operation == 'add':
        result = number1 + number2
    elif operation == 'subtract':
        result = number1 - number2
    else:
        # Handle invalid operations
        return jsonify({'error': 'Invalid operation'}), 400

    # Return the result as a JSON response
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app in debug mode
