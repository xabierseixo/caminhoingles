import os
import pytest
from flask import Flask
from backend import create_app

@pytest.fixture
def app():
    os.environ['API_TOKEN'] = 'token_falso'
    os.environ['API_BASE_URL'] = 'https://gl313.com/api/'
    app = create_app()
    app.config.update({"TESTING": True})
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_ping(client):
    resp = client.get('/api/ping')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'

def test_empresas_proxy_erro_autenticacion(client, monkeypatch):
    # Simular resposta 401 da API externa
    import requests
    class FakeResp:
        status_code = 401
        def raise_for_status(self):
            raise requests.HTTPError(response=self)
        def json(self):
            return {"detail": "Invalid token."}
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp())
    resp = client.get('/api/empresas')
    assert resp.status_code == 401
    data = resp.get_json()
    assert data['success'] is False
    assert data['error'] == "Token de autenticación incorrecto ou expirado"
