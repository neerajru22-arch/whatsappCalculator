from flask import Flask, request
import requests
import os

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")

def send_buttons(to_number):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Choose an option:"},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "btn1", "title": "Calculator"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "btn2", "title": "Help"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "btn3", "title": "Show Menu"}
                    }
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

def send_list(to_number):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Pick a service:"},
            "footer": {"text": "Powered by WhatsApp Bot"},
            "action": {
                "button": "Select",
                "sections": [
                    {
                        "title": "Main Menu",
                        "rows": [
                            {"id": "calc", "title": "Calculator", "description": "Simple number calculator"},
                            {"id": "info", "title": "Info", "description": "Get bot info"},
                            {"id": "help", "title": "Help", "description": "Instructions"}
                        ]
                    }
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

def send_text(to_number, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": text}
    }
    requests.post(url, headers=headers, json=payload)

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
            from_number = message["from"]
            msg_type = message.get("type")

            # Handle interactive replies (buttons or list)
            if msg_type == "interactive":
                interactive = message["interactive"]
                if interactive["type"] == "button_reply":
                    button_id = interactive["button_reply"]["id"]
                    if button_id == "btn1":
                        send_text(from_number, "Send me a number, and I will add +1 to it.")
                    elif button_id == "btn2":
                        send_text(from_number, "This is a demo bot. Use Calculator to try adding +1 to any number.")
                    elif button_id == "btn3":
                        send_list(from_number)
                elif interactive["type"] == "list_reply":
                    list_id = interactive["list_reply"]["id"]
                    if list_id == "calc":
                        send_text(from_number, "Send me a number, and I will add +1 to it.")
                    elif list_id == "info":
                        send_text(from_number, "I am a demo WhatsApp bot with buttons and lists!")
                    elif list_id == "help":
                        send_text(from_number, "Use Calculator to add +1 to a number. Use Info for bot details.")

            # Handle normal text messages
            elif msg_type == "text":
                text = message.get("text", {}).get("body", "").strip().lower()
                if text.isdigit():
                    reply = str(int(text) + 1)
                    send_text(from_number, reply)
                else:
                    # Default: show menu buttons
                    send_buttons(from_number)

        except Exception as e:
            print("Error:", e)
        return "ok", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host="0.0.0.0", port=port)
