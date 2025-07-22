from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
from datetime import datetime, timedelta
import requests

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
db = client.weather_app

# Collections
collection = db.weather_data        # For weather data caching
city_collection = db.cities         # For city suggestions

# Weather API Key
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# ----------------- ROUTES -----------------

@app.route("/", methods=["GET"])
def home():
    return "✅ Weather API is running!"

# City suggestions (autocomplete)
@app.route("/api/city-suggestions", methods=["GET"])
def city_suggestions():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=5&appid={WEATHER_API_KEY}"
        response = requests.get(geo_url)
        if response.status_code != 200:
            return jsonify([])

        data = response.json()
        suggestions = [f"{city['name']}, {city['country']}" for city in data]
        return jsonify(suggestions)

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify([])



# Weather endpoint
@app.route("/api/weather", methods=["POST"])
def get_weather():
    try:
        data = request.get_json()
        city = data.get("city")

        if not city:
            return jsonify({"error": "City is required"}), 400

        city = city.strip().lower()
        now = datetime.utcnow()

        # Check cache
        cached = collection.find_one({"city": city})
        if cached and (now - cached["timestamp"]) < timedelta(hours=12):
            print("📦 Serving weather from cache")
            return jsonify(cached["data"])

        # Fetch from API
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)

        if response.status_code != 200:
            return jsonify({"error": "City not found or server error"}), 500

        weather_data = response.json()

        # Update cache
        collection.update_one(
            {"city": city},
            {"$set": {"data": weather_data, "timestamp": now}},
            upsert=True
        )

        return jsonify(weather_data)

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"error": "Internal Server Error"}), 500

# ----------------- MAIN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
