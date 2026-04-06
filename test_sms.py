import os
import requests

API_KEY = os.getenv("TERMII_API_KEY")

if not API_KEY:
    raise ValueError("TERMII_API_KEY is not set")

url = "https://api.ng.termii.com/api/sms/send"

payload = {
    "to": "2348063645308",
    "from": "IEDLABS",
    "sms": "Dear Nura Alh. Lawan, your lab result is ready.\nView or Download at: https://iandelaboratory.com/lookup\nRef: 50345\n- I&E Laboratory",
    "type": "plain",
    "channel": "generic",
    "api_key": API_KEY
}

response = requests.post(url, json=payload)

print("Status:", response.status_code)
print("Response:", response.text)