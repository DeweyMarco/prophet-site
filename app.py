from flask import Flask, render_template, request, jsonify
import os
import requests
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

users = {"user": "password"}  # Replace with secure storage
logged_in_users = {}  # Store usernames and auth tokens

DEEPSEEK_MODEL = "deepseek/deepseek-r1-distill-llama-70b:free"
GEMINI_MODEL = "google/gemini-2.0-pro-exp-02-05:free"

API_KEY = "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"  # Replace with your actual API key!
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_auth_token(username):
    """Generates a simple (insecure) auth token."""
    # In a real app, use a secure token generation method.
    return f"{username}_token"


def authenticate(token):
    """Authenticates a user based on the token."""
    for username, stored_token in logged_in_users.items():
        if token == stored_token:
            return username
    return None


def analyze_with_deepseek(code):
    """Sends code to DeepSeek for bug analysis."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"Determine if the following code contains any bugs.\n\n{code}\n\nFormat your answer in the following tags <thing> [your reasoning] </thing> <answer> [buggy or correct] </answer>",
            }
        ],
    }
    try:
        logging.info(f"Sending DeepSeek Payload to R1")
        response = requests.post(
            API_URL, headers=headers, json=payload, timeout=20
        )  # Added timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"DeepSeek API error: {e}")
        return f"Error contacting DeepSeek API: {e}"
    except KeyError:
        logging.error("DeepSeek API response format error.")
        return "Error parsing DeepSeek API response."
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"An unexpected error occurred: {e}"


def analyze_with_google(code):
    """Sends code to Google for bug analysis."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Determine if the following code contains any bugs.\n\n{code}\n\nFormat your answer in the following tags <thing> [your reasoning] </thing> <answer> [buggy or correct] </answer>",
                    }
                ],
            }
        ],
    }
    try:
        logging.info(f"Sending Google Payload to Gemini")
        response = requests.post(
            API_URL, headers=headers, json=payload, timeout=20
        )  # Added timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Google API error: {e}")
        return f"Error contacting Google API: {e}"
    except KeyError:
        logging.error("Google API response format error.")
        return "Error parsing Google API response."
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"An unexpected error occurred: {e}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/team")
def team():
    return render_template("team.html")


@app.route("/demo")
def demo():
    return render_template("demo.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Missing username or password"}), 400

    username = data["username"]
    password = data["password"]

    if username in users and users[username] == password:
        token = generate_auth_token(username)
        logged_in_users[username] = token
        logging.info(f"User {username} logged in")
        return jsonify({"token": token, "message": "Login successful"}), 200
    else:
        return jsonify({"message": "Login failed"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization")
    username = authenticate(token)
    if username:
        del logged_in_users[username]
        logging.info(f"User {username} logged out")
        return jsonify({"message": "Logout successful"}), 200
    else:
        return jsonify({"message": "Invalid token"}), 401


@app.route("/analyzedeepseek", methods=["POST"])
def analyzedeepseek():
    logging.info(f"POST Request for DeepSeek Received")
    token = request.headers.get("Authorization")
    username = authenticate(token)
    if not username:
        return jsonify({"message": "Invalid token"}), 401

    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    if file:
        try:
            code = file.read().decode("utf-8")  # Read file content as string
            logging.info(f"Packaging DeepSeek Response")
            report = analyze_with_deepseek(code)
            return jsonify({"report": report}), 200
        except UnicodeDecodeError:
            return (
                jsonify(
                    {
                        "message": "Invalid file encoding. Please upload a UTF-8 encoded Python file."
                    }
                ),
                400,
            )
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            return jsonify({"message": f"Error processing file: {e}"}), 500


@app.route("/analyzegoogle", methods=["POST"])
def analyzegoogle():
    logging.info(f"POST Request for Google Received")
    token = request.headers.get("Authorization")
    username = authenticate(token)
    if not username:
        return jsonify({"message": "Invalid token"}), 401

    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    if file:
        try:
            code = file.read().decode("utf-8")  # Read file content as string
            logging.info(f"Packaging Google Response")
            report = analyze_with_google(code)
            return jsonify({"report": report}), 200
        except UnicodeDecodeError:
            return (
                jsonify(
                    {
                        "message": "Invalid file encoding. Please upload a UTF-8 encoded Python file."
                    }
                ),
                400,
            )
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            return jsonify({"message": f"Error processing file: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # debug = True for development.
