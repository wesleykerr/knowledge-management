# Standard Library
import logging
import os
import traceback
from functools import wraps
from secrets import token_hex

# Third Party
import peewee
from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS

# Project
from bookmarks import bookmark_processor
from bookmarks import models
from bookmarks.utils import secret_creation

# Set up logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d %(name)s: %(message)s [%(process)d]",
    level=logging.WARN,
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Flask(__name__)

# Configure CORS more explicitly
CORS(
    app,
    resources={
        r"/*": {
            "origins": ["*"],  # In production, replace with specific origins
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)


# Initialize database
db = peewee.SqliteDatabase("data/database.db")
models.db.initialize(db)

# Generate a secure API key if it doesn't exist
API_KEY = secret_creation.get_or_create_api_key()


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "No API key provided"}), 401

        try:
            # Expected format: "Bearer <api_key>"
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return jsonify({"error": "Invalid authentication scheme"}), 401
            if token != API_KEY:
                return jsonify({"error": "Invalid API key"}), 401
        except ValueError:
            return jsonify({"error": "Invalid authorization header format"}), 401

        return f(*args, **kwargs)

    return decorated_function


@app.route("/test", methods=["GET"])
def test():
    logger.info("Test endpoint called")
    return jsonify({"status": "API is working"})


@app.route("/api/bookmark", methods=["POST", "OPTIONS"])
@require_api_key
def add_bookmark():
    if request.method == "OPTIONS":
        return handle_preflight()

    try:
        data = request.get_json()
        logger.info(
            f"Request data: URL={data.get('url')}, "
            f"HTML Content Length={len(data.get('html_content', ''))}, "
            f"Screenshot Length={len(data.get('screenshot', ''))}"
        )

        if not data or "url" not in data:
            logger.error("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]
        html_content = data.get("html_content")
        screenshot = data.get("screenshot")  # This will be a base64 encoded PNG

        try:
            # Pass the screenshot to your bookmark processor
            markdown = bookmark_processor.bookmark(
                url,
                html_content=html_content,
                screenshot=screenshot
            )
            logger.info("Successfully processed bookmark")
            return jsonify({"markdown": markdown})
        except Exception as e:
            logger.error("Error processing request: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error("Error parsing request: %s", str(e))
        return jsonify({"error": "Invalid request format"}), 400


def handle_preflight():
    response = jsonify({"status": "ok"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


if __name__ == "__main__":
    logger.info("Starting Flask server...")
    app.run(port=5001, host="0.0.0.0", debug=True)
