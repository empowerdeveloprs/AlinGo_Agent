import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from modules.db import init_db, close_db

def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY","unsafe-development-secret-change-me"),
        DATABASE_PATH=os.getenv("DATABASE_PATH","instance/zentrix_modular.db"),
        DEVICE_OFFLINE_AFTER_SECONDS=90,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
    from modules.auth import bp as auth_bp
    from modules.devices import bp as devices_bp
    from modules.surveys import bp as surveys_bp
    from modules.audit_requests import bp as audit_bp
    from modules.dashboard import bp as dashboard_bp
    from modules.admin import bp as admin_bp
    from modules.candidate_links import bp as candidate_links_bp
    from modules.file_audit import bp as file_audit_bp
    from modules.device_file_audit import bp as device_file_audit_bp
    from modules.screen_viewer import admin_bp as screen_viewer_admin_bp, device_bp as screen_viewer_device_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(surveys_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(candidate_links_bp)
    app.register_blueprint(file_audit_bp)
    app.register_blueprint(device_file_audit_bp)

    app.register_blueprint(screen_viewer_admin_bp)
    app.register_blueprint(screen_viewer_device_bp)

    @app.get("/health")
    def health():
        return jsonify({"status":"ok","app":"Zentrix Device Connect"})
    return app
