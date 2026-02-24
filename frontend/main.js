// Frontend independente (en desenvolvemento)
// Este directorio albergará unha versión desacoplada da aplicación,
// potencialmente baseada nun framework JS moderno (Vite/Vue/React).
// Por agora, o frontend principal está en backend/templates/ + backend/static/js/app.js

// Prototipo inicial: consumir /api/recursos e mostrar recursos no mapa
fetch('/api/recursos')
  .then(res => res.json())
  .then(data => {
    const recursos = data.results || [];
    // Mostrar no sidebar
    const sidebar = document.getElementById('sidebar');
    sidebar.innerHTML = recursos.map(r => `
      <div class="recurso">
        <strong>${r.nome || ''}</strong><br>
        <span>${r.categoria_principal?.cascada || r.categorias_nomes?.[0] || ''}</span><br>
        <span>${r.concello_nome || ''}</span>
      </div>
    `).join('');
    // Mostrar no mapa (Leaflet)
    if (window.map && typeof L !== 'undefined') {
      recursos.forEach(r => {
        if (r.lat && r.lng) {
          L.marker([parseFloat(r.lat), parseFloat(r.lng)])
            .addTo(window.map)
            .bindPopup(`<strong>${r.nome || ''}</strong><br>${r.categoria_principal?.cascada || r.categorias_nomes?.[0] || ''}`);
        }
      });
    }
  });
