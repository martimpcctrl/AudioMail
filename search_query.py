"""Busca avançada do AudioMail. Sem interface e sem rede.

O campo Buscar aceita o mesmo jeito de escrever do Gmail, em inglês ou em
português:  from:ana  subject:"nota fiscal"  has:attachment  is:unread
is:starred  newer_than:7d  older_than:1y  after:2026/01/31  before:2026/02/28
(de:, para:, assunto:, tem:anexo, é:não-lida, é:estrela, depois:, antes:).
O que não tem chave é procurado no texto todo.

No Gmail a busca vai inteira para o próprio buscador dele (X-GM-RAW). Nos
outros servidores vira uma busca IMAP; o que o IMAP não consegue mandar de uma
vez (mais de um texto com acento) é conferido aqui, nos cabeçalhos.
"""
import datetime
import re

_KEYS = {
    "from": "from", "de": "from",
    "to": "to", "para": "to",
    "subject": "subject", "assunto": "subject",
    "after": "after", "depois": "after", "desde": "after",
    "before": "before", "antes": "before",
    "newer_than": "newer", "recentes": "newer",
    "older_than": "older", "antigos": "older",
}
_FLAGS = {
    "has:attachment": "attachment", "tem:anexo": "attachment",
    "is:unread": "unread", "é:não-lida": "unread", "e:nao-lida": "unread", "é:nao-lida": "unread",
    "is:starred": "starred", "é:estrela": "starred", "e:estrela": "starred",
}
_TOKEN = re.compile(r'(\S+?:)?("[^"]*"|\S+)')
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def empty():
    return {"from": "", "to": "", "subject": "", "words": [], "attachment": False,
            "unread": False, "starred": False, "after": None, "before": None}


def _date(text):
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _relative(text, today):
    m = re.fullmatch(r"(\d+)([dmyaw])", text.lower())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    days = {"d": 1, "w": 7, "m": 30, "y": 365, "a": 365}[unit]
    return today - datetime.timedelta(days=n * days)


def parse_query(text, today=None):
    """Transforma o texto do campo Buscar num dict de critérios."""
    today = today or datetime.date.today()
    c = empty()
    for key, value in _TOKEN.findall(text or ""):
        whole = (key + value).lower()
        if whole in _FLAGS:
            c[_FLAGS[whole]] = True
            continue
        value = value.strip('"').strip()
        field = _KEYS.get(key[:-1].lower()) if key else None
        if key and field is None:
            value, field = key + value, None     # "http://..." ou chave desconhecida: texto
        if not value:
            continue
        if field in ("from", "to", "subject"):
            c[field] = (c[field] + " " + value).strip()
        elif field in ("after", "before"):
            day = _date(value)
            if day:
                c[field] = day
        elif field in ("newer", "older"):
            day = _relative(value, today)
            if day:
                c["after" if field == "newer" else "before"] = day
        else:
            c["words"].append(value)
    return c


def is_empty(c):
    return c == empty()


def _quote_gmail(value):
    return '"%s"' % value.replace('"', "") if " " in value else value


def to_gmail_raw(c, extra=""):
    """Texto para o buscador do Gmail (X-GM-RAW)."""
    parts = [extra] if extra else []
    for field in ("from", "to", "subject"):
        if c[field]:
            parts.append("%s:%s" % (field, _quote_gmail(c[field])))
    if c["attachment"]:
        parts.append("has:attachment")
    if c["unread"]:
        parts.append("is:unread")
    if c["starred"]:
        parts.append("is:starred")
    if c["after"]:
        parts.append("after:" + c["after"].strftime("%Y/%m/%d"))
    if c["before"]:
        parts.append("before:" + c["before"].strftime("%Y/%m/%d"))
    parts.extend(_quote_gmail(w) for w in c["words"])
    return " ".join(parts)


def imap_date(day):
    return "%02d-%s-%04d" % (day.day, _MONTHS[day.month - 1], day.year)


def _quote_imap(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_imap(c, flagged=False):
    """``(chaves, literal, conferir)`` para um UID SEARCH comum.

    chaves:   argumentos ASCII do SEARCH
    literal:  (chave, texto) com acento que vai por último como literal, ou None
    conferir: [(campo, texto)] com acento que sobraram, para conferir nos cabeçalhos"""
    keys, literal, check = [], None, []
    if c["unread"]:
        keys.append("UNSEEN")
    if c["starred"] or flagged:
        keys.append("FLAGGED")
    if c["after"]:
        keys += ["SINCE", imap_date(c["after"])]
    if c["before"]:
        keys += ["BEFORE", imap_date(c["before"])]
    if c["attachment"]:
        keys += ["HEADER", "Content-Type", '"multipart/mixed"']
    texts = [("FROM", "from", c["from"]), ("TO", "to", c["to"]), ("SUBJECT", "subject", c["subject"])]
    texts += [("TEXT", "words", w) for w in c["words"]]
    for imap_key, field, value in texts:
        if not value:
            continue
        if value.isascii():
            keys += [imap_key, _quote_imap(value)]
        elif literal is None:
            literal = (imap_key, value)
        else:
            check.append((field, value))
    return keys or (["ALL"] if literal is None else []), literal, check


def passes(msg, check):
    """Confere no cabeçalho o que não coube na busca do servidor."""
    for field, value in check:
        value = value.lower()
        if field == "from":
            hay = msg.get("from_raw") or msg.get("from") or ""
        elif field == "to":
            hay = msg.get("to_raw") or ""
        elif field == "subject":
            hay = msg.get("subject") or ""
        else:   # palavra solta: o corpo não está aqui, então remetente e assunto
            hay = " ".join((msg.get("from_raw") or "", msg.get("subject") or ""))
        if value not in hay.lower():
            return False
    return True


def build(from_="", to="", subject="", words="", attachment=False, unread=False, starred=False,
          period=""):
    """Texto do campo Buscar a partir da janela de busca avançada."""
    parts = []
    for key, value in (("from", from_), ("to", to), ("subject", subject)):
        value = value.strip().replace('"', "")
        if value:
            parts.append('%s:"%s"' % (key, value) if " " in value else "%s:%s" % (key, value))
    if attachment:
        parts.append("has:attachment")
    if unread:
        parts.append("is:unread")
    if starred:
        parts.append("is:starred")
    if period:
        parts.append(period)
    if words.strip():
        parts.append(words.strip())
    return " ".join(parts)


PERIODS = [("", "Qualquer data"), ("newer_than:1d", "Hoje e ontem"),
           ("newer_than:7d", "Últimos 7 dias"), ("newer_than:30d", "Últimos 30 dias"),
           ("newer_than:1y", "Último ano"), ("older_than:1y", "Mais de um ano atrás")]
