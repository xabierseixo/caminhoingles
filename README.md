# Plataforma Xeoespacial Multi-Proxecto

Plataforma flexible para visualización xeoespacial que soporta múltiples proxectos (rutas, xeodestinos, zonas xeográficas). Arquitectura Backend For Frontend (BFF) en Flask, actuando como proxy seguro fronte a unha API REST externa en Django (gl313.com).

## Instalación e execución rápida

```bash
# 1. Copiar e configurar variables de entorno
cp .env.example .env
# Editar .env co teu API_TOKEN e SECRET_KEY

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Executar
export FLASK_APP=backend/__init__.py
flask run --port 5001
```

## Arquitectura multi-proxecto

A aplicación pode servir para calquera ruta, xeodestino ou zona xeográfica. O proxecto activo contrólase cunha variable de entorno:

```bash
export PROXECTO_ACTIVO=camino-ingles
```

### Ficheiros clave

```
backend/config/
  ├── rutas_config.json        ← Define proxectos e capas GeoJSON
  └── sidebar_config.json      ← Configuración do sidebar (universal)

backend/ruta_activa.py           ← Módulo centralizado de xestión do proxecto activo

backend/static/geojson/
  ├── camino_ingles.geojson    ← Capa de ruta (predefinida)
  ├── concellos_camino_ingles.geojson  ← Concellos para filtrado
  └── [calquera.geojson]       ← Auto-detectado como capa extra
```

### Como funciona

- **`rutas_config.json`** define cada proxecto: centro do mapa, zoom, capas GeoJSON predefinidas e se debe filtrar por concellos.
- **`ruta_activa.py`** centraliza a lóxica: carga os códigos de concellos unha soa vez e expón funcións que usan todos os endpoints.
- **Filtrado por concellos**: activo se o proxecto o ten configurado (`filtrar_por_concellos: true`) e existe o GeoJSON de concellos. Se non, os endpoints devolven todos os datos sen filtrar.
- **Auto-detección de capas**: calquera `.geojson` que se meta en `static/geojson/` aparece automaticamente no endpoint `/api/capas-geojson`.

Para instrucións detalladas, consulta a [Guía de uso](GUIA_USO.md).

## Estrutura do backend

| Ficheiro | Responsabilidade |
|---|---|
| `backend/app.py` | Fábrica da app Flask, blueprints, cache, i18n |
| `backend/config.py` | Configuración centralizada (env vars) |
| `backend/ruta_activa.py` | Xestión do proxecto activo e códigos de concellos |
| `backend/routes.py` | Blueprint principal: sidebar, mapa, proxy API, endpoints novos |
| `backend/aloxamento.py` | Blueprint de aloxamento |
| `backend/recursos.py` | Blueprint de recursos (empresas + espazos) |
| `backend/valhalla.py` | Integración con Valhalla (routing) |
| `backend/config/rutas_config.json` | Definición de proxectos e capas |
| `backend/config/sidebar_config.json` | Configuración do sidebar (categorías, filtros, iconos) |

## Endpoints da API

### Proxecto e capas

| Endpoint | Descrición |
|---|---|
| `GET /api/proxecto-activo` | Info do proxecto activo (nome, centro, zoom, filtrado) |
| `GET /api/capas-geojson` | Capas GeoJSON dispoñibles (predefinidas + extras) |
| `GET /mapa/geojson` | GeoJSON da ruta do proxecto activo |
| `GET /mapa/concellos` | GeoJSON dos concellos do proxecto activo |

### Sidebar e datos

| Endpoint | Descrición |
|---|---|
| `GET /api/sidebar-config` | Configuración das seccións do sidebar |
| `GET /api/sidebar-data/<id>` | Datos dunha sección (items + subcategorías) |

### Recursos

| Endpoint | Descrición |
|---|---|
| `GET /api/empresas` | Empresas filtradas por concellos do proxecto |
| `GET /api/espazos` | Espazos filtrados por concellos do proxecto |
| `GET /api/recursos` | Empresas + espazos combinados |
| `GET /api/aloxamento` | Recursos de aloxamento |
| `GET /api/patrimonio-material` | Patrimonio material filtrado |

### Utilidades

| Endpoint | Descrición |
|---|---|
| `POST /valhalla/route` | Cálculo de rutas vía Valhalla |
| `GET /api/ping` | Health check |
| `GET /api/<path>` | Proxy xenérico á API externa |

## Variables de entorno

| Variable | Obrigatoria | Descrición |
|---|---|---|
| `API_BASE_URL` | Si | URL base da API (por defecto `https://gl313.com/api/`) |
| `API_TOKEN` | Si | Token de autenticación para a API |
| `PROXECTO_ACTIVO` | Non | ID do proxecto activo (por defecto `camino-ingles`) |
| `SECRET_KEY` | Non | Clave secreta para sesións Flask |
| `CACHE_TYPE` | Non | Tipo de cache (`SimpleCache` por defecto) |
| `CACHE_DEFAULT_TIMEOUT` | Non | Timeout da cache en segundos (300 por defecto) |
| `VALHALLA_URL` | Non | URL do servidor Valhalla |
| `VALHALLA_PORT` | Non | Porto do servidor Valhalla |

## Documentación adicional

- [Guía de uso](GUIA_USO.md) — Como engadir proxectos, capas e configurar o sistema
- [CHANGELOG.md](CHANGELOG.md) — Historial de desenvolvemento
- [ANALISE_PROXECTO.md](ANALISE_PROXECTO.md) — Análise técnica da arquitectura
