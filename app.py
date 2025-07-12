from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load secrets from .env
MONGO_URI = os.getenv("MONGO_URI")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())
db = client.weatherDB
collection = db.weatherData

@app.route('/')
def home():
    return "🌤️ Weather API is running!"

@app.route('/api/weather', methods=['POST'])
def get_weather():
    data = request.get_json()
    city = data.get('city')

    if not city:
        return jsonify({'error': 'City name is required'}), 400

    try:
        # Step 1: Check cache in MongoDB
        existing_data = collection.find_one({'city': city.lower()})
        
        if existing_data:
            last_updated = existing_data.get('timestamp')
            if last_updated:
                time_diff = datetime.utcnow() - last_updated
                if time_diff < timedelta(hours=4):
                    print("✅ Returning cached weather data")
                    return jsonify(existing_data['weather'])

        # Step 2: Fetch fresh weather from OpenWeatherMap
        api_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(api_url)

        if response.status_code != 200:
            return jsonify({'error': 'City not found or API error'}), response.status_code

        weather_data = response.json()

        # Step 3: Save fresh data to MongoDB
        collection.update_one(
            {'city': city.lower()},
            {
                '$set': {
                    'city': city.lower(),
                    'weather': weather_data,
                    'timestamp': datetime.utcnow()
                }
            },
            upsert=True
        )

        print("✅ Fetched fresh weather and saved to DB")
        return jsonify(weather_data)

    except Exception as e:
        print("❗ ERROR:", e)
        return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)


# curl "https://api.openweathermap.org/data/2.5/weather?q=London&appid=6d83156e4e40ca97d0c6924b832fe00c"
