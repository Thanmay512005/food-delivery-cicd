from flask import Flask, jsonify, request, render_template
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import random

app = Flask(__name__)

# --- Prometheus Metrics ---
ORDER_COUNT = Counter('food_orders_total', 'Total food orders', ['item', 'status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])
TOTAL_REVENUE = Counter('food_revenue_total', 'Total revenue', ['item'])
ORDER_VALUE = Gauge('food_last_order_value', 'Last order value')
AVERAGE_ORDER = Gauge('food_average_order_value', 'Average order value')
TOTAL_ORDERS = Gauge('food_total_orders_count', 'Total orders count')
HIGHEST_ORDER = Gauge('food_highest_order_value', 'Highest order value')
UNIQUE_CUSTOMERS = Gauge('food_unique_customers_count', 'Unique customers today')
CUSTOMER_ORDER_COUNT = Counter('food_customer_orders_total', 'Orders per customer', ['customer'])
CATEGORY_COUNT = Counter('food_category_orders_total', 'Orders per category', ['category'])
HIGHEST_CUSTOMER_ORDER = Gauge('food_highest_customer_order', 'Highest order by a customer', ['customer'])

# --- Full Menu with 20 Items ---
MENU = {
    "1":  {"name": "Burger",          "price": 120, "prep_time": 15, "category": "Fast Food"},
    "2":  {"name": "Pizza",           "price": 250, "prep_time": 25, "category": "Fast Food"},
    "3":  {"name": "Pasta",           "price": 180, "prep_time": 20, "category": "Italian"},
    "4":  {"name": "Salad",           "price": 90,  "prep_time": 10, "category": "Healthy"},
    "5":  {"name": "Biryani",         "price": 200, "prep_time": 30, "category": "Indian"},
    "6":  {"name": "Dosa",            "price": 80,  "prep_time": 12, "category": "Indian"},
    "7":  {"name": "Paneer Tikka",    "price": 220, "prep_time": 20, "category": "Indian"},
    "8":  {"name": "Fried Rice",      "price": 150, "prep_time": 15, "category": "Chinese"},
    "9":  {"name": "Noodles",         "price": 130, "prep_time": 12, "category": "Chinese"},
    "10": {"name": "Sandwich",        "price": 100, "prep_time": 10, "category": "Fast Food"},
    "11": {"name": "Spring Rolls",    "price": 110, "prep_time": 15, "category": "Chinese"},
    "12": {"name": "Masala Chai",     "price": 30,  "prep_time": 5,  "category": "Drinks"},
    "13": {"name": "Butter Naan",     "price": 40,  "prep_time": 10, "category": "Indian"},
    "14": {"name": "Dal Makhani",     "price": 160, "prep_time": 25, "category": "Indian"},
    "15": {"name": "Chocolate Shake", "price": 120, "prep_time": 8,  "category": "Drinks"},
    "16": {"name": "French Fries",    "price": 80,  "prep_time": 8,  "category": "Fast Food"},
    "17": {"name": "Manchurian",      "price": 140, "prep_time": 15, "category": "Chinese"},
    "18": {"name": "Idli Sambar",     "price": 70,  "prep_time": 10, "category": "Indian"},
    "19": {"name": "Cold Coffee",     "price": 100, "prep_time": 5,  "category": "Drinks"},
    "20": {"name": "Gulab Jamun",     "price": 60,  "prep_time": 5,  "category": "Dessert"},
}

# --- In-memory store ---
orders = []
order_id_counter = 1
total_revenue_sum = 0
highest_order_value = 0
unique_customers = set()
customer_totals = {}
customer_highest = {}

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
    global order_id_counter, total_revenue_sum, highest_order_value
    start = time.time()
    data = request.get_json()

    if not data or 'item_id' not in data:
        return jsonify({"error": "item_id is required"}), 400

    item_id  = str(data.get('item_id'))
    quantity = int(data.get('quantity', 1))
    customer = data.get('customer', 'Guest').strip().title()

    if item_id not in MENU:
        ORDER_COUNT.labels(item='unknown', status='failed').inc()
        return jsonify({"error": "Item not found in menu"}), 404

    item        = MENU[item_id]
    status      = random.choice(['confirmed', 'confirmed', 'confirmed', 'delayed'])
    order_value = item['price'] * quantity

    order = {
        "order_id":    order_id_counter,
        "customer":    customer,
        "item":        item['name'],
        "category":    item['category'],
        "quantity":    quantity,
        "total_price": order_value,
        "status":      status,
        "prep_time":   f"{item['prep_time']} minutes",
        "timestamp":   time.strftime('%H:%M:%S')
    }
    orders.append(order)
    order_id_counter += 1

    # Update revenue and order stats
    total_revenue_sum += order_value
    if order_value > highest_order_value:
        highest_order_value = order_value

    # Track unique customers
    unique_customers.add(customer)
    UNIQUE_CUSTOMERS.set(len(unique_customers))

    # Track per customer totals
    if customer not in customer_totals:
        customer_totals[customer] = 0
    customer_totals[customer] += order_value

    # Track highest order per customer
    if customer not in customer_highest:
        customer_highest[customer] = 0
    if order_value > customer_highest[customer]:
        customer_highest[customer] = order_value
        HIGHEST_CUSTOMER_ORDER.labels(customer=customer).set(order_value)

    # Update all Prometheus metrics
    ORDER_COUNT.labels(item=item['name'], status=status).inc()
    TOTAL_REVENUE.labels(item=item['name']).inc(order_value)
    CUSTOMER_ORDER_COUNT.labels(customer=customer).inc()
    CATEGORY_COUNT.labels(category=item['category']).inc()
    ORDER_VALUE.set(order_value)
    TOTAL_ORDERS.set(len(orders))
    HIGHEST_ORDER.set(highest_order_value)
    AVERAGE_ORDER.set(total_revenue_sum / len(orders))

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
