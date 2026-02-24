# CHANGELOG - Fases do desenvolvemento

## Fase: DonutCluster visual, eliminación persistencia, fix centrado e UX

Cambios realizados:

1. DonutCluster (clustering visual por categorías)
   - backend/static/js/Leaflet.DonutCluster.js — Plugin de kalisio gardado localmente
   - backend/static/js/app.js — O cluster compartido (window.sharedCluster) agora usa L.DonutCluster en vez de L.markerClusterGroup. Os donuts mostran arcos de cor proporcional a cada sección do sidebar
   - As cores e títulos dos donuts xéranse dinámicamente desde sidebar_config.json (campo iconos_subcategorias._default.cor), non están hardcoded
   - Función buildDonutConfig() extrae cores/títulos do sidebarConfig cargado
   - Cada marcador leva seccion: seccion.id nas opcións para que o DonutCluster agrupe correctamente
2. Comportamento do DonutCluster ao premer
   - zoomToBoundsOnClick: false — premer un donut NON fai zoom
   - clusterclick → spiderfy() — premer un donut desprega os marcadores ao redor con liñas conectoras
   - spiderfyDistanceMultiplier: 1.8 para boa separación visual
3. Eliminación completa da persistencia en localStorage
   - Eliminadas funcións: gardarEstado(), restaurarEstado(), aplicarEstadoSeccions(), aplicarEstadoConcellos(), aplicarEstadoRutas(), constante STORAGE_KEY
   - Eliminadas todas as chamadas a gardarEstado() nos listeners de concellos, capas extras e marcadores
   - Ao cargar, fai localStorage.removeItem('mapa_estado') para limpar datos antigos
   - Cada recarga da páxina empeza con estado limpo: sidebar desmarcado, todas as rutas activas
4. Eliminación da URL con hash
   - Eliminadas funcións: actualizarHash(), lerHash(), inicializarHash()
   - A URL xa non engade #zoom/lat/lng ao moverse polo mapa
   - Non se restaura ningunha posición desde o hash ao recargar
5. Fix do centrado do mapa
   - actualizarCapaCamino() xa NON fai fitBounds (non move o mapa ao marcar/desmarcar rutas)
   - O fitBounds faise unha soa vez na carga inicial, despois de activar todas as rutas por defecto
   - Resultado: ao cargar → centra no camiño; ao interactuar → o mapa non se move solo
6. CSS mellorado para donuts
   - .donut-text centrado con position:absolute + transform:translate(-50%,-50%)
   - .donut-legend con sombra e bordes redondeados
   - .donut-arc:hover con cursor pointer
7. Patch visual moderno:
   - Engadida fonte Inter e paleta de cores moderna en backend/static/css/style.css
   - Bordes redondeados, sombras suaves e estilos para sidebar, clusters e marcadores
   - Preparado para integración de marcadores SVG e estilos avanzados no mapa

Ficheiros modificados:
- backend/static/js/app.js (cambios principais)
- backend/templates/mapa.html (CSS donuts, fix centrado, eliminación persistencia rutas)
- backend/static/js/Leaflet.DonutCluster.js (novo, plugin local)
- backend/static/css/style.css (paleta moderna e tipografía)

## Fase: Plataforma Multi-Proxecto e melloras de frontend

Cambios realizados:

1. Arquitectura multi-proxecto:
  - Creado backend/config/rutas_config.json para definir proxectos con capas GeoJSON, centro, zoom e filtrado por concellos
  - Creado backend/ruta_activa.py como módulo centralizado que exporta obter_proxecto_activo(), get_concellos_codigos(), debe_filtrar_concellos() e obter_capas_geojson()
  - Eliminada a carga triplicada do GeoJSON de concellos en routes.py, aloxamento.py e recursos.py — agora todos importan de ruta_activa
  - O proxecto activo contrólase coa variable de entorno PROXECTO_ACTIVO
  - Filtrado por concellos condicional: só se aplica se o proxecto o ten activo e existe o GeoJSON
2. Endpoints novos:
  - GET /api/proxecto-activo — info do proxecto en execución
  - GET /api/capas-geojson — capas predefinidas + extras auto-detectadas do cartafol static/geojson/
3. Limpeza de código:
  - Eliminado backend/static/js/app.v2.js (duplicado exacto)
  - Eliminado backend/static/js/recursos.js (módulo ES6 nunca importado)
  - Eliminado backend/templates/mapa.html--save (backup antigo)
  - Eliminado dobre fetch(urlCamino) en mapa.html
  - Eliminado window.espazosLayer non utilizado
  - Eliminado todo o código de debug (console.log, escrituras a /tmp/camino_debug.log)
  - Consolidados imports duplicados en routes.py
  - Secret key de Flask desde variable de entorno SECRET_KEY
4. Clustering de marcadores:
  - Integrado leaflet.markercluster (CDN)
  - Cluster compartido único para todas as seccións — marcadores de aloxamento, patrimonio, etc. agrúpanse xuntos cando están próximos
5. Panel de capas no sidebar:
  - Nova sección "Capas" con toggle para ocultar/mostrar concellos (polígonos + etiquetas)
  - Toggle para capas GeoJSON extras auto-detectadas
6. Busca no mapa:
  - Campo de busca no topo do sidebar con debounce
  - Busca por nome ou concello en todos os datos cargados
  - Resultados clicables que centran o mapa e abren popup
7. Persistencia de estado:
  - Garda en localStorage checkboxes activos, rutas seleccionadas, visibilidade de concellos e capas extras
  - Restaura o estado ao recargar a páxina
8. URL compartible:
  - O hash da URL actualízase ao mover o mapa (#zoom/lat/lng)
  - Ao abrir un enlace con hash, o mapa centra nesa posición
9. Documentación:
  - README.md reescrito con arquitectura multi-proxecto, táboas de endpoints e variables de entorno
  - GUIA_USO.md creada con instrucións paso a paso para engadir proxectos, capas e configurar o sistema

---

Fase: Selector de camiño no perfil de elevación (Ferrol / A Coruña)

- Engadido toggle Ferrol/A Coruña no panel de elevación (radio buttons Bootstrap)
- O perfil de elevación e as estatísticas actualízanse mostrando só o camiño seleccionado + tramos comúns (Bruma→Santiago)
- O mapa mostra ambos camiños: o seleccionado en amarelo (#ffd600, grosor 5) e o non seleccionado en gris (#888, grosor 4, opacidade 0.7, liña descontinua)
- Os checkboxes do sidebar quedan todos activos (o usuario pode desmarcar manualmente)
- O panel de elevación usa position: fixed e overflow: hidden no body para evitar scroll do navegador
- Ficheiros modificados: backend/templates/mapa.html, backend/static/js/app.js
- Commit: feat(elevación): selector Ferrol/Coruña no perfil, estilo diferenciado no mapa e panel fixed

---

Fase: Integración Valhalla e UX de rutas

Cambios realizados:

1. Selector de modo de transporte (a pé / en bici)
  - Engadido selector no popup de xeolocalización
  - Todos os cálculos de ruta aceptan parámetro modo ('pe' ou 'bici')
  - Tempos estimados diferentes: 4 km/h (pé) vs 15 km/h (bici)
  - Cores diferentes para rutas: azul (pé) vs laranxa (bici)
2. Rutas desde POIs
  - "Desde a miña posición" → ruta GPS usuario → POI
  - "Desde o camiño" → ruta punto máis próximo do camiño → POI
  - Botóns separados para cada modo (a pé / bici) nos popups
3. Panel de información de ruta centrado
  - Aparece ao calcular unha ruta
  - Mostra: distancia, tempo, modo
  - Botón X para pechar (mantén ruta)
  - Botón "Eliminar ruta" para borrar
  - Pinchar na liña da ruta reabre o panel
4. Filtro de proximidade
  - Detecta se usuario está no camiño (<500m pé, <1km bici)
  - Palidece marcadores lonxanos (>2km pé, >5km bici) ao 35% opacidade
  - Indicador visual na esquina inferior esquerda
5. Concellos sen cor de fondo
  - Eliminadas cores de fondo dos concellos
  - Só se mostran os límites administrativos

Ficheiros modificados:
- backend/valhalla.py - función request_valhalla_pedestrian_route() acepta costing
- backend/routes.py - novos endpoints /api/ruta-punto-a-punto, /api/ruta-completa-santiago con modo
- backend/templates/mapa.html - selector modo, xeolocalización mellorada
- backend/static/js/app.js - filtro proximidade, panel rutas, handlers novos

## Fase 6: Corrección nomes concellos no mapa

- Corrixido o código para mostrar os nomes dos concellos usando o campo Concello do GeoJSON (antes usábase NOME, que non existe).
- Agora as etiquetas amosan correctamente o nome de cada concello no mapa.
- Commit realizado ao pechar a corrección.

## Fase 5: UX menú hamburguesa e sidebar

- O botón hamburguesa ten agora tamaño, cor, borde, padding e radio idénticos ao selector de capas, e un icono SVG personalizado con liñas finas.
- Ao abrir o sidebar, a hamburguesa desaparece e reaparece ao pechar, evitando superposicións ou duplicidades.
- O menú lateral mantén o comportamento Bootstrap Offcanvas, sen animacións extra.
- Integración visual profesional e comportamento robusto, igual que apps modernas.
- Documentado o cambio e realizado commit ao pechar a subfase.

## Fase 4: Agrupación e visualización de tramos e recursos


### Subfase 4.x: Filtros e visualización de categorías de recursos
- Implementado sistema de filtrado para mostrar só recursos dunha categoría determinada (exemplo: "Aloxamento → Hostalaría").
- O filtro afecta tanto á visualización no mapa como á lista do sidebar.
- Sistema extensible para outras categorías e subcategorías no futuro.
- Documentada a subfase e realizado commit tras a súa finalización.

- Agrupación automática dos tramos do Camiño Inglés en Ferrol, Coruña e Outros no sidebar do mapa.
- Todos os tramos ata e03t03 (inclusive) clasifícanse como Ferrol, excluíndo explicitamente os de Coruña.
- Os tramos de Coruña clasifícanse como e01Vt01 a e01Vt05.
- O resto clasifícase como Outros.
- Corrección de duplicidades, restauración da visualización dos tramos no mapa e sincronización única da fonte de datos (fetch(urlCamino)).
- Xeración xerárquica dos tramos de Ferrol: etapa > tramo > variante.
- Para e03t01, as variantes p1 e p2 móstranse como tramos independentes, non agrupadas baixo o mesmo tramo.
- Documentación actualizada.
- Commit realizado ao rematar a fase.

## Fase 1: Estrutura inicial
- Instalación de dependencias Python (Flask, Requests, python-dotenv)
- Descarga e almacenamento do schema OpenAPI da API GALIZA
- Creación da estrutura de cartafoles e ficheiros base (backend, frontend, .env.example, README.md)
- Inicialización de git e commit inicial

## Fase 2: Esqueleto do backend
- Backend Flask inicializado en `backend/__init__.py`.
- Carga de configuración desde `.env` (API_BASE_URL, API_TOKEN).
- Endpoint de proba: `/api/ping` devolve status e mensaxe.
- Exemplo de variables de entorno en `.env.example`.
- Commit realizado ao rematar a fase.

## Fase 3.1: Proxy seguro a API externa
- Engadido endpoint `/api/empresas` en Flask que actúa como proxy seguro ao endpoint de empresas da API externa.
- Engadida autenticación por token e control de erros.
- Commit realizado ao rematar a fase.

## Fase 3.2: Paginación e filtros
- O proxy acepta parámetros de consulta do frontend e pásallos á API externa.
- A resposta devolve información de páxina (count, next, previous, page_size) e os datos.
- Commit realizado ao rematar a subfase.

## Fase 3.3: Normalización de respostas
- Unificado o formato de resposta do backend: campo success, estrutura de datos e erros normalizados.
- Inclúe status_code e detalles do erro cando corresponde.
- Commit realizado ao rematar a subfase.

## Fase 3.4: Xestión avanzada de erros
- Melloradas as mensaxes de erro: autenticación (401), parámetros incorrectos (400), API caída (502), etc.
- Documentados exemplos de resposta para cada caso no backend.
- Commit realizado ao rematar a subfase.

## Fase 3.5: Tests básicos do backend
- Engadidos tests para `/api/ping` e `/api/empresas` (erro de autenticación).
- Todos os tests pasan correctamente.
- Commit realizado ao rematar a subfase.

## Fase 3.6: Proxy xeneralizado
- O backend permite acceso seguro e normalizado a todos os recursos principais da API externa (empresas, eventos, persoas, grupos, institucións públicas, fundacións).
- Mantense autenticación, paginación, normalización e xestión de erros.
- Commit realizado ao rematar a subfase.

## Fase 3.7: Proxy xeral para calquera endpoint/método
- Implementado proxy xeral que permite acceder a calquera endpoint e método da API de gl313.com/api, sen hardcodear recursos.
- Mantense autenticación, control de erros e normalización de respostas.
- Máxima flexibilidade ante cambios na API REST externa.
- Commit realizado ao rematar a subfase.

## Fase 4.1: Estrutura modular Flask
- App Flask movida a backend/app.py, engadido blueprint en backend/routes.py, configuración separada en backend/config.py.
- Preparados cartafoles static/ e templates/ para futuro frontend.
- backend/__init__.py baleiro para indicar paquete.
- Commit realizado ao rematar a subfase.

## Fase 4.2: Carga modular de configuración
- Carga de variables de entorno desde .env ao iniciar a app.
- Configuración centralizada en backend/config.py e cargada en Flask.
- Creado .env real co token de produción e variables obrigatorias.
- Subfase completada e commit realizado.

## Fase 4.3: Blueprint principal co proxy xeral
- Toda a lóxica de rutas (proxy xeral e endpoint de proba) está separada en backend/routes.py como blueprint.
- Blueprint rexistrado na app principal en backend/app.py.
- Commit realizado ao rematar a subfase.

## Fase 4.4: Documentación da estrutura modular
- Documentada a estrutura final do backend modular en README e CHANGELOG.
- Commit realizado ao rematar a subfase.

## Fase 5.2: Creación da estrutura de templates e static (HTML base, CSS, JS)
- Creada a estrutura de cartafoles `backend/static/css`, `backend/static/js` e template base para o frontend.
- Engadidos ficheiros base: `style.css` (estilo global) e `app.js` (JS principal).
- Todo preparado para desenvolver as vistas e recursos do frontend con Flask, Bootstrap e Leaflet.

## Fase 5.3: Implementación do mapa de Leaflet como páxina de inicio (home)
- O mapa do Camiño Inglés móstrase directamente na raíz do sitio (`/`), usando Leaflet e descargando o GeoJSON dinámicamente desde a API REST (id=38).
- Eliminado texto e encabezados para mostrar só o mapa.
- Integración de Bootstrap e Leaflet no template base.
- Configurado Flask en modo debug con autorecarga para facilitar o desenvolvemento.

## Fase 5.4: Listaxe de recursos principais (empresas, patrimonio material)
- Engadidas rutas `/empresas` e `/patrimonio` para listar empresas e patrimonio material, descargando os datos da API REST.
- Templates de táboa con Bootstrap para cada recurso.
- Estrutura preparada para ampliar a outros recursos e filtrar por categorías no futuro.

### 2026-02-03 - Subfase: Endpoint local patrimonio material
- Engadido endpoint `/api/patrimonio-material` no backend Flask que actúa como proxy seguro á API REST externa de patrimonio material.
- Permite filtrar por `concello_codigo` e devolve os datos en formato JSON, replicando a estrutura da API externa.
- Validado funcionamento correcto con petición real e datos esperados.
- Listo para integración co frontend e ampliación a outros filtros.
- Commit realizado ao pechar a subfase.

Ficheiro modificado: backend/routes.py, CHANGELOG.md

## Fase 5.5: Xestión de erros e páxinas de erro personalizadas
- Engadidos templates personalizados para erros 404 e 500, integrados con Bootstrap.
- Configurado Flask para mostrar estas páxinas cando se produce un erro correspondente.
- Mellora da experiencia de usuario e coherencia visual ante erros.

## Fase 5.6: Soporte para internacionalización (i18n)
- Integrado Flask-Babel para xestión de idiomas (galego, castelán, inglés).
- Selector de idioma visible en todas as páxinas, cambio vía parámetro ?lang=.
- Estrutura preparada para traducir textos nos templates.

## Fase 5.7: Autenticación e rutas privadas con SQLite
- Engadido modelo de usuario e base de datos SQLite (backend/models.py).
- Templates e rutas para login, logout e zona privada (/login, /logout, /private).
- Decorador para rutas privadas e xestión de sesións.
- Inicialización automática da base de datos ao iniciar a app.
- Estrutura lista para xestión real de usuarios/as e ampliación futura.

## Fase 6 (planificada): Cacheo e integración de Valhalla
- **Cacheo:** O backend implementará unha capa de caché (por exemplo, Flask-Caching con Redis ou filesystem), configurable por variables de entorno (tipo, TTL, etc.), para reducir chamadas á API REST externa. A lóxica decidirá cando servir datos cacheados ou consultar a API REST. En produción, bastará cambiar a configuración do backend para usar un backend de caché axeitado (ex: Redis).
- **Valhalla:** A integración de Valhalla farase como servizo externo configurable (URL, port, etc.), lendo a configuración de variables de entorno. En desenvolvemento, apúntase ao contedor local; en produción, ao endpoint despregado. Así, a integración será transparente e non requirirá cambios de código ao despregar.
- **Notas:** Esta fase está planificada, pero non implementada. A estrutura e configuración deixaranse preparadas para facilitar a súa execución cando se aborde.

### 2026-01-29 - Fix: Babel locale decorator & SQLite DB path
- Substituído o uso do decorador @babel.locale_selector por unha función get_locale() exposta a Jinja, para compatibilidade con flask-babel en versións sen ese decorador.
- Corrixida a ruta da base de datos SQLite: models.py agora usa un camiño absoluto relativo ao módulo (backend/app.db), evitando erros de apertura/creación.

Ficheiros modificados: backend/app.py, backend/models.py, CHANGELOG.md

### 2026-01-29 - Subfase 6.1: Integración inicial de cache
- Engadida dependencia Flask-Caching ao proxecto.
- Engadidas variables de entorno CACHE_TYPE e CACHE_DEFAULT_TIMEOUT en config.py e .env.example.
- Integrada inicialización de cache en backend/app.py, lista para usar en endpoints.

Ficheiros modificados: backend/app.py, backend/config.py, .env.example, CHANGELOG.md

### 2026-01-29 - Subfase 6.1 (cont.): Aplicación de cache a endpoints e exemplos
- Engadido o decorador @current_app.cache.cached() aos endpoints principais: home (/), geojson do mapa, empresas, patrimonio.
- Comentarios e exemplos no código para facilitar a aplicación de cache a novos endpoints no futuro.
- Para cachear un novo endpoint GET, engade @current_app.cache.cached(timeout=segundos) sobre a función.

Ficheiro modificado: backend/routes.py

### 2026-01-29 - Fix: uso correcto de cache con Flask-Caching
- Creado backend/cache.py co obxecto cache reutilizable.
- Decoradores de cache nos endpoints agora usan @cache.cached() en vez de @current_app.cache.cached(), evitando erros de contexto de aplicación.
- Documentado o patrón correcto para futuros endpoints.

Ficheiros modificados: backend/app.py, backend/routes.py, backend/cache.py, CHANGELOG.md

### 2026-01-29 - Subfase 6.2: Integración inicial de Valhalla
- Engadidas variables de entorno VALHALLA_URL e VALHALLA_PORT en config.py e .env.example.
- Engadida función utilitaria para construír a URL e consultar rutas a Valhalla (backend/valhalla.py).
- Engadido endpoint POST /valhalla/route no backend para consultar rutas, configurable por variables de entorno.
- Documentado exemplo de uso e configuración.

Ficheiros modificados: backend/config.py, backend/routes.py, backend/valhalla.py, .env.example, CHANGELOG.md

### 2026-01-29 - Fase 7.1: Tests de templates/views
- Creada estrutura de tests en backend/tests/test_views.py usando pytest.
- Engadidos tests para as views principais: home (mapa), empresas, patrimonio e erro 404.
- Estes tests aseguran que as páxinas clave renderizan correctamente e conteñen os elementos esperados.
- Engadidos ficheiros __init__.py para garantir a detección de paquetes.

Ficheiros modificados: backend/tests/test_views.py, backend/tests/__init__.py, CHANGELOG.md

### 2026-01-29 - Fase 7.2: Helpers e macros Jinja2 reutilizables
- Creado ficheiro backend/templates/_macros.html con macros para táboas e mensaxes.
- Refactorizados templates empresas_list.html e patrimonio_list.html para usar macros reutilizables.
- Isto facilita a ampliación e mantemento do frontend.

Ficheiros modificados: backend/templates/_macros.html, backend/templates/empresas_list.html, backend/templates/patrimonio_list.html, CHANGELOG.md

### 2026-01-29 - Fase 8.2: Menú lateral interactivo (offcanvas)
- Engadido menú lateral Bootstrap Offcanvas ao mapa (mapa.html), accesible cun botón flotante.
- Estrutura base para selección de etapa (select) e toggles de capas adicionais (checkboxes), preparada para integración dinámica vía JS.
- O menú é responsive e non interfire co uso do mapa.
- Sentan as bases para filtrar por etapa e xestionar capas dende a UI.

Ficheiro modificado: backend/templates/mapa.html

---

### 2026-01-30 - Fase 8.5: Selector de rutas agrupado no sidebar
- Engadido dropdown "Rutas" colapsado no sidebar, con checkboxes para cada ruta do GeoJSON.
- As rutas agrúpanse en "Desde Ferrol", "Desde A Coruña" e "Tramo común" para mellor usabilidade.
- O acordeón funciona visualmente, pero non colapsa/expande por falta de integración co Offcanvas real de Bootstrap (pendente de migración).

Ficheiros modificados: backend/templates/mapa.html

### 2026-02-02 - Subfase 8.10: Popups enriquecidos en marcadores
- Os popups dos marcadores de recursos mostran agora: nome, descrición (resumo sen HTML), concello e unha ligazón "Como chegar" a Google Maps usando lat/lng.
- Eliminado o campo tipo_empresa do popup para maior claridade.
- Validado funcionamento correcto e visualización dos novos campos.
- Commit realizado ao pechar a subfase.

Ficheiros modificados: backend/static/js/app.js, CHANGELOG.md

### 2026-02-02 - Subfase 8.9: Eliminación de resultados filtrados no sidebar
- Eliminada completamente a sección de "resultados filtrados" do sidebar en mapa.html e todo o código JS asociado (funcións, listeners e referencias a resultadosFiltrados).
- Simplificado o fluxo de filtrado: agora só se mostran e filtran categorías, sen lista adicional de resultados no sidebar.
- Validado que non quedan erros JS nin referencias rotas tras a limpeza.
- Commit realizado ao pechar a subfase.

Ficheiros modificados: backend/templates/mapa.html, backend/static/js/app.js, CHANGELOG.md

### 2026-01-31 - Subfase 8.8: Filtrado combinado e limpeza de endpoints
- Sidebar permite seleccionar categorías de aloxamento e filtrar espazos en tempo real, mostrando só os resultados filtrados no sidebar.
- Eliminado o endpoint local `/patrimonio` do backend e toda referencia a patrimonio no frontend.
- Eliminada temporalmente a consulta de empresas no filtrado combinado do sidebar (só se mostran espazos).
- Validado funcionamento correcto do filtrado e visualización dos resultados.
- Commit realizado ao pechar a subfase.

Ficheiros modificados: backend/routes.py, backend/static/js/app.js, CHANGELOG.md

### 2026-01-31 - Subfase 8.7: Endpoint local de espazos
- Engadido endpoint `/espazos` no backend Flask que actúa como proxy seguro á API REST externa de espazos.
- Permite filtrar por categoría e outros parámetros vía query string, pasando sempre o token gardado en .env.
- Resposta en JSON, lista para consumo dinámico no frontend.
- Commit realizado tras validar funcionamento co token.

Ficheiros modificados: backend/routes.py, CHANGELOG.md

### 2026-01-31 - Subfase 8.6: Sidebar categorías robusto e recursivo
- Sidebar mostra correctamente toda a árbore de categorías e subcategorías de aloxamento, xeradas de forma recursiva e con sangría por nivel.
- Eliminada execución duplicada do JS e simplificada a manipulación do DOM para garantir visualización correcta dos checkboxes.
- O backend replica exactamente a estrutura da API REST para categorías, garantindo compatibilidade co frontend.
- Documentada a subfase e realizado commit tras a súa finalización.

Ficheiros modificados: backend/routes.py, backend/static/js/app.js, backend/templates/mapa.html, CHANGELOG.md

### 2026-01-30 - Fase 8.4: Correccións de responsividade e usabilidade en móbil
- Engadida etiqueta <meta name="viewport"> en base.html para garantir responsividade real en dispositivos móbiles.
- O mapa Leaflet agora só permite mover/zoom con dous dedos en móbil (previndo interaccións accidentais).
- O control de zoom móstrase no lado dereito abaixo (bottomright).
- Ocúltase só a bandeira de Leaflet (bandeira de Ucraína) mantendo o resto da atribución, mediante CSS (.leaflet-control-attribution a { display: none; }).
- Mantense toda a atribución e créditos obrigatorios.

Ficheiros modificados: backend/templates/base.html, backend/templates/mapa.html, backend/static/css/style.css, CHANGELOG.md

### 2026-01-30 - Fase 8.3: Sidebar colapsable minimalista (Bootstrap Offcanvas idéntico)
- Sidebar migrado a solución baseada en Bootstrap Offcanvas, replicando exactamente o deseño e comportamento manual previo.
- A pestana "Menú" forma parte do sidebar e permanece sempre visible, mesmo cando o panel está colapsado.
- Ao premer na pestana, o sidebar expándese ou colapsa, mantendo a UX orixinal.
- Eliminado todo o JS e CSS manual innecesario, usando só transicións CSS e control mínimo JS.
- O sidebar ocupa todo o alto da pantalla, é responsivo e non interfire co mapa.

Ficheiros modificados: backend/templates/mapa.html, backend/static/css/style.css, CHANGELOG.md


### 2026-01-29 - Fase 8.1: Descarga e filtrado de capas xeográficas
- Descargados os ficheiros GeoJSON do camiño inglés e de todos os concellos de Galiza, gardados en backend/static/geojson/.
- Filtrado e xerado o ficheiro concellos_camino_ingles.geojson con só os concellos polos que pasa o camiño inglés, usando script en backend/scripts/filtra_concellos_camino_ingles.py.
- Integradas ambas capas estáticas no mapa Leaflet da home, con estilos diferenciados e selector de mapas base (OSM, Voyager, Satélite, CartoDB Voyager, PNOA España, Acuarela, Tóner, Terreo, Alidade Smooth/Dark, Topográfico, MTN España, Claro/Escuro, Positron, National Geographic, Relevo sombreado).
- Corrixidos os endpoints para servir ficheiros estáticos sen cache adicional.
- O mapa agora é fullscreen real (100% viewport), sen navbar nin marxes, e axústase automaticamente á extensión do camiño ao cargar.
- CartoDB Voyager é a capa base por defecto.

Ficheiros modificados: backend/static/geojson/camino_ingles.geojson, backend/static/geojson/concellos_camino.geojson, backend/static/geojson/concellos_camino_ingles.geojson, backend/scripts/filtra_concellos_camino_ingles.py, backend/routes.py, backend/templates/mapa.html, backend/templates/base.html, CHANGELOG.md
## Sidebar de aloxamento

- Xerarquía correcta: categorías e fillas anidadas.
- Só se mostran categorías con contido (espazos/empresas).
- Checkboxes desmarcados por defecto.
- Evítanse duplicados na xeración.
- Filtrado por categoría funciona correctamente.

Cambios en backend/static/js/app.js.
