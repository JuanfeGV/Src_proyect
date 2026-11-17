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
    if (!el) {
      console.error("No se encontraron los datos del mapa.");
      return null;
    }
    try {
      var puntos = JSON.parse(el.textContent);
      if (Array.isArray(puntos)) return puntos;
      console.error("Los datos del mapa no tienen el formato esperado.");
      return null;
    } catch (e) {
      console.error("No se pudieron leer los datos del mapa.", e);
      return null;
    }
  }

  function coordenadasValidas(punto) {
    return punto
      && typeof punto.lat === "number"
      && typeof punto.lng === "number"
      && Number.isFinite(punto.lat)
      && Number.isFinite(punto.lng)
      && punto.lat >= -90
      && punto.lat <= 90
      && punto.lng >= -180
      && punto.lng <= 180;
  }

  // El contenido del globo usa textContent para no interpretar el texto como HTML.
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
    if (punto.resumen) {
      var resumen = document.createElement("p");
      resumen.className = "mb-2 mt-1";
      resumen.textContent = punto.resumen;
      caja.appendChild(resumen);
    }
    if (punto.url) {
      var enlace = document.createElement("a");
      enlace.href = punto.url;
      enlace.textContent = "Ver ficha del municipio";
      caja.appendChild(enlace);
    }
    return caja;
  }

  function agregarLeyenda(mapa, haySeleccionado) {
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
      if (haySeleccionado) {
        var filaSeleccionado = document.createElement("div");
        var seleccionado = document.createElement("span");
        seleccionado.className = "leyenda-seleccionado";
        seleccionado.setAttribute("aria-hidden", "true");
        filaSeleccionado.appendChild(seleccionado);
        filaSeleccionado.appendChild(document.createTextNode("Municipio seleccionado"));
        caja.appendChild(filaSeleccionado);
      }
      return caja;
    };
    leyenda.addTo(mapa);
  }

  function iniciarMapa(contenedor) {
    var puntos = leerPuntos(contenedor);
    var aviso = contenedor.querySelector(".mapa-aviso");

    var mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(CENTRO_SABANA_CENTRO, 10);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; Colaboradores de OpenStreetMap",
    }).addTo(mapa);

    if (!Array.isArray(puntos)) {
      if (aviso) aviso.textContent = "No se pudieron cargar los datos del mapa.";
      return;
    }

    var coordenadas = [];
    var haySeleccionado = false;
    puntos.forEach(function (punto) {
      if (!coordenadasValidas(punto)) return;
      var nivel = punto.nivel && tiene(COLORES, punto.nivel) ? punto.nivel : "ninguno";
      var seleccionado = punto.seleccionado === true;
      var marcador = L.circleMarker([punto.lat, punto.lng], {
        radius: seleccionado ? 13 : 10,
        color: seleccionado ? "#14558a" : "#ffffff",
        weight: seleccionado ? 4 : 2,
        fillColor: COLORES[nivel],
        fillOpacity: 0.9,
      }).addTo(mapa);
      marcador.bindTooltip(
        punto.nombre + (seleccionado ? " — municipio seleccionado" : "")
      );
      marcador.bindPopup(contenidoGlobo(punto, nivel));
      coordenadas.push([punto.lat, punto.lng]);
      if (seleccionado) {
        haySeleccionado = true;
        marcador.bringToFront();
      }
    });

    if (aviso) {
      if (coordenadas.length) {
        aviso.remove();
      } else {
        aviso.textContent = "No hay municipios con coordenadas válidas para mostrar.";
      }
    }

    if (coordenadas.length === 1) {
      mapa.setView(coordenadas[0], Number(contenedor.dataset.zoom) || 12);
    } else if (coordenadas.length > 1) {
      mapa.fitBounds(coordenadas, { padding: [30, 30] });
    }
    if (coordenadas.length) agregarLeyenda(mapa, haySeleccionado);
  }

  contenedores.forEach(iniciarMapa);
})();