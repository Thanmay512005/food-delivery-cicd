from flask import Flask, jsonify, request, render_template
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import random

app = Flask(__name__)

# --- Prometheus Metrics ---
ORDER_COUNT = Counter('food_orders_total', 'Total number of food orders', ['item', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency in seconds', ['endpoint'])

# --- Sample Menu ---
MENU = {
    "1": {"name": "Burger",      "price": 120, "prep_time": 15},
    "2": {"name": "Pizza",       "price": 250, "prep_time": 25},
    "3": {"name": "Pasta",       "price": 180, "prep_time": 20},
    "4": {"name": "Salad",       "price": 90,  "prep_time": 10},
    "5": {"name": "Biryani",     "price": 200, "prep_time": 30},
    "6": {"name": "Dosa",        "price": 80,  "prep_time": 12},
}

# --- In-memory order store ---
orders = []
order_id_counter = 1

@app.route('/')
def home():
    start = time.time()
    REQUEST_LATENCY.labels(endpoint='/').observe(time.time() - start)
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "QuickBite"}), 200

@app.route('/menu')
def get_menu():
    start = time.time()
    result = jsonify({"menu": MENU})
    REQUEST_LATENCY.labels(endpoint='/menu').observe(time.time() - start)
    return result

@app.route('/order', methods=['POST'])
def place_order():
    global order_id_counter
    start = time.time()
    data = request.get_json()

    if not data or 'item_id' not in data:
        return jsonify({"error": "item_id is required"}), 400

    item_id  = str(data.get('item_id'))
    quantity = int(data.get('quantity', 1))
    customer = data.get('customer', 'Guest')

    if item_id not in MENU:
        ORDER_COUNT.labels(item='unknown', status='failed').inc()
        return jsonify({"error": "Item not found in menu"}), 404

    item   = MENU[item_id]
    status = random.choice(['confirmed', 'confirmed', 'confirmed', 'delayed'])
    order  = {
        "order_id":    order_id_counter,
        "customer":    customer,
        "item":        item['name'],
        "quantity":    quantity,
        "total_price": item['price'] * quantity,
        "status":      status,
        "prep_time":   f"{item['prep_time']} minutes"
    }
    orders.append(order)
    order_id_counter += 1

    ORDER_COUNT.labels(item=item['name'], status=status).inc()
    REQUEST_LATENCY.labels(endpoint='/order').observe(time.time() - start)
    return jsonify({"message": "Order placed!", "order": order}), 201

@app.route('/orders')
def get_orders():
    start = time.time()
    result = jsonify({"total_orders": len(orders), "orders": orders})
    REQUEST_LATENCY.labels(endpoint='/orders').observe(time.time() - start)
    return result

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
