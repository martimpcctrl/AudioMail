"""Núcleo de e-mail do AudioMail: IMAP e SMTP, sem nada de interface."""
import base64
import imaplib
import mimetypes
import os
import re
import smtplib
import socket
import ssl
import threading
import time
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import (formataddr, formatdate, getaddresses, make_msgid,
                         parseaddr, parsedate_to_datetime)
from html.parser import HTMLParser

import i18n
import message_text as mt
import search_query as sq
from contacts import parse_addresses

_OUTLOOK = ("outlook.office365.com", 993, "smtp-mail.outlook.com", 587, "starttls")
_YAHOO = ("imap.mail.yahoo.com", 993, "smtp.mail.yahoo.com", 465, "ssl")
_GMAIL = ("imap.gmail.com", 993, "smtp.gmail.com", 465, "ssl")

# dominio: (servidor imap, porta imap, servidor smtp, porta smtp, seguranca smtp)
PRESETS = {
    "gmail.com": _GMAIL,
    "googlemail.com": _GMAIL,
    "outlook.com": _OUTLOOK,
    "hotmail.com": _OUTLOOK,
    "live.com": _OUTLOOK,
    "yahoo.com": _YAHOO,
    "yahoo.com.br": _YAHOO,
    "icloud.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587, "starttls"),
}


class MailError(Exception):
    pass


# ---------- utilidades puras (testaveis sem rede) ----------

def decode_imap_utf7(text):
    def repl(m):
        chunk = m.group(1)
        if chunk == "":
            return "&"
        chunk = chunk.replace(",", "/")
        chunk += "=" * (-len(chunk) % 4)
        return base64.b64decode(chunk).decode("utf-16-be")
    return re.sub(r"&([^-]*)-", repl, text)


def encode_imap_utf7(text):
    """O contrário de decode_imap_utf7: nome com acentos para o servidor."""
    out, buf = [], []

    def flush():
        if buf:
            data = "".join(buf).encode("utf-16-be")
            out.append("&" + base64.b64encode(data).decode().rstrip("=").replace("/", ",") + "-")
            buf.clear()

    for ch in text:
        if 0x20 <= ord(ch) <= 0x7e:
            flush()
            out.append("&-" if ch == "&" else ch)
        else:
            buf.append(ch)
    flush()
    return "".join(out)


def quote_folder(raw):
    return '"' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_list_item(item):
    """Converte uma linha da resposta LIST em dict com raw, flags."""
    if isinstance(item, tuple):
        head = item[0].decode("utf-8", "replace")
        raw = item[1].decode("utf-8", "replace")
        m = re.match(r"\((?P<flags>[^)]*)\)", head)
        flags = m.group("flags") if m else ""
    elif isinstance(item, bytes):
        line = item.decode("utf-8", "replace")
        m = re.match(r'\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$', line)
        if not m:
            return None
        flags = m.group("flags")
        raw = m.group("name").strip()
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            raw = raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    else:
        return None
    return {"raw": raw, "flags": {f.lower() for f in flags.split()}}


_SPECIAL_NAMES = [
    ("\\inbox", "Caixa de entrada"),
    ("\\sent", "Enviados"),
    ("\\drafts", "Rascunhos"),
    ("\\trash", "Lixeira"),
    ("\\junk", "Spam"),
    ("\\archive", "Arquivo"),
    ("\\all", "Todos os e-mails"),
    ("\\flagged", "Com estrela"),
]


def folder_display(folder):
    raw = folder["raw"]
    if raw.upper() == "INBOX":
        return "Caixa de entrada"
    for flag, label in _SPECIAL_NAMES:
        if flag in folder["flags"]:
            return label
    return decode_imap_utf7(raw)


def folder_sort_key(folder):
    if folder["raw"].upper() == "INBOX":
        return (0, "")
    for i, (flag, _) in enumerate(_SPECIAL_NAMES):
        if flag in folder["flags"]:
            return (1 + i, "")
    return (20, folder["display"].lower())


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
             "table", "ul", "ol", "blockquote"}
    SKIP = {"script", "style", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag == "a":
            self.href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag == "a":
            if self.href and self.href.startswith("http") and not self.skip:
                self.parts.append(" (" + self.href + ")")
            self.href = None

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html):
    """Texto simples (antigo); a leitura usa message_text.html_to_readable."""
    p = _HTMLText()
    p.feed(html)
    text = "".join(p.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fmt_date(value):
    try:
        return parsedate_to_datetime(value).astimezone().strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value or ""


def short_sender(value):
    name, addr = parseaddr(value or "")
    return name or addr or (value or "")


def _h(msg, name):
    try:
        return str(msg.get(name, "") or "")
    except Exception:
        return ""


def parse_header_fetch(data):
    """Le a resposta de UID FETCH (FLAGS + cabeçalhos) e devolve lista de dicts."""
    out = []
    for i, item in enumerate(data):
        if not isinstance(item, tuple):
            continue
        meta = item[0].decode("utf-8", "replace")
        if i + 1 < len(data) and isinstance(data[i + 1], bytes):
            meta += " " + data[i + 1].decode("utf-8", "replace")
        uid = re.search(r"UID (\d+)", meta)
        if not uid:
            continue
        thrid = re.search(r"X-GM-THRID (\d+)", meta)
        labels = parse_labels(meta)
        flags = re.search(r"FLAGS \(([^)]*)\)", meta)
        flagset = {f.lower() for f in (flags.group(1).split() if flags else [])}
        hdr = message_from_bytes(item[1], policy=policy.default)
        sender = _h(hdr, "From")
        out.append({
            "uid": uid.group(1),
            "from": short_sender(sender),
            "from_raw": sender,
            "to_raw": _h(hdr, "To"),
            "subject": _h(hdr, "Subject") or "(sem assunto)",
            "date": fmt_date(_h(hdr, "Date")),
            "unread": "\\seen" not in flagset,
            "flagged": "\\flagged" in flagset,
            "thrid": thrid.group(1) if thrid else None,
            "labels": labels,
        })
    out.sort(key=lambda m: int(m["uid"]), reverse=True)
    return out


def _label_tokens(text):
    """Itens de uma lista IMAP entre parênteses: "texto com espaço" ou átomo."""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            j, buf = i + 1, []
            while j < len(text) and text[j] != '"':
                if text[j] == "\\" and j + 1 < len(text):
                    j += 1
                buf.append(text[j])
                j += 1
            out.append("".join(buf))
            i = j + 1
        elif ch == ")":
            break
        elif ch.isspace():
            i += 1
        else:
            j = i
            while j < len(text) and not text[j].isspace() and text[j] != ")":
                j += 1
            out.append(text[i:j])
            i = j
    return out


def parse_labels(meta):
    """Marcadores do Gmail (X-GM-LABELS) que a pessoa criou; os do sistema
    (\\Inbox, \\Important...) ficam de fora."""
    m = re.search(r"X-GM-LABELS \(", meta or "")
    if not m:
        return []
    return [decode_imap_utf7(t) for t in _label_tokens(meta[m.end():])
            if t and not t.startswith("\\")]


def parse_fetch_items(data):
    """Resposta de um UID FETCH com várias partes por mensagem:
    {uid: {"meta": texto, "parts": {seção: bytes}}}."""
    out, current = {}, None
    for item in data or []:
        if isinstance(item, tuple):
            meta = item[0].decode("utf-8", "replace")
            if re.match(r"\s*\d+ \(", meta):
                current = {"meta": "", "parts": {}}
            if current is None:
                continue
            current["meta"] += " " + meta
            sec = re.findall(r"BODY\[([^\]]*)\](?:<\d+>)?\s*\{\d+\}\s*$", meta)
            if sec:
                current["parts"][sec[-1]] = item[1]
        elif isinstance(item, bytes) and current is not None:
            current["meta"] += " " + item.decode("utf-8", "replace")
        else:
            continue
        uid = re.search(r"UID (\d+)", current["meta"])
        if uid:
            out[uid.group(1)] = current
    return out


def snippet_from_raw(header_bytes, text_bytes, limit=140):
    """O começo do texto de uma mensagem para a prévia da lista, a partir do
    cabeçalho de tipo e dos primeiros bytes do corpo (pode vir cortado)."""
    try:
        msg = message_from_bytes((header_bytes or b"").rstrip(b"\r\n") + b"\r\n\r\n" + (text_bytes or b""),
                                 policy=policy.default)
        part = msg.get_body(preferencelist=("plain", "html"))
    except Exception:
        return ""
    if part is None:
        return ""
    cte = str(part.get("Content-Transfer-Encoding", "")).lower()
    raw = part.get_payload(decode=False) or ""
    if isinstance(raw, list):
        return ""
    try:
        if "base64" in cte:
            # o corpo vem cortado: decodifica só os blocos inteiros de 4 letras
            clean = re.sub(r"[^A-Za-z0-9+/]", "", raw)
            text = base64.b64decode(clean[:len(clean) // 4 * 4]).decode(
                part.get_content_charset() or "utf-8", "replace")
        else:
            text = part.get_content()
    except Exception:
        try:
            text = raw.encode("latin-1", "replace").decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:
            return ""
    if part.get_content_type() == "text/html":
        text, _ = mt.html_to_readable(text)
        text = mt.LINK_MARK.sub("", text)
    lines = []
    for line in text.replace("\r", "").split("\n"):
        line = line.strip()
        if line.startswith(">") or re.match(r"(?i)^(em|on|el) .{5,80}(escreveu|wrote|escribió):$", line):
            break
        if line:
            lines.append(line)
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def parse_full_message(raw_bytes, uid):
    msg = message_from_bytes(raw_bytes, policy=policy.default)
    body, links = "", []
    # O HTML vira texto organizado, com os links numerados; o texto puro das
    # newsletters costuma ser uma sopa de endereços compridos.
    part = msg.get_body(preferencelist=("html", "plain"))
    if part is not None:
        try:
            body = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            body = payload.decode("utf-8", "replace")
        if part.get_content_type() == "text/html":
            body, links = mt.html_to_readable(body)
        else:
            links = mt.links_in_text(body)
    attachments = []
    try:
        for i, p in enumerate(msg.iter_attachments(), 1):
            data = part_bytes(p)
            name = p.get_filename() or ("anexo%d%s" % (
                i, mimetypes.guess_extension(p.get_content_type()) or ""))
            attachments.append({"name": name, "size": len(data),
                                "type": p.get_content_type(), "part": p})
    except Exception:
        pass
    return {
        "uid": uid,
        "from": _h(msg, "From"),
        "to": _h(msg, "To"),
        "cc": _h(msg, "Cc"),
        "bcc": _h(msg, "Bcc"),
        "reply_to": _h(msg, "Reply-To"),
        "subject": _h(msg, "Subject") or "(sem assunto)",
        "date": fmt_date(_h(msg, "Date")),
        "message_id": _h(msg, "Message-ID"),
        "references": _h(msg, "References"),
        "body": body.replace("\r\n", "\n").strip(),
        "links": links,
        "list_unsubscribe": _h(msg, "List-Unsubscribe"),
        "list_unsubscribe_post": _h(msg, "List-Unsubscribe-Post"),
        "attachments": attachments,
    }


def build_forward(orig):
    """Assunto e texto para encaminhar uma mensagem (os anexos vão à parte)."""
    subject = orig["subject"] or ""
    prefix = i18n.tr("Enc:")
    if not re.match(r"(?i)\s*(enc|fwd?|rv)\s*:", subject):
        subject = "%s %s" % (prefix, subject)
    lines = ["", "", i18n.tr("---------- Mensagem encaminhada ----------"),
             i18n.tr("De: %s") % orig["from"], i18n.tr("Data: %s") % orig["date"],
             i18n.tr("Assunto: %s") % orig["subject"]]
    if orig.get("to"):
        lines.append(i18n.tr("Para: %s") % orig["to"])
    if orig.get("cc"):
        lines.append(i18n.tr("Cópia: %s") % orig["cc"])
    body = "\n".join(lines) + "\n\n" + (orig.get("body") or "")
    return {"subject": subject.strip(), "body": body}


def state_text(row):
    """Coluna Estado da lista: não lida e/ou com estrela."""
    parts = []
    if row.get("unread"):
        parts.append(i18n.tr("Não lida"))
    if row.get("flagged"):
        parts.append(i18n.tr("Com estrela"))
    parts.extend(row.get("labels") or [])     # marcadores do Gmail
    return ", ".join(parts)


def build_reply(orig, my_email, reply_all=False):
    to = orig["reply_to"] or orig["from"]
    cc = ""
    if reply_all:
        seen = {parseaddr(to)[1].lower(), my_email.lower()}
        others = []
        for name, addr in parse_addresses(orig["to"], orig["cc"]):
            if addr and addr.lower() not in seen:
                seen.add(addr.lower())
                others.append(formataddr((name, addr)))
        cc = ", ".join(others)
    subject = orig["subject"]
    if not re.match(r"(?i)^\s*(re|res)\s*:", subject):
        subject = "Re: " + subject
    quoted = "\n".join("> " + line for line in orig["body"].splitlines())
    body = "\n\nEm %s, %s escreveu:\n%s" % (orig["date"], orig["from"], quoted)
    refs = (orig["references"] + " " + orig["message_id"]).strip()
    return {"to": to, "cc": cc, "subject": subject, "body": body,
            "in_reply_to": orig["message_id"] or None, "references": refs or None}


def part_bytes(part):
    """Conteudo bruto (ja decodificado) de uma parte de e-mail."""
    if part.get_content_maintype() == "message":
        inner = part.get_payload()
        if isinstance(inner, list) and inner:
            return inner[0].as_bytes()
    data = part.get_payload(decode=True)
    return data if data is not None else b""


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "").strip(" .")
    return name or "anexo"


def format_size(n):
    if n < 1024:
        return "%d bytes" % n
    if n < 1024 * 1024:
        return "%.0f KB" % (n / 1024)
    return "%.1f MB" % (n / (1024 * 1024))


def save_attachment(att, path):
    with open(path, "wb") as f:
        f.write(part_bytes(att["part"]))


def message_header(full):
    lines = ["De: " + full["from"], "Para: " + full["to"]]
    if full.get("cc"):
        lines.append("Cópia: " + full["cc"])
    if full.get("bcc"):
        lines.append("Cópia oculta: " + full["bcc"])
    lines.append("Assunto: " + full["subject"])
    lines.append("Data: " + full["date"])
    if full["attachments"]:
        lines.append("Anexos: " + ", ".join(a["name"] for a in full["attachments"]))
    return "\n".join(lines)


def render_text(prefix, sections, bodies=None):
    """Monta o texto da leitura. sections = [(cabecalho, corpo)]; bodies troca os corpos (traducao)."""
    bodies = bodies if bodies is not None else [body for _, body in sections]
    blocks = ["%s\n\n%s" % (head, body or "(mensagem sem texto)")
              for (head, _), body in zip(sections, bodies)]
    text = ("\n\n" + "-" * 40 + "\n\n").join(blocks)
    return (prefix + "\n\n" + text) if prefix else text


def full_to_text(full):
    return render_text("", [(message_header(full), full["body"])])


_PREFIX = re.compile(r"^\s*((re|res|fwd|fw|enc|rv|tr)\s*(\[\d+\])?\s*:\s*)+", re.I)


def normalize_subject(subject):
    return re.sub(r"\s+", " ", _PREFIX.sub("", subject or "")).strip()


def _row(msgs):
    msgs = sorted(msgs, key=lambda m: int(m["uid"]), reverse=True)
    newest = msgs[0]
    if len(msgs) == 1:
        sender, subject = newest["from"], newest["subject"]
    else:
        senders = []
        for m in msgs:
            if m["from"] not in senders:
                senders.append(m["from"])
        sender = ", ".join(senders[:3]) + (" e outros" if len(senders) > 3 else "")
        subject = (normalize_subject(newest["subject"]) or newest["subject"]) + \
            "  (%d mensagens)" % len(msgs)
    return {"uids": [m["uid"] for m in msgs], "from": sender, "subject": subject,
            "date": newest["date"], "unread": any(m["unread"] for m in msgs),
            "flagged": any(m.get("flagged") for m in msgs),
            "labels": list(newest.get("labels") or []),
            "from_raw": newest.get("from_raw", ""), "count": len(msgs)}


def build_rows(msgs, grouped):
    """Linhas da lista: uma por mensagem, ou uma por conversa quando agrupado."""
    if not grouped:
        return [_row([m]) for m in msgs]
    groups, order = {}, []
    for m in sorted(msgs, key=lambda m: int(m["uid"]), reverse=True):
        key = m.get("thrid") or ("s:" + normalize_subject(m["subject"]).lower())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(m)
    return [_row(groups[k]) for k in order]


MAX_ATTACH = 18 * 1024 * 1024  # o Gmail limita a mensagem a 25 MB depois da codificacao


def build_message(sender, to, cc, bcc, subject, body, in_reply_to=None,
                  references=None, attachments=None, draft=False):
    to, cc, bcc = (x.replace(";", ",") for x in (to or "", cc or "", bcc or ""))
    recipients = [a for _, a in parse_addresses(to, cc, bcc)]
    if not recipients and not draft:
        raise MailError("Informe pelo menos um destinatário.")
    msg = EmailMessage()
    msg["From"] = sender
    if to.strip():
        msg["To"] = to
    if cc.strip():
        msg["Cc"] = cc
    if draft and bcc.strip():
        msg["Bcc"] = bcc  # so no rascunho; no envio o CCO nunca vai no cabecalho
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[-1])
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg.set_content(body)
    total = 0
    for path in attachments or []:
        try:
            total += os.path.getsize(path)
            if total > MAX_ATTACH:
                raise MailError("Os anexos passam do limite de envio (cerca de 18 MB no total).")
            ctype, enc = mimetypes.guess_type(path)
            if not ctype or enc:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            raise MailError("Não foi possível ler o anexo %s: %s" % (os.path.basename(path), e))
        msg.add_attachment(data, maintype=maintype, subtype=subtype,
                           filename=os.path.basename(path))
    return msg, recipients


def parse_appenduid(data):
    for item in data or []:
        if isinstance(item, bytes):
            item = item.decode("utf-8", "replace")
        m = re.search(r"APPENDUID \d+ (\d+)", str(item))
        if m:
            return m.group(1)
    return None


def find_new(msgs, baseline_uid):
    """Mensagens nao lidas com UID maior que o ultimo visto."""
    return [m for m in msgs if m["unread"] and int(m["uid"]) > baseline_uid]


def format_notification(new):
    """Devolve (titulo, texto) para a notificacao de mensagens novas."""
    if len(new) == 1:
        return (i18n.tr("Nova mensagem de %s") % new[0]["from"], new[0]["subject"])
    names = []
    for m in new:
        if m["from"] not in names:
            names.append(m["from"])
    shown = ", ".join(names[:3])
    if len(names) > 3:
        shown += i18n.tr(" e outros")
    return (i18n.tr("%d novas mensagens") % len(new), i18n.tr("De %s") % shown)


# ---------- cliente ----------

class MailClient:
    def __init__(self, email, password, imap_host, imap_port,
                 smtp_host, smtp_port, smtp_security="ssl"):
        self.email = email
        self.password = password
        if "gmail" in imap_host.lower():
            self.password = password.replace(" ", "")
        self.imap_host = imap_host
        self.imap_port = int(imap_port)
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_security = smtp_security
        self.imap = None
        self.selected = None
        self.folders = []
        self.gmail = "gmail" in imap_host.lower()   # conversas (X-GM-THRID) so no Gmail
        self.can_move = False
        self.lock = threading.RLock()

    # conexao
    def connect(self):
        with self.lock:
            try:
                if self.imap_port == 143:
                    self.imap = imaplib.IMAP4(self.imap_host, self.imap_port)
                    self.imap.starttls(ssl.create_default_context())
                else:
                    self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port,
                                                  ssl_context=ssl.create_default_context())
                self.imap.login(self.email, self.password)
                caps = [c.upper() for c in (self.imap.capabilities or ())]
                self.gmail = "X-GM-EXT-1" in caps
                self.can_move = "MOVE" in caps
            except imaplib.IMAP4.error as e:
                raise MailError("Não foi possível entrar. Confira o e-mail e a senha de app. "
                                "Detalhe: %s" % e)
            except OSError as e:
                raise MailError("Não foi possível conectar ao servidor %s. Detalhe: %s"
                                % (self.imap_host, e))
            self.selected = None

    def close(self):
        with self.lock:
            try:
                if self.imap:
                    self.imap.logout()
            except Exception:
                pass
            self.imap = None

    def _ensure(self):
        try:
            self.imap.noop()
        except Exception:
            self.connect()

    def _select(self, raw):
        if self.selected != raw:
            typ, data = self.imap.select(quote_folder(raw))
            if typ != "OK":
                raise MailError("Não foi possível abrir a pasta.")
            self.selected = raw

    # pastas
    def list_folders(self):
        with self.lock:
            self._ensure()
            typ, data = self.imap.list()
            if typ != "OK":
                raise MailError("Não foi possível listar as pastas.")
            folders = []
            for item in data:
                f = parse_list_item(item)
                if f and "\\noselect" not in f["flags"]:
                    f["display"] = folder_display(f)
                    folders.append(f)
            folders.sort(key=folder_sort_key)
            self.folders = folders
            return folders

    def _find_special(self, flag, names):
        for f in self.folders:
            if flag in f["flags"]:
                return f["raw"]
        for f in self.folders:
            if decode_imap_utf7(f["raw"]).lower().split("/")[-1] in names:
                return f["raw"]
        return None

    # mensagens
    def fetch_headers(self, folder_raw, limit=100, with_total=False):
        """As ``limit`` mensagens mais novas da pasta (com o total, se pedido)."""
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            typ, data = self.imap.uid("SEARCH", None, "ALL")
            if typ != "OK":
                raise MailError("Falha ao buscar mensagens.")
            uids = data[0].split()
            msgs = self._headers_for(uids[-limit:])
        return (msgs, len(uids)) if with_total else msgs

    def search(self, folder_raw, query, limit=100, flagged=False):
        """Busca simples (texto do campo Buscar); devolve só as mensagens."""
        return self.search_query(folder_raw, query, limit,
                                 view_filter="flagged" if flagged else None)[0]

    def search_query(self, folder_raw, query, limit=100, view_filter=None):
        """Busca com o jeito de escrever do Gmail (veja search_query.py).
        ``view_filter``: None, "flagged" (só com estrela) ou "category:..." (aba do Gmail).
        Devolve (mensagens, total encontrado)."""
        c = sq.parse_query(query)
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            check = []
            if self.gmail and (not sq.is_empty(c) or (view_filter or "").startswith("category:")):
                extra = view_filter if (view_filter or "").startswith("category:") else ""
                if view_filter == "flagged":
                    c["starred"] = True
                typ, data = self._search_literal([], ("X-GM-RAW", sq.to_gmail_raw(c, extra)))
            else:
                keys, literal, check = sq.to_imap(c, flagged=view_filter == "flagged")
                typ, data = self._search_literal(keys, literal)
            if typ != "OK":
                raise MailError("Falha na busca.")
            uids = data[0].split() if data and data[0] else []
            if not check:
                return self._headers_for(uids[-limit:]), len(uids)
            # parte da busca é conferida aqui: lê mais cabeçalhos para sobrar o bastante
            msgs = [m for m in self._headers_for(uids[-limit * 3:]) if sq.passes(m, check)]
            return msgs[:limit], len(msgs)

    def _search_literal(self, keys, literal):
        if literal is None:
            return self.imap.uid("SEARCH", None, *keys)
        self.imap.literal = literal[1].encode("utf-8")
        try:
            return self.imap.uid("SEARCH", "CHARSET", "UTF-8", *keys, literal[0])
        finally:
            self.imap.literal = None

    def snippets(self, folder_raw, uids, size=4096):
        """{uid: começo do texto} para a prévia da lista. Nunca levanta erro."""
        if not uids:
            return {}
        try:
            with self.lock:
                self._ensure()
                self._select(folder_raw)
                typ, data = self.imap.uid(
                    "FETCH", ",".join(uids),
                    "(BODY.PEEK[HEADER.FIELDS (CONTENT-TYPE CONTENT-TRANSFER-ENCODING MIME-VERSION)] "
                    "BODY.PEEK[TEXT]<0.%d>)" % size)
            if typ != "OK":
                return {}
        except Exception:
            return {}
        out = {}
        for uid, item in parse_fetch_items(data).items():
            header = next((v for k, v in item["parts"].items() if k.startswith("HEADER")), b"")
            body = item["parts"].get("TEXT", b"")
            out[uid] = snippet_from_raw(header, body)
        return out

    def folder_counts(self, folders):
        """{pasta: (não lidas, total)} das pastas da lista, para falar junto do nome.
        As abas do Gmail e a estrela de mentira são contadas pela busca."""
        out = {}
        for f in folders:
            try:
                with self.lock:
                    self._ensure()
                    view = f.get("filter") or ""
                    if view:
                        if view.startswith("category:") and not self.gmail:
                            continue
                        self._select("INBOX")
                        counts = []
                        for unread in (True, False):
                            if view.startswith("category:"):
                                typ, data = self._search_literal(
                                    [], ("X-GM-RAW", view + (" is:unread" if unread else "")))
                            else:
                                typ, data = self.imap.uid("SEARCH", None, "FLAGGED",
                                                          *(("UNSEEN",) if unread else ()))
                            if typ != "OK":
                                break
                            counts.append(len(data[0].split()) if data and data[0] else 0)
                        if len(counts) == 2:
                            out[f["raw"]] = tuple(counts)
                        continue
                    typ, data = self.imap.status(quote_folder(f["raw"]), "(MESSAGES UNSEEN)")
                if typ == "OK":
                    text = b" ".join(d for d in data if isinstance(d, bytes))
                    unseen = re.search(rb"UNSEEN (\d+)", text)
                    total = re.search(rb"MESSAGES (\d+)", text)
                    if unseen and total:
                        out[f["raw"]] = (int(unseen.group(1)), int(total.group(1)))
            except Exception:
                continue
        return out

    def change_labels(self, folder_raw, uids, add=(), remove=()):
        """Põe e tira marcadores do Gmail (nomes como no servidor)."""
        if not uids:
            return
        ids = ",".join(uids)
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            for sign, names in (("+", add), ("-", remove)):
                if names:
                    typ, _ = self.imap.uid("STORE", ids, sign + "X-GM-LABELS",
                                           "(" + " ".join(quote_folder(n) for n in names) + ")")
                    if typ != "OK":
                        raise MailError("Não foi possível mudar os marcadores.")

    def _headers_for(self, uids):
        if not uids:
            return []
        ids = b",".join(uids).decode()
        thread = "X-GM-THRID X-GM-LABELS " if self.gmail else ""
        typ, data = self.imap.uid(
            "FETCH", ids,
            "(FLAGS %sBODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])" % thread)
        if typ != "OK":
            raise MailError("Falha ao ler os cabeçalhos.")
        return parse_header_fetch(data)

    def recent_recipients(self, limit=300):
        """Cabeçalhos Para e Cópia das últimas mensagens enviadas (para os contatos)."""
        sent = self._find_special("\\sent", {"sent", "enviados", "sent items", "itens enviados",
                                               "sent mail", "e-mails enviados"})
        if not sent:
            return []
        with self.lock:
            self._ensure()
            self._select(sent)
            typ, data = self.imap.uid("SEARCH", None, "ALL")
            if typ != "OK" or not data or not data[0]:
                return []
            ids = b",".join(data[0].split()[-limit:]).decode()
            typ, data = self.imap.uid("FETCH", ids, "(BODY.PEEK[HEADER.FIELDS (TO CC)])")
            if typ != "OK":
                return []
        values = []
        for item in data:
            if isinstance(item, tuple):
                hdr = message_from_bytes(item[1], policy=policy.default)
                values.extend(v for v in (_h(hdr, "To"), _h(hdr, "Cc")) if v)
        return values

    def fetch_message(self, folder_raw, uid):
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            typ, data = self.imap.uid("FETCH", uid, "(BODY[])")
            if typ != "OK":
                raise MailError("Falha ao abrir a mensagem.")
        for item in data:
            if isinstance(item, tuple):
                return parse_full_message(item[1], uid)
        raise MailError("Mensagem não encontrada.")

    def set_seen(self, folder_raw, uid, seen=True):
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            self.imap.uid("STORE", uid, "+FLAGS" if seen else "-FLAGS", "(\\Seen)")

    def delete(self, folder_raw, uid):
        trash = self._find_special(
            "\\trash", {"trash", "lixeira", "deleted items", "itens excluídos",
                        "itens excluídos", "deleted", "bin"})
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            if trash and trash != folder_raw:
                typ, _ = self.imap.uid("COPY", uid, quote_folder(trash))
                if typ != "OK":
                    raise MailError("Não foi possível mover para a lixeira.")
            self.imap.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            self.imap.expunge()

    def set_flagged(self, folder_raw, uid, flagged=True):
        """Estrela (no Gmail é a mesma estrela do site)."""
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            self.imap.uid("STORE", uid, "+FLAGS" if flagged else "-FLAGS", "(\\Flagged)")

    def trash_folder(self):
        return self._find_special("\\trash", {"trash", "lixeira", "deleted items", "itens excluídos",
                                              "deleted", "bin"})

    def junk_folder(self):
        return self._find_special("\\junk", {"spam", "junk", "lixo eletrônico", "junk e-mail",
                                             "junk email", "bulk mail", "bulk"})

    def archive_folder(self, create=True):
        """Pasta para arquivar: Arquivo do servidor; no Gmail, Todos os e-mails
        (sair da caixa de entrada é o que o Gmail chama de arquivar)."""
        found = self._find_special("\\archive", {"archive", "arquivo", "arquivados", "archives"})
        if not found and self.gmail:
            found = self._find_special("\\all", {"all mail", "todos os e-mails"})
        if not found and create:
            found = self.create_folder("Archive")
        return found

    def create_folder(self, name):
        """Cria a pasta (o nome pode ter acentos) e devolve o nome no servidor."""
        raw = encode_imap_utf7(name.strip())
        with self.lock:
            self._ensure()
            typ, data = self.imap.create(quote_folder(raw))
            if typ != "OK":
                raise MailError("Não foi possível criar a pasta %s." % name)
        try:
            self.list_folders()
        except Exception:
            pass
        return raw

    def move(self, folder_raw, uids, dest_raw):
        """Move as mensagens para outra pasta (MOVE quando o servidor tem)."""
        if not uids or dest_raw == folder_raw:
            return
        ids = ",".join(uids)
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            if self.can_move:
                typ, _ = self.imap.uid("MOVE", ids, quote_folder(dest_raw))
                if typ == "OK":
                    return
            typ, _ = self.imap.uid("COPY", ids, quote_folder(dest_raw))
            if typ != "OK":
                raise MailError("Não foi possível mover a mensagem.")
            self.imap.uid("STORE", ids, "+FLAGS", "(\\Deleted)")
            self.imap.expunge()

    def delete_permanent(self, folder_raw, uid):
        """Apaga de vez da pasta (usado para trocar rascunhos antigos)."""
        with self.lock:
            self._ensure()
            self._select(folder_raw)
            self.imap.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
            self.imap.expunge()

    def save_draft(self, to, cc, bcc, subject, body, in_reply_to=None,
                   references=None, attachments=None, old=None):
        """Salva na pasta de rascunhos. Devolve (pasta, uid). 'old' = (pasta, uid) a substituir."""
        draft = self._find_special("\\drafts", {"drafts", "rascunhos"})
        if not draft:
            raise MailError("Não encontrei a pasta de rascunhos.")
        msg, _ = build_message(self.email, to, cc, bcc, subject, body, in_reply_to,
                               references, attachments, draft=True)
        with self.lock:
            self._ensure()
            typ, data = self.imap.append(quote_folder(draft), "\\Draft",
                                         imaplib.Time2Internaldate(time.time()),
                                         msg.as_bytes())
            if typ != "OK":
                raise MailError("Não foi possível salvar o rascunho.")
            uid = parse_appenduid(data)
        if old:
            try:
                self.delete_permanent(old[0], old[1])
            except Exception:
                pass
        return draft, uid

    # envio
    def send(self, to, cc, bcc, subject, body, in_reply_to=None, references=None,
             attachments=None):
        msg, recipients = build_message(self.email, to, cc, bcc, subject, body,
                                        in_reply_to, references, attachments)
        ctx = ssl.create_default_context()
        try:
            if self.smtp_security == "ssl":
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port,
                                          context=ctx, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls(context=ctx)
            with server:
                server.login(self.email, self.password)
                server.send_message(msg, to_addrs=recipients)
        except smtplib.SMTPAuthenticationError:
            raise MailError("O servidor recusou a senha ao enviar.")
        except (smtplib.SMTPException, OSError) as e:
            raise MailError("Falha ao enviar: %s" % e)
        self._save_sent_copy(msg)

    def _save_sent_copy(self, msg):
        # O Gmail guarda sozinho a cópia dos enviados; nos outros servidores guardamos aqui.
        if "gmail" in self.smtp_host.lower():
            return
        try:
            sent = self._find_special("\\sent", {"sent", "enviados", "sent items",
                                                 "itens enviados"})
            if sent:
                with self.lock:
                    self._ensure()
                    self.imap.append(quote_folder(sent), "\\Seen",
                                     imaplib.Time2Internaldate(time.time()),
                                     msg.as_bytes())
        except Exception:
            pass


# ---------- tempo real (IMAP IDLE) ----------

class _LineReader:
    """Le linhas do socket com tempo limite, sem perder dados (diferente do makefile)."""

    def __init__(self, sock):
        self.sock = sock
        self.buf = b""

    def readline(self, timeout):
        while b"\r\n" not in self.buf:
            self.sock.settimeout(timeout)
            try:
                chunk = self.sock.recv(4096)
            except (socket.timeout, TimeoutError):
                return None
            if not chunk:
                raise ConnectionError("Conexao encerrada pelo servidor.")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\r\n", 1)
        return line


class IdleNotSupported(MailError):
    pass


class IdleWatcher(threading.Thread):
    """Mantem uma conexao propria em IDLE na caixa de entrada.

    Chama on_event() quando o servidor avisa de mudanca (mensagem nova, apagada
    ou alterada) e on_status(True/False) quando o tempo real liga ou cai.
    Reconecta sozinho se a conexao cair.
    """

    def __init__(self, host, port, email, password, on_event, on_status=None,
                 use_ssl=True, renew_seconds=480):
        super().__init__(daemon=True)
        self.host, self.port = host, int(port)
        self.email, self.password = email, password
        self.on_event = on_event
        self.on_status = on_status or (lambda ok: None)
        self.use_ssl = use_ssl
        self.renew_seconds = renew_seconds
        self._halt = threading.Event()
        self._tagnum = 0
        self._connected = False

    def stop(self):
        self._halt.set()

    def _set_status(self, ok):
        if ok != self._connected:
            self._connected = ok
            try:
                self.on_status(ok)
            except Exception:
                pass

    def _open(self):
        if self.use_ssl:
            imap = imaplib.IMAP4_SSL(self.host, self.port,
                                     ssl_context=ssl.create_default_context())
        else:
            imap = imaplib.IMAP4(self.host, self.port)
        try:
            imap.login(self.email, self.password)
            if "IDLE" not in [c.upper() for c in imap.capabilities]:
                raise IdleNotSupported("O servidor nao oferece IDLE.")
            imap.select("INBOX", readonly=True)
        except Exception:
            try:
                imap.shutdown()
            except Exception:
                pass
            raise
        sock = imap.sock
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        return sock, _LineReader(sock)

    @staticmethod
    def _is_event(line):
        return line.startswith(b"*") and any(
            w in line for w in (b"EXISTS", b"EXPUNGE", b"FETCH"))

    def _idle_once(self, sock, reader):
        self._tagnum += 1
        tag = ("IDLE%d" % self._tagnum).encode()
        sock.sendall(tag + b" IDLE\r\n")
        deadline = time.monotonic() + 30
        while True:
            line = reader.readline(2.0)
            if line is None:
                if self._halt.is_set():
                    return False
                if time.monotonic() > deadline:
                    raise MailError("O servidor nao respondeu ao IDLE.")
                continue
            if line.startswith(b"+"):
                break
            if line.startswith(tag + b" "):
                raise MailError("O servidor recusou o IDLE.")
        self._set_status(True)
        got = False
        end = time.monotonic() + self.renew_seconds
        while not got and not self._halt.is_set() and time.monotonic() < end:
            line = reader.readline(2.0)
            if line is None:
                continue
            if self._is_event(line):
                got = True
            elif line.startswith(tag + b" "):
                return got  # o servidor encerrou por conta propria
        sock.sendall(b"DONE\r\n")
        deadline = time.monotonic() + 30
        while True:
            line = reader.readline(2.0)
            if line is None:
                if time.monotonic() > deadline:
                    raise MailError("O servidor nao confirmou o fim do IDLE.")
                continue
            if self._is_event(line):
                got = True
            if line.startswith(tag + b" "):
                return got

    def run(self):
        delay = 5
        while not self._halt.is_set():
            sock = None
            try:
                sock, reader = self._open()
                delay = 5
                self.on_event()  # confere o que pode ter chegado enquanto estava fora
                while not self._halt.is_set():
                    if self._idle_once(sock, reader):
                        self.on_event()
            except IdleNotSupported:
                self._set_status(False)
                return
            except Exception:
                pass
            finally:
                self._set_status(False)
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass
            if self._halt.wait(delay):
                break
            delay = min(delay * 2, 120)
