import base64
import json
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request

#!CONFIG
Xendit_API_key = "You-Xendit-API-key"
api_version = "2022-07-31"
BASE_URL="http://localhost:5000" #NOTE change it with your domain
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

def set_header():
    head={
        'Authorization': f"Basic {basic_auth}",
        'content-type': 'application/json',
        'api-version':api_version
    }
    return (head)

@app.route("/QRpayment", methods=["POST"])
def createQR():
    url='https://api.xendit.co/qr_codes'
    
    data = request.get_json()
    total = int(data.get("total"))
    ref_id = data.get("reference_id")
    curr=data.get("currency")

    body={
        'reference_id':ref_id,
        'type':"DYNAMIC",
        'currency':curr,
        "channel_code": "ID_LINKAJA",
        'expires_at':format_datetime(None,15*60), #for 15mins expiration
        'amount':list(total) if isinstance(total, set) else total 
    }
    
    response = API_Send(url,'post', set_header(), body)

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

    response = API_Send(url,'post', set_header(), body)

    if (not response['status_code']==200):
        return jsonify({"Error": response['data']}), response['status_code']
    else:
        return jsonify(response['data']), response['status_code']


@app.route("/EWpayment", methods=["POST"])
def createEW():
    url='https://api.xendit.co/ewallets/charges'
    
    data = request.get_json()
    total = int(data.get("total"))
    ref_id = data.get("reference_id")
    chann=data.get("channel_code")
    if (chann not in ["ID_LINKAJA","ID_DANA","ID_OVO","ID_ASTRAPAY","ID_JENIUSPAY","ID_SHOPEEPAY","ID_SAKUKU"]):    #NOTE change the channel list if not Indonesian
            return jsonify({"error":"Incorrect channel_code"}),400
    phone=data.get("phone_number",None)
    cashtag=data.get("cashtag",None)
    
    body={
        
            'reference_id':ref_id,
            'currency':'IDR',
            "channel_code": chann,
            "checkout_method": "ONE_TIME_PAYMENT",
            'expires_at':format_datetime(None,15*60), #for 15mins expiration
            'amount':list(total) if isinstance(total, set) else total,
        'channel_properties':{
            "cashtag":cashtag,
            "mobile_number":phone,
            'success_redirect_url':BASE_URL+'/webhook/success',
            'failure_redirect_url':BASE_URL+'/webhook/failed',
        }
    }

    if (chann=="ID_JENIUSPAY"):
        if (cashtag==None):
            return jsonify({"error":"Cashtag needed for selected channel"}),400
        else:
            body.update(
                {'channel_properties':{
                    "cashtag":cashtag
                }}
            )
    elif (chann=="ID_OVO"):
        if (phone==None):
            return jsonify({"error":"Phone number needed for selected channel"}),400
        else:
            if (phone==None or not isinstance(phone, str)):
                return jsonify({"error":"Phone number needed in string format"}),400
            body.update(
                {'channel_properties':{
                    "mobile_number":phone,
                    'success_redirect_url':BASE_URL+'/webhook/success',
                    'failure_redirect_url':BASE_URL+'/webhook/failed',
                }}
            )
    else:body.update(
                {'channel_properties':{
                    'success_redirect_url':BASE_URL+'/webhook/success',
                    'failure_redirect_url':BASE_URL+'/webhook/failed',
                }}
            )
    
    response = API_Send(url,'post', set_header(), body)

    if (not response['status_code']==202):
        return jsonify({"Error": response['data']}), response['status_code']
    else:
        return jsonify(response['data']), response['status_code']


@app.route("/balance", methods=["POST"])
def get_balance():
    url=['https://api.xendit.co/balance?account_type=CASH','https://api.xendit.co/balance?account_type=HOLDING','https://api.xendit.co/balance?account_type=TAX']

    balance={}
    for n in url:
        response = API_Send(n,'get', set_header(), {})
        if (not response['status_code']==200):
            return jsonify({"Error": response['data']}), response['status_code']
        else:
            account_type = n.split('=')[-1]
            balance[account_type] = response['data']['balance']
    return jsonify(balance), 200

def process_payment(data, status):
    # Common processing logic for both routes
    # NOTE processing logic here
    res=data
    status="Payment "+status

    return jsonify({"Status": status,"Output":res}), 200

@app.route("/webhook", methods=["POST"])
@app.route("/webhook/<status>", methods=["POST"])      #NOTE this line to handle callback from eWallet
def handle_webhook(status=None):
    data = request.get_json()
    
    if status is None:
        if (data.get("event")=="payment.succeeded"): return process_payment(data, "success")
        if (data.get("event")=="payment.failed"): return process_payment(data, "failed")
        # Handle case when status is not provided
        return jsonify({"Status": "Webhook Received"}), 200
    else:
        # Handle case when status is provided
        return process_payment(data, status)


if __name__ == "__main__":
    app.run(debug=True)  # Set debug=False in production
