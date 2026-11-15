"""Tradutor do AudioMail: usa o serviço de tradução do Google (sem chave de acesso).

O texto só é enviado quando o usuário pede para traduzir, e depois de ele autorizar.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import i18n

ENDPOINT = "https://translate.googleapis.com/translate_a/single"
ENC_LIMIT = 3500  # tamanho maximo do texto de cada pedido, ja codificado na URL

LANGS = [
    ("pt", "Português"), ("en", "Inglês"), ("es", "Espanhol"), ("fr", "Francês"),
    ("de", "Alemão"), ("it", "Italiano"), ("nl", "Holandês"), ("pl", "Polonês"),
    ("ru", "Russo"), ("uk", "Ucraniano"), ("tr", "Turco"), ("ar", "Árabe"),
    ("he", "Hebraico"), ("hi", "Hindi"), ("ja", "Japonês"), ("ko", "Coreano"),
    ("zh-CN", "Chinês simplificado"), ("zh-TW", "Chinês tradicional"),
    ("sv", "Sueco"), ("el", "Grego"), ("id", "Indonésio"), ("vi", "Vietnamita"),
    ("th", "Tailandês"),
]
ALIASES = {"iw": "he", "zh": "zh-CN"}


class TranslateError(Exception):
    pass


def lang_name(code):
    code = ALIASES.get(code, code)
    for c, name in LANGS:
        if c.lower() == str(code).lower():
            return i18n.tr(name)
    return str(code) or "idioma desconhecido"


def same_language(a, b):
    """'pt' e 'pt-BR' contam como o mesmo idioma; 'zh-CN' e 'zh-TW' não."""
    a, b = ALIASES.get(a, a), ALIASES.get(b, b)
    if not a or not b:
        return False
    if a.lower() == b.lower():
        return True
    base = a.split("-")[0].lower()
    return base == b.split("-")[0].lower() and base != "zh"


def _enc_len(text):
    return len(urllib.parse.quote(text))


def _fit(text, enc_limit):
    """Quantos caracteres do começo do texto cabem no limite (já codificado)."""
    n = min(len(text), enc_limit)
    while n > 1 and _enc_len(text[:n]) > enc_limit:
        n = int(n * 0.8)
    return max(n, 1)


def _cut(line, enc_limit):
    parts = []
    while _enc_len(line) > enc_limit:
        window = line[:_fit(line, enc_limit)]
        cut = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
        cut = cut + 1 if cut > 0 else window.rfind(" ")
        if cut <= 0:
            cut = len(window)
        parts.append(line[:cut].rstrip())
        line = line[cut:].lstrip()
    parts.append(line)
    return parts


def split_chunks(text, enc_limit=ENC_LIMIT):
    """Divide o texto em pedaços, sempre em quebras de linha (ou de frase, se a linha for enorme)."""
    chunks, current, size = [], [], 0
    for line in text.split("\n"):
        for piece in _cut(line, enc_limit):
            add = _enc_len(piece) + 3
            if current and size + add > enc_limit:
                chunks.append("\n".join(current))
                current, size = [], 0
            current.append(piece)
            size += add
    if current:
        chunks.append("\n".join(current))
    return chunks


def translate_chunk(chunk, target, source="auto", endpoint=ENDPOINT, timeout=20):
    params = urllib.parse.urlencode({"client": "gtx", "sl": source, "tl": target, "dt": "t",
                                     "ie": "UTF-8", "oe": "UTF-8", "q": chunk})
    req = urllib.request.Request(endpoint + "?" + params,
                                 headers={"User-Agent": "Mozilla/5.0 (AudioMail)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise TranslateError("O serviço de tradução limitou o uso. Tente de novo em alguns minutos.")
        raise TranslateError("O serviço de tradução respondeu com erro %s." % e.code)
    except Exception as e:
        raise TranslateError("Não consegui falar com o serviço de tradução: %s" % e)
    try:
        data = json.loads(raw)
        text = "".join(seg[0] for seg in data[0] if seg and seg[0])
        detected = data[2] if len(data) > 2 and isinstance(data[2], str) else ""
    except Exception:
        raise TranslateError("O serviço de tradução devolveu uma resposta que não entendi.")
    return text, detected


def translate_text(text, target, source="auto", progress=None, endpoint=ENDPOINT):
    """Traduz o texto. Devolve (texto traduzido, código do idioma detectado)."""
    if not text.strip():
        return text, ""
    chunks = split_chunks(text)
    out, detected = [], ""
    for i, chunk in enumerate(chunks, 1):
        if chunk.strip():
            piece, lang = translate_chunk(chunk, target, source, endpoint)
            out.append(piece)
            detected = detected or lang
        else:
            out.append(chunk)
        if progress:
            progress(i, len(chunks))
    return "\n".join(out), detected
