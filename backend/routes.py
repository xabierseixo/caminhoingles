from flask import (
    Blueprint, jsonify, request, render_template,
    send_from_directory, current_app, session, redirect, url_for,
)
import os
import json
import requests

from backend.cache import cache
from backend.ruta_activa import (
    obter_proxecto_activo,
    get_concellos_codigos,
    debe_filtrar_concellos,
    obter_capas_geojson,
)


bp = Blueprint('main', __name__)

# Exemplo: para cachear un endpoint GET, engade o decorador @cache.cached(timeout=segundos)
# Podes usar @cache.cached() para usar o timeout por defecto (configurable por CACHE_DEFAULT_TIMEOUT)

# --- Endpoint de configuración do sidebar ---
@bp.route('/api/sidebar-config')
def sidebar_config():
    """
    Serve a configuración do sidebar desde o ficheiro JSON.
    Só devolve as seccións activas.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config/sidebar_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # Filtrar só seccións activas
        config['seccions'] = [s for s in config.get('seccions', []) if s.get('activo', True)]
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e), "seccions": []}), 500


# --- ENDPOINT UNIFICADO PARA DATOS DO SIDEBAR ---
@bp.route('/api/sidebar-data/<seccion_id>')
def sidebar_data(seccion_id):
    """
    Endpoint unificado que devolve datos para calquera sección do sidebar.

    Se a sección ten 'taxonomia.endpoint', obtén as categorías desde a taxonomía
    e devolve estrutura xerárquica.

    Formato de resposta:
    {
        "subcategorias": [
            {"slug": "...", "nome": "...", "count": N, "children": [...]}, ...
        ],
        "items": [{"nome": "...", "lat": N, "lng": N, ...}, ...]
    }
    """
    from flask import current_app

    # 1. Ler configuración
    config_path = os.path.join(os.path.dirname(__file__), 'config/sidebar_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Erro lendo configuración: {e}"}), 500

    # 2. Buscar a sección
    seccion = None
    for s in config.get('seccions', []):
        if s.get('id') == seccion_id:
            seccion = s
            break

    if not seccion:
        return jsonify({"error": f"Sección '{seccion_id}' non atopada"}), 404

    if not seccion.get('activo', True):
        return jsonify({"error": f"Sección '{seccion_id}' non activa"}), 404

    # 3. Obter parámetros da configuración
    fonte = seccion.get('fonte', 'patrimonio-material')
    filtro_categoria = seccion.get('filtro_categoria', '')
    filtros = seccion.get('filtros', {})
    taxonomia_config = seccion.get('taxonomia', {})

    API_TOKEN = os.environ.get("API_TOKEN")
    headers = {"Authorization": f"Token {API_TOKEN}"}
    codigos_camino = get_concellos_codigos()
    filtrar = debe_filtrar_concellos()

    items = []

    try:
        if fonte == 'recursos':
            # Consultar espazos + empresas
            url_espazos = f"{current_app.config['API_BASE_URL']}informacion/espazos/"
            url_empresas = f"{current_app.config['API_BASE_URL']}entidades/empresas/"

            params = {"page_size": 500}

            resp_espazos = requests.get(url_espazos, headers=headers, params=params, timeout=15)
            resp_empresas = requests.get(url_empresas, headers=headers, params=params, timeout=15)

            espazos = resp_espazos.json().get('results', []) if resp_espazos.status_code == 200 else []
            empresas = resp_empresas.json().get('results', []) if resp_empresas.status_code == 200 else []

            # Filtrar por concellos do proxecto activo
            if filtrar and filtros.get('filtrar_concellos_camino', True):
                espazos = [e for e in espazos if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos_camino]
                empresas = [e for e in empresas if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos_camino]

            items = espazos + empresas

        else:  # patrimonio-material
            url = f"{current_app.config['API_BASE_URL']}patrimonio-material/patrimonio-material/"
            params = {"page_size": 500}
            if filtro_categoria:
                params["categoria"] = filtro_categoria

            resp = requests.get(url, headers=headers, params=params, timeout=15)
            items = resp.json().get('results', []) if resp.status_code == 200 else []

            # Filtrar por concellos do proxecto activo
            if filtrar and filtros.get('filtrar_concellos_camino', True):
                items = [i for i in items if str(i.get('concello_codigo', '')).zfill(5) in codigos_camino]

    except Exception as e:
        return jsonify({"error": str(e), "subcategorias": [], "items": []}), 500

    # 4. Aplicar filtros aos items
    if filtros.get('requirir_coordenadas', True):
        items = [i for i in items if i.get('lat') and i.get('lng')]

    if filtros.get('requirir_foto', False):
        items = [i for i in items if i.get('foto_principal_url')]

    excluir_items = filtros.get('excluir_items', [])
    if excluir_items:
        items = [i for i in items if i.get('slug') not in excluir_items]

    # 5. Extraer subcategorías - MODO TAXONOMÍA ou MODO EXTRACCIÓN
    subcats_list = []

    if taxonomia_config.get('endpoint'):
        # MODO TAXONOMÍA: Obter categorías desde o endpoint de taxonomía
        try:
            taxonomia_url = f"{current_app.config['API_BASE_URL']}{taxonomia_config['endpoint']}"
            resp_tax = requests.get(taxonomia_url, headers=headers, timeout=10)
            if resp_tax.status_code == 200:
                taxonomia_data = resp_tax.json()

                # Recoller todos os slugs da taxonomía para saber cales son válidos
                def recoller_slugs_taxonomia(subcats):
                    slugs = set()
                    for subcat in subcats:
                        slugs.add(subcat.get('slug', ''))
                        slugs.update(recoller_slugs_taxonomia(subcat.get('subcategorias', [])))
                    return slugs

                slugs_taxonomia = recoller_slugs_taxonomia(taxonomia_data.get('subcategorias', []))

                # Para cada item, atopar o slug MÁIS ESPECÍFICO (folla) que está na taxonomía
                # Así evitamos contar dúas veces
                items_por_slug_especifico = {}
                for item in items:
                    slug_mais_especifico = None
                    max_profundidade = -1

                    # Buscar nos breadcrumbs (o último elemento é o máis específico)
                    for bc in item.get('categorias_breadcrumbs', []):
                        for i, cat in enumerate(bc):
                            slug = cat.get('slug', '')
                            if slug in slugs_taxonomia and i > max_profundidade:
                                slug_mais_especifico = slug
                                max_profundidade = i

                    # Buscar en categorias_list
                    for cat in item.get('categorias_list', []):
                        slug = cat.get('slug', '')
                        if slug in slugs_taxonomia:
                            # categorias_list non ten profundidade, usamos como fallback
                            if slug_mais_especifico is None:
                                slug_mais_especifico = slug

                    if slug_mais_especifico:
                        if slug_mais_especifico not in items_por_slug_especifico:
                            items_por_slug_especifico[slug_mais_especifico] = []
                        items_por_slug_especifico[slug_mais_especifico].append(item)

                # Función recursiva para construír a xerarquía
                def construir_xerarquia(subcats):
                    resultado = []
                    for subcat in subcats:
                        slug = subcat.get('slug', '')
                        nome = subcat.get('nome', slug)
                        children_data = subcat.get('subcategorias', [])

                        # Construír fillos recursivamente primeiro
                        children = construir_xerarquia(children_data) if children_data else []

                        # Contar items propios (só os que teñen ESTE slug como máis específico)
                        count_propio = len(items_por_slug_especifico.get(slug, []))

                        # Contar fillos (suma recursiva)
                        count_fillos = sum(c.get('count', 0) for c in children)

                        total = count_propio + count_fillos

                        # Só engadir se ten items (non mostrar categorías baleiras)
                        if total > 0:
                            cat_entry = {
                                "slug": slug,
                                "nome": nome,
                                "count": total,
                                "count_propio": count_propio
                            }

                            # Filtrar fillos baleiros
                            children_con_items = [c for c in children if c.get('count', 0) > 0]
                            if children_con_items:
                                cat_entry["children"] = children_con_items

                            resultado.append(cat_entry)

                    return resultado

                # Construír desde as subcategorías da taxonomía
                subcats_list = construir_xerarquia(taxonomia_data.get('subcategorias', []))
        except Exception as e:
            # Se falla a taxonomía, continuar con extracción normal
            pass

    # Se non hai taxonomía ou fallou, extraer subcategorías dos items
    if not subcats_list:
        subcategorias = {}
        for item in items:
            # Buscar nos breadcrumbs
            for bc in item.get('categorias_breadcrumbs', []):
                if len(bc) >= 2:
                    subcat = bc[1]
                    slug = subcat.get('slug', '')
                    if slug:
                        if slug not in subcategorias:
                            subcategorias[slug] = {"slug": slug, "nome": subcat.get('nome', slug), "count": 0}
                        subcategorias[slug]["count"] += 1
            # Buscar en categorias_list
            for cat in item.get('categorias_list', []):
                slug = cat.get('slug', '')
                if slug:
                    if slug not in subcategorias:
                        subcategorias[slug] = {"slug": slug, "nome": cat.get('nome', slug), "count": 0}
                    subcategorias[slug]["count"] += 1

        subcats_list = list(subcategorias.values())

    # 6. Aplicar filtros de subcategorías (só para modo non-xerárquico)
    if not taxonomia_config.get('endpoint'):
        minimo = filtros.get('minimo_items', 1)
        subcats_list = [s for s in subcats_list if s.get('count', 0) >= minimo]

        incluir = filtros.get('incluir_subcategorias', [])
        if incluir:
            subcats_list = [s for s in subcats_list if s['slug'] in incluir]

        excluir = filtros.get('excluir_subcategorias', [])
        if excluir:
            subcats_list = [s for s in subcats_list if s['slug'] not in excluir]

        ordenar = filtros.get('ordenar_por', 'nome')
        if ordenar == 'nome':
            subcats_list.sort(key=lambda x: x['nome'])
        elif ordenar == 'count':
            subcats_list.sort(key=lambda x: -x.get('count', 0))

        limite = filtros.get('limite_subcategorias')
        if limite:
            subcats_list = subcats_list[:limite]

    return jsonify({
        "subcategorias": subcats_list,
        "items": items,
        "taxonomia": bool(taxonomia_config.get('endpoint'))
    })

# Endpoint optimizado para categorías de aloxamento
# OPTIMIZACIÓN: Só 3 peticións á API externa (categorías + espazos + empresas)
@bp.route('/categorias/servizos/hostalaria/aloxamento/')
def categorias_aloxamento():
    from flask import current_app
    API_TOKEN = os.environ.get("API_TOKEN")
    headers = {"Authorization": f"Token {API_TOKEN}"}

    # 1. Obter árbore de categorías (1 petición)
    url_cats = "https://gl313.com/api/taxonomia/categorias/servizos/hostalaria/aloxamento/"
    try:
        resp_cats = requests.get(url_cats, headers=headers, timeout=10)
        if resp_cats.status_code != 200:
            return jsonify({"error": "Erro ao consultar a API", "status": resp_cats.status_code}), resp_cats.status_code
        categorias = resp_cats.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 2. Obter TODOS os espazos de aloxamento dunha soa vez (1 petición)
    url_espazos = f"{current_app.config['API_BASE_URL']}informacion/espazos/"
    try:
        resp_espazos = requests.get(url_espazos, headers=headers, params={"page_size": 500}, timeout=15)
        todos_espazos = resp_espazos.json().get('results', []) if resp_espazos.status_code == 200 else []
    except Exception:
        todos_espazos = []

    # 3. Obter TODAS as empresas de aloxamento dunha soa vez (1 petición)
    url_empresas = f"{current_app.config['API_BASE_URL']}entidades/empresas/"
    try:
        resp_empresas = requests.get(url_empresas, headers=headers, params={"page_size": 500}, timeout=15)
        todas_empresas = resp_empresas.json().get('results', []) if resp_empresas.status_code == 200 else []
    except Exception:
        todas_empresas = []

    # Filtrar por concellos do proxecto activo
    if debe_filtrar_concellos():
        codigos_camino = get_concellos_codigos()
        todos_espazos = [e for e in todos_espazos if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos_camino]
        todas_empresas = [e for e in todas_empresas if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos_camino]

    # Crear índice de slugs de categoría -> conteo
    # Para cada espazo/empresa, extraer os slugs das súas categorías
    conteo_por_slug = {}

    def contar_item(item):
        slugs = set()
        # Extraer slugs de categorias_nomes (formato: "cat1 > cat2 > cat3")
        for cat_nome in item.get('categorias_nomes', []):
            partes = [p.strip().lower().replace(' ', '-') for p in cat_nome.split('>')]
            slugs.update(partes)
        # Extraer slugs de categorias_breadcrumbs
        for bc in item.get('categorias_breadcrumbs', []):
            for cat in bc:
                if cat.get('slug'):
                    slugs.add(cat['slug'])
        # Extraer de categorias_list
        for cat in item.get('categorias_list', []):
            if cat.get('slug'):
                slugs.add(cat['slug'])
        return slugs

    for espazo in todos_espazos:
        for slug in contar_item(espazo):
            conteo_por_slug[slug] = conteo_por_slug.get(slug, 0) + 1

    for empresa in todas_empresas:
        for slug in contar_item(empresa):
            conteo_por_slug[slug] = conteo_por_slug.get(slug, 0) + 1

    # Asignar conteos ás categorías recursivamente
    def asignar_conteo(cat):
        slug = cat.get('slug', '')
        propios = conteo_por_slug.get(slug, 0)
        fillos = 0
        for subcat in cat.get('subcategorias', []):
            fillos += asignar_conteo(subcat)
        cat['contido_count'] = propios + fillos
        return propios + fillos

    for cat in categorias.get('subcategorias', []):
        asignar_conteo(cat)

    # Filtrar só categorías con contido
    def filtrar_con_contido(cat):
        cat['subcategorias'] = [s for s in cat.get('subcategorias', []) if s.get('contido_count', 0) > 0]
        for subcat in cat['subcategorias']:
            filtrar_con_contido(subcat)
        return cat.get('contido_count', 0) > 0

    categorias['subcategorias'] = [cat for cat in categorias.get('subcategorias', []) if filtrar_con_contido(cat)]

    return jsonify(categorias)

from backend.valhalla import (
    request_valhalla_route,
    request_valhalla_pedestrian_route,
    find_nearest_point,
    find_nearest_point_with_feature,
    truncar_forma_no_camino,
)

# --- Cache do GeoJSON enriquecido con elevación ---
_elevation_geojson_cache = None


def _load_elevation_geojson():
    global _elevation_geojson_cache
    if _elevation_geojson_cache is None:
        elev_path = os.path.join(
            os.path.dirname(__file__),
            'static', 'geojson', 'camino_ingles_elevation.geojson',
        )
        if not os.path.exists(elev_path):
            return None
        with open(elev_path, 'r', encoding='utf-8') as f:
            _elevation_geojson_cache = json.load(f)
    return _elevation_geojson_cache


@bp.route('/api/elevation-data')
def elevation_data():
    """Devolve datos de elevación de todos os tramos."""
    geojson = _load_elevation_geojson()
    if not geojson:
        return jsonify({
            "error": "GeoJSON de elevación non dispoñible.",
        }), 404

    tramos = []
    total_dist = 0
    total_dpos = 0
    total_dneg = 0

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        dist = props.get("distancia_km", 0)
        dpos = props.get("desnivel_positivo", 0)
        dneg = props.get("desnivel_negativo", 0)

        tramos.append({
            "nome": props.get("Name", ""),
            "distancia_km": dist,
            "desnivel_positivo": dpos,
            "desnivel_negativo": dneg,
            "altitude_max": props.get("altitude_max", 0),
            "altitude_min": props.get("altitude_min", 0),
            "perfil": props.get("perfil", []),
        })

        total_dist += dist
        total_dpos += dpos
        total_dneg += dneg

    # Tempo estimado: 4 km/h + 1 min extra por cada 10m D+
    tempo_min = (total_dist / 4) * 60 + (total_dpos / 10)

    return jsonify({
        "tramos": tramos,
        "total": {
            "distancia_km": round(total_dist, 1),
            "desnivel_positivo": round(total_dpos),
            "desnivel_negativo": round(total_dneg),
            "tempo_estimado_min": round(tempo_min),
        },
    })


@bp.route('/api/ruta-ao-camino', methods=['POST'])
def ruta_ao_camino():
    """Calcula ruta desde un punto ata o camiño (a pé ou en bici)."""
    data = request.get_json()
    if not data or 'lat' not in data or 'lng' not in data:
        return jsonify({"error": "Faltan parámetros lat/lng"}), 400

    lat = float(data['lat'])
    lng = float(data['lng'])
    modo = data.get('modo', 'pe')  # 'pe' ou 'bici'
    costing = 'bicycle' if modo == 'bici' else 'pedestrian'

    # Cargar GeoJSON
    geojson = _load_elevation_geojson()
    if not geojson:
        geojson_path = os.path.join(
            os.path.dirname(__file__),
            'static', 'geojson', 'camino_ingles.geojson',
        )
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

    nearest_lat, nearest_lng, _ = find_nearest_point(lat, lng, geojson)

    try:
        route = request_valhalla_pedestrian_route(
            lat, lng, nearest_lat, nearest_lng, costing=costing,
        )
        if not route:
            return jsonify({"error": "Non se puido calcular a ruta"}), 502

        # Truncar o traxecto no primeiro cruce xeométrico co camiño.
        # Se o shape de Valhalla cruza a liña do GeoJSON antes de chegar
        # ao destino final, ese cruce é o punto real de entrada ao camiño.
        if route.get('shape'):
            route['shape'] = truncar_forma_no_camino(route['shape'], geojson)

        return jsonify(route)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp.route('/api/ruta-punto-a-punto', methods=['POST'])
def ruta_punto_a_punto():
    """
    Calcula ruta entre dous puntos calquera (ex: posición usuario → POI).
    Parámetros: origin_lat, origin_lng, dest_lat, dest_lng, modo ('pe' ou 'bici')
    """
    data = request.get_json()
    required = ['origin_lat', 'origin_lng', 'dest_lat', 'dest_lng']
    if not data or not all(k in data for k in required):
        return jsonify({"error": "Faltan parámetros de orixe/destino"}), 400

    origin_lat = float(data['origin_lat'])
    origin_lng = float(data['origin_lng'])
    dest_lat = float(data['dest_lat'])
    dest_lng = float(data['dest_lng'])
    modo = data.get('modo', 'pe')
    costing = 'bicycle' if modo == 'bici' else 'pedestrian'

    try:
        route = request_valhalla_pedestrian_route(
            origin_lat, origin_lng, dest_lat, dest_lng, costing=costing,
        )
        if route:
            return jsonify(route)
        return jsonify({"error": "Non se puido calcular a ruta"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@bp.route('/api/ruta-completa-santiago', methods=['POST'])
def ruta_completa_santiago():
    """
    Calcula a ruta completa desde a posición do usuario ata Santiago.
    Combina: ruta ata o camiño + segmentos do camiño ata Santiago.
    modo: 'pe' (a pé) ou 'bici' (en bicicleta)
    """
    data = request.get_json()
    if not data or 'lat' not in data or 'lng' not in data:
        return jsonify({"error": "Faltan parámetros lat/lng"}), 400

    lat = float(data['lat'])
    lng = float(data['lng'])
    orixe = data.get('orixe', 'auto')  # 'ferrol', 'coruna', ou 'auto'
    modo = data.get('modo', 'pe')  # 'pe' ou 'bici'
    costing = 'bicycle' if modo == 'bici' else 'pedestrian'

    geojson = _load_elevation_geojson()
    if not geojson:
        geojson_path = os.path.join(
            os.path.dirname(__file__),
            'static', 'geojson', 'camino_ingles.geojson',
        )
        with open(geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)

    # Atopar punto máis próximo con info do segmento
    nearest = find_nearest_point_with_feature(lat, lng, geojson)

    # Calcular ruta ata o camiño
    ruta_ao_camino = None
    try:
        ruta_ao_camino = request_valhalla_pedestrian_route(
            lat, lng, nearest['lat'], nearest['lng'], costing=costing,
        )
    except Exception:
        pass

    # Determinar que segmentos seguir ata Santiago
    # Lóxica: desde o segmento onde está o usuario ata o final
    # Os segmentos están ordenados por etapa/tramo no GeoJSON
    features = geojson.get("features", [])

    # Clasificar segmentos por orixe
    def clasificar(nome):
        if 'e01Vt' in nome:
            return 'coruna'
        m = nome and nome.startswith('CIN-e0')
        if m:
            etapa = int(nome[5:7]) if len(nome) > 6 else 0
            if etapa <= 3:
                return 'ferrol'
        return 'comun'

    # Determinar orixe automáticamente se non se especifica
    if orixe == 'auto':
        orixe = clasificar(nearest['feature_name'])
        if orixe == 'comun':
            orixe = 'ferrol'  # Default se está na parte común

    # Seleccionar segmentos relevantes
    segmentos_a_seguir = []
    total_dist = 0
    total_dpos = 0
    total_dneg = 0
    en_ruta = False

    for idx, feature in enumerate(features):
        nome = feature.get("properties", {}).get("Name", "")
        props = feature.get("properties", {})
        tipo = clasificar(nome)

        # Comezar cando atopamos o segmento do usuario
        if nome == nearest['feature_name']:
            en_ruta = True

        if en_ruta:
            # Incluír só se é da mesma orixe ou común
            if tipo == orixe or tipo == 'comun':
                segmentos_a_seguir.append({
                    "nome": nome,
                    "distancia_km": props.get("distancia_km", 0),
                    "desnivel_positivo": props.get("desnivel_positivo", 0),
                    "desnivel_negativo": props.get("desnivel_negativo", 0),
                })
                total_dist += props.get("distancia_km", 0)
                total_dpos += props.get("desnivel_positivo", 0)
                total_dneg += props.get("desnivel_negativo", 0)

    # Engadir ruta ao camiño á distancia total
    dist_ao_camino = ruta_ao_camino['distancia_km'] if ruta_ao_camino else 0
    total_dist += dist_ao_camino

    # Tempo estimado segundo modo:
    # A pé: 4 km/h + 1 min por cada 10m D+
    # En bici: 15 km/h + 1 min por cada 20m D+
    if modo == 'bici':
        velocidade_kmh = 15
        penalizacion_desnivel = total_dpos / 20
    else:
        velocidade_kmh = 4
        penalizacion_desnivel = total_dpos / 10

    tempo_min = (total_dist / velocidade_kmh) * 60 + penalizacion_desnivel

    return jsonify({
        "ruta_ao_camino": ruta_ao_camino,
        "punto_entrada": {
            "lat": nearest['lat'],
            "lng": nearest['lng'],
            "distancia_metros": nearest['distancia'],
            "segmento": nearest['feature_name'],
        },
        "orixe_detectada": orixe,
        "modo": modo,
        "segmentos": segmentos_a_seguir,
        "total": {
            "distancia_km": round(total_dist, 1),
            "desnivel_positivo": round(total_dpos),
            "desnivel_negativo": round(total_dneg),
            "tempo_estimado_min": round(tempo_min),
            "tempo_estimado_horas": round(tempo_min / 60, 1),
        },
    })


@bp.route('/valhalla/route', methods=['POST'])
def valhalla_route():
    """
    Exemplo de body:
    {
      "locations": [
        {"lat": 43.3707, "lon": -8.3950},
        {"lat": 43.3623, "lon": -8.4115}
      ],
      "costing": "auto"
    }
    """
    data = request.get_json()
    locations = data.get('locations')
    costing = data.get('costing', 'auto')
    try:
        result = request_valhalla_route(locations, costing)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@bp.route('/')
def home():
    from flask import current_app
    proxecto = obter_proxecto_activo()
    map_id = proxecto.get('map_id')
    centro = proxecto.get('centro', {})
    centro_lat = centro.get('lat', 42.8782)
    centro_lng = centro.get('lng', -8.5446)
    zoom_inicial = proxecto.get('zoom_inicial', 10)
    proxecto_nome = proxecto.get('nome', 'Mapa')

    # Intentar obter centro/zoom desde a API do mapa se hai map_id
    if map_id:
        api_url = f"{current_app.config['API_BASE_URL']}maps/mapas/{map_id}/"
        headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            centro_lat = float(data.get('centro_lat', centro_lat))
            centro_lng = float(data.get('centro_lng', centro_lng))
            zoom_inicial = int(data.get('zoom_inicial', zoom_inicial))
        except Exception:
            pass

    return render_template(
        'mapa.html',
        centro_lat=centro_lat,
        centro_lng=centro_lng,
        zoom_inicial=zoom_inicial,
        proxecto_nome=proxecto_nome,
    )


@bp.route('/mapa/geojson')
def geojson_camino_ingles():
    proxecto = obter_proxecto_activo()
    ficheiro = proxecto.get('capas', {}).get('ruta', {}).get('ficheiro', 'camino_ingles.geojson')
    static_dir = os.path.join(current_app.root_path, 'static', 'geojson')
    return send_from_directory(static_dir, ficheiro, mimetype='application/geo+json')

@bp.route('/mapa/concellos')
def geojson_concellos_camino():
    proxecto = obter_proxecto_activo()
    ficheiro = proxecto.get('capas', {}).get('concellos', {}).get('ficheiro', 'concellos_camino_ingles.geojson')
    static_dir = os.path.join(current_app.root_path, 'static', 'geojson')
    return send_from_directory(static_dir, ficheiro, mimetype='application/geo+json')

@bp.route('/api/proxecto-activo')
def api_proxecto_activo():
    """Devolve información do proxecto activo."""
    proxecto = obter_proxecto_activo()
    return jsonify({
        'id': proxecto.get('id'),
        'nome': proxecto.get('nome'),
        'centro': proxecto.get('centro'),
        'zoom_inicial': proxecto.get('zoom_inicial'),
        'filtrar_por_concellos': debe_filtrar_concellos(),
    })

@bp.route('/api/capas-geojson')
def api_capas_geojson():
    """Devolve todas as capas GeoJSON dispoñibles (predefinidas + extras auto-detectadas)."""
    return jsonify(obter_capas_geojson())

@bp.route('/empresas')
def empresas_list():
    from flask import current_app
    api_url = f"{current_app.config['API_BASE_URL']}entidades/empresas/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        empresas = data.get('results', data)
    except Exception:
        empresas = []
    return render_template('empresas_list.html', empresas=empresas)

@bp.route('/api/empresas')
def empresas_api():
    from flask import current_app
    api_url = f"{current_app.config['API_BASE_URL']}entidades/empresas/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    try:
        resp = requests.get(api_url, headers=headers, params=request.args, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        empresas = data.get('results', data)
        # Filtrado estrito: só empresas cuxo concello_codigo_ige está en CONCELLOS_CAMINO_CODIGOS
        if debe_filtrar_concellos():
            codigos = get_concellos_codigos()
            empresas = [e for e in empresas if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
    except Exception:
        empresas = []
    return jsonify({"results": empresas})

@bp.route('/api/espazos')
def espazos_list():
    from flask import current_app
    import re
    api_url = f"{current_app.config['API_BASE_URL']}informacion/espazos/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    try:
        resp = requests.get(api_url, headers=headers, params=request.args, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        espazos = data.get('results', data)
        # Filtrado por categoría se se especifica
        categorias = request.args.get('categoria')
        if categorias:
            categorias = categorias.split(',')
            espazos_filtrados = []
            for e in espazos:
                nomes = ' '.join(e.get('categorias_nomes') or []).lower()
                for cat in categorias:
                    patron = re.compile(r'\b' + re.escape(cat.lower().rstrip('s')) + r's?\b')
                    if patron.search(nomes):
                        espazos_filtrados.append(e)
                        break
            espazos = espazos_filtrados
        # Filtrar por concellos do proxecto activo
        if debe_filtrar_concellos():
            codigos = get_concellos_codigos()
            espazos = [e for e in espazos if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
    except Exception:
        espazos = []
    return jsonify({"results": espazos})


@bp.route('/api/recursos')
def recursos_api():
    from flask import current_app, request
    import re
    # Filtro por categoría
    categorias = request.args.get('categoria')
    if categorias:
        categorias = categorias.split(',')
    filtrar = debe_filtrar_concellos()
    codigos = get_concellos_codigos() if filtrar else []
    # Empresas
    api_url_empresas = f"{current_app.config['API_BASE_URL']}entidades/empresas/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    try:
        resp_empresas = requests.get(api_url_empresas, headers=headers, params=request.args, timeout=10)
        resp_empresas.raise_for_status()
        empresas = resp_empresas.json().get('results', [])
        if filtrar:
            empresas = [e for e in empresas if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
        if categorias:
            empresas_filtradas = []
            for e in empresas:
                nomes = ' '.join([cat.get('cascada','') for cat in e.get('categorias_list',[]) if cat.get('cascada')]).lower()
                for cat in categorias:
                    patron = re.compile(r'\b' + re.escape(cat.lower().rstrip('s')) + r's?\b')
                    if patron.search(nomes):
                        empresas_filtradas.append(e)
                        break
            empresas = empresas_filtradas
    except Exception:
        empresas = []
    # Espazos
    api_url_espazos = f"{current_app.config['API_BASE_URL']}informacion/espazos/"
    try:
        resp_espazos = requests.get(api_url_espazos, headers=headers, params=request.args, timeout=10)
        resp_espazos.raise_for_status()
        espazos = resp_espazos.json().get('results', [])
        if filtrar:
            espazos = [e for e in espazos if str(e.get('concello_codigo_ige', '')).zfill(5) in codigos]
        if categorias:
            espazos_filtrados = []
            for e in espazos:
                nomes = ' '.join(e.get('categorias_nomes') or []).lower()
                for cat in categorias:
                    patron = re.compile(r'\b' + re.escape(cat.lower().rstrip('s')) + r's?\b')
                    if patron.search(nomes):
                        espazos_filtrados.append(e)
                        break
            espazos = espazos_filtrados
    except Exception:
        espazos = []
    return jsonify({"results": empresas + espazos})

@bp.route('/api/patrimonio-material/<slug>')
def patrimonio_material_detalle(slug):
    """
    Endpoint de detalle de patrimonio material por slug
    """
    from flask import current_app
    api_url = f"https://gl313.com/api/patrimonio-material/patrimonio-material/{slug}/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return jsonify({"error": f"Erro consultando API externa: {str(e)}"}), 502
    return jsonify(data)

@bp.route('/api/patrimonio-material')
def patrimonio_material_api():
    """
    Endpoint de patrimonio material. Acepta filtros:
    - categoria: slug da categoría (ex: patrimonio-relixioso)
    - concello_codigo: código do concello
    """
    from flask import current_app
    api_url = f"https://gl313.com/api/patrimonio-material/patrimonio-material/"
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}

    # Pasar todos os parámetros de query á API externa
    params = dict(request.args)
    params['page_size'] = params.get('page_size', 100)

    try:
        resp = requests.get(api_url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        patrimonio = data.get('results', [])

        # Filtrar por concellos do proxecto activo
        if debe_filtrar_concellos():
            codigos = get_concellos_codigos()
            patrimonio = [p for p in patrimonio
                         if str(p.get('concello_codigo', '')).zfill(5) in codigos]

    except Exception as e:
        patrimonio = []
    return jsonify({"results": patrimonio})

# --- Autenticación (Flask-Login) ---
from flask_login import login_user, logout_user, login_required, current_user
from backend.models import get_user_by_username, create_user

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = get_user_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(request.args.get('next') or url_for('main.home'))
        error = 'Usuario ou contrasinal incorrectos'
    return render_template('login.html', error=error)

@bp.route('/rexistro', methods=['GET', 'POST'])
def rexistro():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        if not username or not email or not password:
            error = 'Todos os campos son obrigatorios'
        elif password != password2:
            error = 'Os contrasinais non coinciden'
        elif len(password) < 8:
            error = 'O contrasinal debe ter polo menos 8 caracteres'
        else:
            rol = request.form.get('rol', 'peregrino')
            if rol not in ('peregrino', 'provedor'):
                rol = 'peregrino'
            user = create_user(username, email, password, rol=rol)
            if user:
                login_user(user)
                return redirect(url_for('main.home'))
            error = 'O usuario ou email xa existe'
    return render_template('rexistro.html', error=error)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/perfil')
@login_required
def perfil():
    from backend.models import get_checkins_usuario, get_posts_usuario
    checkins = get_checkins_usuario(current_user.id)
    posts = get_posts_usuario(current_user.id)
    return render_template('perfil.html', user=current_user, checkins=checkins, posts=posts)

@bp.route('/api/checkin', methods=['POST'])
@login_required
def api_checkin():
    from backend.models import create_checkin
    data = request.get_json(silent=True) or {}
    slug = data.get('slug', '').strip()
    try:
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'erro': 'Coordenadas inválidas'}), 400
    if not slug:
        return jsonify({'ok': False, 'erro': 'Falta o slug'}), 400

    puntuacion = data.get('puntuacion')
    if puntuacion is not None:
        try:
            puntuacion = int(puntuacion)
            if not 1 <= puntuacion <= 5:
                puntuacion = None
        except (TypeError, ValueError):
            puntuacion = None

    resena = (data.get('resena') or '').strip()[:500] or None

    feito = create_checkin(current_user.id, slug, lat, lng,
                           puntuacion=puntuacion, resena=resena)
    if feito:
        return jsonify({'ok': True})
    else:
        return jsonify({'ok': False, 'repetido': True})


@bp.route('/api/posts', methods=['POST'])
@login_required
def api_create_post():
    from backend.models import create_post
    data = request.get_json(silent=True) or {}
    contido = (data.get('contido') or '').strip()[:1000]
    if not contido:
        return jsonify({'ok': False, 'erro': 'O post non pode estar baleiro'}), 400
    lat = data.get('lat')
    lng = data.get('lng')
    try:
        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        lat = lng = None
    visibilidade = data.get('visibilidade', 'publico')
    if visibilidade not in ('publico', 'privado'):
        visibilidade = 'publico'
    poi_slug = (data.get('poi_slug') or '').strip() or None
    post_id = create_post(current_user.id, contido, lat=lat, lng=lng,
                          poi_slug=poi_slug, visibilidade=visibilidade)
    return jsonify({'ok': True, 'id': post_id,
                    'username': current_user.username,
                    'contido': contido, 'lat': lat, 'lng': lng,
                    'visibilidade': visibilidade,
                    'created_at': 'agora'})


@bp.route('/api/posts', methods=['GET'])
def api_get_posts():
    from backend.models import get_posts_publicos
    try:
        limit = min(int(request.args.get('limit', 100)), 200)
        offset = int(request.args.get('offset', 0))
    except (TypeError, ValueError):
        limit, offset = 100, 0
    posts = get_posts_publicos(limit=limit, offset=offset)
    # Só devolver posts con coordenadas para o mapa
    with_coords = [p for p in posts if p.get('lat') and p.get('lng')]
    return jsonify({'posts': with_coords})


@bp.route('/feed')
def feed():
    from backend.models import get_posts_publicos_con_stats
    uid = current_user.id if current_user.is_authenticated else None
    posts = get_posts_publicos_con_stats(limit=50, user_id=uid)
    return render_template('feed.html', posts=posts)


@bp.route('/api/posts/<int:post_id>/reaccionar', methods=['POST'])
@login_required
def api_reaccionar(post_id):
    from backend.models import toggle_reaccion, get_reaccions_post
    activa = toggle_reaccion(post_id, current_user.id)
    stats = get_reaccions_post(post_id, current_user.id)
    return jsonify({'ok': True, 'activa': activa, 'total': stats['total']})


@bp.route('/api/posts/<int:post_id>/comentarios', methods=['GET'])
def api_get_comentarios(post_id):
    from backend.models import get_comentarios_post
    return jsonify({'comentarios': get_comentarios_post(post_id)})


@bp.route('/api/posts/<int:post_id>/comentarios', methods=['POST'])
@login_required
def api_create_comentario(post_id):
    from backend.models import create_comentario, get_comentarios_post
    data = request.get_json(silent=True) or {}
    contido = (data.get('contido') or '').strip()[:500]
    if not contido:
        return jsonify({'ok': False, 'erro': 'Comentario baleiro'}), 400
    cid = create_comentario(post_id, current_user.id, contido)
    comentarios = get_comentarios_post(post_id)
    return jsonify({'ok': True, 'id': cid, 'comentarios': comentarios})


@bp.route('/api/ping')
def ping():
    return jsonify({'status': 'ok', 'message': 'Backend Flask operativo'}), 200


@bp.route('/api/buscar')
def buscar():
    """
    Busca intelixente en toda a API (patrimonio, empresas, espazos).

    Analiza a query palabra a palabra para detectar:
    - Slugs de categoría do sidebar  → parámetro 'categoria' da API
    - Palabras que poidan ser concellos → parámetro 'concello_nome' da API
    - Resto de palabras → parámetro 'search' (nome + descrición)

    Exemplo: "aloxamento betanzos"
      → categoria=aloxamento + concello_nome=betanzos  ✓

    Constrúe múltiples variantes de parámetros e execútalas en paralelo,
    devolvendo resultados únicos (deduplicados por slug).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from flask import current_app
    import json as _json

    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({"results": []})

    api_base = current_app.config['API_BASE_URL']
    headers = {"Authorization": f"Token {current_app.config['API_TOKEN']}"}
    codigos = get_concellos_codigos()
    filtrar = debe_filtrar_concellos()

    # --- Cargar slugs e mapeo de seccións desde sidebar_config ---
    slugs_config = {}
    filtro_cat_a_seccion = {}   # filtro_categoria → seccion_id  (para patrimonio)
    seccion_recursos_id = None  # seccion_id con fonte='recursos' (aloxamento)
    try:
        cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'sidebar_config.json')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            sidebar = _json.load(f)
        for seccion in sidebar.get('seccions', []):
            sid = seccion['id']
            api_slug = seccion.get('filtro_categoria', sid)
            slugs_config[sid] = api_slug
            for sub in seccion.get('iconos_subcategorias', {}):
                if not sub.startswith('_'):
                    slugs_config[sub] = sub
            if seccion.get('filtro_categoria'):
                filtro_cat_a_seccion[seccion['filtro_categoria']] = sid
            if seccion.get('fonte') == 'recursos':
                seccion_recursos_id = sid
    except Exception:
        pass

    # --- Detectar categorías e palabras libres ---
    def _detectar_slug(word):
        """Devolve o slug da API se a palabra coincide cunha categoría coñecida."""
        if len(word) < 4:
            return None
        w = word.lower()
        if w in slugs_config:
            return slugs_config[w]
        # Coincidencia por prefixo (ex: "igrexa" → "igrexas")
        for slug, api_slug in slugs_config.items():
            if slug.startswith(w) or w.startswith(slug):
                return api_slug
        return None

    palabras = q.split()
    cats_detectadas = []
    posibles_concellos = []  # palabras longas non recoñecidas: filtraranse en Python
    texto_libre_real = []    # palabras curtas: van ao parámetro 'search' da API
    for p in palabras:
        slug = _detectar_slug(p)
        if slug and slug not in cats_detectadas:
            cats_detectadas.append(slug)
        elif len(p) >= 4:
            # Palabra longa non recoñecida: pode ser nome de concello ou lugar
            # Non a enviamos á API (concello_nome non é soportado), filtramos en Python
            posibles_concellos.append(p.lower())
        else:
            texto_libre_real.append(p)

    texto_libre = ' '.join(texto_libre_real).strip()

    # --- Parámetros base comúns ---
    base = {}
    if cats_detectadas:
        base["categoria"] = ",".join(cats_detectadas)

    # Base con filtro de área do Camiño
    base_camino = {**base}
    if filtrar and codigos:
        base_camino["concello_codigo"] = ",".join(codigos)

    # --- Construír variantes de busca ---
    variantes = []

    # Variante principal: categoría + área Camiño + texto curto libre
    # Se hai posibles concellos, pedimos máis resultados para poder filtrar en Python
    v1 = {**base_camino, "page_size": 100 if posibles_concellos else 20}
    if texto_libre:
        v1["search"] = texto_libre
    variantes.append(v1)

    # Variante fallback: query completa como search (útil cando non hai categoría detectada)
    if not cats_detectadas:
        variantes.append({**base_camino, "search": q, "page_size": 20})

    # --- Fontes ---
    fontes = [
        (f"{api_base}patrimonio-material/patrimonio-material/", "patrimonio"),
        (f"{api_base}entidades/empresas/", "empresa"),
        (f"{api_base}informacion/espazos/", "espazo"),
    ]

    def _buscar_en(url, tipo, params):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=8)
            if resp.status_code != 200:
                return []

            def _seccion_id(i):
                if tipo in ('empresa', 'espazo'):
                    return seccion_recursos_id
                # Para patrimonio: buscar nas categorías do ítem
                for cat in (i.get('categorias_list') or []):
                    s = filtro_cat_a_seccion.get(cat.get('slug', ''))
                    if s:
                        return s
                # Fallback: usar as categorías detectadas na query
                for cat in cats_detectadas:
                    s = filtro_cat_a_seccion.get(cat)
                    if s:
                        return s
                return None

            return [
                {
                    "nome": i.get("nome", ""),
                    "slug": i.get("slug", ""),
                    "concello_nome": i.get("concello_nome", ""),
                    "lat": i.get("lat"),
                    "lng": i.get("lng"),
                    "foto": i.get("foto_principal_url") or "",
                    "tipo": tipo,
                    "seccion_id": _seccion_id(i),
                }
                for i in resp.json().get("results", [])
            ]
        except Exception:
            return []

    # --- Executar en paralelo e deduplicar por slug ---
    resultados = []
    vistos = set()
    n_workers = max(3, len(variantes) * len(fontes))
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(_buscar_en, url, tipo, params)
            for params in variantes
            for url, tipo in fontes
        ]
        for future in as_completed(futures):
            for r in future.result():
                slug = r.get("slug")
                if r.get("lat") and r.get("lng") and slug and slug not in vistos:
                    vistos.add(slug)
                    resultados.append(r)

    # --- Filtrar por concello en Python (evita usar concello_nome na API, non soportado) ---
    if posibles_concellos:
        filtrados = [
            r for r in resultados
            if any(pc in (r.get("concello_nome") or "").lower() for pc in posibles_concellos)
        ]
        if filtrados:
            resultados = filtrados
        # Se non filtra nada, devolvemos todo (mellor resultados xenerais que nada)

    return jsonify({"results": resultados})

@bp.route('/api/<path:subpath>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def proxy_any(subpath):
    from flask import current_app
    api_url = f"{current_app.config['API_BASE_URL']}{subpath}"
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    headers["Authorization"] = f"Token {current_app.config['API_TOKEN']}"
    method = request.method
    try:
        resp = requests.request(
            method,
            api_url,
            headers=headers,
            params=request.args,
            json=request.get_json(silent=True),
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json() if resp.headers.get('content-type','').startswith('application/json') else resp.text
        paginacion = {}
        if isinstance(data, dict):
            for campo in ["count", "next", "previous", "results", "page_size"]:
                if campo in data:
                    paginacion[campo] = data[campo]
        return jsonify({
            "success": True,
            "pagination": paginacion,
            "data": data.get("results", data) if isinstance(data, dict) else data
        }), 200
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else 502
        try:
            err_data = e.response.json() if e.response else {}
        except Exception:
            err_data = {}
        if status == 401:
            msg = "Token de autenticación incorrecto ou expirado"
        elif status == 400:
            msg = "Parámetros incorrectos na petición"
        else:
            msg = "Erro HTTP ao consultar a API externa"
        return jsonify({
            "success": False,
            "error": msg,
            "status_code": status,
            "details": err_data
        }), status
    except requests.RequestException as e:
        return jsonify({
            "success": False,
            "error": "Erro de conexión coa API externa (API caída ou sen resposta)",
            "status_code": 502,
            "details": str(e)
        }), 502
