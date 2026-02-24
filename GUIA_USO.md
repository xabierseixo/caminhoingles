# Guia de uso: Sistema Multi-Proxecto

Esta guía explica como configurar, estender e operar a plataforma xeoespacial.

---

## 1. Configuración inicial

### Variables de entorno

Copiar `.env.example` a `.env` e configurar:

```bash
cp .env.example .env
```

Contido mínimo:

```env
API_BASE_URL=https://gl313.com/api/
API_TOKEN=o_teu_token
PROXECTO_ACTIVO=camino-ingles
SECRET_KEY=unha-clave-segura-para-produccion
```

### Executar

```bash
export FLASK_APP=backend/__init__.py
flask run --port 5001
```

### Verificar que funciona

```bash
curl http://localhost:5001/api/proxecto-activo
curl http://localhost:5001/api/capas-geojson
curl http://localhost:5001/api/sidebar-config
curl http://localhost:5001/mapa/geojson
curl http://localhost:5001/api/ping
```

---

## 2. Engadir un novo proxecto

### Paso 1: Preparar os ficheiros GeoJSON

Meter os ficheiros en `backend/static/geojson/`. Exemplo para un xeodestino:

```
backend/static/geojson/
  ├── ruta_rias_baixas.geojson
  └── concellos_rias_baixas.geojson   ← Opcional (para filtrado por concellos)
```

O GeoJSON de concellos debe ter a propiedade `CODIGOINE` en cada feature:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "CODIGOINE": "36057",
        "Concello": "Vilagarcía de Arousa"
      },
      "geometry": { "..." }
    }
  ]
}
```

### Paso 2: Engadir a entrada en `rutas_config.json`

Editar `backend/config/rutas_config.json`:

```json
{
  "proxectos": {
    "camino-ingles": {
      "...": "..."
    },
    "rias-baixas": {
      "id": "rias-baixas",
      "nome": "Rías Baixas",
      "centro": {"lat": 42.43, "lng": -8.65},
      "zoom_inicial": 11,
      "map_id": null,
      "capas": {
        "ruta": {
          "ficheiro": "ruta_rias_baixas.geojson",
          "estilo": {"cor": "#2196F3", "grosor": 3},
          "visible_por_defecto": true
        },
        "concellos": {
          "ficheiro": "concellos_rias_baixas.geojson",
          "estilo": {"cor_borde": "#333", "opacidade": 0.3},
          "visible_por_defecto": true
        }
      },
      "filtrar_por_concellos": true
    }
  },
  "proxecto_por_defecto": "camino-ingles",
  "auto_detectar_geojson": true
}
```

### Paso 3: Activar o proxecto

No ficheiro `.env`:

```env
PROXECTO_ACTIVO=rias-baixas
```

Ou como variable de entorno:

```bash
export PROXECTO_ACTIVO=rias-baixas
flask run --port 5001
```

### Paso 4: Reiniciar

A configuración cárgase ao iniciar a app. Despois de cambiar `rutas_config.json` ou `PROXECTO_ACTIVO`, reiniciar Flask.

---

## 3. Proxecto sen filtrado por concellos

Se o proxecto non precisa filtrar por concellos (por exemplo, un mapa xeral de Galicia), hai dúas opcións:

### Opción A: Non incluír capa de concellos

```json
{
  "id": "galicia-xeral",
  "nome": "Galicia",
  "centro": {"lat": 42.75, "lng": -7.87},
  "zoom_inicial": 8,
  "map_id": null,
  "capas": {
    "ruta": {
      "ficheiro": "galicia_comarcas.geojson",
      "estilo": {"cor": "#4CAF50", "grosor": 2},
      "visible_por_defecto": true
    }
  },
  "filtrar_por_concellos": false
}
```

### Opcion B: Ter concellos visuais pero sen filtrar datos

```json
{
  "filtrar_por_concellos": false,
  "capas": {
    "concellos": {
      "ficheiro": "concellos_galicia.geojson",
      "estilo": {"cor_borde": "#333", "opacidade": 0.2},
      "visible_por_defecto": true
    }
  }
}
```

Neste caso, os concellos amósanse no mapa pero os endpoints de datos (empresas, espazos, patrimonio) devolven **todo** sen filtrar.

---

## 4. Engadir capas GeoJSON extra (sen configurar nada)

Simplemente meter un ficheiro `.geojson` no cartafol `backend/static/geojson/`:

```bash
cp xeodestino_rias_baixas.geojson backend/static/geojson/
```

A capa aparece automaticamente no endpoint `/api/capas-geojson`:

```bash
curl http://localhost:5001/api/capas-geojson
```

Resposta:

```json
{
  "predefinidas": {
    "ruta": {"url": "/mapa/geojson", "estilo": {"cor": "#e63946", "grosor": 4}, "visible": true},
    "concellos": {"url": "/mapa/concellos", "estilo": {"cor_borde": "#333", "opacidade": 0.3}, "visible": true}
  },
  "extras": [
    {"nome": "xeodestino_rias_baixas", "url": "/static/geojson/xeodestino_rias_baixas.geojson"}
  ]
}
```

O frontend pode usar esta resposta para ofrecer un panel de activación/desactivación de capas.

---

## 5. Configuración do sidebar

O sidebar configúrase en `backend/config/sidebar_config.json` e é **compartido por todos os proxectos**. As seccións definen:

- **`fonte`**: tipo de datos (`recursos` ou `patrimonio-material`)
- **`filtro_categoria`**: slug de categoría para filtrar na API
- **`taxonomia.endpoint`**: endpoint para obter xerarquía de categorías
- **`filtros.filtrar_concellos_camino`**: se debe filtrar por concellos (respéctase só se o proxecto o permite)
- **`iconos_subcategorias`**: iconos Font Awesome e cores por subcategoría

Exemplo de sección:

```json
{
  "id": "patrimonio-relixioso",
  "nome": "Patrimonio relixioso",
  "fonte": "patrimonio-material",
  "filtro_categoria": "patrimonio-relixioso",
  "icono_seccion": "fa-church",
  "activo": true,
  "filtros": {
    "minimo_items": 1,
    "requirir_coordenadas": true,
    "filtrar_concellos_camino": true,
    "ordenar_por": "nome"
  },
  "iconos_subcategorias": {
    "igrexas": {"icon": "fa-church", "cor": "#8b0000"},
    "_default": {"icon": "fa-landmark", "cor": "#8b4513"}
  }
}
```

Para desactivar unha sección: poñer `"activo": false`.

---

## 6. Referencia de endpoints

### `/api/proxecto-activo`

Devolve a información do proxecto en execución:

```json
{
  "id": "camino-ingles",
  "nome": "Camiño Inglés",
  "centro": {"lat": 42.8782, "lng": -8.5446},
  "zoom_inicial": 10,
  "filtrar_por_concellos": true
}
```

### `/api/capas-geojson`

Lista todas as capas GeoJSON dispoñibles, separadas en predefinidas (do proxecto) e extras (auto-detectadas):

```json
{
  "predefinidas": {
    "ruta": {"url": "/mapa/geojson", "estilo": {}, "visible": true},
    "concellos": {"url": "/mapa/concellos", "estilo": {}, "visible": true}
  },
  "extras": [
    {"nome": "nome_do_ficheiro", "url": "/static/geojson/nome_do_ficheiro.geojson"}
  ]
}
```

### `/api/sidebar-data/<seccion_id>`

Devolve items e subcategorías para unha sección do sidebar:

```json
{
  "subcategorias": [
    {"slug": "igrexas", "nome": "Igrexas", "count": 12}
  ],
  "items": [
    {"nome": "Igrexa de Santiago", "lat": 42.87, "lng": -8.54}
  ],
  "taxonomia": true
}
```

---

## 7. Referencia do módulo `ruta_activa.py`

O módulo `backend/ruta_activa.py` centraliza toda a lóxica do proxecto activo. Funcións dispoñibles:

| Función | Devolve | Descrición |
|---|---|---|
| `obter_proxecto_activo()` | `dict` | Config completa do proxecto activo |
| `debe_filtrar_concellos()` | `bool` | `True` se o proxecto ten filtrado activo e existe o GeoJSON |
| `get_concellos_codigos()` | `list[str]` | Códigos de concellos (5 díxitos). Lista baleira se non filtra |
| `obter_capas_geojson()` | `dict` | Capas predefinidas + extras auto-detectadas |

Uso en calquera blueprint:

```python
from backend.ruta_activa import get_concellos_codigos, debe_filtrar_concellos

if debe_filtrar_concellos():
    codigos = get_concellos_codigos()
    items = [i for i in items if i['concello_codigo'] in codigos]
```

---

## 8. Campos de `rutas_config.json`

| Campo | Tipo | Obrigatorio | Descrición |
|---|---|---|---|
| `proxectos` | object | Si | Dict de proxectos, clave = ID do proxecto |
| `proxecto_por_defecto` | string | Si | ID do proxecto cando `PROXECTO_ACTIVO` non está definido |
| `auto_detectar_geojson` | bool | Non | Auto-detectar `.geojson` extras (por defecto `true`) |

### Campos de cada proxecto

| Campo | Tipo | Obrigatorio | Descrición |
|---|---|---|---|
| `id` | string | Si | Identificador único |
| `nome` | string | Si | Nome para mostrar na interface |
| `centro.lat` / `centro.lng` | float | Si | Coordenadas iniciais do mapa |
| `zoom_inicial` | int | Si | Nivel de zoom inicial |
| `map_id` | int/null | Non | ID do mapa na API (para obter centro/zoom dinámico) |
| `capas.ruta` | object | Non | GeoJSON da ruta principal |
| `capas.concellos` | object | Non | GeoJSON dos concellos |
| `capas.ruta.ficheiro` | string | Si | Nome do ficheiro en `static/geojson/` |
| `capas.ruta.estilo` | object | Non | Estilo visual (cor, grosor) |
| `capas.ruta.visible_por_defecto` | bool | Non | Se se mostra ao cargar (por defecto `true`) |
| `filtrar_por_concellos` | bool | Si | Se os endpoints filtran datos por concellos |
