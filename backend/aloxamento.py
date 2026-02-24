from flask import Blueprint, jsonify, current_app
import requests

from backend.ruta_activa import get_concellos_codigos, debe_filtrar_concellos

aloxamento_bp = Blueprint('aloxamento', __name__, template_folder='templates')


@aloxamento_bp.route('/api/aloxamento')
def api_aloxamento():
    """
    Endpoint que devolve empresas e espazos de aloxamento dos concellos do proxecto activo.
    Filtro estrito por código de concello (concello_codigo_ige) e categoría de aloxamento.
    """
    api_base = current_app.config['API_BASE_URL']
    token = current_app.config['API_TOKEN']
    headers = {"Authorization": f"Token {token}"}
    # Empresas de aloxamento
    empresas_url = f"{api_base}entidades/empresas/"
    empresas_resp = requests.get(empresas_url, headers=headers, timeout=10)
    empresas = empresas_resp.json().get('results', []) if empresas_resp.status_code == 200 else []
    # Espazos de aloxamento
    espazos_url = f"{api_base}informacion/espazos/"
    espazos_resp = requests.get(espazos_url, headers=headers, timeout=10)
    espazos = espazos_resp.json().get('results', []) if espazos_resp.status_code == 200 else []
    # Filtrado por concellos do proxecto activo
    if debe_filtrar_concellos():
        codigos = set(get_concellos_codigos())
        empresas = [e for e in empresas if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
        espazos = [e for e in espazos if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
    resultados = empresas + espazos
    return jsonify({"results": resultados})

