import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    """Test home endpoint returns 200"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "message" in data
    assert "QuickBite" in data["message"]

def test_health(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "healthy"

def test_get_menu(client):
    """Test menu returns all 5 items"""
    response = client.get('/menu')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "menu" in data
    assert len(data["menu"]) == 5

def test_place_valid_order(client):
    """Test placing a valid order"""
    order_data = {
        "item_id": "1",
        "quantity": 2,
        "customer": "Test User"
    }
    response = client.post('/order',
                          data=json.dumps(order_data),
                          content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["order"]["item"] == "Burger"
    assert data["order"]["total_price"] == 240

def test_place_invalid_order(client):
    """Test placing an order with invalid item"""
    order_data = {
        "item_id": "99",
        "quantity": 1,
        "customer": "Test User"
    }
    response = client.post('/order',
                          data=json.dumps(order_data),
                          content_type='application/json')
    assert response.status_code == 404

def test_place_order_missing_item_id(client):
    """Test order without item_id returns 400"""
    response = client.post('/order',
                          data=json.dumps({"customer": "Test"}),
                          content_type='application/json')
    assert response.status_code == 400

def test_get_orders(client):
    """Test orders endpoint works"""
    response = client.get('/orders')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "total_orders" in data

def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint is accessible"""
    response = client.get('/metrics')
    assert response.status_code == 200
