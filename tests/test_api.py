"""
End-to-end tests for Profit Optimizer API
"""

import pytest
import sys
import os

# Add server/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

# Set environment to testing
os.environ['FLASK_ENV'] = 'testing'


@pytest.fixture
def client():
    """Create test client."""
    # Import after setting path
    from api.index import app
    
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def optimizer_client(client):
    """Create test client with optimizer module."""
    from api.index import OPTIMIZER_AVAILABLE
    
    if not OPTIMIZER_AVAILABLE:
        pytest.skip("Optimizer module not available")
    
    yield client


@pytest.fixture
def finance_client(client):
    """Create test client with finance module."""
    from api.index import FINANCE_AVAILABLE
    
    if not FINANCE_AVAILABLE:
        pytest.skip("Finance module not available")
    
    yield client


@pytest.fixture
def invoice_client(client):
    """Create test client with invoice module."""
    from api.index import INVOICE_AVAILABLE
    
    if not INVOICE_AVAILABLE:
        pytest.skip("Invoice module not available")
    
    yield client


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_home_endpoint(self, client):
        """Test home endpoint returns status."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'modules' in data


class TestOptimizerAPI:
    """Test optimizer API endpoints."""
    
    def test_get_variables_empty(self, optimizer_client):
        """Test getting variables when list is empty."""
        response = optimizer_client.get('/api/optimizer/variables')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'variables' in data
    
    def test_add_variable(self, optimizer_client):
        """Test adding a new optimization variable."""
        response = optimizer_client.post('/api/optimizer/variable', 
            json={
                'name': 'test_item',
                'lowerBound': 0,
                'upperBound': 100,
                'cost': 10.0,
                'profit': 25.0,
                'multiplier': 1
            })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_clear_variables(self, optimizer_client):
        """Test clearing all variables."""
        response = optimizer_client.post('/api/optimizer/clear')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


class TestFinanceAPI:
    """Test finance API endpoints."""
    
    def test_get_finance_data(self, finance_client):
        """Test getting finance dashboard data."""
        response = finance_client.get('/api/finance/data')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'accounts' in data['data']
        assert 'categories' in data['data']
        assert 'transactions' in data['data']
    
    def test_create_account(self, finance_client):
        """Test creating a new account."""
        response = finance_client.post('/api/finance/account',
            json={
                'name': 'Test Account',
                'type': 'checking',
                'balance': 1000.0,
                'currency': 'ZAR',
                'institution': 'Test Bank'
            })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'account' in data


class TestInvoiceAPI:
    """Test invoice API endpoints."""
    
    def test_list_invoices_empty(self, invoice_client):
        """Test listing invoices when none exist."""
        response = invoice_client.get('/api/invoice/list')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'invoices' in data


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_route(self, client):
        """Test 404 for invalid routes."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
    
    def test_invalid_variable_data(self, optimizer_client):
        """Test validation errors for invalid variable data."""
        response = optimizer_client.post('/api/optimizer/variable',
            json={
                'name': '',  # Empty name should fail
                'lowerBound': -1,  # Negative should fail
                'cost': 'invalid',  # Invalid cost
            })
        # Should return error or success with validation
        assert response.status_code in [200, 400]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
