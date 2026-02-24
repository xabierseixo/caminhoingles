#!/usr/bin/env python3
"""
Script offline para enriquecer o GeoJSON do Camiño Inglés con datos de elevación
usando Valhalla /height endpoint.

Uso:
    python backend/scripts/enriquecer_elevacion.py

Require Valhalla correndo en localhost:8002 con datos de elevación.
"""

import json
import os
import sys
import requests
import time

VALHALLA_URL = os.environ.get("VALHALLA_URL", "http://localhost:8002")
HEIGHT_ENDPOINT = f"{VALHALLA_URL}/height"
BATCH_SIZE = 100  # Puntos por petición a /height

INPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "static", "geojson", "camino_ingles.geojson"
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "static", "geojson", "camino_ingles_elevation.geojson"
)


def request_height(points):
    """
    Chama a Valhalla /height con range=true.
    points: lista de {"lat": ..., "lon": ...}
    Devolve range_height: lista de [distancia_acumulada, altitude]
    """
    data = {"range": True, "shape": points}
    resp = requests.post(HEIGHT_ENDPOINT, json=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get("range_height", [])


def enriquecer_feature(feature, idx, total):
    """Enriquece unha feature con altitudes reais e estatísticas."""
    name = feature["properties"].get("Name", f"feature_{idx}")
    coords = feature["geometry"]["coordinates"]  # MultiLineString: [[coords...], ...]

    all_range_heights = []  # Para o perfil completo
    new_coords = []

    for line_idx, line in enumerate(coords):
        # Preparar puntos para Valhalla (lat, lon)
        shape = [{"lat": c[1], "lon": c[0]} for c in line]

        # Enviar en lotes, acumulando distancias correctamente
        line_heights = []  # Lista final con distancias acumuladas correctas
        dist_offset = 0  # Offset de distancia acumulada entre lotes

        for batch_start in range(0, len(shape), BATCH_SIZE):
            batch = shape[batch_start : batch_start + BATCH_SIZE]
            try:
                rh = request_height(batch)
                # Axustar distancias con offset e engadir
                for j, entry in enumerate(rh):
                    adjusted_dist = entry[0] + dist_offset
                    alt = entry[1]
                    # Non duplicar punto de unión (último do lote anterior = primeiro do novo)
                    if j == 0 and line_heights:
                        continue
                    line_heights.append([adjusted_dist, alt])
                # Actualizar offset para o seguinte lote
                if rh:
                    dist_offset += rh[-1][0]
            except Exception as e:
                print(f"  ERRO en lote {batch_start}-{batch_start+len(batch)}: {e}")
                for j in range(len(batch)):
                    line_heights.append([dist_offset, 0])
            # Pequena pausa entre lotes
            if batch_start + BATCH_SIZE < len(shape):
                time.sleep(0.1)

        # Actualizar coordenadas con altitudes
        new_line = []
        for j, coord in enumerate(line):
            if j < len(line_heights):
                alt = line_heights[j][1]
            else:
                alt = 0.0
            new_line.append([coord[0], coord[1], alt])

        new_coords.append(new_line)

        # Acumular ao perfil global (con offset entre liñas)
        line_offset = all_range_heights[-1][0] if all_range_heights else 0
        for j, rh in enumerate(line_heights):
            dist = rh[0] + line_offset
            alt = rh[1]
            if j == 0 and all_range_heights:
                continue
            all_range_heights.append([dist, alt])

    # Actualizar coordenadas
    feature["geometry"]["coordinates"] = new_coords

    # Calcular estatísticas
    altitudes = [rh[1] for rh in all_range_heights]
    distancia_total = all_range_heights[-1][0] if all_range_heights else 0

    desnivel_pos = 0
    desnivel_neg = 0
    for i in range(1, len(altitudes)):
        diff = altitudes[i] - altitudes[i - 1]
        if diff > 0:
            desnivel_pos += diff
        else:
            desnivel_neg += abs(diff)

    feature["properties"]["distancia_km"] = round(distancia_total / 1000, 2)
    feature["properties"]["desnivel_positivo"] = round(desnivel_pos)
    feature["properties"]["desnivel_negativo"] = round(desnivel_neg)
    feature["properties"]["altitude_max"] = round(max(altitudes)) if altitudes else 0
    feature["properties"]["altitude_min"] = round(min(altitudes)) if altitudes else 0
    feature["properties"]["perfil"] = all_range_heights

    pts = sum(len(line) for line in coords)
    print(
        f"  [{idx+1}/{total}] {name}: {pts} pts, "
        f"{feature['properties']['distancia_km']} km, "
        f"D+{feature['properties']['desnivel_positivo']}m "
        f"D-{feature['properties']['desnivel_negativo']}m, "
        f"alt {feature['properties']['altitude_min']}-{feature['properties']['altitude_max']}m"
    )


def main():
    input_path = os.path.abspath(INPUT_FILE)
    output_path = os.path.abspath(OUTPUT_FILE)

    print(f"Lendo {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    total = len(geojson["features"])
    print(f"Features: {total}")
    print(f"Valhalla endpoint: {HEIGHT_ENDPOINT}")
    print()

    # Verificar que Valhalla está dispoñible
    try:
        test = request_height([{"lat": 43.37, "lon": -8.39}])
        print(f"Valhalla OK (test altitude: {test[0][1]}m)")
    except Exception as e:
        print(f"ERRO: Non se pode conectar con Valhalla en {HEIGHT_ENDPOINT}: {e}")
        sys.exit(1)

    print()
    for idx, feature in enumerate(geojson["features"]):
        enriquecer_feature(feature, idx, total)

    print(f"\nGardando en {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)

    # Resumo
    dist_total = sum(f["properties"].get("distancia_km", 0) for f in geojson["features"])
    dpos_total = sum(f["properties"].get("desnivel_positivo", 0) for f in geojson["features"])
    dneg_total = sum(f["properties"].get("desnivel_negativo", 0) for f in geojson["features"])
    print(f"\nResumo:")
    print(f"  Distancia total: {round(dist_total, 1)} km")
    print(f"  Desnivel total +: {dpos_total}m")
    print(f"  Desnivel total -: {dneg_total}m")
    print(f"  Ficheiro: {output_path}")


if __name__ == "__main__":
    main()
