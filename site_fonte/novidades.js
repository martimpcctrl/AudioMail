/* Página Novidades: busca as notas direto das versões publicadas no GitHub.
   O que já está na página (gerado junto com o site) aparece primeiro; se o GitHub
   tiver algo mais novo, a lista é trocada e o leitor de tela avisa. Sem internet,
   ou com o GitHub fora do ar, a página continua com as notas que já tinha. */
(function () {
  var API = "https://api.github.com/repos/martimpcctrl/AudioMail/releases?per_page=60";
  var MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"];
  var lista = document.getElementById("lista-versoes");
  var aviso = document.getElementById("novidades-status");
  if (!lista || !window.fetch) return;

  function escapar(t) {
    return String(t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function inline(t) {
    return escapar(t)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  }
  function linhas(corpo) {
    return (corpo || "").replace(/\r\n/g, "\n").split("\n").filter(function (l) {
      return l.indexOf("**Para baixar:**") !== 0 && l.indexOf("são usados pelo atualizador automático") < 0;
    });
  }
  function blocos(corpo) {
    var out = [], lis = [], par = [];
    function fecha() {
      if (lis.length) { out.push("<ul>" + lis.join("") + "</ul>"); lis = []; }
      if (par.length) { out.push("<p>" + par.join(" ") + "</p>"); par = []; }
    }
    linhas(corpo).forEach(function (l) {
      var t = l.trim();
      if (!t) { fecha(); return; }
      if (/^#{2,3} /.test(t)) { fecha(); out.push("<h3>" + inline(t.replace(/^#+ /, "")) + "</h3>"); return; }
      if (/^- /.test(t)) { if (par.length) fecha(); lis.push("<li>" + inline(t.slice(2)) + "</li>"); return; }
      if (lis.length) fecha();
      par.push(inline(t));
    });
    fecha();
    return out.join("\n");
  }
  function data(iso) {
    var d = new Date(iso);
    return isNaN(d) ? "" : d.getDate() + " de " + MESES[d.getMonth()] + " de " + d.getFullYear();
  }
  function chave(v) {
    return v.split(".").map(function (n) { return ("0000" + n).slice(-4); }).join(".");
  }

  fetch(API, { headers: { "Accept": "application/vnd.github+json" } })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (versoes) {
      var boas = versoes.filter(function (r) {
        return !r.draft && !r.prerelease && /^v?\d+(\.\d+)*$/.test(r.tag_name || "");
      }).map(function (r) {
        return { v: r.tag_name.replace(/^v/i, ""), data: data(r.published_at), corpo: r.body };
      }).sort(function (a, b) { return chave(b.v) < chave(a.v) ? -1 : 1; });
      if (!boas.length) return;
      var atual = lista.getAttribute("data-mais-nova");
      lista.innerHTML = boas.map(function (r) {
        var id = "versao-" + r.v.replace(/\./g, "-");
        return '<section aria-labelledby="' + id + '"><h2 id="' + id + '">Versão ' + escapar(r.v) +
          '</h2><p class="meta">' + escapar(r.data) + "</p>\n" + blocos(r.corpo) + "</section>";
      }).join("\n");
      lista.setAttribute("data-mais-nova", boas[0].v);
      if (aviso && boas[0].v !== atual) {
        aviso.textContent = "Notas atualizadas. A versão mais nova é a " + boas[0].v + ".";
      }
      if (location.hash) {
        var alvo = document.getElementById(location.hash.slice(1));
        if (alvo) alvo.scrollIntoView();
      }
    })
    .catch(function () { /* sem internet: ficam as notas que já estavam na página */ });
})();
