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

def fetch_messages():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/messages?order=created_at.desc&limit=50"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    res = requests.get(url, headers=headers)
    return res.json()

# ---------------------- WhatsApp Helpers ----------------------
def send_text(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    requests.post(url, headers=headers, json=payload)

# ---------------------- Gemini ----------------------
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

            if msg_type == "text":
                raw_text = message.get("text", {}).get("body", "")
                save_message(from_number, raw_text, "user")

                cleaned = re.sub(r'[^a-z]', '', raw_text.strip().lower())
                if cleaned in ["hi", "hello", "hey", "menu", "start", "ok"]:
                    reply = "🍽️ Welcome! Type 'order' to see our menu."
                elif "thank" in cleaned:
                    reply = "👍 Thanks for visiting Demo Restaurant!"
                else:
                    reply = ask_gemini(raw_text)

                send_text(from_number, reply)
                save_message(from_number, reply, "bot")

        except Exception as e:
            print("Error:", e)
        return "ok", 200

# ---------------------- Dashboard ----------------------
@app.route("/dashboard")
def dashboard():
    messages = fetch_messages()
    return render_template("dashboard.html", messages=messages)

@app.route("/reply", methods=["POST"])
def reply():
    user = request.form["user"]
    message = request.form["message"]
    send_text(user, message)
    save_message(user, message, "admin")
    return redirect("/dashboard")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
