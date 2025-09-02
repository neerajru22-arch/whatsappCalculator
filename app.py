from flask import Flask, request
import requests
import os
import re
import google.generativeai as genai

app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini with updated model name
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")  # updated model name
else:
    gemini_model = None

# ---------------------- Menu Context ----------------------
MENU_CONTEXT = """
You are Demo Restaurant’s assistant. Only answer based on this menu.

Starters: Garlic Bread, Spring Rolls
Mains: Pizza, Pasta, Burgers
Desserts: Ice Cream, Brownie
Drinks: Coke, Lemonade

Rules:
- If asked about items not on the menu, politely say they are unavailable and list available options.
- Keep answers short and helpful, like a restaurant waiter.
- Do not answer general knowledge or off-topic questions.
"""

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
                    {"type": "reply", "reply": {"id": "more_options", "title": "More Options"}}
                ]
            },
        },
    }
    requests.post(url, headers=headers, json=payload)

def send_more_options(to):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Here are more options:"},
            "action": {
                "button": "Select",
                "sections": [
                    {
                        "title": "More Options",
                        "rows": [
                            {"id": "view_menu", "title": "View Menu (PDF)", "description": "See our full menu"},
                            {"id": "contact_us", "title": "Contact Us", "description": "Location & contact details"},
                            {"id": "offers", "title": "Special Offers", "description": "See latest deals"},
                        ]
                    }
                ]
            }
        }
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

# ---------------------- Gemini Integration ----------------------
def ask_gemini(query):
    if not gemini_model:
        return "Sorry, Gemini API is not configured."
    prompt = f"{MENU_CONTEXT}\nCustomer: {query}\nAssistant:"
    response = gemini_model.generate_content(prompt)
    return response.text

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
                    elif button_id == "more_options":
                        send_more_options(from_number)
                elif interactive["type"] == "list_reply":
                    list_id = interactive["list_reply"]["id"]
                    if list_id == "view_menu":
                        send_media(from_number, "document")
                    elif list_id == "contact_us":
                        send_location(from_number)
                        send_contact(from_number)
                    elif list_id == "offers":
                        send_media(from_number, "image")
                    else:
                        send_text(from_number, f"You selected {list_id}. (Demo order placed)")

            # Handle text replies
            elif msg_type == "text":
                raw_text = message.get("text", {}).get("body", "")
                cleaned = re.sub(r'[^a-z]', '', raw_text.strip().lower())

                if cleaned in ["hi", "hello", "hey", "menu", "start", "ok"]:
                    send_buttons(from_number)
                elif "thank" in cleaned:
                    send_reaction(msg_id, "👍")
                else:
                    reply = ask_gemini(raw_text)
                    send_text(from_number, reply)

        except Exception as e:
            print("Error:", e)
        return "ok", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
