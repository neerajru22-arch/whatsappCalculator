from flask import Flask, request
import requests
import os

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")

# ---------------------- Helper Functions ----------------------
def send_text(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    requests.post(url, headers=headers, json=payload)

def send_buttons(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🍽️ Welcome to Demo Restaurant! What would you like to do?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "order_food", "title": "Order Food"}},
                    {"type": "reply", "reply": {"id": "book_table", "title": "Table Booking"}},
                    {"type": "reply", "reply": {"id": "view_menu", "title": "View Menu"}},
                    {"type": "reply", "reply": {"id": "contact_us", "title": "Contact Us"}},
                    {"type": "reply", "reply": {"id": "offers", "title": "Special Offers"}},
                ]
            },
        },
    }
    requests.post(url, headers=headers, json=payload)

def send_food_list(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Choose a category:"},
            "action": {
                "button": "Select Category",
                "sections": [
                    {
                        "title": "Menu Categories",
                        "rows": [
                            {"id": "starters", "title": "Starters", "description": "Garlic Bread, Spring Rolls"},
                            {"id": "mains", "title": "Mains", "description": "Pizza, Pasta, Burgers"},
                            {"id": "desserts", "title": "Desserts", "description": "Ice Cream, Brownie"},
                            {"id": "drinks", "title": "Drinks", "description": "Coke, Lemonade"},
                        ],
                    }
                ],
            },
        },
    }
    requests.post(url, headers=headers, json=payload)

def send_media(to, media_type="image"):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    media_urls = {
        "image": "https://www.w3schools.com/w3images/pizza.jpg",
        "video": "https://www.w3schools.com/html/mov_bbb.mp4",
        "audio": "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav",
        "document": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "sticker": "https://www.gstatic.com/webp/gallery/1.sm.webp",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        media_type: {"link": media_urls.get(media_type, media_urls["image"])},
        "type": media_type,
    }
    requests.post(url, headers=headers, json=payload)

def send_location(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "location",
        "location": {
            "latitude": "40.748817",
            "longitude": "-73.985428",
            "name": "Demo Restaurant",
            "address": "350 5th Ave, New York, NY 10118",
        },
    }
    requests.post(url, headers=headers, json=payload)

def send_contact(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "contacts",
        "contacts": [
            {
                "name": {"formatted_name": "Demo Restaurant", "first_name": "Demo", "last_name": "Restaurant"},
                "phones": [{"phone": "+15551234567", "type": "WORK"}],
                "emails": [{"email": "info@demorestaurant.com", "type": "WORK"}],
            }
        ],
    }
    requests.post(url, headers=headers, json=payload)

def send_reaction(to_msg_id, emoji="👍"):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "reaction",
        "reaction": {"message_id": to_msg_id, "emoji": emoji},
    }
    requests.post(url, headers=headers, json=payload)

def send_template(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": "hello_world", "language": {"code": "en_US"}},
    }
    requests.post(url, headers=headers, json=payload)

# ---------------------- Webhook ----------------------
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
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
            msg_id = message.get("id")

            # Handle interactive replies
            if msg_type == "interactive":
                interactive = message["interactive"]
                if interactive["type"] == "button_reply":
                    button_id = interactive["button_reply"]["id"]
                    if button_id == "order_food":
                        send_food_list(from_number)
                    elif button_id == "book_table":
                        send_text(from_number, "How many guests? (Demo only)")
                    elif button_id == "view_menu":
                        send_media(from_number, "document")
                    elif button_id == "contact_us":
                        send_location(from_number)
                        send_contact(from_number)
                    elif button_id == "offers":
                        send_media(from_number, "image")
                elif interactive["type"] == "list_reply":
                    list_id = interactive["list_reply"]["id"]
                    send_text(from_number, f"You selected {list_id}. (Demo order placed)")

            # Handle text replies
            elif msg_type == "text":
                text = message.get("text", {}).get("body", "").strip().lower()

                if text in ["hi", "hello", "menu", "start"]:
                    send_buttons(from_number)
                elif "thank" in text:
                    send_reaction(msg_id, "👍")
                elif "video" in text:
                    send_media(from_number, "video")
                elif "audio" in text:
                    send_media(from_number, "audio")
                elif "sticker" in text:
                    send_media(from_number, "sticker")
                elif "template" in text:
                    send_template(from_number)
                else:
                    send_text(from_number, "I didn’t understand that 🤔. Type 'hi' to see the main menu again.")

        except Exception as e:
            print("Error:", e)
        return "ok", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
