# utils/visualizer.py

import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

def plot_price_vs_time(prices: list[dict]) -> str:
    """
    Generate a base64-encoded plot of price vs time.
    Input: list of dicts with keys: {'timestamp', 'price'}
    """
    if not prices:
        return None

    times = [datetime.fromtimestamp(p['timestamp']) for p in prices]
    price_values = [p['price'] for p in prices]

    plt.figure(figsize=(10, 5))
    plt.plot(times, price_values, label="Price", color='blue')
    plt.title("Price vs Time")
    plt.xlabel("Time")
    plt.ylabel("Price (SOL)")
    plt.grid(True)
    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)

    # Encode as base64 to embed or send
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64