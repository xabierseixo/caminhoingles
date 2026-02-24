import os
import math
from flask import current_app
import requests


def get_valhalla_base_url():
    url = current_app.config.get('VALHALLA_URL', 'http://localhost')
    port = current_app.config.get('VALHALLA_PORT', 8002)
    return f"{url}:{port}"


def get_valhalla_url():
    return f"{get_valhalla_base_url()}/route"


def request_valhalla_route(locations, costing="auto"):
    """
    locations: list of dicts with 'lat' and 'lon' keys
    costing: 'auto', 'bicycle', etc.
    """
    valhalla_url = get_valhalla_url()
    headers = {"Content-Type": "application/json"}
    data = {
        "locations": locations,
        "costing": costing
    }
    resp = requests.post(valhalla_url, json=data, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def request_valhalla_pedestrian_route(origin_lat, origin_lng, dest_lat, dest_lng, costing="pedestrian"):
    """
    Calcula unha ruta entre dous puntos usando Valhalla.
    costing: "pedestrian" (a pé) ou "bicycle" (en bici)
    Devolve: dict con shape, distancia_km, tempo_min, instrucions, modo
    """
    base_url = get_valhalla_base_url()
    data = {
        "locations": [
            {"lat": origin_lat, "lon": origin_lng},
            {"lat": dest_lat, "lon": dest_lng}
        ],
        "costing": costing,
        "directions_options": {"language": "es-ES"},
    }
    resp = requests.post(f"{base_url}/route", json=data, timeout=15)
    resp.raise_for_status()
    result = resp.json()

    trip = result.get("trip", {})
    legs = trip.get("legs", [])
    if not legs:
        return None

    leg = legs[0]
    shape_encoded = leg.get("shape", "")
    maneuvers = leg.get("maneuvers", [])
    summary = leg.get("summary", {})

    # Decodificar polyline (Valhalla usa precisión 6)
    shape = decode_polyline(shape_encoded, precision=6)

    instrucions = [
        m.get("instruction", "")
        for m in maneuvers if m.get("instruction")
    ]

    return {
        "distancia_km": round(summary.get("length", 0), 2),
        "tempo_min": round(summary.get("time", 0) / 60, 1),
        "shape": shape,
        "instrucions": instrucions,
        "modo": "bici" if costing == "bicycle" else "pe",
    }


def decode_polyline(encoded, precision=6):
    """Decodifica unha polyline codificada (Google/Valhalla)."""
    inv = 1.0 / (10 ** precision)
    decoded = []
    previous = [0, 0]
    i = 0
    while i < len(encoded):
        ll = [0, 0]
        for j in range(2):
            shift = 0
            byte = 0x20
            while byte >= 0x20:
                byte = ord(encoded[i]) - 63
                i += 1
                ll[j] |= (byte & 0x1F) << shift
                shift += 5
            ll[j] = previous[j] + (
                ~(ll[j] >> 1) if ll[j] & 1 else (ll[j] >> 1)
            )
            previous[j] = ll[j]
        decoded.append([round(ll[0] * inv, 6), round(ll[1] * inv, 6)])
    return decoded  # [[lat, lng], ...]


def _proxectar_punto_sobre_segmento(plat, plng, alat, alng, blat, blng):
    """
    Atopa o punto máis próximo ao punto P (plat, plng) no segmento AB.
    Usa aproximación de terra plana: válida para segmentos de poucos km.
    Devolve (lat, lng) do punto proxectado (sempre dentro do segmento).
    """
    abx = blng - alng
    aby = blat - alat
    ab2 = abx * abx + aby * aby
    if ab2 == 0:
        return alat, alng  # A e B son o mesmo punto
    apx = plng - alng
    apy = plat - alat
    t = (apx * abx + apy * aby) / ab2
    t = max(0.0, min(1.0, t))  # clampar ao intervalo [0, 1]
    return alat + t * aby, alng + t * abx


def find_nearest_point(lat, lng, geojson_data):
    """
    Atopa o punto máis próximo do GeoJSON ao punto dado.
    Proxecta o punto sobre cada segmento (non só vértices) para maior precisión.
    Devolve (nearest_lat, nearest_lng, distancia_metros).
    """
    min_dist = float('inf')
    nearest = None

    for feature in geojson_data.get("features", []):
        coords = feature["geometry"]["coordinates"]
        for line in coords:
            for i in range(len(line) - 1):
                alat, alng = line[i][1], line[i][0]
                blat, blng = line[i + 1][1], line[i + 1][0]
                clat, clng = _proxectar_punto_sobre_segmento(lat, lng, alat, alng, blat, blng)
                dist = haversine(lat, lng, clat, clng)
                if dist < min_dist:
                    min_dist = dist
                    nearest = (clat, clng)

    if nearest:
        return nearest[0], nearest[1], round(min_dist)
    return lat, lng, 0


def find_nearest_point_with_feature(lat, lng, geojson_data):
    """
    Atopa o punto máis próximo do GeoJSON ao punto dado.
    Proxecta o punto sobre cada segmento (non só vértices) para maior precisión.
    Devolve dict con: lat, lng, distancia, feature_name, feature_idx.
    """
    min_dist = float('inf')
    result = {
        "lat": lat,
        "lng": lng,
        "distancia": 0,
        "feature_name": None,
        "feature_idx": -1,
    }

    for idx, feature in enumerate(geojson_data.get("features", [])):
        name = feature.get("properties", {}).get("Name", "")
        coords = feature["geometry"]["coordinates"]
        for line in coords:
            for i in range(len(line) - 1):
                alat, alng = line[i][1], line[i][0]
                blat, blng = line[i + 1][1], line[i + 1][0]
                clat, clng = _proxectar_punto_sobre_segmento(lat, lng, alat, alng, blat, blng)
                dist = haversine(lat, lng, clat, clng)
                if dist < min_dist:
                    min_dist = dist
                    result = {
                        "lat": clat,
                        "lng": clng,
                        "distancia": round(dist),
                        "feature_name": name,
                        "feature_idx": idx,
                    }

    return result


def _interseccion_segmentos(p1lat, p1lng, p2lat, p2lng, p3lat, p3lng, p4lat, p4lng):
    """
    Calcula a intersección entre o segmento P1P2 e o segmento P3P4.
    Usa aproximación de terra plana (válida para distancias de poucos km).
    Devolve (lat, lng) do punto de intersección ou None se non se intersecan.
    """
    x1, y1 = p1lng, p1lat
    x2, y2 = p2lng, p2lat
    x3, y3 = p3lng, p3lat
    x4, y4 = p4lng, p4lat

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None  # Paralelos ou coincidentes

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (iy, ix)  # (lat, lng)

    return None


def truncar_forma_no_camino(shape, geojson_data):
    """
    Trunca o traxecto de Valhalla no primeiro punto onde cruza xeometricamente
    o camiño GeoJSON, usando intersección real de segmentos (non proximidade a vértices).

    Problema que resolve: Valhalla pode cruzar a liña do camiño e continuar
    cara ao nodo de destino, facendo que o traxecto pase "por riba" do camiño
    e siga un anaco antes de conectar. Este cruce é o punto real de entrada.

    A intersección detecta o cruce exacto entre calquera segmento do shape
    de Valhalla e calquera segmento do GeoJSON, independentemente da densidade
    de vértices. Devolve o shape truncado no punto exacto do primeiro cruce.
    """
    if len(shape) < 2:
        return shape

    # Recoller todos os segmentos do camiño GeoJSON
    segmentos_camino = []
    for feature in geojson_data.get("features", []):
        for line in feature["geometry"]["coordinates"]:
            for i in range(len(line) - 1):
                alat, alng = line[i][1], line[i][0]
                blat, blng = line[i + 1][1], line[i + 1][0]
                segmentos_camino.append((alat, alng, blat, blng))

    # Percorrer o shape de Valhalla de inicio a fin buscando o primeiro cruce
    for i in range(len(shape) - 1):
        p1lat, p1lng = shape[i]
        p2lat, p2lng = shape[i + 1]

        for alat, alng, blat, blng in segmentos_camino:
            cruce = _interseccion_segmentos(
                p1lat, p1lng, p2lat, p2lng,
                alat, alng, blat, blng,
            )
            if cruce is not None:
                # Truncar no punto exacto do cruce
                return shape[:i + 1] + [list(cruce)]

    # Sen cruce detectado: o traxecto chega ao camiño sen cruzalo
    return shape


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dous puntos."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
