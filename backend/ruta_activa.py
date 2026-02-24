"""
Módulo centralizado para xestión do proxecto activo.

Carga a configuración de rutas_config.json e exporta:
- obter_proxecto_activo(): devolve o dict do proxecto activo
- get_concellos_codigos(): devolve lista de códigos de concellos (ou lista baleira se non aplica)
- debe_filtrar_concellos(): devolve True/False segundo a configuración do proxecto
"""

import os
import json

_BASE_DIR = os.path.dirname(__file__)
_CONFIG_PATH = os.path.join(_BASE_DIR, 'config', 'rutas_config.json')
_GEOJSON_DIR = os.path.join(_BASE_DIR, 'static', 'geojson')

# Cargar configuración de rutas unha soa vez
with open(_CONFIG_PATH, 'r', encoding='utf-8') as _f:
    _rutas_config = json.load(_f)

# Cache interno
_concellos_codigos = None
_proxecto_activo_cache = None


def _get_proxecto_id():
    """Obtén o ID do proxecto activo desde env var ou valor por defecto."""
    return os.environ.get('PROXECTO_ACTIVO', _rutas_config.get('proxecto_por_defecto', ''))


def obter_proxecto_activo():
    """Devolve o dict completo do proxecto activo."""
    global _proxecto_activo_cache
    proxecto_id = _get_proxecto_id()
    if _proxecto_activo_cache and _proxecto_activo_cache.get('id') == proxecto_id:
        return _proxecto_activo_cache
    proxecto = _rutas_config.get('proxectos', {}).get(proxecto_id)
    if not proxecto:
        raise ValueError(f"Proxecto '{proxecto_id}' non atopado en rutas_config.json")
    _proxecto_activo_cache = proxecto
    return proxecto


def debe_filtrar_concellos():
    """Devolve True se o proxecto activo ten filtrado por concellos activado e existe o GeoJSON."""
    proxecto = obter_proxecto_activo()
    if not proxecto.get('filtrar_por_concellos', False):
        return False
    capas = proxecto.get('capas', {})
    concellos_capa = capas.get('concellos', {})
    ficheiro = concellos_capa.get('ficheiro', '')
    if not ficheiro:
        return False
    return os.path.exists(os.path.join(_GEOJSON_DIR, ficheiro))


def get_concellos_codigos():
    """
    Devolve lista de códigos de concellos do proxecto activo.
    Se non debe filtrar, devolve lista baleira.
    Os códigos devólvense como strings de 5 díxitos (zfill).
    """
    global _concellos_codigos
    if _concellos_codigos is not None:
        return _concellos_codigos

    if not debe_filtrar_concellos():
        _concellos_codigos = []
        return _concellos_codigos

    proxecto = obter_proxecto_activo()
    ficheiro = proxecto['capas']['concellos']['ficheiro']
    ruta = os.path.join(_GEOJSON_DIR, ficheiro)

    with open(ruta, 'r', encoding='utf-8') as f:
        geojson = json.load(f)

    _concellos_codigos = [
        str(feat['properties']['CODIGOINE']).zfill(5)
        for feat in geojson.get('features', [])
        if 'CODIGOINE' in feat.get('properties', {})
    ]
    return _concellos_codigos


def obter_capas_geojson():
    """
    Devolve un dict con capas predefinidas e extras auto-detectadas.
    """
    proxecto = obter_proxecto_activo()
    capas = proxecto.get('capas', {})

    predefinidas = {}
    ficheiros_predefinidos = set()

    if 'ruta' in capas:
        predefinidas['ruta'] = {
            'url': '/mapa/geojson',
            'estilo': capas['ruta'].get('estilo', {}),
            'visible': capas['ruta'].get('visible_por_defecto', True)
        }
        ficheiros_predefinidos.add(capas['ruta']['ficheiro'])

    if 'concellos' in capas:
        predefinidas['concellos'] = {
            'url': '/mapa/concellos',
            'estilo': capas['concellos'].get('estilo', {}),
            'visible': capas['concellos'].get('visible_por_defecto', True)
        }
        ficheiros_predefinidos.add(capas['concellos']['ficheiro'])

    extras = []
    if _rutas_config.get('auto_detectar_geojson', True) and os.path.isdir(_GEOJSON_DIR):
        for ficheiro in sorted(os.listdir(_GEOJSON_DIR)):
            if ficheiro.endswith('.geojson') and ficheiro not in ficheiros_predefinidos:
                nome = ficheiro.replace('.geojson', '')
                extras.append({
                    'nome': nome,
                    'url': f'/static/geojson/{ficheiro}'
                })

    return {
        'predefinidas': predefinidas,
        'extras': extras
    }
