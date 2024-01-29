import json
from datetime import datetime, timedelta
from pprint import pprint

import xendit
from flask import Flask, jsonify, request
from xendit.apis import BalanceApi, PaymentRequestApi

app = Flask(__name__)

#NOTE config
Xendit_API_key = "you-Xendit-API-Key"
BASE_URL="http://localhost:5000"

#NOTE init
xendit.set_api_key(Xendit_API_key)  #API key being encrypted by Xendit's modul
client = xendit.ApiClient()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            return obj.to_dict()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return super().default(obj)
        
def serialize_to_json(data, code=200, message="OK"):
    # Use the custom encoder to handle datetime objects and custom objects
    response = {
        'code': code,
        'message': message,
        'data': data
    }
    json_data = json.dumps(response, cls=CustomJSONEncoder, indent=2)
    return json_data

def format_datetime(dt=None, seconds_to_add=0):
  if dt is None:
    dt = datetime.now()

  # Add the specified seconds to the datetime
  adjusted_dt = dt + timedelta(seconds=seconds_to_add)

  # Format the adjusted datetime
  formatted_datetime = adjusted_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

  return formatted_datetime

@app.route("/balance", methods=["POST"])
def get_balance():
    response = [BalanceApi(client).get_balance('CASH'),BalanceApi(client).get_balance('TAX'),BalanceApi(client).get_balance('HOLDING')]
    prettier_response = {
        'CASH': response[0].balance,
        'HOLDING':response[2].balance,
        'TAX':response[1].balance,
    }
    return serialize_to_json(prettier_response)

@app.route("/checkout/payment", methods=["POST"])
def do_pay():
    data = request.get_json()
    total = int(data.get("total"))
    ext_id = data.get("external_id")
    payment_method = data.get("payment_method")

    #NOTE: VA method
    if (payment_method=="VIRTUAL_ACCOUNT"):
        channel=data.get("channel_code")
        if (channel not in ["BSI","BJB","CIMB","SAHABAT_SAMPOERNA","ARTAJASA","BRI","BNI","MANDIRI","PERMATA"]):   #NOTE change the channel list if not Indonesian
            return jsonify({"error":"Incorrect channel_code"}),400
        
        name=data.get("customer_name")
        if (name==None):
            return jsonify({"error":"Customer name is empty"}),400
        
        detail={
            "channel_code":channel,
            "currency":"IDR",
            "amount":total,
            "channel_properties":{
                "customer_name":name,
                "expires_at":format_datetime(None,3600)
            }
        }
    #-----------------------------------------------------------------------
    #NOTE: QR Code method
    if (payment_method=="QR_CODE"):
        channel=data.get("channel_code")

        if (channel not in ["LINKAJA","DANA"]):
            return jsonify({"error":"Incorrect channel_code"}),400

        detail={
            "channel_code":channel,
            "currency":"IDR",
            "amount":total,
        }
    #-----------------------------------------------------------------------
    #NOTE: eWallet method
    if (payment_method=="EWALLET"):
        channel=data.get("channel_code")

        if (channel not in ["LINKAJA","DANA","OVO","ASTRAPAY","JENIUSPAY","SHOPEEPAY","SAKUKU"]):    #NOTE change the channel list if not Indonesian
            return jsonify({"error":"Incorrect channel_code"}),400

        phone=data.get("phone_number")
        if (phone==None or not isinstance(phone, str)):
            return jsonify({"error":"Phone number needed in string format"}),400

        detail={
            "channel_code":channel,
            "currency":"IDR",
            "channel_properties":{
                "mobile_number":phone,
                "success_return_url":BASE_URL+"/webhook/success",
                "failure_return_url":BASE_URL+"/webhook/failed",
            },
            "amount":total,
        }
    #-----------------------------------------------------------------------

    api_instance = PaymentRequestApi(client)
    idempotency_key = data.get("idempotency_key",None)
    for_user_id= data.get("for_user_id",None)
    payment_request_parameters={
        "reference_id" : ext_id,
        "amount" : total,
        "currency" : "IDR",                       #NOTE change currency code if needed
        "country" : "ID",                         #NOTE change country code if needed
        "payment_method":{
            "type":payment_method,
            "reusability" : "ONE_TIME_USE",       #NOTE change if needed
            str(payment_method).lower():detail,
        },
    }

    api_response = api_instance.create_payment_request(idempotency_key=idempotency_key, for_user_id=for_user_id, payment_request_parameters=payment_request_parameters)

    return(serialize_to_json(api_response))

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
