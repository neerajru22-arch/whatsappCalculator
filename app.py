from flask import Flask, request
import requests
import os

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification with Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode and token and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Forbidden", 403

    if request.method == 'POST':
        data = request.json
        try:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            from_number = message["from"]  # sender’s number
            text = message.get("text", {}).get("body", "")

            if text.isdigit():
                reply = str(int(text) + 1)
            else:
                reply = "Please send a number."

            url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": from_number,   # reply to whoever sent the message
                "text": {"body": reply}
            }
            requests.post(url, headers=headers, json=payload)
        except Exception as e:
            print("Error:", e)
        return "ok", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
