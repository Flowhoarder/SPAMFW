import sqlite3
import imaplib
import email
import re
import socket
from datetime import datetime
from flask import Flask, render_template_string, request

app = Flask(__name__)
DB_NAME = "propipo_live.db"

# ==========================================
# 🔧 VOS IDENTIFIANTS
# ==========================================
IMAP_SERVER = "outlook.office365.com"
EMAIL_USER = "spamfw@hotmail.com"
# ⚠️ REMETTEZ VOTRE MOT DE PASSE D'APPLICATION ICI
EMAIL_PASSWORD = "oxtgprzhozhbquep" 
# ==========================================

# --- 1. BASE DE DONNÉES ---
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reports 
                     (scammer_email TEXT PRIMARY KEY, scammer_name TEXT, count INTEGER, last_seen DATE)''')
        conn.commit()
        conn.close()
        print("Base de données initialisée.")
    except Exception as e:
        print(f"Erreur init DB: {e}")

# 🔥 CRUCIAL : On lance l'initialisation tout de suite au chargement
init_db()

# --- 2. EXTRACTION (FONCTION QUI MANQUAIT PEUT-ÊTRE) ---
def extract_scammer_info(text):
    if not text: return None, None
    
    # Regex pour "Nom <email>"
    pattern = r"(?:De|From)\s?:\s?(.*?)\s?<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        raw_name = match.group(1).replace('"', '').strip()
        email_addr = match.group(2).lower().strip()
        if "spamfw" in email_addr: return None, None
        if not raw_name: raw_name = "Inconnu"
        return raw_name, email_addr
        
    # Regex pour "email" simple
    pattern_simple = r"(?:De|From)\s?:\s?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    match_simple = re.search(pattern_simple, text, re.IGNORECASE)
    if match_simple:
        email_addr = match_simple.group(1).lower().strip()
        if "spamfw" in email_addr: return None, None
        return "Inconnu", email_addr
    return None, None

# --- 3. SAUVEGARDE (FONCTION QUI MANQUAIT PEUT-ÊTRE) ---
def save_to_db(name, email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    c.execute("SELECT * FROM reports WHERE scammer_email=?", (email,))
    data = c.fetchone()
    
    if data:
        c.execute("UPDATE reports SET count = count + 1, last_seen = ?, scammer_name = ? WHERE scammer_email = ?", (today, name, email))
    else:
        c.execute("INSERT INTO reports (scammer_email, scammer_name, count, last_seen) VALUES (?, ?, 1, ?)", (email, name, today))
    conn.commit()
    conn.close()

# --- 4. CONNEXION ET ANALYSE ---
def check_mail_and_update():
    new_reports = 0
    try:
        # Correctif IPv4 Doux
        allowed_families = (socket.AF_INET,)
        original_getaddrinfo = socket.getaddrinfo
        def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        socket.getaddrinfo = ipv4_only_getaddrinfo

        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        finally:
            socket.getaddrinfo = original_getaddrinfo
        
        mail.login(EMAIL_USER, EMAIL_PASSWORD)

        folders_to_check = ["inbox", "junk"]

        for folder in folders_to_check:
            try:
                mail.select(folder)
                status, messages = mail.search(None, "UNSEEN")
                
                if not messages or messages[0] == b'':
                    continue

                email_ids = messages[0].split()

                for e_id in email_ids:
                    try:
                        res, msg_data = mail.fetch(e_id, "(RFC822)")
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            try: body = part.get_payload(decode=True).decode()
                                            except: pass
                                else:
                                    try: body = msg.get_payload(decode=True).decode()
                                    except: pass

                                name, email_addr = extract_scammer_info(body)
                                if email_addr:
                                    save_to_db(name, email_addr)
                                    new_reports += 1
                    except Exception:
                        continue
            except Exception:
                continue

        mail.close()
        mail.logout()
        
        if new_reports == 0:
            return "Rien à signaler (Inbox & Spam vérifiés)."
        return f"Mise à jour : {new_reports} ajouts (depuis Inbox et Spam)."

    except Exception as e:
        return f"Erreur : {str(e)}"

# --- 5. DESIGN ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpamFW</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #ffffff; color: #2f3542; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .logo-container { text-align: center; margin-bottom: 30px; }
        .site-logo { max-width: 250px; height: auto; }
        .actions-box { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 30px; }
        .search-form { display: flex; gap: 5px; }
        .search-input { padding: 10px; border: 1px solid #ced6e0; border-radius: 20px; outline: none; width: 200px; }
        .search-btn { background: #2f3542; color: white; border: none; padding: 10px 15px; border-radius: 20px; cursor: pointer; }
        .update-btn { background: #ff4757; color: white; padding: 10px 20px; border-radius: 20px; text-decoration: none; font-weight: bold; border: none; cursor: pointer; }
        .update-btn:hover { background: #ff6b81; }
        .msg { text-align: center; margin-bottom: 20px; color: #2ed573; font-weight: bold; font-size: 0.9em; }
        .filter-info { text-align: center; color: #a4b0be; margin-bottom: 10px; font-size: 0.8em; font-style: italic;}
        .card { background: #f8f9fa; border: 1px solid #dfe4ea; margin-bottom: 10px; padding: 12px 20px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; }
        .card:hover { border-color: #ff4757; }
        .name { font-weight: bold; font-size: 1em; color: #1a1a1a; }
        .email { color: #747d8c; font-size: 0.85em; font-family: monospace; }
        .stats { text-align: right; }
        .count { font-weight: bold; color: #ff4757; font-size: 1.1em; }
        .date { font-size: 0.7em; color: #a4b0be; }
    </style>
</head>
<body>
<div class="container">
    <div class="logo-container">
        <a href="/"><img src="/static/logo_spamfw.png" alt="SpamFW" class="site-logo"></a>
    </div>
    <div class="actions-box">
        <a href="/update" class="update-btn">🔄 Actualiser</a>
        <form action="/" method="get" class="search-form">
            <input type="text" name="q" class="search-input" placeholder="Chercher un mail..." value="{{ query }}">
            <button type="submit" class="search-btn">🔍</button>
        </form>
    </div>
    {% if msg %}
        <div class="msg">{{ msg }}</div>
    {% endif %}
    {% if query %}
        <p style="text-align:center;">Résultats pour : <b>{{ query }}</b> (<a href="/">Voir tout</a>)</p>
    {% else %}
        <div class="filter-info">Classement des 10 derniers jours (Top 100)</div>
    {% endif %}
    {% for row in rows %}
    <div class="card">
        <div>
            <div class="name">{{ row[1] }}</div>
            <div class="email">{{ row[0] }}</div>
        </div>
        <div class="stats">
            <div class="count">{{ row[2] }}</div>
            <div class="date">Vu le {{ row[3] }}</div>
        </div>
    </div>
    {% endfor %}
    {% if not rows %}
        <p style="text-align:center; color:#a4b0be; margin-top:50px;">Aucun résultat trouvé.</p>
    {% endif %}
</div>
</body>
</html>
"""

@app.route('/')
def home():
    init_db() # Sécurité
    query = request.args.get('q', '')
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        if query:
            sql = "SELECT * FROM reports WHERE scammer_email LIKE ? OR scammer_name LIKE ? ORDER BY count DESC"
            c.execute(sql, ('%'+query+'%', '%'+query+'%'))
        else:
            c.execute("SELECT * FROM reports WHERE last_seen >= date('now', '-10 days') ORDER BY count DESC LIMIT 100")
            
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erreur home: {e}")
        rows = []
        
    return render_template_string(HTML_PAGE, rows=rows, query=query)

@app.route('/update')
def update():
    init_db() # Sécurité
    msg = check_mail_and_update()
    
    rows = []
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM reports WHERE last_seen >= date('now', '-10 days') ORDER BY count DESC LIMIT 100")
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        print(f"Erreur update: {e}")
        
    return render_template_string(HTML_PAGE, rows=rows, msg=msg, query='')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
