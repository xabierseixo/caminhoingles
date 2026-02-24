// JS principal - Sistema unificado de sidebar v2.1 (con xerarquía)

// =============================================================================
// CONFIGURACIÓN GLOBAL
// =============================================================================

window.sidebarConfig = null;    // Configuración das seccións
window.sidebarData = {};        // Datos por sección: {seccionId: {subcategorias: [], items: []}}
window.categoryMarkers = {};    // Marcadores por sección: {seccionId: [markers]}
window.markerBySlug = {};       // Acceso rápido: slug → marker (para busca)
window.sharedCluster = null;    // DonutCluster compartido para todas as seccións

// =============================================================================
// FILTRO DE PROXIMIDADE (palidecer marcadores lonxanos cando estás no camiño)
// =============================================================================

window.proximityConfig = {
  // Distancia para considerar que estás "no camiño" (metros)
  umbralNoCamino: { pe: 500, bici: 1000 },
  // Distancia para palidecer marcadores (metros)
  umbralPalidecer: { pe: 2000, bici: 5000 },
  // Opacidade para marcadores lonxanos
  opacidadeLonxanos: 0.35,
  // Estado actual
  activo: false,
  distanciaAoCamino: null,
};

// Calcular distancia haversine en metros
function haversineMetrosGlobal(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// Atopar distancia ao punto máis próximo do camiño
function calcularDistanciaAoCamino(userLat, userLng) {
  if (!window.geojsonCamino?.features) return Infinity;

  let minDist = Infinity;
  for (const feature of window.geojsonCamino.features) {
    const coords = feature.geometry?.coordinates || [];
    for (const line of coords) {
      // Comprobar cada 10 puntos para rapidez (o camiño ten moitos puntos)
      for (let i = 0; i < line.length; i += 10) {
        const coord = line[i];
        const dist = haversineMetrosGlobal(userLat, userLng, coord[1], coord[0]);
        if (dist < minDist) minDist = dist;
      }
    }
  }
  return minDist;
}

// Aplicar filtro de opacidade aos marcadores segundo proximidade
function aplicarFiltroProximidade() {
  if (!window.userPosition || !window.sharedCluster) return;

  const modo = window.modoRutaActual || 'pe';
  const umbralCamino = window.proximityConfig.umbralNoCamino[modo];
  const umbralPalidecer = window.proximityConfig.umbralPalidecer[modo];
  const opacidadeLonxanos = window.proximityConfig.opacidadeLonxanos;

  // Calcular distancia ao camiño
  const distAoCamino = calcularDistanciaAoCamino(
    window.userPosition.lat,
    window.userPosition.lng
  );
  window.proximityConfig.distanciaAoCamino = distAoCamino;

  // Se estamos lonxe do camiño, mostrar todo normal
  if (distAoCamino > umbralCamino) {
    window.proximityConfig.activo = false;
    resetearOpacidadeMarcadores();
    actualizarIndicadorProximidade(false, distAoCamino);
    return;
  }

  // Estamos no camiño: aplicar filtro
  window.proximityConfig.activo = true;
  actualizarIndicadorProximidade(true, distAoCamino);

  // Percorrer todos os marcadores e axustar opacidade
  for (const seccionId of Object.keys(window.categoryMarkers)) {
    const markers = window.categoryMarkers[seccionId] || [];
    markers.forEach(marker => {
      const pos = marker.getLatLng();
      const distAoUsuario = haversineMetrosGlobal(
        window.userPosition.lat, window.userPosition.lng,
        pos.lat, pos.lng
      );

      const icon = marker.getIcon();
      if (icon && icon.options) {
        if (distAoUsuario > umbralPalidecer) {
          // Lonxano: palidecer
          marker.setOpacity(opacidadeLonxanos);
        } else {
          // Próximo: opacidade normal
          marker.setOpacity(1);
        }
      }
    });
  }

  // Refrescar cluster
  if (window.sharedCluster.refreshClusters) {
    window.sharedCluster.refreshClusters();
  }
}

// Resetear opacidade de todos os marcadores
function resetearOpacidadeMarcadores() {
  for (const seccionId of Object.keys(window.categoryMarkers)) {
    const markers = window.categoryMarkers[seccionId] || [];
    markers.forEach(marker => marker.setOpacity(1));
  }
  if (window.sharedCluster?.refreshClusters) {
    window.sharedCluster.refreshClusters();
  }
}

// Mostrar indicador de proximidade na UI
function actualizarIndicadorProximidade(noCamino, distancia) {
  let indicador = document.getElementById('proximityIndicator');

  if (!indicador) {
    // Crear indicador se non existe
    indicador = document.createElement('div');
    indicador.id = 'proximityIndicator';
    indicador.style.cssText = `
      position: fixed;
      bottom: 70px;
      left: 10px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 0.8em;
      font-weight: 500;
      z-index: 1000;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      transition: all 0.3s ease;
    `;
    document.body.appendChild(indicador);
  }

  const modo = window.modoRutaActual || 'pe';
  const modoIcon = modo === 'bici' ? '🚴' : '🚶';
  const distanciaKm = (distancia / 1000).toFixed(1);

  if (noCamino) {
    indicador.style.background = '#4CAF50';
    indicador.style.color = '#fff';
    indicador.innerHTML = `${modoIcon} No camiño <small>(${distanciaKm}km)</small>`;
    indicador.title = `Mostrando POIs próximos. Modo: ${modo === 'bici' ? 'bicicleta' : 'a pé'}`;
  } else {
    indicador.style.background = 'rgba(255,255,255,0.95)';
    indicador.style.color = '#666';
    indicador.innerHTML = `${modoIcon} ${distanciaKm}km do camiño`;
    indicador.title = 'Mostrando todos os POIs';
  }
}

// =============================================================================
// LIMPAR RUTAS DE "COMO CHEGAR" (non afecta á ruta de Santiago)
// =============================================================================

// Comprobar se hai rutas de navegación activas
function hayRutasNavegacion() {
  return !!(window.rutaAoCaminoLayer || window.rutaDesdeAquiLayer);
}

// Limpar rutas de navegación (como chegar a un punto)
function limparRutasNavegacion() {
  if (window.rutaAoCaminoLayer) {
    window.map.removeLayer(window.rutaAoCaminoLayer);
    window.rutaAoCaminoLayer = null;
  }
  if (window.rutaDesdeAquiLayer) {
    window.map.removeLayer(window.rutaDesdeAquiLayer);
    window.rutaDesdeAquiLayer = null;
  }
  window.rutaActiva = null;
}

// =============================================================================
// POPUP ÚNICO — os resultados engádense DENTRO do popup orixinal
// Usa popup.setContent() de Leaflet para persistir o contido entre aperturas.
// Non depende de querySelector nin do estado do DOM.
// =============================================================================

window.rutaActiva = null; // { source, html }

// Xera só o HTML dos resultados (vai dentro de .popup-resultado-ruta)
function xerarResultadoHtml(info) {
  const modo = info.modo || 'pe';
  const modoIcon = modo === 'bici' ? 'fa-bicycle' : 'fa-person-walking';
  const modoNome = modo === 'bici' ? 'En bici' : 'A pé';

  let html = `<div class="mt-2 pt-2 border-top" style="font-size:0.9em">
    <div style="font-weight:600;color:#333;margin-bottom:4px">
      <i class="fa-solid fa-route me-1"></i>${info.tipo}
    </div>
    <div style="display:flex;gap:15px;margin:4px 0">
      <div>
        <span style="color:#888;font-size:0.85em">Dist. </span>
        <span style="font-weight:700;color:#1976D2">${info.distancia_km} km</span>
      </div>
      <div>
        <span style="color:#888;font-size:0.85em">Tempo </span>
        <span style="font-weight:700;color:#4CAF50">${info.tempoTexto}</span>
      </div>
    </div>
    <div style="color:#666;margin-bottom:2px">
      <i class="fa-solid ${modoIcon} me-1"></i>${modoNome}
    </div>`;

  if (info.orixeNome) {
    html += `<div style="font-size:0.85em"><b>Orixe:</b> ${info.orixeNome}</div>`;
  }
  if (info.desnivel_positivo !== undefined) {
    html += `<div style="font-size:0.85em"><b>D+:</b> ${info.desnivel_positivo}m | <b>D-:</b> ${info.desnivel_negativo}m</div>`;
  }
  if (info.diasEstimados) {
    html += `<div style="font-size:0.85em;color:#555">~${info.diasEstimados} días</div>`;
  }

  html += `<button class="btn btn-sm btn-outline-danger w-100 mt-2 btn-limpar-ruta-popup">
    <i class="fa-solid fa-trash me-1"></i>Limpar ruta
  </button>
  </div>`;

  return html;
}

// Inxecta resultados no popup usando a API de Leaflet (setContent).
// Funciona sempre: popup aberto, pechado, antes ou despois de fitBounds.
function inxectarResultadosEnPopup(source, resultadoHtml) {
  if (!source) return;
  const popup = source.getPopup();
  if (!popup) return;

  // Gardar o contido orixinal (sen resultados) a primeira vez
  if (!popup._orixinalContent) {
    popup._orixinalContent = popup.getContent();
  }

  // Construír contido novo: orixinal + resultados dentro do placeholder
  let contido = popup._orixinalContent;

  // Preservar o modo pe/bici seleccionado
  const modo = window.modoRutaActual || 'pe';
  if (modo === 'bici') {
    contido = contido
      .replace('id="modoPe" value="pe" checked', 'id="modoPe" value="pe"')
      .replace('id="modoBici" value="bici"', 'id="modoBici" value="bici" checked');
  }

  contido = contido.replace(
    '<div class="popup-resultado-ruta"></div>',
    '<div class="popup-resultado-ruta">' + resultadoHtml + '</div>'
  );

  popup.setContent(contido);
}

// Limpar ruta e restaurar o popup orixinal
function limparRutaDesdePopup() {
  if (window.rutaActiva && window.rutaActiva.source) {
    const popup = window.rutaActiva.source.getPopup();
    if (popup && popup._orixinalContent) {
      popup.setContent(popup._orixinalContent);
      delete popup._orixinalContent;
    }
  }
  limparRutasNavegacion(); // pon rutaActiva = null e elimina capas
}

// Handler: botón "Limpar ruta"
document.addEventListener('click', (e) => {
  if (e.target.closest('.btn-limpar-ruta-popup')) {
    limparRutaDesdePopup();
  }
});

// Constrúe o mapa de cores e títulos para o DonutCluster a partir do sidebarConfig
function buildDonutConfig() {
  const colors = {};
  const titles = {};
  if (window.sidebarConfig?.seccions) {
    const fallback = ['#4a90d9','#8b0000','#228b22','#666','#e6a800','#9c27b0','#ff5722','#009688'];
    window.sidebarConfig.seccions.forEach((s, i) => {
      colors[s.id] = s.iconos_subcategorias?._default?.cor || fallback[i % fallback.length];
      titles[s.id] = s.nome;
    });
  }
  return { colors, titles };
}

// =============================================================================
// =============================================================================
// POSTS
// =============================================================================

let postLayer = null;
window._postLayerAdded = false;

function crearMarkerPost(post) {
  const icon = L.divIcon({
    className: '',
    html: `<div style="background:#6c63ff;color:#fff;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.25);font-size:1em;">
             <i class="fa-solid fa-pen-to-square"></i>
           </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
  const m = L.marker([post.lat, post.lng], {icon});
  const estrelasHtml = post.puntuacion ? '★'.repeat(post.puntuacion) : '';
  const poiHtml = post.poi_slug ? `<div class="text-muted small"><i class="fa-solid fa-location-dot me-1"></i>${post.poi_slug}</div>` : '';
  m.bindPopup(`
    <div style="min-width:180px;">
      <b class="text-primary">@${post.username}</b>
      <span class="text-muted small ms-1">${(post.created_at || '').slice(0,10)}</span>
      ${poiHtml}
      <p class="mb-1 mt-1">${post.contido}</p>
      ${estrelasHtml ? `<span class="text-warning">${estrelasHtml}</span>` : ''}
    </div>`);
  return m;
}

async function cargarPostsMapa() {
  if (!window.map) return;
  if (!postLayer) postLayer = L.layerGroup();
  try {
    const r = await fetch('/api/posts');
    const d = await r.json();
    postLayer.clearLayers();
    (d.posts || []).forEach(p => postLayer.addLayer(crearMarkerPost(p)));
    if (!window._postLayerAdded) {
      postLayer.addTo(window.map);
      window._postLayerAdded = true;
    }
  } catch(e) {}
}

// Contexto activo do modal (post libre ou vinculado a un POI)
let _postContexto = null;

// Abre o modal de post. contexto opcional: {poi_slug, lat, lng, nome}
function abrirModalPost(contexto) {
  const modalEl = document.getElementById('modalPost');
  if (!modalEl) return;
  _postContexto = contexto || null;

  const label = document.getElementById('postLocLabel');
  const titulo = document.getElementById('modalPostLabel');
  document.getElementById('postContido').value = '';
  document.getElementById('postErro').style.display = 'none';
  document.getElementById('postPublico').checked = true;

  if (_postContexto) {
    // Post sobre un POI: coordenadas fixas, etiqueta do lugar
    titulo.innerHTML = `<i class="fa-solid fa-pen-to-square me-1 text-primary"></i>Escribir sobre <b>${_postContexto.nome}</b>`;
    label.innerHTML = `<i class="fa-solid fa-location-dot me-1 text-primary"></i>${_postContexto.nome}`;
  } else {
    // Post libre: capturar GPS
    titulo.innerHTML = '<i class="fa-solid fa-pen-to-square me-1 text-primary"></i>Publicar no camiño';
    label.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Obtendo posición...';
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          _postContexto = {lat: pos.coords.latitude, lng: pos.coords.longitude};
          label.innerHTML = '<i class="fa-solid fa-location-dot me-1 text-success"></i>Posición obtida';
        },
        () => {
          if (window.map) {
            const c = window.map.getCenter();
            _postContexto = {lat: c.lat, lng: c.lng};
            label.innerHTML = '<i class="fa-solid fa-map-pin me-1 text-warning"></i>Usando centro do mapa';
          } else {
            label.innerHTML = '<i class="fa-solid fa-location-slash me-1 text-muted"></i>Sen posición';
          }
        },
        {timeout: 8000, maximumAge: 60000}
      );
    } else if (window.map) {
      const c = window.map.getCenter();
      _postContexto = {lat: c.lat, lng: c.lng};
      label.innerHTML = '<i class="fa-solid fa-map-pin me-1 text-warning"></i>Usando centro do mapa';
    }
  }

  bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

function inicializarPosts() {
  const btnNovo = document.getElementById('btnNuevoPost');
  const btnEnviar = document.getElementById('btnEnviarPost');
  if (!btnNovo || !btnEnviar) return;  // non autenticado

  // Botón ✏️ flotante → post libre
  btnNovo.addEventListener('click', () => abrirModalPost(null));

  btnEnviar.addEventListener('click', async () => {
    const contido = document.getElementById('postContido').value.trim();
    const erroDiv = document.getElementById('postErro');
    erroDiv.style.display = 'none';

    if (!contido) {
      erroDiv.textContent = 'Escribe algo antes de publicar.';
      erroDiv.style.display = '';
      return;
    }

    const publico = document.getElementById('postPublico').checked;
    btnEnviar.disabled = true;
    btnEnviar.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Publicando...';

    const ctx = _postContexto || {};
    try {
      const r = await fetch('/api/posts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          contido,
          lat: ctx.lat ?? null,
          lng: ctx.lng ?? null,
          poi_slug: ctx.poi_slug ?? null,
          visibilidade: publico ? 'publico' : 'privado',
        }),
      });
      const d = await r.json();
      if (r.ok && d.ok) {
        bootstrap.Modal.getInstance(document.getElementById('modalPost')).hide();
        if (d.lat && d.lng && window.map) {
          if (!postLayer) postLayer = L.layerGroup();
          postLayer.addLayer(crearMarkerPost(d));
          if (!window._postLayerAdded) {
            postLayer.addTo(window.map);
            window._postLayerAdded = true;
          }
        }
      } else {
        erroDiv.textContent = d.erro || 'Erro ao publicar. Inténtao de novo.';
        erroDiv.style.display = '';
      }
    } catch {
      erroDiv.textContent = 'Erro de conexión.';
      erroDiv.style.display = '';
    } finally {
      btnEnviar.disabled = false;
      btnEnviar.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i>Publicar';
    }
  });

  // Cargar posts existentes no mapa
  cargarPostsMapa();
}

// =============================================================================
// INICIALIZACIÓN
// =============================================================================

window.addEventListener('DOMContentLoaded', async () => {
  // Limpar estado antigo de localStorage (xa non se usa)
  try { localStorage.removeItem('mapa_estado'); } catch(e) {}

  await inicializarCapas();
  await inicializarSidebar();
  inicializarBusca();
  inicializarPosts();
});

async function inicializarSidebar() {
  try {
    // 1. Cargar configuración
    const resp = await fetch('/api/sidebar-config');
    window.sidebarConfig = await resp.json();

    if (!window.sidebarConfig?.seccions?.length) {
      console.error('Configuración de sidebar inválida');
      return;
    }

    // 2. Construír HTML do sidebar
    construirSidebarHTML();

    // 3. Cargar datos para cada sección
    for (const seccion of window.sidebarConfig.seccions) {
      await cargarSeccion(seccion);
    }

  } catch(e) {
    console.error('Erro inicializando sidebar:', e);
  }
}

// =============================================================================
// CONSTRUCIÓN DO SIDEBAR HTML
// =============================================================================

function construirSidebarHTML() {
  const accordion = document.getElementById('sidebarAccordion');
  if (!accordion) return;

  window.sidebarConfig.seccions.forEach(seccion => {
    // Non crear se xa existe
    if (document.getElementById(`${seccion.id}Checkboxes`)) return;

    const iconHtml = seccion.icono_seccion
      ? `<i class="fa-solid ${seccion.icono_seccion} me-2"></i>`
      : '';

    const item = document.createElement('div');
    item.className = 'accordion-item';
    item.innerHTML = `
      <h2 class="accordion-header">
        <button class="accordion-button collapsed" type="button"
                data-bs-toggle="collapse" data-bs-target="#collapse-${seccion.id}">
          ${iconHtml}${seccion.nome}
        </button>
      </h2>
      <div id="collapse-${seccion.id}" class="accordion-collapse collapse"
           data-bs-parent="#sidebarAccordion">
        <div class="accordion-body p-2" id="${seccion.id}Checkboxes">
          <div class="text-muted small">Cargando...</div>
        </div>
      </div>
    `;
    accordion.appendChild(item);
  });
}

// =============================================================================
// CARGA DE DATOS (ENDPOINT UNIFICADO)
// =============================================================================

async function cargarSeccion(seccion) {
  const container = document.getElementById(`${seccion.id}Checkboxes`);
  if (!container) return;

  container.innerHTML = '<div class="text-muted small">Cargando categorías...</div>';

  try {
    // Chamar ao endpoint unificado
    const resp = await fetch(`/api/sidebar-data/${seccion.id}`);
    const data = await resp.json();

    if (data.error) {
      container.innerHTML = `<div class="text-danger small">${data.error}</div>`;
      return;
    }

    // Gardar datos
    window.sidebarData[seccion.id] = data;

    if (!data.subcategorias?.length) {
      container.innerHTML = '<div class="text-muted small">Non hai contido nesta zona.</div>';
      return;
    }

    // Renderizar checkboxes (con soporte para xerarquía)
    renderizarCheckboxes(container, data.subcategorias, seccion, data.taxonomia);

  } catch(e) {
    container.innerHTML = '<div class="text-danger small">Erro ao cargar.</div>';
    console.error(`Erro cargando ${seccion.id}:`, e);
  }
}

// =============================================================================
// RENDERIZADO DE CHECKBOXES (CON XERARQUÍA)
// =============================================================================

function renderizarCheckboxes(container, subcategorias, seccion, esXerarquico = false) {
  container.innerHTML = '';
  const mostrarContador = window.sidebarConfig.configuracion_global?.mostrar_contador !== false;

  // Función recursiva para renderizar con indentación
  function renderizarNivel(cats, nivel = 0) {
    cats.forEach(subcat => {
      const div = document.createElement('div');
      div.className = 'form-check';
      if (nivel > 0) {
        div.style.marginLeft = `${nivel * 16}px`;
      }

      const chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.className = 'form-check-input';
      chk.value = subcat.slug;
      chk.id = `chk-${seccion.id}-${subcat.slug}`;
      // Gardar os slugs dos fillos para filtrar despois
      if (subcat.children?.length) {
        chk.dataset.childrenSlugs = JSON.stringify(obterTodosSlugsFillo(subcat));
      }

      const lbl = document.createElement('label');
      lbl.className = 'form-check-label';
      lbl.htmlFor = chk.id;

      // Mostrar contador se está activo
      if (mostrarContador && subcat.count !== undefined) {
        lbl.textContent = `${subcat.nome} (${subcat.count})`;
      } else {
        lbl.textContent = subcat.nome;
      }

      // Icono para categorías con fillos
      if (subcat.children?.length) {
        const iconSpan = document.createElement('i');
        iconSpan.className = 'fa-solid fa-caret-right ms-1 text-muted';
        iconSpan.style.fontSize = '0.8em';
        lbl.appendChild(iconSpan);
      }

      div.appendChild(chk);
      div.appendChild(lbl);
      container.appendChild(div);

      // Listener
      chk.addEventListener('change', () => filtrarSeccion(seccion));

      // Renderizar fillos recursivamente
      if (subcat.children?.length) {
        renderizarNivel(subcat.children, nivel + 1);
      }
    });
  }

  renderizarNivel(subcategorias);

  // Total (calculado de forma plana)
  const total = contarItemsTotais(subcategorias);
  if (total > 0) {
    const totalDiv = document.createElement('div');
    totalDiv.className = 'text-muted small mt-2 border-top pt-2';
    totalDiv.textContent = `Total: ${total} elementos`;
    container.appendChild(totalDiv);
  }
}

// Función auxiliar para obter todos os slugs dos fillos (recursivo)
function obterTodosSlugsFillo(cat) {
  let slugs = [];
  if (cat.children) {
    for (const child of cat.children) {
      slugs.push(child.slug);
      slugs = slugs.concat(obterTodosSlugsFillo(child));
    }
  }
  return slugs;
}

// Función para contar items totais (evitar contar dúas veces por xerarquía)
function contarItemsTotais(subcategorias) {
  let total = 0;
  function contar(cats) {
    for (const cat of cats) {
      total += cat.count_propio || cat.count || 0;
      if (cat.children) {
        // Se ten count_propio, os fillos xa están contados á parte
        if (!cat.count_propio) {
          contar(cat.children);
        }
      }
    }
  }
  // Para xerarquía, sumar só os count_propio
  // Para modo plano, sumar count
  const esXerarquico = subcategorias.some(s => s.children?.length > 0);
  if (esXerarquico) {
    // Sumar count do nivel superior (xa inclúe fillos)
    return subcategorias.reduce((sum, s) => sum + (s.count || 0), 0);
  } else {
    return subcategorias.reduce((sum, s) => sum + (s.count || 0), 0);
  }
}

// =============================================================================
// FILTRADO E MARCADORES
// =============================================================================

function filtrarSeccion(seccion) {
  const container = document.getElementById(`${seccion.id}Checkboxes`);
  if (!container) return;

  // Obter checkboxes seleccionados e os seus fillos
  const checkedInputs = Array.from(container.querySelectorAll('input:checked'));
  let slugsAFiltrar = [];

  checkedInputs.forEach(chk => {
    slugsAFiltrar.push(chk.value);
    // Engadir tamén os slugs dos fillos
    if (chk.dataset.childrenSlugs) {
      try {
        const childSlugs = JSON.parse(chk.dataset.childrenSlugs);
        slugsAFiltrar = slugsAFiltrar.concat(childSlugs);
      } catch(e) {}
    }
  });

  // Eliminar duplicados
  slugsAFiltrar = [...new Set(slugsAFiltrar)];

  // Inicializar DonutCluster compartido (unha soa vez)
  if (!window.sharedCluster) {
    const cfg = buildDonutConfig();
    window.sharedCluster = L.DonutCluster(
      {
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: false,
        chunkedLoading: true,
        spiderfyDistanceMultiplier: 1.8,
        spiderLegPolylineOptions: { weight: 1.5, color: '#888', opacity: 0.6 }
      },
      {
        key: 'seccion',
        arcColorDict: cfg.colors,
        title: cfg.titles,
        style: function(points) {
          var count = points.length, size, weight;
          if (count < 10) { size = 40; weight = 8; }
          else if (count < 100) { size = 50; weight = 10; }
          else { size = 60; weight = 12; }
          return { size: size, weight: weight, fill: 'rgba(255,255,255,0.85)', opacity: 0.85 };
        }
      }
    );
    // Ao premer un donut, despegar os marcadores (spiderfy) en vez de facer zoom
    window.sharedCluster.on('clusterclick', function(e) {
      e.layer.spiderfy();
    });
    if (window.map) window.sharedCluster.addTo(window.map);
  }

  // Eliminar marcadores anteriores desta sección
  if (window.categoryMarkers[seccion.id]) {
    window.categoryMarkers[seccion.id].forEach(m => {
      if (m.options.slug) delete window.markerBySlug[m.options.slug];
      window.sharedCluster.removeLayer(m);
    });
  }
  window.categoryMarkers[seccion.id] = [];

  if (!slugsAFiltrar.length) return;

  // Filtrar items polos slugs (incluíndo fillos)
  const data = window.sidebarData[seccion.id];
  if (!data?.items) return;

  const itemsFiltrados = data.items.filter(item => {
    // Obter todos os slugs do item
    const itemSlugs = new Set();

    // Desde breadcrumbs
    for (const bc of item.categorias_breadcrumbs || []) {
      for (const cat of bc) {
        if (cat.slug) itemSlugs.add(cat.slug);
      }
    }

    // Desde categorias_list
    for (const cat of item.categorias_list || []) {
      if (cat.slug) itemSlugs.add(cat.slug);
    }

    // Comprobar se algún slug coincide
    return slugsAFiltrar.some(slug => itemSlugs.has(slug));
  });

  // Mostrar marcadores
  mostrarMarcadores(itemsFiltrados, seccion);
}

// Activa unha sección programaticamente (desde busca): marca todos os checkboxes e mostra marcadores.
// Require que window.sidebarData[seccionId] xa estea cargado (cárgase ao inicio para todas as seccións).
function activarSeccion(seccionId) {
  const seccion = window.sidebarConfig?.seccions?.find(s => s.id === seccionId);
  if (!seccion || !window.sidebarData[seccionId]) return;

  // Marcar todos os checkboxes da sección
  const container = document.getElementById(`${seccionId}Checkboxes`);
  if (container) {
    container.querySelectorAll('input[type=checkbox]').forEach(chk => { chk.checked = true; });
  }

  // Expandir o acordeón para que o usuario vexa a sección activa
  const collapseEl = document.getElementById(`collapse-${seccionId}`);
  if (collapseEl && !collapseEl.classList.contains('show') && window.bootstrap) {
    bootstrap.Collapse.getOrCreateInstance(collapseEl).show();
  }

  filtrarSeccion(seccion);
}

function mostrarMarcadores(items, seccion) {
  if (!window.map || !window.sharedCluster) {
    setTimeout(() => mostrarMarcadores(items, seccion), 200);
    return;
  }

  const iconos = seccion.iconos_subcategorias || {};
  const defaultIcon = iconos['_default'] || { icon: 'fa-map-marker', cor: '#333' };

  items.forEach(item => {
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lng);
    if (isNaN(lat) || isNaN(lng)) return;

    // Determinar icono buscando nos slugs do item
    let iconConfig = defaultIcon;

    // Buscar nos breadcrumbs (máis específico primeiro)
    for (const bc of item.categorias_breadcrumbs || []) {
      // Buscar de máis específico a menos específico
      for (let i = bc.length - 1; i >= 0; i--) {
        if (bc[i]?.slug && iconos[bc[i].slug]) {
          iconConfig = iconos[bc[i].slug];
          break;
        }
      }
      if (iconConfig !== defaultIcon) break;
    }

    // Se non atopamos, buscar en categorias_list
    if (iconConfig === defaultIcon) {
      for (const cat of item.categorias_list || []) {
        if (cat.slug && iconos[cat.slug]) {
          iconConfig = iconos[cat.slug];
          break;
        }
      }
    }

    const icon = L.divIcon({
      html: `<div style="
          width:32px;height:32px;border-radius:50%;
          background:${iconConfig.cor};
          border:2px solid rgba(255,255,255,0.9);
          display:flex;align-items:center;justify-content:center;
          box-shadow:0 1px 5px rgba(0,0,0,0.35);
        "><i class="fa-solid ${iconConfig.icon}" style="color:#fff;font-size:13px;line-height:1"></i></div>`,
      className: 'marker-modern',
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([lat, lng], { icon, title: item.nome || item.slug, seccion: seccion.id, slug: item.slug });

    // Popup
    const nome = item.nome || item.name || item.slug;
    const concello = item.concello_nome || '';
    const tipo = item.tipo_empresa || '';
    // Mostrar descrición completa se existe, sen truncar
    let descricionHtml = '';
    // Non mostrar resumo nunca, só descrición vía fetch




    marker.bindPopup(`
      <div class="popup-modern" style="min-width:220px" id="popup-${item.slug}">
        <b style="font-size:1.5em;color:#222">${nome}</b><br>
        <b style=\"color:#888\">Concello:</b> ${concello}<br>
        ${item.foto_principal_url ? `<img src='${item.foto_principal_url}' alt='Foto principal' style='width:100%;max-height:120px;object-fit:cover;margin:6px 0 6px 0;border-radius:6px;'>` : ''}
        ${tipo ? `<span class=\"badge bg-primary\" style=\"background:#4a90e2\">${tipo}</span><br>` : ''}
        <div class=\"popup-descricion\" style=\"max-height:120px;overflow:auto;margin:4px 0 8px 0;\"></div>
        ${window.currentUser ? `<div class=\"popup-accions-usuario mt-2 mb-1 d-flex gap-1\">
          <button class=\"btn btn-sm btn-outline-primary flex-grow-1 btn-publicar-poi\"
            data-slug=\"${item.slug}\" data-lat=\"${lat}\" data-lng=\"${lng}\" data-nome=\"${nome.replace(/"/g,'&quot;')}\">
            <i class=\"fa-solid fa-pen-to-square me-1\"></i>Escribir
          </button>
          <div class=\"popup-checkin-area flex-grow-1\">
            <button class=\"btn btn-sm btn-outline-success w-100 btn-checkin\" data-slug=\"${item.slug}\" data-lat=\"${lat}\" data-lng=\"${lng}\">
              <i class=\"fa-solid fa-stamp me-1\"></i>Check-in
            </button>
          </div>
        </div>` : ''}
        <div class="accordion accordion-flush" id="popup-accordion-${item.slug}">
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button p-1" type="button" data-bs-toggle="collapse" data-bs-target="#como-${item.slug}" aria-expanded="true" aria-controls="como-${item.slug}" style="font-size: 0.5em;font-weight:600;">
                Como chegar
              </button>
            </h2>
            <div id="como-${item.slug}" class="accordion-collapse collapse">
              <div class="accordion-body p-2" style="font-size:2em;">
                <div class=\"popup-resultado-ruta\"></div>
                <div class=\"mt-2 pt-2 border-top\" style=\"font-size: 0.5em;\">
                  <div class=\"text-muted mb-1\"><i class=\"fa-solid fa-location-crosshairs me-1\"></i>Desde a miña posición:</div>
                  <div class=\"btn-group btn-group-sm w-100 mb-2\">
                    <button class=\"btn btn-outline-success btn-ruta-desde-aqui\" data-lat=\"${lat}\" data-lng=\"${lng}\" data-modo=\"pe\" title=\"Ruta a pé desde onde estou\">
                      <i class=\"fa-solid fa-person-walking\"></i> A pé
                    </button>
                    <button class=\"btn btn-outline-success btn-ruta-desde-aqui\" data-lat=\"${lat}\" data-lng=\"${lng}\" data-modo=\"bici\" title=\"Ruta en bici desde onde estou\">
                      <i class=\"fa-solid fa-bicycle\"></i> Bici
                    </button>
                  </div>
                  <div class=\"text-muted mb-1\"><i class=\"fa-solid fa-route me-1\"></i>Desde o camiño:</div>
                  <div class=\"btn-group btn-group-sm w-100\">
                    <button class=\"btn btn-outline-primary btn-ruta-camino\" data-lat=\"${lat}\" data-lng=\"${lng}\" data-modo=\"pe\" title=\"Ruta a pé desde o camiño\">
                      <i class=\"fa-solid fa-person-walking\"></i> A pé
                    </button>
                    <button class=\"btn btn-outline-warning btn-ruta-camino\" data-lat=\"${lat}\" data-lng=\"${lng}\" data-modo=\"bici\" title=\"Ruta en bici desde o camiño\">
                      <i class=\"fa-solid fa-bicycle\"></i> Bici
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `);

    marker.on('popupopen', async function(e) {
      if (window.map && e.target && e.target.getLatLng) window.map.panTo(e.target.getLatLng(), {animate:true, duration:0.5});
      try {
        const popupDiv = document.getElementById(`popup-${item.slug}`);
        if (!popupDiv) return;

        // Cargar descrición (só a primeira vez)
        if (!popupDiv.dataset.detalleCargado) {
          const descrDiv = popupDiv.querySelector('.popup-descricion');
          if (descrDiv) {
            descrDiv.innerHTML = '<span class="text-muted">Cargando descrición...</span>';
            const resp = await fetch(`/api/patrimonio-material/${item.slug}`);
            popupDiv.dataset.detalleCargado = '1';
            if (resp.ok) {
              const detalle = await resp.json();
              descrDiv.innerHTML = detalle.descricion || '';
            } else {
              descrDiv.innerHTML = '';
            }
          }
        }

        // Publicar sobre este POI (sen proximidade)
        const btnPublicar = popupDiv.querySelector('.btn-publicar-poi');
        if (btnPublicar && !btnPublicar.dataset.listenerOk) {
          btnPublicar.dataset.listenerOk = '1';
          btnPublicar.addEventListener('click', () => {
            abrirModalPost({
              poi_slug: btnPublicar.dataset.slug,
              lat: parseFloat(btnPublicar.dataset.lat),
              lng: parseFloat(btnPublicar.dataset.lng),
              nome: btnPublicar.dataset.nome,
            });
          });
        }

        // Check-in: engadir listener ao botón
        const btnCheckin = popupDiv.querySelector('.btn-checkin');
        if (btnCheckin && !btnCheckin.dataset.listenerOk) {
          btnCheckin.dataset.listenerOk = '1';
          btnCheckin.addEventListener('click', async () => {
            const area = popupDiv.querySelector('.popup-checkin-area');

            // Paso 1: obter posición GPS
            btnCheckin.disabled = true;
            btnCheckin.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Obtendo posición...';

            let pos;
            try {
              pos = await new Promise((resolve, reject) =>
                navigator.geolocation.getCurrentPosition(resolve, reject, {timeout: 10000, maximumAge: 60000})
              );
            } catch {
              btnCheckin.disabled = false;
              btnCheckin.innerHTML = '<i class="fa-solid fa-location-slash me-1"></i>Activa a xeolocalización';
              return;
            }

            // Paso 2: comprobar proximidade (300 m)
            const UMBRAL_M = 300;
            const dist = Math.round(haversineMetrosGlobal(pos.coords.latitude, pos.coords.longitude, lat, lng));
            if (dist > UMBRAL_M) {
              btnCheckin.disabled = false;
              btnCheckin.className = 'btn btn-sm btn-warning w-100';
              btnCheckin.innerHTML = `<i class="fa-solid fa-location-dot me-1"></i>Estás a ${dist} m · Aproxímate`;
              return;
            }

            // Paso 3: mostrar formulario de reseña
            if (area) {
              area.innerHTML = `
                <div class="border-top pt-2 mt-1">
                  <div class="d-flex gap-2 justify-content-center mb-2 checkin-stars">
                    ${[1,2,3,4,5].map(n =>
                      `<i class="fa-regular fa-star fa-xl text-warning" data-val="${n}" style="cursor:pointer" title="${n} estrela${n>1?'s':''}"></i>`
                    ).join('')}
                  </div>
                  <textarea class="form-control form-control-sm mb-2 checkin-resena"
                    placeholder="Deixa a túa reseña (opcional)..." rows="2" maxlength="500"></textarea>
                  <button class="btn btn-sm btn-success w-100 btn-confirmar-checkin">
                    <i class="fa-solid fa-stamp me-1"></i>Confirmar check-in
                  </button>
                </div>`;

              // Interacción de estrelas
              let puntuacion = 0;
              const estrelas = area.querySelectorAll('.checkin-stars i');
              const actualizarEstrelas = (val) => {
                estrelas.forEach((s, i) => {
                  s.className = `fa-${i < val ? 'solid' : 'regular'} fa-star fa-xl text-warning`;
                  s.style.cursor = 'pointer';
                });
              };
              estrelas.forEach(s => {
                s.addEventListener('click', () => { puntuacion = parseInt(s.dataset.val); actualizarEstrelas(puntuacion); });
                s.addEventListener('mouseover', () => actualizarEstrelas(parseInt(s.dataset.val)));
                s.addEventListener('mouseout', () => actualizarEstrelas(puntuacion));
              });

              // Submit
              area.querySelector('.btn-confirmar-checkin').addEventListener('click', async () => {
                const btnConf = area.querySelector('.btn-confirmar-checkin');
                btnConf.disabled = true;
                btnConf.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Gardando...';
                const resena = area.querySelector('.checkin-resena').value.trim();
                try {
                  const r = await fetch('/api/checkin', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                      slug: item.slug, lat, lng,
                      puntuacion: puntuacion || null,
                      resena: resena || null,
                    }),
                  });
                  const d = await r.json();
                  if (r.ok && d.ok) {
                    area.innerHTML = `<div class="alert alert-success py-1 px-2 small mt-2 mb-0">
                      <i class="fa-solid fa-check me-1"></i>Check-in gardado!
                      ${puntuacion ? `<span class="ms-1 text-warning">${'★'.repeat(puntuacion)}</span>` : ''}
                      ${resena ? `<p class="mb-0 mt-1 fst-italic">"${resena}"</p>` : ''}
                    </div>`;
                  } else if (d.repetido) {
                    area.innerHTML = `<div class="alert alert-secondary py-1 px-2 small mt-2 mb-0">
                      <i class="fa-solid fa-stamp me-1"></i>Xa fixeches check-in aquí anteriormente
                    </div>`;
                  } else {
                    btnConf.disabled = false;
                    btnConf.innerHTML = '<i class="fa-solid fa-stamp me-1"></i>Confirmar check-in';
                  }
                } catch {
                  btnConf.disabled = false;
                  btnConf.innerHTML = '<i class="fa-solid fa-stamp me-1"></i>Confirmar check-in';
                }
              });
            }
          });
        }
      } catch (err) {}
    });
    window.sharedCluster.addLayer(marker);
    window.categoryMarkers[seccion.id].push(marker);
    window.markerBySlug[item.slug] = marker;
  });

}

// =============================================================================
// PANEL DE CAPAS GEOJSON
// =============================================================================

window.extraLayers = {};  // Capas GeoJSON extra cargadas

async function inicializarCapas() {
  const container = document.getElementById('capasCheckboxes');
  if (!container) return;

  try {
    const resp = await fetch('/api/capas-geojson');
    const data = await resp.json();
    let html = '';

    // Toggle de concellos (predefinida)
    if (data.predefinidas?.concellos) {
      html += `
        <div class="form-check">
          <input class="form-check-input" type="checkbox" id="capaConcellos" checked>
          <label class="form-check-label" for="capaConcellos">
            <i class="fa-solid fa-draw-polygon me-1 text-muted"></i>Concellos
          </label>
        </div>`;
    }

    // Capas extras auto-detectadas
    if (data.extras?.length) {
      html += '<div class="text-muted small mt-2 mb-1">Capas extras</div>';
      data.extras.forEach(extra => {
        const nomeDisplay = extra.nome.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        html += `
          <div class="form-check">
            <input class="form-check-input" type="checkbox" id="capa-${extra.nome}" data-url="${extra.url}">
            <label class="form-check-label" for="capa-${extra.nome}">
              <i class="fa-solid fa-map me-1 text-muted"></i>${nomeDisplay}
            </label>
          </div>`;
      });
    }

    if (!html) {
      html = '<div class="text-muted small">Non hai capas dispoñibles.</div>';
    }
    container.innerHTML = html;

    // Listener toggle concellos
    const chkConcellos = document.getElementById('capaConcellos');
    if (chkConcellos) {
      chkConcellos.addEventListener('change', () => {
        if (chkConcellos.checked) {
          if (window.concelloLayer && !window.map.hasLayer(window.concelloLayer)) {
            window.concelloLayer.addTo(window.map);
          }
          if (window.concelloLabelsLayer && !window.map.hasLayer(window.concelloLabelsLayer)) {
            window.concelloLabelsLayer.addTo(window.map);
          }
        } else {
          if (window.concelloLayer) window.map.removeLayer(window.concelloLayer);
          if (window.concelloLabelsLayer) window.map.removeLayer(window.concelloLabelsLayer);
        }
        window.concellosVisible = chkConcellos.checked;
      });
    }

    // Listeners capas extras
    container.querySelectorAll('input[data-url]').forEach(chk => {
      chk.addEventListener('change', () => {
        const url = chk.dataset.url;
        const id = chk.id;
        if (chk.checked) {
          fetch(url)
            .then(r => r.json())
            .then(geojson => {
              const layer = L.geoJSON(geojson, {
                style: { color: '#2196F3', weight: 2, opacity: 0.7, fillOpacity: 0.1 }
              }).addTo(window.map);
              window.extraLayers[id] = layer;
            });
        } else {
          if (window.extraLayers[id]) {
            window.map.removeLayer(window.extraLayers[id]);
            delete window.extraLayers[id];
          }
        }
      });
    });

  } catch(e) {
    container.innerHTML = '<div class="text-danger small">Erro ao cargar capas.</div>';
  }
}

// =============================================================================
// BUSCA NO MAPA (vía API REST)
// =============================================================================

const _TIPO_LABEL = { patrimonio: 'Patrimonio', empresa: 'Empresa', espazo: 'Espazo' };
const _TIPO_COR   = { patrimonio: '#8b0000',    empresa: '#1565c0',  espazo: '#2e7d32' };

function inicializarBusca() {
  const input = document.getElementById('buscaMapa');
  const resultados = document.getElementById('buscaResultados');
  if (!input || !resultados) return;

  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => buscar(input.value.trim()), 300);
  });

  // Pechar resultados ao facer clic fóra
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !resultados.contains(e.target)) {
      resultados.style.display = 'none';
    }
  });
}

async function buscar(texto) {
  const resultados = document.getElementById('buscaResultados');
  if (!resultados) return;

  if (texto.length < 2) {
    resultados.style.display = 'none';
    return;
  }

  // Indicador de carga
  resultados.innerHTML = '<div class="list-group-item text-muted small"><i class="fa-solid fa-spinner fa-spin me-1"></i>Buscando...</div>';
  resultados.style.display = 'block';

  try {
    const resp = await fetch(`/api/buscar?q=${encodeURIComponent(texto)}`);
    if (!resp.ok) throw new Error();
    const data = await resp.json();
    const items = data.results || [];

    if (!items.length) {
      resultados.innerHTML = '<div class="list-group-item text-muted small">Sen resultados</div>';
      return;
    }

    resultados.innerHTML = items.map((r, i) => {
      const cor = _TIPO_COR[r.tipo] || '#555';
      const label = _TIPO_LABEL[r.tipo] || r.tipo;
      return `<button type="button" class="list-group-item list-group-item-action py-1 px-2"
                data-lat="${r.lat}" data-lng="${r.lng}"
                data-slug="${r.slug || ''}"
                data-seccion="${r.seccion_id || ''}"
                data-nome="${(r.nome || '').replace(/"/g, '&quot;')}"
                data-concello="${(r.concello_nome || '').replace(/"/g, '&quot;')}">
        <div class="d-flex align-items-center gap-2">
          <span style="background:${cor};color:#fff;font-size:0.65em;padding:1px 5px;border-radius:3px;white-space:nowrap">${label}</span>
          <span class="small fw-semibold text-truncate">${r.nome || ''}</span>
        </div>
        <div class="text-muted" style="font-size:0.75em;padding-left:2px">${r.concello_nome || ''}</div>
      </button>`;
    }).join('');

    // Listeners: navegar ao resultado e asegurar que o marcador está visible
    resultados.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        const lat = parseFloat(btn.dataset.lat);
        const lng = parseFloat(btn.dataset.lng);
        const slug = btn.dataset.slug;
        const seccionId = btn.dataset.seccion;
        resultados.style.display = 'none';
        document.getElementById('buscaMapa').value = '';
        if (isNaN(lat) || isNaN(lng) || !window.map) return;

        // Se o marcador non está no mapa aínda, activar a sección correspondente
        if (slug && !window.markerBySlug[slug] && seccionId) {
          activarSeccion(seccionId);
        }

        window.map.setView([lat, lng], 17);
      });
    });

  } catch {
    resultados.innerHTML = '<div class="list-group-item text-muted small">Erro na busca</div>';
  }
}

// =============================================================================
// PANEL DE ELEVACIÓN
// =============================================================================

window.elevationData = null;
window.elevMarker = null;
window.rutaAoCaminoLayer = null;

async function cargarElevacion() {
  try {
    const resp = await fetch('/api/elevation-data');
    if (!resp.ok) return;
    window.elevationData = await resp.json();
    actualizarElevacion();
    inicializarPanelElevacion();
  } catch (e) {
    console.warn('Datos de elevación non dispoñibles:', e.message);
  }
}

function inicializarPanelElevacion() {
  const toggle = document.getElementById('elevationToggle');
  const panel = document.getElementById('elevationPanel');
  const icon = document.getElementById('elevToggleIcon');
  if (!toggle || !panel) return;

  toggle.addEventListener('click', (e) => {
    // Non toglear o panel ao premer no selector de camiño
    if (e.target.closest('#selectorCamino')) return;
    panel.classList.toggle('collapsed');
    if (icon) {
      icon.className = panel.classList.contains('collapsed')
        ? 'fa-solid fa-chevron-up'
        : 'fa-solid fa-chevron-down';
    }
    if (window.map) setTimeout(() => window.map.invalidateSize(), 350);
  });
}

function actualizarElevacion() {
  if (!window.elevationData) return;

  const orixe = window.caminoSeleccionado || 'ferrol';
  const outroOrixe = orixe === 'ferrol' ? 'coruna' : 'ferrol';
  const tramosActivos = window.elevationData.tramos.filter(t =>
    clasificarTramo(t.nome) !== outroOrixe
  );

  let totalDist = 0, totalDpos = 0, totalDneg = 0;
  tramosActivos.forEach(t => {
    totalDist += t.distancia_km;
    totalDpos += t.desnivel_positivo;
    totalDneg += t.desnivel_negativo;
  });
  const tempoMin = (totalDist / 4) * 60 + (totalDpos / 10);

  const elDist = document.getElementById('elevStatDist');
  const elDpos = document.getElementById('elevStatDpos');
  const elDneg = document.getElementById('elevStatDneg');
  const elTempo = document.getElementById('elevStatTempo');
  if (elDist) elDist.innerHTML = `<span class="stat-val">${totalDist.toFixed(1)}</span> km`;
  if (elDpos) elDpos.innerHTML = `D+ <span class="stat-val">${Math.round(totalDpos)}</span>m`;
  if (elDneg) elDneg.innerHTML = `D- <span class="stat-val">${Math.round(totalDneg)}</span>m`;
  if (elTempo) {
    const h = Math.floor(tempoMin / 60);
    const m = Math.round(tempoMin % 60);
    elTempo.innerHTML = `<span class="stat-val">${h}h${m < 10 ? '0' : ''}${m}</span>`;
  }

  const { perfil, segmentos } = construirPerfilCombinado(tramosActivos);
  debuxarElevacion(perfil, segmentos);
  actualizarStatsTramos();
}

// Clasificar tramo por orixe
function clasificarTramo(nome) {
  if (nome.match(/^CIN-e01Vt/)) return 'coruna';      // A Coruña (variante)
  if (nome.match(/^CIN-e0[1-3]t/)) return 'ferrol';   // Ferrol (etapas 1-3)
  return 'comun';                                      // Común (etapas 4-5)
}

const CORES_RUTA = {
  ferrol: { line: '#FFB300', fill: 'rgba(255, 179, 0, 0.25)', nome: 'Ferrol' },
  coruna: { line: '#1E88E5', fill: 'rgba(30, 136, 229, 0.25)', nome: 'A Coruña' },
  comun:  { line: '#43A047', fill: 'rgba(67, 160, 71, 0.25)', nome: 'Común' }
};

// Selector de camiño (Ferrol / A Coruña) no panel de elevación
window.caminoSeleccionado = 'ferrol';

function aplicarSelectorCamino(orixe) {
  window.caminoSeleccionado = orixe;
  if (typeof actualizarCapaCamino === 'function') actualizarCapaCamino();
  if (window.elevationData) actualizarElevacion();
}

document.addEventListener('change', (e) => {
  if (e.target.name === 'caminoOrixe') {
    aplicarSelectorCamino(e.target.value);
  }
});

// Autoseleccionar variante Ferrol/Coruña segundo proximidade do usuario
function autoseleccionarVariante() {
  if (!window.userPosition || !window.geojsonCamino?.features) return;

  const userLat = window.userPosition.lat;
  const userLng = window.userPosition.lng;
  let distFerrol = Infinity;
  let distCoruna = Infinity;

  for (const feature of window.geojsonCamino.features) {
    const nome = feature.properties?.Name || '';
    const tipo = clasificarTramo(nome);
    if (tipo === 'comun') continue; // Os tramos comúns non contan

    const coords = feature.geometry?.coordinates || [];
    for (const line of coords) {
      for (let i = 0; i < line.length; i += 10) {
        const dist = haversineMetrosGlobal(userLat, userLng, line[i][1], line[i][0]);
        if (tipo === 'ferrol' && dist < distFerrol) distFerrol = dist;
        if (tipo === 'coruna' && dist < distCoruna) distCoruna = dist;
      }
    }
  }

  const orixe = distCoruna < distFerrol ? 'coruna' : 'ferrol';
  if (orixe !== window.caminoSeleccionado) {
    // Actualizar radio button
    const radio = document.getElementById(orixe === 'coruna' ? 'caminoCoruna' : 'caminoFerrol');
    if (radio) radio.checked = true;
    aplicarSelectorCamino(orixe);
  }
}

function construirPerfilCombinado(tramos) {
  const perfil = [];
  const segmentos = []; // {inicio, fin, tipo, nome}
  let offset = 0;

  for (const tramo of tramos) {
    if (!tramo.perfil?.length) continue;
    const tipo = clasificarTramo(tramo.nome);
    const inicio = perfil.length;

    for (let i = 0; i < tramo.perfil.length; i++) {
      const [dist, alt] = tramo.perfil[i];
      if (i === 0 && perfil.length > 0) continue;
      perfil.push([dist + offset, alt, tipo]);
    }

    segmentos.push({
      inicio,
      fin: perfil.length - 1,
      tipo,
      nome: tramo.nome,
      distInicio: offset,
      distFin: offset + tramo.perfil[tramo.perfil.length - 1][0]
    });

    offset += tramo.perfil[tramo.perfil.length - 1][0];
  }
  return { perfil, segmentos };
}

function debuxarElevacion(perfil, segmentos) {
  const canvas = document.getElementById('elevCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const rect = canvas.parentElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const W = rect.width;
  const H = rect.height;
  const pad = { top: 10, bottom: 24, left: 45, right: 80 }; // Máis espazo para lenda

  ctx.clearRect(0, 0, W, H);

  if (!perfil.length) {
    ctx.fillStyle = '#999';
    ctx.font = '13px Inter, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Selecciona tramos para ver o perfil', W / 2, H / 2);
    return;
  }

  const maxDist = perfil[perfil.length - 1][0];
  const alts = perfil.map(p => p[1]);
  const minAlt = Math.min(...alts);
  const maxAlt = Math.max(...alts);
  const altRange = maxAlt - minAlt || 1;

  const gw = W - pad.left - pad.right;
  const gh = H - pad.top - pad.bottom;

  function x(dist) { return pad.left + (dist / maxDist) * gw; }
  function y(alt) { return pad.top + gh - ((alt - minAlt) / altRange) * gh; }

  // Debuxar área con gradiente por segmento
  for (const seg of segmentos) {
    if (seg.inicio >= perfil.length) continue;
    const cor = CORES_RUTA[seg.tipo] || CORES_RUTA.comun;

    ctx.beginPath();
    ctx.moveTo(x(perfil[seg.inicio][0]), y(perfil[seg.inicio][1]));
    for (let i = seg.inicio + 1; i <= seg.fin && i < perfil.length; i++) {
      ctx.lineTo(x(perfil[i][0]), y(perfil[i][1]));
    }
    ctx.lineTo(x(perfil[Math.min(seg.fin, perfil.length - 1)][0]), H - pad.bottom);
    ctx.lineTo(x(perfil[seg.inicio][0]), H - pad.bottom);
    ctx.closePath();
    ctx.fillStyle = cor.fill;
    ctx.fill();
  }

  // Debuxar liñas por segmento
  for (const seg of segmentos) {
    if (seg.inicio >= perfil.length) continue;
    const cor = CORES_RUTA[seg.tipo] || CORES_RUTA.comun;

    ctx.beginPath();
    ctx.moveTo(x(perfil[seg.inicio][0]), y(perfil[seg.inicio][1]));
    for (let i = seg.inicio + 1; i <= seg.fin && i < perfil.length; i++) {
      ctx.lineTo(x(perfil[i][0]), y(perfil[i][1]));
    }
    ctx.strokeStyle = cor.line;
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }

  // Eixo Y
  ctx.fillStyle = '#888';
  ctx.font = '10px Inter, Arial, sans-serif';
  ctx.textAlign = 'right';
  const nTicksY = 4;
  for (let i = 0; i <= nTicksY; i++) {
    const alt = minAlt + (altRange * i) / nTicksY;
    const yy = y(alt);
    ctx.fillText(`${Math.round(alt)}m`, pad.left - 4, yy + 3);
    ctx.beginPath();
    ctx.moveTo(pad.left, yy);
    ctx.lineTo(W - pad.right, yy);
    ctx.strokeStyle = 'rgba(0,0,0,0.06)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Eixo X
  ctx.textAlign = 'center';
  const nTicksX = Math.min(6, Math.max(2, Math.floor(gw / 80)));
  for (let i = 0; i <= nTicksX; i++) {
    const dist = (maxDist * i) / nTicksX;
    const xx = x(dist);
    ctx.fillText(`${(dist / 1000).toFixed(1)}km`, xx, H - pad.bottom + 14);
  }

  // Lenda (á dereita)
  const tiposActivos = [...new Set(segmentos.map(s => s.tipo))];
  let ly = pad.top + 5;
  ctx.font = '10px Inter, Arial, sans-serif';
  ctx.textAlign = 'left';
  for (const tipo of tiposActivos) {
    const cor = CORES_RUTA[tipo];
    // Liña de cor
    ctx.beginPath();
    ctx.moveTo(W - pad.right + 8, ly + 5);
    ctx.lineTo(W - pad.right + 22, ly + 5);
    ctx.strokeStyle = cor.line;
    ctx.lineWidth = 3;
    ctx.stroke();
    // Texto
    ctx.fillStyle = '#555';
    ctx.fillText(cor.nome, W - pad.right + 26, ly + 8);
    ly += 16;
  }

  canvas._elevPerfil = perfil;
  canvas._elevSegmentos = segmentos;
  canvas._elevDims = { W, H, pad, maxDist, minAlt, maxAlt, altRange, gw, gh };

  debuxarPosicionUsuario();

  if (!canvas._elevListenerAdded) {
    canvas._elevListenerAdded = true;
    canvas.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      onElevHover(mx);
    });
    canvas.addEventListener('mouseleave', () => {
      const tooltip = document.getElementById('elevationTooltip');
      if (tooltip) tooltip.style.display = 'none';
      if (window.elevMarker) {
        window.map.removeLayer(window.elevMarker);
        window.elevMarker = null;
      }
    });
  }
}

// Atopar a posición do usuario no perfil de elevación (xeo→perfil)
function atoparDistanciaUsuarioNoPerfil() {
  if (!window.userPosition || !window.elevationData || !window.geojsonCamino) return null;

  const canvas = document.getElementById('elevCanvas');
  if (!canvas?._elevPerfil?.length) return null;

  const orixe = window.caminoSeleccionado || 'ferrol';
  const outroOrixe = orixe === 'ferrol' ? 'coruna' : 'ferrol';
  const tramosActivos = window.elevationData.tramos.filter(t =>
    clasificarTramo(t.nome) !== outroOrixe
  );

  const userLat = window.userPosition.lat;
  const userLng = window.userPosition.lng;
  let globalIdx = 0;
  let minDist = Infinity;
  let bestIdx = -1;

  for (const tramo of tramosActivos) {
    const feature = window.geojsonCamino?.features?.find(f => f.properties.Name === tramo.nome);
    if (!feature) continue;
    for (const line of feature.geometry.coordinates) {
      for (let i = 0; i < line.length; i++) {
        const dist = haversineMetrosGlobal(userLat, userLng, line[i][1], line[i][0]);
        if (dist < minDist) {
          minDist = dist;
          bestIdx = globalIdx;
        }
        globalIdx++;
      }
    }
  }

  if (bestIdx < 0 || minDist > 500) return null;

  const perfil = canvas._elevPerfil;
  if (bestIdx >= perfil.length) return null;

  return { distancia: perfil[bestIdx][0], altitude: perfil[bestIdx][1], idx: bestIdx };
}

// Debuxar marcador "Estás aquí" no perfil de elevación
function debuxarPosicionUsuario() {
  const pos = atoparDistanciaUsuarioNoPerfil();
  if (!pos) return;

  const canvas = document.getElementById('elevCanvas');
  if (!canvas?._elevDims) return;
  const ctx = canvas.getContext('2d');
  const { pad, maxDist, minAlt, altRange, gw, gh } = canvas._elevDims;

  const px = pad.left + (pos.distancia / maxDist) * gw;
  const py = pad.top + gh - ((pos.altitude - minAlt) / altRange) * gh;

  // Liña vertical discontinua
  ctx.save();
  ctx.setLineDash([5, 4]);
  ctx.strokeStyle = '#e57373';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(px, pad.top);
  ctx.lineTo(px, pad.top + gh);
  ctx.stroke();
  ctx.setLineDash([]);

  // Círculo no punto exacto
  ctx.beginPath();
  ctx.arc(px, py, 4, 0, Math.PI * 2);
  ctx.fillStyle = '#e57373';
  ctx.fill();
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Etiqueta "Estás aquí"
  const label = 'Estás aquí';
  ctx.font = 'bold 10px Inter, Arial, sans-serif';
  const tw = ctx.measureText(label).width;
  let lx = px - tw / 2;
  // Evitar que saia do canvas
  if (lx < pad.left) lx = pad.left;
  if (lx + tw + 4 > pad.left + gw) lx = pad.left + gw - tw - 4;
  const ly = pad.top - 2;

  ctx.fillStyle = 'rgba(255,255,255,0.85)';
  ctx.fillRect(lx - 2, ly - 10, tw + 4, 13);
  ctx.fillStyle = '#e57373';
  ctx.fillText(label, lx, ly);

  ctx.restore();
}

function onElevHover(mx) {
  const canvas = document.getElementById('elevCanvas');
  if (!canvas?._elevPerfil?.length) return;

  const { pad, maxDist, gw } = canvas._elevDims;
  const perfil = canvas._elevPerfil;
  const segmentos = canvas._elevSegmentos || [];

  const distAtMouse = ((mx - pad.left) / gw) * maxDist;
  if (distAtMouse < 0 || distAtMouse > maxDist) return;

  let idx = 0;
  for (let i = 1; i < perfil.length; i++) {
    if (Math.abs(perfil[i][0] - distAtMouse) < Math.abs(perfil[idx][0] - distAtMouse)) {
      idx = i;
    }
  }

  const [dist, alt, tipo] = perfil[idx];
  const rutaNome = CORES_RUTA[tipo]?.nome || '';

  // Atopar o tramo actual
  let tramoNome = '';
  for (const seg of segmentos) {
    if (idx >= seg.inicio && idx <= seg.fin) {
      // Extraer nome curto do tramo
      const m = seg.nome.match(/\(([^)]+)\)/);
      tramoNome = m ? m[1] : seg.nome;
      break;
    }
  }

  const tooltip = document.getElementById('elevationTooltip');
  if (tooltip) {
    tooltip.style.display = 'block';
    tooltip.innerHTML = `<b>${rutaNome}</b> — ${tramoNome}<br>${(dist / 1000).toFixed(2)} km — ${Math.round(alt)} m`;
    const panelRect = document.getElementById('elevationPanel').getBoundingClientRect();
    tooltip.style.left = (mx + 10) + 'px';
    tooltip.style.bottom = (window.innerHeight - panelRect.top + 8) + 'px';
  }

  moverMarcadorElevacion(idx);
}

function moverMarcadorElevacion(perfilIdx) {
  if (!window.elevationData || !window.map || !window.geojsonCamino) return;

  const orixe = window.caminoSeleccionado || 'ferrol';
  const outroOrixe = orixe === 'ferrol' ? 'coruna' : 'ferrol';
  const tramosActivos = window.elevationData.tramos.filter(t =>
    clasificarTramo(t.nome) !== outroOrixe
  );

  let globalIdx = 0;
  let found = null;

  for (const tramo of tramosActivos) {
    const feature = window.geojsonCamino?.features?.find(f => f.properties.Name === tramo.nome);
    if (!feature) continue;
    for (const line of feature.geometry.coordinates) {
      for (let i = 0; i < line.length; i++) {
        if (globalIdx === perfilIdx) {
          found = [line[i][1], line[i][0]];
          break;
        }
        globalIdx++;
      }
      if (found) break;
    }
    if (found) break;
  }

  if (!found) return;

  if (window.elevMarker) {
    window.elevMarker.setLatLng(found);
  } else {
    window.elevMarker = L.circleMarker(found, {
      radius: 6,
      color: '#4CAF50',
      fillColor: '#fff',
      fillOpacity: 1,
      weight: 3,
      zIndexOffset: 2000
    }).addTo(window.map);
  }
}

function actualizarStatsTramos() {
  if (!window.elevationData) return;

  const tramos = window.elevationData.tramos;
  document.querySelectorAll('#rutasCheckboxes input[type=checkbox]').forEach(chk => {
    const tramo = tramos.find(t => t.nome === chk.value);
    if (!tramo) return;

    const label = chk.parentElement.querySelector('label');
    if (!label) return;

    label.querySelectorAll('.elev-stat-badge').forEach(b => b.remove());

    if (tramo.distancia_km > 0) {
      const badge = document.createElement('span');
      badge.className = 'elev-stat-badge';
      badge.textContent = `${tramo.distancia_km} km`;
      badge.title = `D+${tramo.desnivel_positivo}m D-${tramo.desnivel_negativo}m | Alt: ${tramo.altitude_min}-${tramo.altitude_max}m`;
      label.appendChild(badge);
    }
  });
}

// =============================================================================
// RUTA ATA O CAMIÑO
// =============================================================================

// Modo de transporte global (a pé ou en bici)
window.modoRutaActual = 'pe';

// Obter modo de transporte seleccionado (a pé ou en bici)
function getModoRuta() {
  const radio = document.querySelector('input[name="modoRuta"]:checked');
  if (radio) {
    window.modoRutaActual = radio.value;
  }
  return window.modoRutaActual;
}

// Actualizar modo cando cambia o selector
document.addEventListener('change', (e) => {
  if (e.target.name === 'modoRuta') {
    window.modoRutaActual = e.target.value;
    // Reaplicar filtro de proximidade co novo modo
    if (window.userPosition) {
      aplicarFiltroProximidade();
    }
  }
});

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.btn-ruta-camino');
  if (!btn) return;

  const lat = parseFloat(btn.dataset.lat);
  const lng = parseFloat(btn.dataset.lng);
  if (isNaN(lat) || isNaN(lng)) return;

  const modo = btn.dataset.modo || getModoRuta();
  const textoOrixinal = btn.innerHTML;
  const popupSource = window.map._popup ? window.map._popup._source : null;

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  try {
    const resp = await fetch('/api/ruta-ao-camino', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng, modo })
    });

    if (!resp.ok) {
      btn.innerHTML = textoOrixinal;
      btn.disabled = false;
      return;
    }

    const data = await resp.json();

    // Limpar capas anteriores
    if (window.rutaAoCaminoLayer) window.map.removeLayer(window.rutaAoCaminoLayer);
    if (window.rutaDesdeAquiLayer) {
      window.map.removeLayer(window.rutaDesdeAquiLayer);
      window.rutaDesdeAquiLayer = null;
    }

    const latlngs = data.shape.map(p => [p[0], p[1]]);
    const corRuta = modo === 'bici' ? '#E65100' : '#1976D2';

    window.rutaAoCaminoLayer = L.polyline(latlngs, {
      color: corRuta, weight: 5, opacity: 0.85, dashArray: '10 6'
    }).addTo(window.map);

    // Inxectar resultados no popup via API de Leaflet (funciona sempre)
    const resultadoHtml = xerarResultadoHtml({ tipo: 'Ruta ata o camiño', distancia_km: data.distancia_km, tempoTexto: `${data.tempo_min} min`, modo });
    window.rutaActiva = { source: popupSource, html: resultadoHtml };
    inxectarResultadosEnPopup(popupSource, resultadoHtml);

    window.map.fitBounds(window.rutaAoCaminoLayer.getBounds().pad(0.3));

  } catch (err) {
    btn.innerHTML = textoOrixinal;
    btn.disabled = false;
    console.error('Erro calculando ruta ao camiño:', err);
  }
});

// =============================================================================
// RUTA DESDE A MIÑA POSICIÓN (usuario → POI)
// =============================================================================

window.rutaDesdeAquiLayer = null;

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.btn-ruta-desde-aqui');
  if (!btn) return;

  if (!window.userPosition) {
    alert('Non se puido obter a túa posición. Permite a xeolocalización no navegador.');
    return;
  }

  const destLat = parseFloat(btn.dataset.lat);
  const destLng = parseFloat(btn.dataset.lng);
  if (isNaN(destLat) || isNaN(destLng)) return;

  const modo = btn.dataset.modo || 'pe';
  const corRuta = modo === 'bici' ? '#E65100' : '#4CAF50';
  const textoOrixinal = btn.innerHTML;
  const popupSource = window.map._popup ? window.map._popup._source : null;

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  try {
    const resp = await fetch('/api/ruta-punto-a-punto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin_lat: window.userPosition.lat,
        origin_lng: window.userPosition.lng,
        dest_lat: destLat,
        dest_lng: destLng,
        modo
      })
    });

    if (!resp.ok) {
      btn.innerHTML = textoOrixinal;
      btn.disabled = false;
      return;
    }

    const data = await resp.json();

    // Limpar capas anteriores
    if (window.rutaDesdeAquiLayer) window.map.removeLayer(window.rutaDesdeAquiLayer);
    if (window.rutaAoCaminoLayer) {
      window.map.removeLayer(window.rutaAoCaminoLayer);
      window.rutaAoCaminoLayer = null;
    }

    const latlngs = data.shape.map(p => [p[0], p[1]]);

    window.rutaDesdeAquiLayer = L.polyline(latlngs, {
      color: corRuta, weight: 5, opacity: 0.85
    }).addTo(window.map);

    // Inxectar resultados no popup via API de Leaflet (funciona sempre)
    const resultadoHtml = xerarResultadoHtml({ tipo: 'Desde a miña posición', distancia_km: data.distancia_km, tempoTexto: `${data.tempo_min} min`, modo });
    window.rutaActiva = { source: popupSource, html: resultadoHtml };
    inxectarResultadosEnPopup(popupSource, resultadoHtml);

    window.map.fitBounds(window.rutaDesdeAquiLayer.getBounds().pad(0.2));

  } catch (err) {
    btn.innerHTML = textoOrixinal;
    btn.disabled = false;
    console.error('Erro calculando ruta desde posición:', err);
  }
});

// =============================================================================
// RUTA COMPLETA A SANTIAGO
// =============================================================================

window.rutaSantiagoLayer = null;
window.rutaSantiagoInfo = null;

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.btn-ruta-santiago');
  if (!btn) return;

  const lat = parseFloat(btn.dataset.lat);
  const lng = parseFloat(btn.dataset.lng);
  if (isNaN(lat) || isNaN(lng)) return;

  const modo = btn.dataset.modo || getModoRuta();
  const textoOrixinal = btn.innerHTML;
  const popupSource = window.map._popup ? window.map._popup._source : null;

  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Calculando...';

  try {
    const resp = await fetch('/api/ruta-completa-santiago', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng, modo })
    });

    if (!resp.ok) {
      btn.innerHTML = textoOrixinal;
      btn.disabled = false;
      return;
    }

    const data = await resp.json();
    window.rutaSantiagoInfo = data;

    // Limpar capas anteriores
    if (window.rutaAoCaminoLayer) {
      window.map.removeLayer(window.rutaAoCaminoLayer);
      window.rutaAoCaminoLayer = null;
    }
    if (window.rutaSantiagoLayer) {
      window.map.removeLayer(window.rutaSantiagoLayer);
    }

    // Debuxar ruta ao camiño se existe
    if (data.ruta_ao_camino?.shape) {
      const latlngs = data.ruta_ao_camino.shape.map(p => [p[0], p[1]]);
      const corRuta = modo === 'bici' ? '#E65100' : '#1976D2';
      window.rutaAoCaminoLayer = L.polyline(latlngs, {
        color: corRuta, weight: 4, opacity: 0.9, dashArray: '8 6'
      }).addTo(window.map);
    }

    // Marcar os segmentos do camiño a seguir
    const segmentosNomes = new Set(data.segmentos.map(s => s.nome));
    document.querySelectorAll('#rutasCheckboxes input[type=checkbox]').forEach(chk => {
      const shouldCheck = segmentosNomes.has(chk.value);
      if (chk.checked !== shouldCheck) chk.checked = shouldCheck;
    });

    if (typeof actualizarCapaCamino === 'function') actualizarCapaCamino();
    if (typeof actualizarElevacion === 'function') actualizarElevacion();

    const total = data.total;
    const horasPorDia = modo === 'bici' ? 8 : 6;
    const diasEstimados = Math.ceil(total.tempo_estimado_horas / horasPorDia);
    const orixeNome = data.orixe_detectada === 'ferrol' ? 'Ferrol' : 'A Coruña';

    // Inxectar resultados no popup via API de Leaflet (funciona sempre)
    const resultadoHtml = xerarResultadoHtml({
      tipo: 'Ruta completa a Santiago',
      distancia_km: total.distancia_km,
      tempoTexto: `${total.tempo_estimado_horas}h`,
      modo, orixeNome,
      desnivel_positivo: total.desnivel_positivo,
      desnivel_negativo: total.desnivel_negativo,
      diasEstimados
    });
    window.rutaActiva = { source: popupSource, html: resultadoHtml };
    inxectarResultadosEnPopup(popupSource, resultadoHtml);

    // Axustar vista e reabrir o popup despois da animación
    const bounds = L.latLngBounds([[lat, lng]]);
    if (window.rutaAoCaminoLayer) bounds.extend(window.rutaAoCaminoLayer.getBounds());
    bounds.extend([42.8805, -8.5456]);
    window.map.fitBounds(bounds.pad(0.1));

  } catch (err) {
    btn.innerHTML = textoOrixinal;
    btn.disabled = false;
    console.error('Erro calculando ruta a Santiago:', err);
  }
});

