"""Texto legível de e-mails em HTML, links e cancelamento de inscrição. Sem interface.

Um e-mail em HTML (newsletter, loja, banco) vira texto corrido para o leitor de
tela: títulos e parágrafos separados, listas com marcador, texto escondido e
códigos de rastreio fora. Cada link fica marcado no texto como "[link N]" e vai
para uma lista à parte, com o texto e o site de destino, para abrir direto.
"""
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

LINK_MARK = re.compile(r"\[link (\d+)\]")
URL_IN_TEXT = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"'\]\)]+")
_TRAILING = ".,;:!?…"
# caracteres invisíveis que as newsletters usam para encher o "pré-cabeçalho"
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿͏­᠎"), None)
SAFE_SCHEMES = ("http", "https")
_UNSUBSCRIBE_WORDS = ("unsubscribe", "descadastr", "cancelar inscrição", "cancelar a inscrição",
                      "cancelar assinatura", "cancelar sua inscrição", "sair da lista",
                      "darse de baja", "darte de baja", "cancelar suscripción", "opt-out", "opt out")


def domain_of(url):
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_safe_link(url):
    return urlparse(url or "").scheme.lower() in SAFE_SCHEMES and bool(urlparse(url).hostname)


class _Readable(HTMLParser):
    BLOCK = {"p", "div", "tr", "table", "section", "article", "header", "footer", "blockquote",
             "center", "ul", "ol", "dl", "dt", "dd", "form", "address", "pre", "main", "nav", "aside"}
    HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP = {"script", "style", "head", "title", "noscript", "template", "svg", "object"}
    VOID = {"br", "img", "hr", "meta", "link", "input", "area", "base", "col", "wbr", "source"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []          # [(texto, url)]
        self.numbers = {}        # url -> número, para não repetir o mesmo link
        self.stack = []          # [(tag, escondido)]
        self.hidden = 0
        self.skip = 0
        self.anchor = None       # (url, posição em parts)

    @staticmethod
    def _is_hidden(attrs):
        style = re.sub(r"\s+", "", (attrs.get("style") or "").lower())
        return ("display:none" in style or "visibility:hidden" in style or "mso-hide:all" in style
                or "hidden" in attrs or (attrs.get("aria-hidden") == "true" and "max-height:0" in style))

    def _out(self, text):
        if not self.skip and not self.hidden:
            self.parts.append(text)

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in self.SKIP:
            self.skip += 1
            return
        if tag not in self.VOID:
            hid = self._is_hidden(a)
            self.stack.append((tag, hid))
            self.hidden += hid
        if tag == "br":
            self._out("\n")
        elif tag in self.HEADINGS:
            self._out("\n\n")
        elif tag in self.BLOCK:
            self._out("\n")
        elif tag == "li":
            self._out("\n• ")
        elif tag in ("td", "th"):
            self._out(" ")
        elif tag == "hr":
            self._out("\n")
        elif tag == "img":
            alt = re.sub(r"\s+", " ", a.get("alt", "")).strip()
            if alt and len(alt) <= 150 and not self._is_hidden(a):
                self._out(alt if self.anchor else "[%s]" % alt)
        elif tag == "a":
            self.anchor = (a.get("href", "").strip(), len(self.parts))

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "a" and self.anchor:
            self._close_anchor()
        if tag in self.VOID:
            return
        # fecha até a tag correspondente (HTML de e-mail costuma vir mal fechado)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, hid in self.stack[i:]:
                    self.hidden -= hid
                del self.stack[i:]
                break
        if tag in self.HEADINGS:
            self._out("\n\n")
        elif tag in self.BLOCK:
            self._out("\n")

    def _close_anchor(self):
        url, start = self.anchor
        self.anchor = None
        if self.skip or self.hidden or not is_safe_link(url):
            return
        text = re.sub(r"\s+", " ", "".join(self.parts[start:])).strip()
        number = self.numbers.get(url)
        if number is None:
            self.links.append((text or domain_of(url), url))
            number = self.numbers[url] = len(self.links)
        if not text:
            self.parts.append(domain_of(url))
        self.parts.append(" [link %d]" % number)

    def handle_data(self, data):
        self._out(data)


def tidy(text):
    text = text.translate(_INVISIBLE).replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line != "|")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_readable(html):
    """``(texto, links)``: o HTML como texto para ler e a lista [(texto, url)]."""
    parser = _Readable()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass
    if parser.anchor:
        parser._close_anchor()
    return tidy("".join(parser.parts)), parser.links


def links_in_text(text):
    """Links escritos no texto puro: [(url, url)], sem repetir, na ordem."""
    links, seen = [], set()
    for match in URL_IN_TEXT.finditer(text or ""):
        url = match.group(0).rstrip(_TRAILING)
        if url.lower().startswith("www."):
            url = "https://" + url
        if is_safe_link(url) and url not in seen:
            seen.add(url)
            links.append((url, url))
    return links


def merge_links(bodies_and_links):
    """Junta as mensagens de uma conversa numa só lista de links.

    Recebe [(texto, links)] e devolve ``(textos, links)``: os "[link N]" de cada
    mensagem são renumerados para apontar para a lista única."""
    all_links, bodies = [], []
    for body, links in bodies_and_links:
        offset = len(all_links)
        if offset:
            body = LINK_MARK.sub(lambda m: "[link %d]" % (int(m.group(1)) + offset), body)
        bodies.append(body)
        all_links.extend(links)
    return bodies, all_links


def link_label(number, text, url):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > 90:
        text = text[:87].rstrip() + "…"
    site = domain_of(url)
    return "%d. %s (%s)" % (number, text, site) if text and text != url else "%d. %s" % (number, site or url)


def link_on_line(line, links):
    """O link da linha onde o cursor está: o primeiro "[link N]" ou endereço escrito nela."""
    match = LINK_MARK.search(line or "")
    if match:
        number = int(match.group(1))
        if 1 <= number <= len(links):
            return links[number - 1][1]
    found = links_in_text(line)
    return found[0][1] if found else None


# ---------- cancelar inscrição ----------

def unsubscribe_options(list_unsubscribe, list_unsubscribe_post="", links=()):
    """O que dá para fazer para sair de uma lista de e-mails.

    Usa o cabeçalho List-Unsubscribe (o jeito oficial) e, sem ele, um link do
    texto chamado "cancelar inscrição" ou parecido. Devolve um dict com
    ``one_click`` (pedido automático, RFC 8058), ``https`` (página para abrir),
    ``mailto`` (e-mail para mandar) e ``link`` (link achado no texto), ou None."""
    found = re.findall(r"<([^>]+)>", list_unsubscribe or "")
    https = next((u.strip() for u in found if u.strip().lower().startswith("https://")
                  and is_safe_link(u.strip())), None)
    mailto = next((u.strip() for u in found if u.strip().lower().startswith("mailto:")), None)
    one_click = bool(https) and "list-unsubscribe=one-click" in (list_unsubscribe_post or "").lower()
    link = None
    if not (https or mailto):
        link = next((url for text, url in links
                     if any(word in (text or "").lower() for word in _UNSUBSCRIBE_WORDS)), None)
    if not (https or mailto or link):
        return None
    return {"one_click": one_click, "https": https, "mailto": mailto, "link": link}


def mailto_parts(mailto, default=""):
    """``(endereço, assunto, texto)`` de um link mailto:; ``default`` preenche o que faltar."""
    parsed = urlparse(mailto)
    address = unquote(parsed.path)
    query = parse_qs(parsed.query)
    subject = (query.get("subject") or [default])[0]
    body = (query.get("body") or [default])[0]
    return address, subject, body


def one_click_unsubscribe(url, timeout=20, opener=urllib.request.urlopen):
    """Pede o cancelamento automático (RFC 8058). Devolve True se o site aceitou."""
    if not url.lower().startswith("https://"):
        return False
    request = urllib.request.Request(url, data=b"List-Unsubscribe=One-Click", method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded",
                                              "User-Agent": "AudioMail"})
    with opener(request, timeout=timeout) as response:
        return 200 <= getattr(response, "status", 200) < 300
