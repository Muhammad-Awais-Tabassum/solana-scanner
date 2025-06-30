import os
import pickle
import numpy as np
from datetime import datetime, timedelta
from utils.api_helpers import fetch_price_history_birdeye

# Load model from root directory
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token_revival_model.pkl')
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

def extract_features(price_data: list[dict]) -> dict:
    """
    Given Birdeye price history, extract revival features.
    """
    if not price_data or len(price_data) < 2:
        return None

    prices = [point['value'] for point in price_data]
    timestamps = [point['timestamp'] for point in price_data]

    ath = max(prices)
    current_price = prices[-1]
    dip_percent = (ath - current_price) / ath * 100 if ath != 0 else 0

    # Check last 5 min volume
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    recent_prices = [
        point['value'] for point in price_data
        if datetime.utcfromtimestamp(point['timestamp']) > cutoff_time
    ]
    recent_volume = np.sum(recent_prices) if recent_prices else 0

    return {
        'ath': ath,
        'current_price': current_price,
        'dip_percent': dip_percent,
        'recent_volume': recent_volume
    }

def predict_token_status(token_address: str) -> str:
    """
    Predict whether token is reviving or dead using trained ML model.
    """
    price_data = fetch_price_history_birdeye(token_address, interval='1m', span='1h')
    features = extract_features(price_data)

    if not features:
        return "unknown"

    feature_vector = np.array([
        features['ath'],
        features['current_price'],
        features['dip_percent'],
        features['recent_volume']
    ]).reshape(1, -1)

    prediction = model.predict(feature_vector)[0]
    return "reviving" if prediction == 1 else "dead"