from flask import Flask, jsonify, request
from dotenv import load_dotenv

from config import Config

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'self'; base-uri 'self'"
        origin = request.headers.get("Origin")
        if origin and origin in app.config["ALLOWED_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response

    @app.get("/")
    def home():
        return jsonify(
            {
                "app": "erp",
                "status": "ok",
                "message": "ERP base is running",
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
