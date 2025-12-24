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
EMAIL_PASSWORD = "VOTRE_MOT_DE_PASSE_D_APPLICATION" 
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
        print("Base de données initialisée avec succès.")
    except Exception as e:
        print(f"Erreur d'initialisation DB: {e}")

# 🔥 CRUCIAL : On lance l'initialisation TOUT DE SUITE (pas à la fin)
init_db()

# --- 2. CONNEXION ET ANALYSE ---
def check_mail_and_update():
    # ... (Le reste de votre code ne change pas) ...
    # Je ne recopie pas tout pour ne pas saturer,
    # gardez votre fonction check_mail_and_update telle quelle.
    new_reports = 0
    try:
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
        
        # ... suite de la fonction ...
        # (Assurez-vous d'avoir le reste du code ici)
        # ...
        
        mail.logout()
        if new_reports == 0:
            return "Rien à signaler (Inbox & Spam vérifiés)."
        return f"Mise à jour : {new_reports} ajouts."
    except Exception as e:
        return f"Erreur : {str(e)}"

# ... (Gardez vos fonctions extract_scammer_info et save_to_db) ...

# ... (Gardez votre variable HTML_PAGE) ...

@app.route('/')
def home():
    # Par sécurité, on peut aussi appeler init_db ici au cas où
    # init_db() 
    query = request.args.get('q', '')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # On vérifie si la table existe avant de requêter pour éviter le crash 500
    try:
        if query:
            sql = "SELECT * FROM reports WHERE scammer_email LIKE ? OR scammer_name LIKE ? ORDER BY count DESC"
            c.execute(sql, ('%'+query+'%', '%'+query+'%'))
        else:
            c.execute("SELECT * FROM reports WHERE last_seen >= date('now', '-10 days') ORDER BY count DESC LIMIT 100")
        rows = c.fetchall()
    except sqlite3.OperationalError:
        # Si la table n'existe pas encore (cas rare), on renvoie une liste vide
        init_db() # On tente de la créer pour la prochaine fois
        rows = []
        
    conn.close()
    return render_template_string(HTML_PAGE, rows=rows, query=query)

@app.route('/update')
def update():
    # Ici, c'était votre point de crash
    init_db() # ON FORCE LA CREATION SI BESOIN AVANT DE SCANNER
    
    msg = check_mail_and_update()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM reports WHERE last_seen >= date('now', '-10 days') ORDER BY count DESC LIMIT 100")
        rows = c.fetchall()
    except:
        rows = []
    conn.close()
    return render_template_string(HTML_PAGE, rows=rows, msg=msg, query='')

if __name__ == '__main__':
    # Ceci ne sert que sur votre PC
    app.run(host='0.0.0.0', port=8080)
