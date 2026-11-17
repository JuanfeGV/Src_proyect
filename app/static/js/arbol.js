(function () {
  "use strict";

  var arboles = document.querySelectorAll(".arbol-componente");
  if (!arboles.length) return;

  arboles.forEach(inicializarArbol);

  function inicializarArbol(arbol) {
    var lienzo = arbol.querySelector(".arbol-lienzo");
    var nodos = Array.prototype.slice.call(arbol.querySelectorAll(".arbol-nodo"));
    var conectores = Array.prototype.slice.call(arbol.querySelectorAll(".arbol-conector"));
    var nodosPorId = new Map(nodos.map(function (nodo) {
      return [nodo.dataset.nodeId, nodo];
    }));
    var descripcion = arbol.querySelector("#arbol-detalle-descripcion");
    var titulo = arbol.querySelector("#arbol-detalle-titulo");
    var fuente = arbol.querySelector("#arbol-detalle-fuente");

    arbol.querySelectorAll(".arbol-control").forEach(function (control) {
      control.addEventListener("click", function () {
        var capa = arbol.querySelector("#" + control.dataset.targetLayer);
        if (!capa) return;
        var expandida = control.getAttribute("aria-expanded") !== "true";
        capa.hidden = !expandida;
        control.setAttribute("aria-expanded", String(expandida));
        control.textContent = (expandida ? "Contraer " : "Expandir ") + control.dataset.label;
        var seleccionado = arbol.querySelector(".arbol-nodo.is-selected");
        if (!expandida && seleccionado && capa.contains(seleccionado)) {
          var padre = nodosPorId.get(seleccionado.dataset.parentId);
          if (padre) {
            seleccionarNodo(padre);
          } else {
            nodos.forEach(function (nodo) {
              nodo.classList.remove("is-selected");
              nodo.setAttribute("aria-pressed", "false");
            });
            conectores.forEach(function (conector) {
              conector.classList.remove("is-highlighted");
            });
            titulo.textContent = "Detalle del nodo";
            descripcion.textContent = "Selecciona un nodo del diagrama para consultar su información.";
            fuente.replaceChildren();
          }
        }
        dibujarConectores();
      });
    });

    nodos.forEach(function (nodo) {
      nodo.addEventListener("click", function () {
        seleccionarNodo(nodo);
      });
    });

    function seleccionarNodo(seleccionado) {
      var camino = new Set();
      var actual = seleccionado;
      while (actual && !camino.has(actual.dataset.nodeId)) {
        camino.add(actual.dataset.nodeId);
        actual = nodosPorId.get(actual.dataset.parentId);
      }

      nodos.forEach(function (nodo) {
        var esSeleccionado = nodo === seleccionado;
        nodo.classList.toggle("is-selected", esSeleccionado);
        nodo.setAttribute("aria-pressed", String(esSeleccionado));
      });

      conectores.forEach(function (conector) {
        conector.classList.toggle(
          "is-highlighted",
          camino.has(conector.dataset.childId) && camino.has(conector.dataset.parentId)
        );
      });

      titulo.textContent = seleccionado.querySelector(".arbol-nodo-titulo").textContent;
      descripcion.textContent = seleccionado.dataset.description ||
        "No hay una descripción registrada para este nodo.";
      mostrarFuente(seleccionado.dataset.source || "");
    }

    function mostrarFuente(texto) {
      fuente.replaceChildren();
      if (!texto) {
        fuente.textContent = "No hay una fuente oficial registrada.";
        return;
      }

      fuente.appendChild(document.createTextNode("Fuente: "));
      var destino = destinoFuente(texto.trim());
      if (destino) {
        var enlace = document.createElement("a");
        enlace.href = destino.url;
        if (destino.externo) {
          enlace.target = "_blank";
          enlace.rel = "noopener noreferrer";
        }
        enlace.textContent = texto;
        fuente.appendChild(enlace);
      } else {
        fuente.appendChild(document.createTextNode(texto));
      }
    }

    function destinoFuente(texto) {
      if (!texto || texto.indexOf("\\") !== -1) return null;

      var url = texto;
      var externo = false;
      if (/^www\./i.test(texto)) {
        url = "https://" + texto;
        externo = true;
      } else if (/^https?:\/\//i.test(texto)) {
        externo = true;
      } else if (!/^(?:\/(?!\/)|\.\.?\/|#[A-Za-z0-9][\w:.-]*)/.test(texto)) {
        return null;
      }

      try {
        var destino = externo ? new URL(url) : new URL(url, window.location.origin);
        if (
          !/^https?:$/.test(destino.protocol) ||
          !destino.hostname ||
          destino.username ||
          destino.password ||
          (!externo && destino.origin !== window.location.origin)
        ) {
          return null;
        }
      } catch (error) {
        return null;
      }
      return { url: url, externo: externo };
    }

    function dibujarConectores() {
      var limitesLienzo = lienzo.getBoundingClientRect();
      var ancho = Math.max(limitesLienzo.width, 1);
      var alto = Math.max(limitesLienzo.height, 1);
      var svg = arbol.querySelector(".arbol-conectores");
      svg.setAttribute("viewBox", "0 0 " + ancho + " " + alto);
      svg.setAttribute("width", ancho);
      svg.setAttribute("height", alto);

      conectores.forEach(function (conector) {
        var padre = nodosPorId.get(conector.dataset.parentId);
        var hijo = nodosPorId.get(conector.dataset.childId);
        if (!padre || !hijo || padre.closest("[hidden]") || hijo.closest("[hidden]")) {
          conector.setAttribute("d", "");
          return;
        }

        var cajaPadre = padre.getBoundingClientRect();
        var cajaHijo = hijo.getBoundingClientRect();
        var baja = cajaPadre.top <= cajaHijo.top;
        var x1 = cajaPadre.left + cajaPadre.width / 2 - limitesLienzo.left;
        var x2 = cajaHijo.left + cajaHijo.width / 2 - limitesLienzo.left;
        var y1 = (baja ? cajaPadre.bottom : cajaPadre.top) - limitesLienzo.top;
        var y2 = (baja ? cajaHijo.top : cajaHijo.bottom) - limitesLienzo.top;
        var direccion = y2 >= y1 ? 1 : -1;
        var curva = Math.max(20, Math.abs(y2 - y1) * 0.42);
        conector.setAttribute(
          "d",
          "M " + x1 + " " + y1 +
            " C " + x1 + " " + (y1 + direccion * curva) +
            ", " + x2 + " " + (y2 - direccion * curva) +
            ", " + x2 + " " + y2
        );
      });
    }

    function seleccionarAncla() {
      if (!location.hash) return;
      var destino;
      try {
        destino = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      } catch (error) {
        return;
      }
      if (!destino || !arbol.contains(destino) || !destino.matches(".arbol-nodo")) return;

      var capaOculta = destino.closest("[hidden]");
      if (capaOculta) {
        var control = arbol.querySelector(
          '.arbol-control[data-target-layer="' + capaOculta.id + '"]'
        );
        if (control) control.click();
      }
      seleccionarNodo(destino);
      destino.scrollIntoView();
    }

    dibujarConectores();
    seleccionarAncla();
    window.addEventListener("resize", dibujarConectores);
    if (window.ResizeObserver) {
      var observador = new ResizeObserver(dibujarConectores);
      observador.observe(lienzo);
      nodos.forEach(function (nodo) {
        observador.observe(nodo);
      });
    }
  }
})();
