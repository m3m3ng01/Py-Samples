import base64
import json
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request

#!CONFIG
Xendit_API_key = "your-Xendit-API-key"
api_version = "2022-07-31"

#====== CONFIG END ===============


def format_datetime(dt=None, seconds_to_add=0):
  if dt is None:
    dt = datetime.now()

  # Add the specified seconds to the datetime
  adjusted_dt = dt + timedelta(seconds=seconds_to_add)

  # Format the adjusted datetime
  formatted_datetime = adjusted_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

  return formatted_datetime


#NOTE:formula for Xendit basic auth
basic_auth=base64.b64encode((Xendit_API_key+':').encode('utf-8')).decode('utf-8')

app = Flask(__name__)

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

@app.route("/QRpayment", methods=["POST"])
def createQR():
    url='https://api.xendit.co/qr_codes'
    
    data = request.get_json()
    total = int(data.get("total"))
    ref_id = data.get("reference_id")

    headers={
        'Authorization': f"Basic {basic_auth}",
        'api-version':api_version
    }
    body={
        'reference_id':ref_id,
        'type':"DYNAMIC",
        'currency':"IDR",
        "channel_code": "ID_LINKAJA",
        'expires_at':format_datetime(None,15*60), #for 15mins expiration
        'amount':list(total) if isinstance(total, set) else total 
    }
    
    response = API_Send(url,'post', headers, body)

    if (not response['status_code']==201):
        return jsonify({"Error": response['data']}), response['status_code']
    else:
        return jsonify(response['data']), response['status_code']

@app.route("/VApayment", methods=["POST"])
def createVA():
    url='https://api.xendit.co/callback_virtual_accounts'
    
    data = request.get_json()
    total = int(data.get("total"))
    ext_id = data.get("external_id")
    bank = data.get("bank_code")
    name = data.get("name")

    headers={
        'Authorization': f"Basic {basic_auth}",
        'api-version':api_version
    }
    body={
        'external_id':ext_id,
        'bank_code':bank,
        'name':name,
        'type':"DYNAMIC",
        'currency':"IDR",
        'is_closed':True,
        'is_single_use':True,
        'expected_amount':list(total) if isinstance(total, set) else total,
        'expiration_date': format_datetime(None,3600)    #for 1 hour expiration
    }

    response = API_Send(url,'post', headers, body)

    if (not response['status_code']==200):
        return jsonify({"Error": response['data']}), response['status_code']
    else:
        return jsonify(response['data']), response['status_code']

@app.route("/balance", methods=["POST"])
def get_balance():
    url=['https://api.xendit.co/balance?account_type=CASH','https://api.xendit.co/balance?account_type=HOLDING','https://api.xendit.co/balance?account_type=TAX']

    headers={
        'Authorization': f"Basic {basic_auth}",
        'api-version':api_version
    }
    balance={}
    for n in url:
        response = API_Send(n,'get', headers, {})
        print(response)
        if (not response['status_code']==200):
            return jsonify({"Error": response['data']}), response['status_code']
        else:
            account_type = n.split('=')[-1]
            balance[account_type] = response['data']['balance']
    return jsonify(balance), 200

@app.route("/webhook", methods=["POST"])
def handle_webhook():
  data = request.get_json()
  print(data)  #change this with further process after payment received
  return jsonify({"success":"Payment Success"}), 200


if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production
