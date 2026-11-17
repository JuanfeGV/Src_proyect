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
  var CAPAS_INDICADORES = {
    cobertura: {
      titulo: "Prioridad por cobertura rural",
      colores: { alta: "#dc3545", media: "#e0a800", baja: "#2f9e6e", ninguno: "#6c757d" },
      categorias: [
        ["alta", "Prioridad alta"],
        ["media", "Prioridad media"],
        ["baja", "Prioridad baja"],
        ["ninguno", "Sin dato válido de cobertura rural"],
      ],
    },
    recurrencia: {
      titulo: "Recurrencia histórica de desabastecimiento (ENA 2022)",
      colores: { baja: "#2f9e6e", media: "#e0a800", alta: "#dc3545", ninguno: "#6c757d" },
      categorias: [
        ["baja", "Recurrencia baja"],
        ["media", "Recurrencia media"],
        ["alta", "Recurrencia alta"],
        ["ninguno", "Sin clasificación documentada"],
      ],
    },
  };
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

  function agregarLinea(caja, etiqueta, valor) {
    var linea = document.createElement("div");
    var titulo = document.createElement("strong");
    titulo.textContent = etiqueta + ": ";
    linea.appendChild(titulo);
    linea.appendChild(document.createTextNode(valor));
    caja.appendChild(linea);
  }

  function contenidoGloboIndicador(punto, indicador) {
    var caja = document.createElement("div");
    var titulo = document.createElement("strong");
    titulo.textContent = punto.nombre;
    caja.appendChild(titulo);

    var datos = punto[indicador] || {};
    if (indicador === "cobertura") {
      agregarLinea(caja, "Indicador", "Prioridad por cobertura rural");
      var resultado = datos.prioridad
        ? datos.prioridad_texto + (datos.rural_porcentaje_texto ? " — " + datos.rural_porcentaje_texto + " % de cobertura rural" : "")
        : "Sin prioridad calculable por falta de un valor válido de cobertura rural";
      agregarLinea(caja, "Resultado", resultado);
    } else {
      agregarLinea(caja, "Indicador", "Recurrencia histórica de desabastecimiento");
      agregarLinea(caja, "Resultado", datos.nivel ? datos.texto : "Sin clasificación documentada");
      var aclaracion = document.createElement("p");
      aclaracion.className = "mb-1 mt-1";
      aclaracion.textContent =
        "Información histórica del ENA 2022; no es una alerta vigente ni una evaluación integral del riesgo actual.";
      caja.appendChild(aclaracion);
    }
    agregarLinea(caja, "Periodo", datos.periodo || (indicador === "cobertura" ? "2024" : "ENA 2022"));

    if (datos.fuente_url) {
      var fuente = document.createElement("div");
      var enlaceFuente = document.createElement("a");
      enlaceFuente.href = datos.fuente_url;
      enlaceFuente.target = "_blank";
      enlaceFuente.rel = "noopener noreferrer";
      enlaceFuente.textContent = "Consultar fuente oficial";
      fuente.appendChild(document.createTextNode("Fuente: "));
      fuente.appendChild(enlaceFuente);
      caja.appendChild(fuente);
    }

    if (punto.url) {
      var enlace = document.createElement("a");
      enlace.href = punto.url;
      enlace.textContent = "Ver ficha del municipio";
      caja.appendChild(enlace);
    }
    return caja;
  }

  function colorIndicador(punto, indicador) {
    var definicion = CAPAS_INDICADORES[indicador];
    var datos = punto[indicador] || {};
    var categoria = indicador === "cobertura" ? datos.prioridad : datos.nivel;
    return definicion.colores[categoria] || definicion.colores.ninguno;
  }

  function agregarSelectorIndicador(mapa, contenedor, alCambiar) {
    var selector = L.control({ position: "topright" });
    selector.onAdd = function () {
      var caja = L.DomUtil.create("div", "mapa-selector");
      var id = contenedor.id + "-indicador";
      var etiqueta = document.createElement("label");
      etiqueta.htmlFor = id;
      etiqueta.textContent = "Indicador del mapa";
      var select = document.createElement("select");
      select.id = id;
      select.className = "form-select form-select-sm";
      select.addEventListener("change", function () {
        alCambiar(select.value);
      });

      [
        ["cobertura", "Prioridad por cobertura rural (2024)"],
        ["recurrencia", "Recurrencia histórica (IDEAM ENA 2022)"],
      ].forEach(function (opcion) {
        var elemento = document.createElement("option");
        elemento.value = opcion[0];
        elemento.textContent = opcion[1];
        select.appendChild(elemento);
      });
      caja.appendChild(etiqueta);
      caja.appendChild(select);
      L.DomEvent.disableClickPropagation(caja);
      L.DomEvent.disableScrollPropagation(caja);
      return caja;
    };
    selector.addTo(mapa);
  }

  function agregarLeyendaIndicador(mapa, haySeleccionado, indicador) {
    var definicion = CAPAS_INDICADORES[indicador];
    var leyenda = L.control({ position: "bottomright" });
    leyenda.onAdd = function () {
      var caja = L.DomUtil.create("div", "leyenda-mapa leyenda-mapa--indicador");
      var titulo = document.createElement("div");
      titulo.className = "leyenda-mapa-titulo";
      titulo.textContent = definicion.titulo;
      caja.appendChild(titulo);

      definicion.categorias.forEach(function (categoria) {
        var fila = document.createElement("div");
        var color = document.createElement("span");
        color.className = "leyenda-color";
        color.style.background = definicion.colores[categoria[0]];
        fila.appendChild(color);
        fila.appendChild(document.createTextNode(categoria[1]));
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
    return leyenda;
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
    var usaIndicadores = contenedor.dataset.indicadores === "true";

    var mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(CENTRO_SABANA_CENTRO, 10);
    mapa.attributionControl.setPrefix(
      '<a href="https://leafletjs.com" target="_blank" rel="noopener noreferrer">Leaflet</a>'
    );
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution:
        '&copy; Colaboradores de <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>',
    }).addTo(mapa);

    if (!Array.isArray(puntos)) {
      if (aviso) aviso.textContent = "No se pudieron cargar los datos del mapa.";
      return;
    }

    var coordenadas = [];
    var marcadores = [];
    var haySeleccionado = false;
    puntos.forEach(function (punto) {
      if (!coordenadasValidas(punto)) return;
      var nivel = punto.nivel && tiene(COLORES, punto.nivel) ? punto.nivel : "ninguno";
      var seleccionado = punto.seleccionado === true;
      var marcador = L.circleMarker([punto.lat, punto.lng], {
        radius: seleccionado ? 13 : 10,
        color: seleccionado ? "#14558a" : "#ffffff",
        weight: seleccionado ? 4 : 2,
        fillColor: usaIndicadores ? colorIndicador(punto, "cobertura") : COLORES[nivel],
        fillOpacity: 0.9,
      }).addTo(mapa);
      marcador.bindTooltip(
        punto.nombre + (seleccionado ? " — municipio seleccionado" : "")
      );
      marcador.bindPopup(
        usaIndicadores
          ? contenidoGloboIndicador(punto, "cobertura")
          : contenidoGlobo(punto, nivel)
      );
      marcadores.push({ marcador: marcador, punto: punto });
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
    if (coordenadas.length && usaIndicadores) {
      var indicadorActual = "cobertura";
      var leyendaActiva = agregarLeyendaIndicador(mapa, haySeleccionado, indicadorActual);
      agregarSelectorIndicador(mapa, contenedor, function (nuevoIndicador) {
        if (!tiene(CAPAS_INDICADORES, nuevoIndicador)) return;
        indicadorActual = nuevoIndicador;
        marcadores.forEach(function (elemento) {
          var estabaAbierto = elemento.marcador.isPopupOpen();
          elemento.marcador.setStyle({
            fillColor: colorIndicador(elemento.punto, indicadorActual),
          });
          elemento.marcador.setPopupContent(
            contenidoGloboIndicador(elemento.punto, indicadorActual)
          );
          if (estabaAbierto) elemento.marcador.openPopup();
        });
        mapa.removeControl(leyendaActiva);
        leyendaActiva = agregarLeyendaIndicador(
          mapa,
          haySeleccionado,
          indicadorActual
        );
      });
    } else if (coordenadas.length) {
      agregarLeyenda(mapa, haySeleccionado);
    }
  }

  contenedores.forEach(iniciarMapa);
})();