import re
import json
from collections import defaultdict

# Cargar lista de tramos do GeoJSON
with open('backend/static/geojson/camino_ingles.geojson', encoding='utf-8') as f:
    data = json.load(f)

# Agrupación: etapa > tramo > variante
hierarquia = defaultdict(lambda: defaultdict(dict))

for feat in data['features']:
    nome = feat['properties']['Name']
    m = re.match(r'CIN-(e\d{2})(V?)(t\d{2})([a-zA-Z0-9]*)-([A-Z\-]+)\\(([^)]+)\\)', nome)
    if not m:
        continue
    etapa, variante_etapa, tramo, variante, nome_etapa, segmento = m.groups()
    etapa_codigo = etapa + variante_etapa
    etapa_nome = nome_etapa
    tramo_codigo = tramo
    tramo_segmento = segmento
    variante_codigo = variante if variante else 'única'
    # Agrupar
    if tramo_codigo not in hierarquia[(etapa_codigo, etapa_nome)]:
        hierarquia[(etapa_codigo, etapa_nome)][(tramo_codigo, tramo_segmento)] = {}
    hierarquia[(etapa_codigo, etapa_nome)][(tramo_codigo, tramo_segmento)][variante_codigo] = nome

# Xeración de texto
for (etapa_codigo, etapa_nome), tramos in hierarquia.items():
    print(f"Etapa {etapa_codigo} - {etapa_nome}")
    for (tramo_codigo, tramo_segmento), variantes in tramos.items():
        print(f"  └── Tramo {tramo_codigo} ({tramo_segmento})")
        for variante_codigo, nome_cin in variantes.items():
            if variante_codigo == 'única':
                print(f"      └── Variante única: {nome_cin}")
            else:
                print(f"      └── Variante {variante_codigo}: {nome_cin}")
    print()