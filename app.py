from flask import Flask, request, render_template, jsonify
import requests, os, re, google.generativeai as genai

app = Flask(__name__)

# Env - required
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_verify_token")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # optional

# Supabase - service role key (server-side) and anon key (for frontend realtime)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # service_role (server)
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")  # anon (frontend realtime)

# Configure Gemini only if key provided
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None

MENU_CONTEXT = """You are Demo Restaurant’s assistant. Only answer based on this menu.

Starters: Garlic Bread, Spring Rolls
Mains: Pizza, Pasta, Burgers
Desserts: Ice Cream, Brownie
Drinks: Coke, Lemonade

Rules:
- If asked about items not on the menu, politely say they are unavailable and list available options.
- Keep answers short and helpful, like a restaurant waiter.
- Do not answer general knowledge or off-topic questions.
"""

# ---------------------- Supabase helpers (server-side - use service_role key) ----------------------
def supabase_headers(service=True):
    key = SUPABASE_KEY if service else SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

def save_message(user, text, sender="user"):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    url = f"{SUPABASE_URL}/rest/v1/messages"
    payload = {"user_number": user, "text": text, "sender": sender}
    try:
        requests.post(url, headers=supabase_headers(service=True), json=payload, timeout=10)
    except Exception as e:
        print("Failed to save message:", e)

def fetch_messages_server(user_number):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    # return ordered ascending for chat display
    url = f"{SUPABASE_URL}/rest/v1/messages?user_number=eq.{user_number}&order=created_at.asc&limit=500"            headers = supabase_headers(service=True)
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        return res.json()
    print("fetch_messages_server failed", res.status_code, res.text)
    return []

def fetch_unique_users():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/messages?select=user_number&distinct=true"            headers = supabase_headers(service=True)
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        rows = res.json()
        # rows are objects like {'user_number': '919...'} - return list of numbers
        return [r['user_number'] for r in rows if 'user_number' in r]
    print("fetch_unique_users failed", res.status_code, res.text)
    return []

# ---------------------- WhatsApp helpers ----------------------
def send_text(to, text):
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("send_text missing credentials")
        return None
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "text": {"body": text}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print("WhatsApp API Response:", r.status_code, r.text)
        return r
    except Exception as e:
        print("send_text error", e)
        return None

def send_menu(to):
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("send_menu missing credentials")
        return None
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
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print("Menu Response:", r.status_code, r.text)
        return r
    except Exception as e:
        print("send_menu error", e)
        return None

# ---------------------- Gemini with memory ----------------------
def ask_gemini(user_number, query):
    if not gemini_model:
        return "Sorry, Gemini API is not configured."
    history = fetch_messages_server(user_number)[-10:]  # last 10 items
    history_text = ""
    for m in history:
        sender = m.get('sender','user').capitalize()
        history_text += f"{sender}: {m.get('text','')}\n"
    prompt = f"""{MENU_CONTEXT}\nPast conversation with this customer:\n{history_text}\nCustomer just said: {query}\nReply as the restaurant assistant."""
    try:
        resp = gemini_model.generate_content(prompt)
        # resp may have .text or structured - handle safely
        return getattr(resp, 'text', str(resp))
    except Exception as e:
        print("Gemini error", e)
        return "Sorry, I couldn't process that right now."

# ---------------------- Webhook ----------------------
@app.route('/webhook', methods=['GET','POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode and token and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403
    data = request.json
    try:
        changes = data.get('entry',[{}])[0].get('changes',[{}])[0].get('value',{})
        # Only process if 'messages' exists
        if 'messages' in changes:
            message = changes['messages'][0]
            from_number = message.get('from')
            msg_type = message.get('type')
            if msg_type == 'text':
                raw_text = message.get('text',{}).get('body','')
                save_message(from_number, raw_text, 'user')
                cleaned = re.sub(r'[^a-z]','', raw_text.strip().lower())
                if cleaned in ['hi','hello','hey','menu','start','ok']:
                    send_menu(from_number)
                    save_message(from_number, '[Menu shown]', 'bot')
                elif 'thank' in cleaned:
                    reply = '👍 Thanks for visiting Demo Restaurant!'
                    send_text(from_number, reply)
                    save_message(from_number, reply, 'bot')
                else:
                    reply = ask_gemini(from_number, raw_text)
                    send_text(from_number, reply)
                    save_message(from_number, reply, 'bot')
        else:
            print('Non-message event received:', changes.get('statuses') or changes)
    except Exception as e:
        print('Error in webhook:', e)
    return 'ok', 200

# ---------------------- Server APIs for dashboard ----------------------
@app.route('/api/users')
def api_users():
    users = fetch_unique_users()
    return jsonify({'users': users})

@app.route('/api/messages')
def api_messages():
    user = request.args.get('user')
    if not user:
        return jsonify({'messages': []})
    msgs = fetch_messages_server(user)
    return jsonify({'messages': msgs})

@app.route('/reply', methods=['POST'])
def reply_post():
    user = request.form.get('user')
    message = request.form.get('message')
    if not user or not message:
        return 'missing', 400
    send_text(user, message)
    save_message(user, message, 'admin')
    return ('', 204)

@app.route('/dashboard')
def dashboard():
    users = fetch_unique_users()
    # pass anon key and supabase url for realtime client in frontend
    return render_template('dashboard_realtime.html',
                           users=users,
                           supabase_url=SUPABASE_URL,
                           supabase_anon_key=SUPABASE_ANON_KEY)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
