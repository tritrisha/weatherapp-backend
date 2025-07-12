from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, os
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=True
)
db = client.weather_app
collection = db.weather_data

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

@app.route("/")
def home():
    return "✅ Weather API is live!"

@app.route("/api/weather", methods=["POST"])
def get_weather():
    try:
        data = request.get_json()
        city = data.get("city", "").strip().lower()
        if not city:
            return jsonify({"error": "City is required"}), 400

        cached = collection.find_one({"city": city})
        now = datetime.utcnow()

        if cached and (now - cached["timestamp"]) < timedelta(hours=4):
            print("📦 Serving from cache")
            return jsonify(cached["data"])

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)

        if response.status_code != 200:
            return jsonify({"error": "City not found or API error"}), 500

        weather_data = response.json()
        collection.update_one(
            {"city": city},
            {"$set": {"data": weather_data, "timestamp": now}},
            upsert=True
        )
        return jsonify(weather_data)

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": "Internal Server Error"}), 500

    

# Run locally only
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

# curl -X POST "https://weatherapp-backend-6jhn.onrender.com/api/weather" \
#   -H "Content-Type: application/json" \
#   -d '{"city": "London"}'

#curl -X POST "https://weatherapp-backend-6jhn.onrender.com/api/weather" -H "Content-Type: application/json" -d '{"city": "London"}'
