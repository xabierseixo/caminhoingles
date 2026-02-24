# Análise Técnica do Proxecto Camiño Inglés

Data: 2026-02-04

## 1. VISIÓN XERAL DA ARQUITECTURA

### Arquitectura actual: Backend For Frontend (BFF)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   NAVEGADOR     │────▶│  FLASK BACKEND   │────▶│   API GALIZA    │
│   (Leaflet)     │◀────│     (Proxy)      │◀────│  (gl313.com)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                        ┌──────┴──────┐
                        │   SQLite    │
                        │  (usuarios) │
                        └─────────────┘
```

### Compoñentes principais

| Compoñente | Ficheiro(s) | Responsabilidade |
|------------|-------------|------------------|
| App Flask | `backend/app.py` | Factory, blueprints, cache |
| Rutas | `backend/routes.py` | Proxy API, endpoints locais |
| Cache | `backend/cache.py` | Flask-Caching configurable |
| Modelos | `backend/models.py` | SQLite usuarios |
| Config | `backend/config.py` | Variables de entorno |
| Mapa | `templates/mapa.html` | Leaflet + sidebar Bootstrap |
| JS | `static/js/app.js` | Lóxica frontend |

---

## 2. ANÁLISE DA CALIDADE DO CÓDIGO

### Puntos fortes

1. **Separación de responsabilidades**: O backend actúa como proxy seguro, o token nunca se expón no frontend
2. **Configuración por variables de entorno**: Fácil de despregar
3. **Cache integrado**: Flask-Caching configurado
4. **Internacionalización**: Flask-Babel preparado
5. **Estrutura modular**: Blueprints separados
6. **GeoJSON estático optimizado**: Ficheiros filtrados para o camiño

### Áreas de mellora identificadas

1. **Código de depuración en produción**: O ficheiro `routes.py` ten logs a `/tmp/camino_debug.log` (liñas 190-230)
2. **Duplicación de imports**: `requests`, `os`, `json` importados múltiples veces
3. **Filtrado de concellos comentado**: Liña 222 de routes.py ten filtrado desactivado
4. **Falta de validación de entrada**: Os endpoints non validan parámetros
5. **Sen documentación de API**: Falta OpenAPI/Swagger para os endpoints propios

---

## 3. MELLORAS FUTURAS RECOMENDADAS

### Prioridade Alta

1. **Limpeza de código de depuración**
   - Eliminar logs a `/tmp/camino_debug.log`
   - Reactivar filtrado de concellos

2. **Optimización de consultas á API**
   - Implementar caché por categoría
   - Usar paginación na consulta inicial

3. **Validación de parámetros**
   - Validar `concello_codigo` como número
   - Validar `categoria` como slug válido

### Prioridade Media

1. **Clustering de marcadores**
   - Implementar PruneCluster ou MarkerCluster
   - Mellora significativa de rendemento con moitos puntos

2. **Documentación OpenAPI**
   - Xerar schema para endpoints propios
   - Integrar con Swagger UI

3. **Tests de integración**
   - Engadir tests para filtrado
   - Tests E2E con Playwright

### Prioridade Baixa

1. **PWA (Progressive Web App)**
   - Modo offline con service worker
   - Cacheo de GeoJSON

2. **Isocronas con Valhalla**
   - Completar integración
   - Filtrar por tempo de desprazamento

---

## 4. IMPLEMENTACIÓN: SELECTOR DE CAMIÑO NO PERFIL DE ELEVACIÓN

### Obxectivo
Mellorar a visualización do perfil de elevación para distinguir correctamente entre as dúas rutas principais do Camiño Inglés: Ferrol e A Coruña, que se xuntan en Bruma.

### Problema resolto
O perfil de elevación mostraba todos os segmentos (Ferrol + A Coruña + Comúns) mesturados. Son dúas rutas diferentes que se xuntan en Bruma, e o usuario necesita ver cada unha por separado.

### Solución implementada
- Toggle "Ferrol" / "A Coruña" no panel de elevación (#selectorCamino) con radio buttons Bootstrap
- Ao cambiar de orixe:
  - O perfil de elevación e as estatísticas (dist, D+, D-, tempo) actualízanse mostrando o camiño seleccionado + tramos comúns (Bruma→Santiago) = ruta completa ata Santiago
  - O mapa mostra AMBOS camiños: o seleccionado en amarelo (#ffd600, grosor 5) e o non seleccionado en gris (#888, grosor 4, opacidade 0.7, liña descontinua)
  - Os checkboxes do sidebar quedan todos activos (o usuario pode desmarcar manualmente)
- O panel de elevación usa position: fixed con overflow: hidden no body para evitar scroll do navegador
- O click no selector non toglea o panel (garda con e.target.closest('#selectorCamino'))

### Ficheiros modificados
- backend/templates/mapa.html:
  - HTML do selector (btn-group dentro de #elevationToggle)
  - CSS: #selectorCamino styling, position: fixed no panel, overflow: hidden en html/body
  - Style function en actualizarCapaCamino() con lóxica de cor activo/inactivo por clasificarTramo()
  - Inicialización con window.caminoSeleccionado = 'ferrol'
- backend/static/js/app.js:
  - Nova función aplicarSelectorCamino(orixe) — actualiza window.caminoSeleccionado e chama as funcións de actualización
  - Listener para name="caminoOrixe" (cambio de radio buttons)
  - actualizarElevacion() — filtra tramos por clasificarTramo() excluíndo o orixe non seleccionado (xa NON depende dos checkboxes)
  - moverMarcadorElevacion() — filtra tramos igual que actualizarElevacion() para que o marcador no mapa se posicione correctamente (fix crítico: antes usaba checkboxes e o marcador ía cara A Coruña en vez de Santiago)
  - Garda de click no #selectorCamino dentro de inicializarPanelElevacion() para non toglear o panel

### Funcións clave
- clasificarTramo(nome) — clasifica cada segmento como 'ferrol', 'coruna' ou 'comun'
- aplicarSelectorCamino(orixe) — actualiza window.caminoSeleccionado e chama actualizarCapaCamino() + actualizarElevacion()
- actualizarElevacion() — filtra: clasificarTramo(t.nome) !== outroOrixe (orixe seleccionado + comúns)
- moverMarcadorElevacion() — mesma lóxica de filtrado para mapear índice do perfil → coordenada xeográfica correcta

---

## 4. IMPLEMENTACIÓN: PATRIMONIO RELIXIOSO

### Obxectivo
Engadir unha nova sección no sidebar para mostrar categorías de patrimonio relixioso nos concellos do Camiño Inglés.

### Cambios realizados

#### 4.1 Backend - `backend/routes.py`

**Engadido endpoint `/api/categorias/patrimonio-relixioso/`**

```python
@bp.route('/api/categorias/patrimonio-relixioso/')
def categorias_patrimonio_relixioso():
    # Consulta á API externa para obter patrimonio material
    # Filtrado por concellos do Camiño Inglés
    # Agrupación por categorías con contido
```

Liñas afectadas: [ver sección de cambios]

#### 4.2 Frontend - `backend/static/js/app.js`

**Engadida función `cargarCategoriasPatrimonioRelixioso()`**

- Carga categorías desde o endpoint
- Xera checkboxes no sidebar
- Filtra recursos no mapa

#### 4.3 Template - `backend/templates/mapa.html`

**Engadida sección no sidebar para patrimonio relixioso**

- Acordeón Bootstrap para categorías
- Checkboxes para filtrado

---

## 5. SISTEMA EXTENSIBLE PARA NOVAS CATEGORÍAS

### Patrón implementado

Para engadir unha nova categoría ao sidebar, hai que:

1. **Backend**: Crear endpoint `/api/categorias/<nome-categoria>/`
   ```python
   @bp.route('/api/categorias/<nome>/')
   def categorias_xenerico(nome):
       # Consultar API externa
       # Filtrar por concellos do Camiño
       # Devolver categorías con contido
   ```

2. **Frontend**: Engadir función JS
   ```javascript
   async function cargarCategorias<Nome>() {
       // Mesmo patrón que cargarCategoriasAloxamento()
   }
   ```

3. **Template**: Engadir sección no acordeón
   ```html
   <div class="accordion-item">
       <h2 class="accordion-header" id="heading<Nome>">...</h2>
   </div>
   ```

### Exemplo: Engadir "Patrimonio Natural"

**1. Backend (`routes.py`):**
```python
@bp.route('/api/patrimonio-natural/')
def patrimonio_natural_api():
    # Mesmo patrón que patrimonio_relixioso_api
    # Cambiar: params['categoria'] = 'patrimonio-ambiental'
```

**2. Frontend (`app.js`):**
```javascript
async function cargarCategoriasPatrimonioNatural() {
    // Mesmo patrón que cargarCategoriasPatrimonioMaterial
    // Cambiar: containerId e endpoint
}
```

**3. Template (`mapa.html`):**
```html
<div class="accordion-item">
  <h2 class="accordion-header" id="headingPatrimonioNatural">
    <button class="accordion-button collapsed" ...>
      Patrimonio natural
    </button>
  </h2>
  <div id="collapsePatrimonioNatural" ...>
    <div id="patrimonioNaturalCheckboxes">...</div>
  </div>
</div>
```

### Ficheiro de configuración proposto (futuro)

Para simplificar aínda máis, proponse crear un ficheiro `categorias_config.json`:

```json
{
  "categorias": [
    {
      "id": "aloxamento",
      "nome": "Aloxamento",
      "endpoint": "/categorias/servizos/hostalaria/aloxamento/",
      "icono": "fa-bed",
      "cor": "#007bff"
    },
    {
      "id": "patrimonio-material",
      "nome": "Patrimonio relixioso",
      "endpoint": "/api/categorias/patrimonio-material/",
      "icono": "fa-landmark",
      "cor": "#8b4513"
    }
  ]
}
```

Esta configuración permitiría xerar automaticamente:
- Endpoints no backend
- Seccións no sidebar
- Marcadores no mapa con cores personalizadas

---

## 6. REXISTRO DE CAMBIOS DESTA SESIÓN

### Ficheiros modificados

| Ficheiro | Cambio |
|----------|--------|
| `backend/routes.py` | Engadido endpoint `/api/categorias/patrimonio-relixioso/` |
| `backend/static/js/app.js` | Engadidas funcións para patrimonio relixioso |
| `backend/templates/mapa.html` | Sección patrimonio relixioso xa presente, integrada con JS |
| `ANALISE_PROXECTO.md` | Creado (este ficheiro) |

### Liñas específicas modificadas

Ver sección seguinte para detalle liña a liña.

---

## 7. DETALLE DOS CAMBIOS POR FICHEIRO

### backend/routes.py

**Engadidos 2 novos endpoints despois de `categorias_aloxamento()` (liña 83+):**

1. **`/api/categorias/patrimonio-material/`** - Devolve categorías agrupadas con conteo
2. **`/api/patrimonio-relixioso/`** - Devolve elementos filtrados por categoría

```python
@bp.route('/api/categorias/patrimonio-material/')
def categorias_patrimonio_material():
    """
    Devolve as categorías de patrimonio material con contido
    nos concellos do Camiño Inglés.
    """
    # Consulta á API externa
    # Agrupación por categoría
    # Devolve: {"categorias": [...], "total": N}

@bp.route('/api/patrimonio-relixioso/')
def patrimonio_relixioso_api():
    """
    Devolve elementos de patrimonio filtrados.
    Parámetros: ?categoria=<slug>
    """
    # Consulta á API con filtro
    # Devolve: {"results": [...]}
```

### backend/static/js/app.js

**Engadidas 4 funcións novas ao final do ficheiro (liña 207+):**

```javascript
// Sistema extensible de categorías
window.categoryLayers = {};

// 1. Cargar categorías de patrimonio material
async function cargarCategoriasPatrimonioMaterial() { ... }

// 2. Filtrar por categoría seleccionada
async function filtrarPatrimonioPorCategoria() { ... }

// 3. Mostrar marcadores no mapa
function mostrarMarcadoresPatrimonio(patrimonio) { ... }

// 4. Inicialización ao cargar a páxina
window.addEventListener('DOMContentLoaded', () => { ... });
```

### backend/templates/mapa.html

**Sección patrimonio relixioso xa existente** (liñas 67-78)
- O acordeón xa estaba creado
- Integración automática via `app.js`

---

## 8. INSTRUCIÓNS PARA COPILOT

Para integrar estes cambios no fluxo de traballo:

1. **Revisar `backend/routes.py`** - Novo endpoint de patrimonio relixioso
2. **Revisar `backend/static/js/app.js`** - Novas funcións JS
3. **Verificar funcionamento** - Probar no navegador
4. **Commit**: `git add . && git commit -m "Feature: patrimonio relixioso no sidebar con checkboxes"`

---

*Xerado automaticamente - Claude Code*
