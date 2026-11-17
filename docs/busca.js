/* Busca do site: procura no manual, na privacidade e nos termos (busca-indice.js).
   Sem acento e sem diferença de maiúsculas: "politica" acha "Política". */
(function () {
  var itens = window.AUDIOMAIL_BUSCA || [];
  var form = document.getElementById("form-busca");
  var campo = document.getElementById("campo-busca");
  var status = document.getElementById("busca-status");
  var lista = document.getElementById("busca-resultados");
  if (!form || !campo) return;

  function normal(t) {
    return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  var preparados = itens.map(function (it) {
    return { it: it, titulo: normal(it.t), texto: normal(it.x) };
  });

  function trecho(texto, palavra) {
    var n = normal(texto);
    var i = n.indexOf(palavra);
    if (i < 0) return texto.slice(0, 160) + (texto.length > 160 ? "…" : "");
    var ini = Math.max(0, i - 60);
    var fim = Math.min(texto.length, i + palavra.length + 100);
    return (ini > 0 ? "…" : "") + texto.slice(ini, fim) + (fim < texto.length ? "…" : "");
  }

  function escapar(t) {
    return t.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function marcar(texto, palavras) {
    var html = escapar(texto);
    palavras.forEach(function (p) {
      if (p.length < 2) return;
      // marca ignorando acentos: percorre o texto original procurando a palavra normalizada
      var norm = normal(html), saida = "", i = 0, j;
      while ((j = norm.indexOf(p, i)) >= 0) {
        saida += html.slice(i, j) + "<mark>" + html.slice(j, j + p.length) + "</mark>";
        i = j + p.length;
      }
      html = saida + html.slice(i);
    });
    return html;
  }

  function buscar(consulta) {
    var frase = normal(consulta).trim();
    var todas = frase.split(/\s+/).filter(Boolean);
    // "de", "a", "o" não ajudam a achar nada; só contam se forem a busca inteira
    var palavras = todas.filter(function (w) { return w.length > 2; });
    if (!palavras.length) palavras = todas;
    lista.innerHTML = "";
    if (!palavras.length) {
      lista.hidden = true;
      status.textContent = "";
      return;
    }
    var achados = [];
    preparados.forEach(function (p) {
      var pontos = 0;
      for (var k = 0; k < palavras.length; k++) {
        var w = palavras[k];
        var noTitulo = p.titulo.indexOf(w) >= 0, noTexto = p.texto.indexOf(w) >= 0;
        if (!noTitulo && !noTexto) return;
        pontos += (noTitulo ? 5 : 0) + (noTexto ? 1 : 0);
      }
      if (todas.length > 1 && (p.titulo + " " + p.texto).indexOf(frase) >= 0) pontos += 8;
      achados.push({ p: p, pontos: pontos });
    });
    achados.sort(function (a, b) { return b.pontos - a.pontos; });
    achados = achados.slice(0, 20);
    if (!achados.length) {
      lista.hidden = true;
      status.textContent = "Nada encontrado para " + consulta + ". Tente outra palavra.";
      return;
    }
    achados.forEach(function (a) {
      var it = a.p.it;
      var li = document.createElement("li");
      li.innerHTML = '<a href="' + escapar(it.u) + '">' + marcar(it.t, palavras) + "</a>" +
        ' <span class="onde">(' + escapar(it.p) + ")</span><br>" +
        marcar(trecho(it.x, palavras[0]), palavras);
      lista.appendChild(li);
    });
    lista.hidden = false;
    status.textContent = achados.length === 1 ? "1 resultado." : achados.length + " resultados.";
  }

  var espera;
  campo.addEventListener("input", function () {
    clearTimeout(espera);
    espera = setTimeout(function () { buscar(campo.value); }, 250);
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    clearTimeout(espera);
    buscar(campo.value);
    var primeiro = lista.querySelector("a");
    if (primeiro) primeiro.focus();
  });
  campo.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      campo.value = "";
      buscar("");
    }
  });
})();
