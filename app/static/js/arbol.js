// Si la dirección trae un ancla (#nodo-5), despliega ese recuadro del árbol y lo muestra.
(function () {
  if (!location.hash) return;
  var destino = null;
  try {
    destino = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  } catch (e) {
    return;
  }
  if (!destino) return;
  for (var el = destino; el; el = el.parentElement) {
    if (el.tagName === "DETAILS") el.open = true;
  }
  destino.scrollIntoView();
})();