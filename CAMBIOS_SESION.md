# Cambios realizados - Sesión 2026-02-04

## Resumo
Implementación dun **sistema dinámico de sidebar v2.1** baseado en configuración JSON con soporte para **xerarquías de categorías** desde a API de taxonomía. Permite engadir novas categorías simplemente editando un ficheiro de configuración, sen tocar código.

---

## Fase: Selector de camiño no perfil de elevación (Ferrol / A Coruña)

- Engadido toggle Ferrol/A Coruña no panel de elevación (radio buttons Bootstrap)
- O perfil de elevación e as estatísticas actualízanse mostrando só o camiño seleccionado + tramos comúns (Bruma→Santiago)
- O mapa mostra ambos camiños: o seleccionado en amarelo (#ffd600, grosor 5) e o non seleccionado en gris (#888, grosor 4, opacidade 0.7, liña descontinua)
- Os checkboxes do sidebar quedan todos activos (o usuario pode desmarcar manualmente)
- O panel de elevación usa position: fixed e overflow: hidden no body para evitar scroll do navegador
- Ficheiros modificados: backend/templates/mapa.html, backend/static/js/app.js
- Commit: feat(elevación): selector Ferrol/Coruña no perfil, estilo diferenciado no mapa e panel fixed

---

## Arquitectura do Sistema

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  sidebar_config │────▶│  /api/sidebar-data/  │────▶│  API gl313.com  │
│     .json       │     │    <seccion_id>      │     │                 │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  {subcategorias,     │
                        │   items, taxonomia}  │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  app.js v2.1         │
                        │  - Renderiza xerarquía│
                        │  - Filtra por slug   │
                        │  - Mostra marcadores │
                        └──────────────────────┘
```

---

## Ficheiros do sistema

### 1. backend/config/sidebar_config.json

Ficheiro de configuración que define todas as seccións do sidebar.

**Estrutura dunha sección CON taxonomía (aloxamento):**
```json
{
  "id": "aloxamento",
  "nome": "Aloxamento",
  "fonte": "recursos",
  "icono_seccion": "fa-bed",
  "activo": true,

  "taxonomia": {
    "endpoint": "taxonomia/categorias/servizos/hostalaria/aloxamento/",
    "mostrar_xerarquia": true
  },

  "filtros": {
    "minimo_items": 0,
    "requirir_coordenadas": true,
    "filtrar_concellos_camino": true,
    "ordenar_por": "nome"
  },

  "iconos_subcategorias": {
    "hoteis": {"icon": "fa-hotel", "cor": "#4a90d9"},
    "albergues": {"icon": "fa-campground", "cor": "#7ac0ca"},
    "albergues-do-camino-de-santiago": {"icon": "fa-route", "cor": "#e6a800"},
    "_default": {"icon": "fa-bed", "cor": "#4a90d9"}
  }
}
```

**Estrutura dunha sección SEN taxonomía (patrimonio):**
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
    "filtrar_concellos_camino": true
  },

  "iconos_subcategorias": {
    "igrexas": {"icon": "fa-church", "cor": "#8b0000"},
    "_default": {"icon": "fa-landmark", "cor": "#8b4513"}
  }
}
```

**Seccións activas:**
- Aloxamento (con taxonomía xerárquica)
- Patrimonio relixioso
- Patrimonio ambiental
- Patrimonio civil

**Campos importantes:**
| Campo | Descrición |
|-------|------------|
| `fonte` | `recursos` (espazos+empresas) ou `patrimonio-material` |
| `filtro_categoria` | Slug para filtrar na API (só para patrimonio) |
| `taxonomia.endpoint` | Endpoint para obter árbore de categorías |
| `iconos_subcategorias` | Mapa slug → {icon, cor} para marcadores |

---

### 2. backend/routes.py

**Endpoint `/api/sidebar-config`** (liñas 38-52)
- Serve a configuración do sidebar
- Filtra só seccións activas

**Endpoint `/api/sidebar-data/<seccion_id>`** (liñas 56-220)

Endpoint unificado con dous modos de funcionamento:

#### MODO TAXONOMÍA (cando existe `taxonomia.endpoint`):
1. Consulta o endpoint de taxonomía para obter a árbore de categorías
2. Consulta espazos + empresas
3. Filtra por concellos do Camiño Inglés
4. Para cada item, determina o **slug máis específico** (evita contar dúas veces)
5. Constrúe xerarquía recursiva con contadores
6. **Filtra categorías baleiras** (count == 0)
7. Devolve estrutura con `children`

```python
# Resposta modo taxonomía:
{
  "subcategorias": [
    {
      "slug": "albergues",
      "nome": "Albergues",
      "count": 6,
      "count_propio": 0,
      "children": [
        {
          "slug": "albergues-do-camino-de-santiago",
          "nome": "Albergues do Camiño de Santiago",
          "count": 6,
          "count_propio": 6
        }
      ]
    }
  ],
  "items": [...],
  "taxonomia": true
}
```

#### MODO EXTRACCIÓN (sen `taxonomia.endpoint`):
1. Consulta a API correspondente (patrimonio-material)
2. Filtra por concellos do Camiño Inglés
3. Extrae subcategorías dos `categorias_breadcrumbs` dos items
4. Aplica filtros (minimo_items, excluir, etc.)
5. Devolve lista plana

```python
# Resposta modo extracción:
{
  "subcategorias": [
    {"slug": "igrexas", "nome": "Igrexas", "count": 15},
    {"slug": "capelas", "nome": "Capelas", "count": 8}
  ],
  "items": [...],
  "taxonomia": false
}
```

**Lóxica de conteo (IMPORTANTE):**
- Cada item só se conta UNHA vez, na categoría **máis específica**
- Se un item está en "Albergues do Camiño de Santiago", NON se conta en "Albergues"
- O `count` do pai é a suma dos `count` dos fillos
- Categorías con `count == 0` NON se mostran

---

### 3. backend/static/js/app.js (v2.1)

Sistema con soporte para xerarquías.

**Variables globais:**
```javascript
window.sidebarConfig = null;    // Configuración das seccións
window.sidebarData = {};        // Datos: {seccionId: {subcategorias, items, taxonomia}}
window.categoryLayers = {};     // Capas Leaflet por sección
```

**Funcións principais:**

| Función | Descrición |
|---------|------------|
| `inicializarSidebar()` | Carga config e inicializa cada sección |
| `construirSidebarHTML()` | Crea acordeóns Bootstrap dinámicos |
| `cargarSeccion(seccion)` | Chama a `/api/sidebar-data/<id>` |
| `renderizarCheckboxes()` | Renderiza con indentación para xerarquías |
| `obterTodosSlugsFillo(cat)` | Extrae slugs recursivamente |
| `filtrarSeccion(seccion)` | Filtra items por slugs seleccionados + fillos |
| `mostrarMarcadores()` | Crea marcadores Leaflet con iconos |

**Renderizado xerárquico:**
```javascript
function renderizarNivel(cats, nivel = 0) {
  cats.forEach(subcat => {
    const div = document.createElement('div');
    div.className = 'form-check';
    if (nivel > 0) {
      div.style.marginLeft = `${nivel * 16}px`;  // Indentación
    }
    // ... crear checkbox ...

    // Gardar slugs dos fillos para filtrar despois
    if (subcat.children?.length) {
      chk.dataset.childrenSlugs = JSON.stringify(obterTodosSlugsFillo(subcat));
    }

    // Renderizar fillos recursivamente
    if (subcat.children?.length) {
      renderizarNivel(subcat.children, nivel + 1);
    }
  });
}
```

**Filtrado con fillos:**
```javascript
function filtrarSeccion(seccion) {
  let slugsAFiltrar = [];

  checkedInputs.forEach(chk => {
    slugsAFiltrar.push(chk.value);
    // Engadir tamén os slugs dos fillos
    if (chk.dataset.childrenSlugs) {
      const childSlugs = JSON.parse(chk.dataset.childrenSlugs);
      slugsAFiltrar = slugsAFiltrar.concat(childSlugs);
    }
  });

  // Filtrar items que teñan calquera dos slugs
  const itemsFiltrados = data.items.filter(item => {
    const itemSlugs = new Set();
    // Extraer de breadcrumbs e categorias_list
    return slugsAFiltrar.some(slug => itemSlugs.has(slug));
  });
}
```

---

## Fluxo de funcionamento (v2.1)

```
1. Usuario abre a páxina
   ↓
2. JS carga /api/sidebar-config
   ↓
3. Para cada sección activa:
   ├─ [CON taxonomia.endpoint]
   │   a. Backend consulta taxonomía → árbore de categorías
   │   b. Backend consulta recursos (espazos + empresas)
   │   c. Conta items por slug máis específico
   │   d. Filtra categorías baleiras
   │   e. Devolve xerarquía con children
   │   f. JS renderiza con indentación
   │
   └─ [SEN taxonomia.endpoint]
       a. Backend consulta patrimonio-material
       b. Extrae subcategorías dos breadcrumbs
       c. Devolve lista plana
       d. JS renderiza sen indentación
   ↓
4. Usuario selecciona checkbox
   ↓
5. JS obtén slugs seleccionados + slugs dos fillos
   ↓
6. Filtra items que teñan calquera deses slugs
   ↓
7. Mostra marcadores con iconos específicos
```

---

## Como engadir unha nova categoría

### Caso A: Categoría con taxonomía (como aloxamento)

1. Buscar o endpoint de taxonomía na API:
```bash
curl -H "Authorization: Token XXX" https://gl313.com/api/taxonomia/categorias/servizos/hostalaria/aloxamento/
```

2. Engadir en `sidebar_config.json`:
```json
{
  "id": "restauracion",
  "nome": "Restauración",
  "fonte": "recursos",
  "icono_seccion": "fa-utensils",
  "activo": true,
  "taxonomia": {
    "endpoint": "taxonomia/categorias/servizos/hostalaria/restauracion/",
    "mostrar_xerarquia": true
  },
  "filtros": {...},
  "iconos_subcategorias": {...}
}
```

### Caso B: Categoría de patrimonio (sen taxonomía)

```json
{
  "id": "patrimonio-arqueolóxico",
  "nome": "Patrimonio arqueolóxico",
  "fonte": "patrimonio-material",
  "filtro_categoria": "patrimonio-arqueolóxico",
  "icono_seccion": "fa-monument",
  "activo": true,
  "filtros": {...},
  "iconos_subcategorias": {...}
}
```

---

## APIs externas utilizadas

| Endpoint | Uso |
|----------|-----|
| `GET /api/taxonomia/categorias/{path}/` | Árbore de categorías |
| `GET /api/informacion/espazos/` | Espazos (lugares) |
| `GET /api/entidades/empresas/` | Empresas |
| `GET /api/patrimonio-material/patrimonio-material/` | Patrimonio material |

**Filtros comúns:**
- `?categoria=slug` - Filtrar por categoría
- `?page_size=500` - Obter todos os resultados

---

## Ficheiros para o commit

```bash
git add backend/config/sidebar_config.json
git add backend/routes.py
git add backend/static/js/app.js
git add backend/templates/mapa.html
git add CAMBIOS_SESION.md
```

---

## Commit suxerido

```
feat(sidebar): sistema v2.1 con xerarquías de taxonomía

- Soporte para taxonomia.endpoint en sidebar_config.json
- Categorías xerárquicas con indentación visual
- Conteo correcto: cada item só conta na categoría máis específica
- Filtrado: seleccionar pai inclúe todos os fillos
- Non se mostran categorías baleiras (count == 0)
- Iconos Font Awesome dinámicos por slug

Engadir categorías = editar JSON (sen tocar código)
```

---

## Próximos pasos suxeridos

1. **Probar** o sistema reiniciando o servidor (`flask run --port 5001`)
2. **Verificar** que aloxamento mostra a xerarquía correcta
3. **Engadir máis categorías** de patrimonio se é necesario
4. **Considerar** engadir caché para reducir peticións á API
