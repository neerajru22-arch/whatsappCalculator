from flask import Flask, request, render_template, redirect
import requests
import os
import re
import google.generativeai as genai

app = Flask(__name__)

# ENV Vars
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None

# Menu context
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

# ---------------------- Supabase Helpers ----------------------
def save_message(user, text, sender="user"):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/messages"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"user_number": user, "text": text, "sender": sender}
    requests.post(url, headers=headers, json=payload)

def fetch_messages(user_number=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    if user_number:
        url = f"{SUPABASE_URL}/rest/v1/messages?user_number=eq.{user_number}&order=created_at.asc"
    else:
        url = f"{SUPABASE_URL}/rest/v1/messages?order=created_at.desc&limit=50"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    res = requests.get(url, headers=headers)
    return res.json()

def fetch_unique_users():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/messages?select=user_number&distinct=true"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    res = requests.get(url, headers=headers)
    return list({m['user_number'] for m in res.json()})

# ---------------------- WhatsApp Helpers ----------------------
def send_text(to, text):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    response = requests.post(url, headers=headers, json=payload)
    print("WhatsApp API Response:", response.status_code, response.text)
    return response.json()

def send_menu(to):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": { "text": "Welcome to Demo Restaurant 🍽️\nWhat would you like to do?" },
            "action": {
                "buttons": [
                    { "type": "reply", "reply": { "id": "order_food", "title": "🍕 Order Food" }},
                    { "type": "reply", "reply": { "id": "table_booking", "title": "📅 Table Booking" }},
                    { "type": "reply", "reply": { "id": "help", "title": "❓ Help" }}
                ]
            }
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    print("Menu Response:", response.status_code, response.text)
    return response.json()

# ---------------------- Gemini with Memory ----------------------
def ask_gemini(user_number, query):
    if not gemini_model:
        return "Sorry, Gemini API is not configured."

    # Fetch last 10 messages for this user
    url = f"{SUPABASE_URL}/rest/v1/messages?user_number=eq.{user_number}&order=created_at.asc&limit=10"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    res = requests.get(url, headers=headers)
    history = res.json()

    history_text = ""
    for m in history:
        history_text += f"{m['sender'].capitalize()}: {m['text']}\n"

    prompt = f"""
    {MENU_CONTEXT}

    Past conversation with this customer:
    {history_text}

    Customer just said: {query}
    Reply as the restaurant assistant.
    """
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
            changes = data["entry"][0]["changes"][0]["value"]
            if "messages" in changes:
                message = changes["messages"][0]
                from_number = message["from"]
                msg_type = message.get("type")

                if msg_type == "text":
                    raw_text = message.get("text", {}).get("body", "")
                    save_message(from_number, raw_text, "user")

                    cleaned = re.sub(r'[^a-z]', '', raw_text.strip().lower())
                    if cleaned in ["hi", "hello", "hey", "menu", "start", "ok"]:
                        send_menu(from_number)
                        save_message(from_number, "[Menu shown]", "bot")
                    elif "thank" in cleaned:
                        reply = "👍 Thanks for visiting Demo Restaurant!"
                        send_text(from_number, reply)
                        save_message(from_number, reply, "bot")
                    else:
                        reply = ask_gemini(from_number, raw_text)
                        send_text(from_number, reply)
                        save_message(from_number, reply, "bot")
            else:
                print("Non-message event received:", changes)
        except Exception as e:
            print("Error in webhook:", e)
        return "ok", 200

# ---------------------- Dashboard ----------------------
@app.route("/dashboard")
def dashboard():
    user_number = request.args.get("user")
    if user_number:
        messages = fetch_messages(user_number)
    else:
        messages = []
    users = fetch_unique_users()
    return render_template("dashboard.html", messages=messages, users=users, current_user=user_number)

@app.route("/reply", methods=["POST"])
def reply():
    user = request.form["user"]
    message = request.form["message"]
    send_text(user, message)
    save_message(user, message, "admin")
    return redirect(f"/dashboard?user={user}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
