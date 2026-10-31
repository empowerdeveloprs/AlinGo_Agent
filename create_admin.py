import getpass, os
from werkzeug.security import generate_password_hash
from app import create_app
from modules.db import connect
app = create_app()
with app.app_context():
    username = input("New admin username: ").strip()
    if not username:
        raise SystemExit("Username is required.")
    password = getpass.getpass("New admin password (min 12 chars): ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")
    db = connect()
    db.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",
               (username,generate_password_hash(password)))
    db.commit()
    print("Admin created.")
