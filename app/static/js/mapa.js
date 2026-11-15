// Dibuja los municipios en un mapa Leaflet. Cada punto se colorea según su nivel de riesgo.
(function () {
  var contenedores = document.querySelectorAll(".mapa");
  if (!contenedores.length) return;

  if (typeof L === "undefined") {
    contenedores.forEach(function (c) {
      var aviso = c.querySelector(".mapa-aviso");
      if (aviso) aviso.textContent = "No se pudo cargar el mapa. Usa la lista de municipios.";
    });
    return;
  }

  var COLORES = { bajo: "#2f9e6e", medio: "#e0a800", alto: "#dc3545", ninguno: "#6c757d" };
  var ETIQUETAS = { bajo: "Riesgo bajo", medio: "Riesgo medio", alto: "Riesgo alto", ninguno: "Sin evaluar" };
  var CENTRO_SABANA_CENTRO = [4.95, -74.0];

  function tiene(objeto, clave) {
    return Object.prototype.hasOwnProperty.call(objeto, clave);
  }

  function leerPuntos(contenedor) {
    var el = document.getElementById(contenedor.id + "-datos");
    try {
      return el ? JSON.parse(el.textContent) : [];
    } catch (e) {
      return [];
    }
  }

  // El contenido del globo se arma con textContent (nunca innerHTML) para evitar inyección de HTML.
  function contenidoGlobo(punto, nivel) {
    var caja = document.createElement("div");
    var titulo = document.createElement("strong");
    titulo.textContent = punto.nombre;
    caja.appendChild(titulo);

    var linea = document.createElement("div");
    linea.textContent = ETIQUETAS[nivel];
    caja.appendChild(linea);

    if (punto.suministro) {
      var suministro = document.createElement("div");
      suministro.textContent = "Suministro: " + punto.suministro;
      caja.appendChild(suministro);
    }
    if (punto.url) {
      var enlace = document.createElement("a");
      enlace.href = punto.url;
      enlace.textContent = "Ver ficha del municipio";
      caja.appendChild(enlace);
    }
    return caja;
  }

  function agregarLeyenda(mapa) {
    var leyenda = L.control({ position: "bottomright" });
    leyenda.onAdd = function () {
      var caja = L.DomUtil.create("div", "leyenda-mapa");
      ["bajo", "medio", "alto", "ninguno"].forEach(function (nivel) {
        var fila = document.createElement("div");
        var color = document.createElement("span");
        color.className = "leyenda-color";
        color.style.background = COLORES[nivel];
        fila.appendChild(color);
        fila.appendChild(document.createTextNode(ETIQUETAS[nivel]));
        caja.appendChild(fila);
      });
      return caja;
    };
    leyenda.addTo(mapa);
  }

  function iniciarMapa(contenedor) {
    var puntos = leerPuntos(contenedor);
    var aviso = contenedor.querySelector(".mapa-aviso");
    if (aviso) aviso.remove();

    var mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(CENTRO_SABANA_CENTRO, 10);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; Colaboradores de OpenStreetMap",
    }).addTo(mapa);

    var coordenadas = [];
    puntos.forEach(function (punto) {
      var nivel = punto.nivel && tiene(COLORES, punto.nivel) ? punto.nivel : "ninguno";
      var marcador = L.circleMarker([punto.lat, punto.lng], {
        radius: 10,
        color: "#ffffff",
        weight: 2,
        fillColor: COLORES[nivel],
        fillOpacity: 0.9,
      }).addTo(mapa);
      marcador.bindTooltip(punto.nombre);
      marcador.bindPopup(contenidoGlobo(punto, nivel));
      coordenadas.push([punto.lat, punto.lng]);
    });

    if (coordenadas.length === 1) {
      mapa.setView(coordenadas[0], Number(contenedor.dataset.zoom) || 12);
    } else if (coordenadas.length > 1) {
      mapa.fitBounds(coordenadas, { padding: [30, 30] });
      agregarLeyenda(mapa);
    }
  }

  contenedores.forEach(iniciarMapa);
})();