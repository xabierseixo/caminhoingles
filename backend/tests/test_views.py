import sys, os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"map" in resp.data or b"Mapa" in resp.data

def test_empresas(client):
    resp = client.get('/empresas')
    assert resp.status_code == 200
    assert b"Empresa" in resp.data or b"empresas" in resp.data

def test_patrimonio(client):
    resp = client.get('/patrimonio')
    assert resp.status_code == 200
    assert b"Patrimonio" in resp.data or b"patrimonio" in resp.data

def test_404(client):
    resp = client.get('/nonexiste')
    assert resp.status_code == 404
