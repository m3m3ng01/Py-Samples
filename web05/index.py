import json

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def API_Send(url,method,header,body,print_input=False):
    request_info = {
        "url": url,
        "method": method,
        "headers": header,
        "json_data": body
    }

    if (print_input):
        print("\n ###-------####")
        print("Request Info:", json.dumps(request_info, indent=2))
        print("###-------####\n\n")

    if method=="post":
        # Make a POST request with JSON data
        response = requests.post(url, json=body, headers=header)
    else:
        # Make a GET request with JSON data
        response = requests.get(url, json=body, headers=header)
    return({'data':response.json(),'status_code':response.status_code})

Ollama_url='http://localhost:11434/api/generate'   #NOTE for port, check your running Ollama port


@app.route("/AI", methods=["POST"])
def chatbot():
    headers={
        'Content-Type':'cpplication/json'
    }

    quest = request.get_json()

    body={
        'model':'llama2',
        'prompt':str(quest),   #NOTE make sure the input is string, not dict.
        'stream':False
    }
    

    response = API_Send(Ollama_url,'post',headers,body)
    if (not response['status_code']==200):
        return jsonify({"Error": response['data']}), response['status_code']
    else:
        return jsonify({"reply":response['data']['response']}), response['status_code']
    
    '''
    NOTE this part works fine, but let's try my normal API_Send func
    response = requests.post(Ollama_url, json=body, headers=headers)

    return jsonify(response.json()['response']), response.status_code
    '''
if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production