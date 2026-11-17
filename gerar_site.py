"""Gera o site oficial do AudioMail (várias páginas) a partir do manual e dos
textos legais do próprio programa, para o site nunca ficar diferente do app.

Uso: python gerar_site.py [pasta]   (padrão: docs, pronta para o GitHub Pages)
     python gerar_site.py pasta --artifact   (a página inicial sem o <!doctype>,
                                              para a prévia no claude.ai)
"""
import html
import json
import os
import re
import shutil
import sys

import legal
import manual
import release_notes
from version import APP_VERSION

REPO = "https://github.com/martimpcctrl/AudioMail"
DOWNLOAD = "%s/releases/latest/download/AudioMail-Portatil-%s.zip" % (REPO, APP_VERSION)
RELEASES = REPO + "/releases"
HERE = os.path.dirname(os.path.abspath(__file__))

PAGES = [("index.html", "Início"), ("manual.html", "Manual"), ("novidades.html", "Novidades"),
         ("privacidade.html", "Privacidade"), ("termos.html", "Termos de uso")]

NOT_OFFICIAL = ("O AudioMail é um programa independente e gratuito, feito por Martim Alves. "
                "Não é um aplicativo oficial do Google (Gmail), da Microsoft (Outlook), do Yahoo, "
                "da Apple (iCloud) nem de outro provedor de e-mail, e não tem ligação com essas empresas.")

KEY = re.compile(r"\b(?:(?:Ctrl|Alt|Shift|Windows)\s?\+\s?)+(?:[A-Z0-9]\b|Enter|Espaço|Delete|Del|Tab|Esc|"
                 r"F(?:1[0-2]|[1-9])\b)|\bF(?:1[0-2]|[1-9])\b")


# ---------- texto ----------

def keys(text):
    """Atalhos como Ctrl+Shift+F viram teclas (<kbd>) — o detalhe que mais aparece no manual."""
    def repl(m):
        parts = re.split(r"\s?\+\s?", m.group(0))
        return '<span class="combo">%s</span>' % '<span class="plus">+</span>'.join(
            "<kbd>%s</kbd>" % p for p in parts)
    return KEY.sub(repl, text)


def inline(text):
    out = html.escape(text, quote=False)
    out = re.sub(r"(https?://[^\s<)]+[^\s<).,;])", r'<a href="\1">\1</a>', out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    # as teclas só fora dos links e do código
    pieces = re.split(r"(<a [^>]*>.*?</a>|<code>.*?</code>)", out)
    return "".join(p if p.startswith(("<a ", "<code>")) else keys(p) for p in pieces)


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"`", "", text)).strip()


# ---------- manual ----------

def manual_sections(source):
    """[(id, título, [linhas])] do manual_fonte.txt."""
    sections, current = [], None
    for line in source.replace("{{versao}}", APP_VERSION).replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            current = (manual.slug(line[3:]), line[3:].strip(), [])
            sections.append(current)
        elif current is not None:
            current[2].append(line.rstrip())
    return sections


def blocks(lines):
    """Linhas do manual em HTML: listas, listas numeradas e parágrafos."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("### "):
            out.append("<h3>%s</h3>" % inline(line[4:]))
            i += 1
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li>%s</li>" % inline(lines[i][2:].strip()))
                i += 1
            out.append("<ul>%s</ul>" % "".join(items))
        elif re.match(r"\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append("<li>%s</li>" % inline(re.sub(r"^\d+\. ", "", lines[i]).strip()))
                i += 1
            out.append("<ol>%s</ol>" % "".join(items))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(#|- |\d+\. )", lines[i]):
                para.append(lines[i].strip())
                i += 1
            out.append("<p>%s</p>" % inline(" ".join(para)))
    return "\n".join(out)


# ---------- textos legais ----------

def legal_sections(text):
    """(versão, [(id, título, html, texto)]) de um documento de legal.py."""
    lines = [l.rstrip() for l in text.strip().split("\n")]
    version = lines[1] if len(lines) > 1 else ""
    sections, current = [], None
    for line in lines[2:]:
        if not line.strip():
            continue
        m = re.match(r"(\d+)\. (.+)", line)
        if m:
            current = ["secao-" + m.group(1), line, []]
            sections.append(current)
        elif current is not None:
            current[2].append(line)
    out = []
    for sid, title, body in sections:
        parts, items = [], []
        for line in body:
            if line.startswith("• "):
                items.append("<li>%s</li>" % inline(line[2:]))
                continue
            if items:
                parts.append("<ul>%s</ul>" % "".join(items))
                items = []
            parts.append("<p>%s</p>" % inline(line))
        if items:
            parts.append("<ul>%s</ul>" % "".join(items))
        out.append((sid, title, "\n".join(parts), plain(" ".join(b.lstrip("• ") for b in body))))
    return version, out


# ---------- páginas ----------

def page(file, title, main, description, artifact=False, extra_script=""):
    nav = "".join('<li><a href="%s"%s>%s</a></li>' % (f, ' aria-current="page"' if f == file else "", n)
                  for f, n in PAGES)
    head = ('<title>%s</title>\n'
            '<meta name="description" content="%s">\n'
            '<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:'
            'ital,wght@0,400;0,700;1,400&family=Lexend:wght@500;700&display=swap">\n'
            '<link rel="stylesheet" href="estilo.css">\n'
            % (html.escape(title), html.escape(description)))
    body = """<a class="skip" href="#conteudo">Pular para o conteúdo</a>
<header class="topo">
  <div class="faixa">
    <a class="marca" href="index.html" aria-label="AudioMail, página inicial">
      <span class="marca-icone" aria-hidden="true"></span>AudioMail
    </a>
    <nav aria-label="Páginas do site"><ul class="menu">%s</ul></nav>
    <a class="botao botao-pequeno" href="%s">Baixar</a>
  </div>
  <div class="faixa faixa-busca">
    <form class="busca" role="search" id="form-busca" action="#">
      <label for="campo-busca">Buscar no site</label>
      <div class="busca-linha">
        <input id="campo-busca" type="search" autocomplete="off"
               placeholder="Ex.: senha de app, anexo, Ctrl+I, privacidade">
        <button type="submit" class="botao">Buscar</button>
      </div>
      <p id="busca-status" class="busca-status" role="status" aria-live="polite"></p>
      <ol id="busca-resultados" class="busca-resultados" hidden></ol>
    </form>
  </div>
</header>
<main id="conteudo" tabindex="-1">
%s
</main>
<footer class="rodape">
  <div class="faixa rodape-faixa">
    <p class="aviso"><strong>Não é um aplicativo oficial.</strong> %s</p>
    <p>AudioMail %s · Gratuito, para Windows ·
      <a href="%s">Código e versões no GitHub</a> ·
      <a href="privacidade.html">Privacidade</a> · <a href="termos.html">Termos de uso</a></p>
  </div>
</footer>
<script src="busca-indice.js"></script>
<script src="busca.js"></script>
%s""" % (nav, DOWNLOAD, main, html.escape(NOT_OFFICIAL), APP_VERSION, REPO,
         '<script src="%s"></script>\n' % extra_script if extra_script else "")
    if artifact:
        return head + body
    return ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + '</head>\n<body>\n' + body + '</body>\n</html>\n')


FEATURES = [
    ("Feito para o teclado e o leitor de tela",
     "Funciona com NVDA, JAWS e Narrador. Tudo tem atalho, as listas falam o que importa "
     "(\"Caixa de entrada, 3 não lidas, 120 mensagens\") e nada depende do mouse."),
    ("Avisa na hora",
     "Mensagem nova toca som, fala pelo leitor de tela e mostra a notificação do Windows com os "
     "botões Responder, Arquivar e Marcar como lida."),
    ("Gmail e outros provedores",
     "Gmail, Yahoo, iCloud, Zoho, UOL, BOL, Terra e e-mail de domínio próprio. Várias contas ao mesmo tempo."),
    ("Lê sem internet",
     "As mensagens que você abre ficam guardadas no computador, criptografadas pelo Windows. "
     "Sem conexão, você continua lendo e buscando."),
    ("Anexos dentro do programa",
     "PDF, Word, Excel, PowerPoint e LibreOffice abrem como texto para ler com as setas. "
     "Fotos podem ser descritas por IA."),
    ("Organiza como os apps oficiais",
     "Arquivar, mover, estrela, spam, regras automáticas, bloquear remetente, desfazer e "
     "busca em todas as pastas."),
    ("Escreve melhor",
     "Contatos e grupos, respostas prontas, envio agendado, desfazer envio, assinatura por conta, "
     "tradução e Escrever com IA."),
    ("Calendário e convites",
     "Lembretes com aviso na hora e convites de reunião com Aceitar, Talvez e Recusar."),
]

SHORTCUTS = [("Ctrl+N", "nova mensagem"), ("Ctrl+R", "responder"), ("Ctrl+I", "boletim da caixa"),
             ("Ctrl+L", "ler o anexo"), ("Ctrl+Shift+T", "buscar em todas as pastas"),
             ("F1", "abrir o manual")]


def home():
    feats = "".join('<li class="recurso"><h3>%s</h3><p>%s</p></li>' % (html.escape(t), html.escape(d))
                    for t, d in FEATURES)
    shorts = "".join('<li>%s <span>%s</span></li>' % (keys(k), html.escape(d)) for k, d in SHORTCUTS)
    return """<section class="abertura faixa" aria-labelledby="titulo">
  <div class="abertura-texto">
    <p class="selo">Para Windows · Gratuito · Versão %(v)s</p>
    <h1 id="titulo">E-mail que se ouve.</h1>
    <p class="chamada">O AudioMail é um programa de e-mail feito para quem usa leitor de tela.
      Leia, responda e organize o Gmail e outros e-mails só com o teclado.</p>
    <div class="acoes">
      <a class="botao botao-grande" href="%(dl)s">Baixar o AudioMail %(v)s</a>
      <a class="link-forte" href="manual.html">Ler o manual</a>
    </div>
    <p class="detalhe">Arquivo zip, cerca de 40 MB. Extraia e abra o AudioMail.exe; não precisa instalar.
      Depois ele se atualiza sozinho. <a href="%(rel)s">Todas as versões</a>.</p>
  </div>
  <aside class="teclado" aria-labelledby="titulo-atalhos">
    <h2 id="titulo-atalhos">Alguns atalhos</h2>
    <ul class="atalhos">%(shorts)s</ul>
  </aside>
</section>
<section class="faixa aviso-oficial" aria-labelledby="titulo-aviso">
  <h2 id="titulo-aviso">Não é um aplicativo oficial</h2>
  <p>%(no)s</p>
</section>
<section class="faixa" aria-labelledby="titulo-recursos">
  <h2 id="titulo-recursos">O que ele faz</h2>
  <ul class="recursos">%(feats)s</ul>
</section>
<section class="faixa comecar" aria-labelledby="titulo-comecar">
  <h2 id="titulo-comecar">Como começar</h2>
  <ol class="passos">
    <li><strong>Baixe</strong> o arquivo zip pelo botão Baixar.</li>
    <li><strong>Extraia</strong> a pasta e abra o AudioMail.exe.</li>
    <li><strong>Entre</strong> com o seu e-mail. No Gmail, use uma senha de app;
      o <a href="manual.html#primeiros-passos">manual explica como criar</a>.</li>
  </ol>
  <p>Seus dados ficam no seu computador. Leia a <a href="privacidade.html">Política de privacidade</a>
    e os <a href="termos.html">Termos de uso</a>.</p>
</section>
""" % {"v": APP_VERSION, "dl": DOWNLOAD, "rel": RELEASES, "shorts": shorts, "feats": feats,
       "no": html.escape(NOT_OFFICIAL)}


def doc_page(heading, intro, toc, sections_html):
    toc_html = "".join('<li><a href="#%s">%s</a></li>' % (sid, html.escape(name)) for sid, name in toc)
    return """<div class="faixa documento">
  <nav class="indice" aria-labelledby="titulo-indice">
    <h2 id="titulo-indice">Nesta página</h2>
    <ol>%s</ol>
  </nav>
  <article class="texto">
    <h1>%s</h1>
    %s
    %s
  </article>
</div>""" % (toc_html, html.escape(heading), intro, sections_html)


def news_page(versions):
    """A página Novidades com as notas que vão no programa; o novidades.js troca
    pelas do GitHub quando abre, para a página mostrar a versão mais nova na hora."""
    sections = "".join(
        '<section aria-labelledby="versao-%s"><h2 id="versao-%s">Versão %s</h2>'
        '<p class="meta">%s</p>\n%s</section>\n'
        % (v["version"].replace(".", "-"), v["version"].replace(".", "-"), html.escape(v["version"]),
           html.escape(v["date"]), blocks(v["lines"])) for v in versions)
    newest = versions[0]["version"] if versions else ""
    return """<div class="faixa documento documento-unico">
  <article class="texto">
    <h1>Novidades do AudioMail</h1>
    <p class="meta">O que mudou em cada versão, da mais nova para a mais antiga.
      O AudioMail se atualiza sozinho; para baixar, use o botão Baixar.</p>
    <p id="novidades-status" class="meta" role="status" aria-live="polite"></p>
    <div id="lista-versoes" class="versoes" data-mais-nova="%s">
%s
    </div>
  </article>
</div>""" % (html.escape(newest), sections)


def build(out, artifact=False):
    os.makedirs(out, exist_ok=True)
    index = []
    with open(os.path.join(HERE, manual.SOURCE_NAME), encoding="utf-8") as f:
        msecs = manual_sections(f.read())
    for t, d in FEATURES:
        index.append({"t": t, "p": "Início", "u": "index.html#titulo-recursos", "x": d})
    # manual
    body = "".join('<section aria-labelledby="%s"><h2 id="%s">%s</h2>\n%s</section>\n'
                   % (sid, sid, inline(name), blocks(lines)) for sid, name, lines in msecs)
    intro = '<p class="meta">Versão %s. Atalhos aparecem como teclas, por exemplo %s.</p>' % (
        APP_VERSION, keys("Ctrl+N"))
    files = {"manual.html": ("Manual do AudioMail", doc_page("Manual do AudioMail", intro,
                                                             [(s, n) for s, n, _ in msecs], body),
                             "Como usar o AudioMail: contas, mensagens, anexos, atalhos e configurações.")}
    for sid, name, lines in msecs:
        index.append({"t": name, "p": "Manual", "u": "manual.html#" + sid,
                      "x": plain(" ".join(l.lstrip("-0123456789. ") for l in lines))})
    # privacidade e termos
    for key, file, desc in (("privacy", "privacidade.html", "Como o AudioMail trata os seus dados."),
                            ("terms", "termos.html", "As regras de uso do AudioMail.")):
        name, text = legal.DOCUMENTS["pt"][key]
        version, secs = legal_sections(text)
        sec_html = "".join('<section aria-labelledby="%s"><h2 id="%s">%s</h2>\n%s</section>\n'
                           % (sid, sid, html.escape(t), h) for sid, t, h, _ in secs)
        meta = '<p class="meta">%s</p>' % html.escape(version)
        files[file] = (name + " do AudioMail", doc_page(name, meta, [(s, t) for s, t, _, _ in secs], sec_html),
                       desc)
        for sid, t, _, x in secs:
            index.append({"t": t, "p": name, "u": "%s#%s" % (file, sid), "x": x})
    with open(os.path.join(HERE, release_notes.SOURCE_NAME), encoding="utf-8") as f:
        versions = release_notes.parse(f.read())
    files["novidades.html"] = ("Novidades do AudioMail", news_page(versions),
                               "O que mudou em cada versão do AudioMail.")
    for v in versions:
        index.append({"t": "Versão " + v["version"], "p": "Novidades",
                      "u": "novidades.html#versao-" + v["version"].replace(".", "-"),
                      "x": plain(" ".join(release_notes.clean(l.lstrip("-# ")) for l in v["lines"]))})
    files["index.html"] = ("AudioMail", home(),
                           "AudioMail: programa de e-mail gratuito para Windows feito para leitor de tela.")
    for file, (title, main, desc) in files.items():
        with open(os.path.join(out, file), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(file, title, main, desc, artifact and file == "index.html",
                         "novidades.js" if file == "novidades.html" else ""))
    with open(os.path.join(out, "busca-indice.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write("window.AUDIOMAIL_BUSCA = %s;\n" % json.dumps(index, ensure_ascii=False))
    for asset in ("estilo.css", "busca.js", "novidades.js"):
        shutil.copyfile(os.path.join(HERE, "site_fonte", asset), os.path.join(out, asset))
    return out, len(index)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder, n = build(args[0] if args else os.path.join(HERE, "docs"), "--artifact" in sys.argv)
    print("Site gerado em %s (%d itens na busca)" % (folder, n))
