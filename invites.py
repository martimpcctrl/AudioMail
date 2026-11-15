"""Convites de reunião (arquivos iCalendar, .ics) que chegam por e-mail.

Lê o convite (assunto, data e hora, local, organizador), escreve a frase que a
leitura mostra no começo da mensagem e monta a resposta Aceitar, Talvez ou
Recusar que vai ao organizador, no formato que Google Agenda, Outlook e os
outros calendários entendem e registram sozinhos. Sem interface.
"""
import datetime
import re

import i18n

ANSWERS = {
    "accept": ("ACCEPTED", "Aceito: %s", "Aceitei o convite para %s."),
    "tentative": ("TENTATIVE", "Talvez: %s", "Talvez eu participe de %s."),
    "decline": ("DECLINED", "Recusado: %s", "Não vou poder participar de %s."),
}
WEEKDAYS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira",
            "sábado", "domingo")


def unfold(text):
    """Junta as linhas dobradas do iCalendar (as que começam com espaço continuam a anterior)."""
    return re.sub(r"\r?\n[ \t]", "", (text or "").replace("\r\n", "\n"))


def unescape(value):
    return re.sub(r"\\([\\;,nN])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), value)


def escape(value):
    return (value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,") \
        .replace("\r\n", "\\n").replace("\n", "\\n")


def parse_line(line):
    """'DTSTART;TZID=America/Sao_Paulo:20261120T140000' -> ('DTSTART', {'TZID': ...}, valor)."""
    head, sep, value = _split_value(line)
    if not sep:
        return None
    parts = head.split(";")
    params = {}
    for p in parts[1:]:
        key, _, val = p.partition("=")
        params[key.strip().upper()] = val.strip().strip('"')
    return parts[0].strip().upper(), params, value


def _split_value(line):
    """Separa no primeiro ':' que não está entre aspas (CN="Silva: Ana")."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == ":" and not quoted:
            return line[:i], ":", line[i + 1:]
    return line, "", ""


def parse_dt(value, params):
    """Data e hora no horário deste computador (datetime sem fuso), ou date no dia inteiro."""
    value = (value or "").strip()
    if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", value):
        return datetime.datetime.strptime(value[:8], "%Y%m%d").date()
    utc = value.endswith("Z")
    moment = datetime.datetime.strptime(value.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    if utc:
        return moment.replace(tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None)
    tzid = params.get("TZID")
    if tzid:
        try:
            from zoneinfo import ZoneInfo
            return moment.replace(tzinfo=ZoneInfo(tzid)).astimezone().replace(tzinfo=None)
        except Exception:
            pass   # fuso que este computador não conhece: usa a hora como veio
    return moment


def parse_ics(text):
    """O primeiro evento do convite, ou None se não houver."""
    if not text or "BEGIN:VEVENT" not in text.upper():
        return None
    method, event, inside = "", None, False
    for line in unfold(text).split("\n"):
        parsed = parse_line(line)
        if parsed is None:
            continue
        name, params, value = parsed
        if name == "METHOD" and not inside:
            method = value.strip().upper()
        elif name == "BEGIN" and value.strip().upper() == "VEVENT":
            inside, event = True, {"raw": {}, "attendees": []}
        elif name == "END" and value.strip().upper() == "VEVENT":
            break
        elif inside:
            if name in ("DTSTART", "DTEND", "ORGANIZER", "UID", "SEQUENCE", "RECURRENCE-ID"):
                event["raw"].setdefault(name, line)
            if name == "SUMMARY":
                event["summary"] = unescape(value).strip()
            elif name == "LOCATION":
                event["location"] = unescape(value).strip()
            elif name == "UID":
                event["uid"] = value.strip()
            elif name == "SEQUENCE":
                event["sequence"] = value.strip()
            elif name == "STATUS":
                event["status"] = value.strip().upper()
            elif name in ("DTSTART", "DTEND"):
                try:
                    event[name.lower()] = parse_dt(value, params)
                except ValueError:
                    pass
            elif name == "ORGANIZER":
                event["organizer"] = re.sub(r"(?i)^mailto:", "", value.strip())
                event["organizer_name"] = params.get("CN", "")
            elif name == "ATTENDEE":
                event["attendees"].append(re.sub(r"(?i)^mailto:", "", value.strip()).lower())
    if not event or not event.get("dtstart"):
        return None
    event["method"] = method or "REQUEST"
    event.setdefault("summary", i18n.tr("Reunião"))
    return event


def find_invite(msg):
    """O texto do convite (parte text/calendar ou anexo .ics) de um e-mail, ou ''."""
    for part in msg.walk():
        name = (part.get_filename() or "").lower()
        if part.get_content_type() == "text/calendar" or name.endswith(".ics"):
            try:
                data = part.get_payload(decode=True) or b""
            except Exception:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                return data.decode(charset, "replace")
            except LookupError:
                return data.decode("utf-8", "replace")
    return ""


def can_answer(invite, my_email):
    """Só se responde a um convite (não a um cancelamento ou a uma resposta), e não ao próprio."""
    if not invite or invite.get("method") not in ("REQUEST", "PUBLISH") or invite.get("status") == "CANCELLED":
        return False
    organizer = (invite.get("organizer") or "").lower()
    return bool(organizer) and organizer != (my_email or "").lower()


def when_text(invite):
    start, end = invite.get("dtstart"), invite.get("dtend")
    if not isinstance(start, datetime.datetime):
        day = i18n.tr("%s, %s, dia inteiro") % (i18n.tr(WEEKDAYS[start.weekday()]), start.strftime("%d/%m/%Y"))
        return day
    text = "%s, %s, %s" % (i18n.tr(WEEKDAYS[start.weekday()]), start.strftime("%d/%m/%Y"),
                           start.strftime("%H:%M"))
    if isinstance(end, datetime.datetime):
        if end.date() == start.date():
            text = i18n.tr("%s às %s") % (text, end.strftime("%H:%M"))
        else:
            text = i18n.tr("%s até %s") % (text, end.strftime("%d/%m/%Y %H:%M"))
    return text


def describe(invite):
    """A frase do começo da leitura: 'Convite: Reunião, sexta-feira, 20/11/2026, 14:00 às 15:00, ...'."""
    cancelled = invite.get("method") == "CANCEL" or invite.get("status") == "CANCELLED"
    if cancelled:
        head = i18n.tr("Reunião cancelada: %s") % invite["summary"]
    elif invite.get("method") == "REPLY":
        head = i18n.tr("Resposta a convite: %s") % invite["summary"]
    else:
        head = i18n.tr("Convite: %s") % invite["summary"]
    parts = [head, when_text(invite)]
    if invite.get("location"):
        parts.append(i18n.tr("local: %s") % invite["location"])
    who = invite.get("organizer_name") or invite.get("organizer")
    if who:
        parts.append(i18n.tr("de: %s") % who)
    return ", ".join(parts) + "."


def build_reply(invite, my_email, answer, my_name="", now=None):
    """(assunto, texto, iCalendar) da resposta ao organizador."""
    partstat, subject_fmt, body_fmt = ANSWERS[answer]
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp = now.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cn = ';CN="%s"' % my_name.replace('"', "") if my_name else ""
    lines = ["BEGIN:VCALENDAR", "PRODID:-//AudioMail//AudioMail//PT", "VERSION:2.0",
             "METHOD:REPLY", "BEGIN:VEVENT"]
    raw = invite.get("raw", {})
    for key in ("UID", "RECURRENCE-ID", "SEQUENCE", "DTSTART", "DTEND", "ORGANIZER"):
        if raw.get(key):
            lines.append(raw[key])
    lines += ["SUMMARY:%s" % escape(invite.get("summary", "")),
              "DTSTAMP:%s" % stamp,
              "ATTENDEE;PARTSTAT=%s%s:mailto:%s" % (partstat, cn, my_email),
              "END:VEVENT", "END:VCALENDAR"]
    ics = "\r\n".join(fold(line) for line in lines) + "\r\n"
    summary = invite.get("summary", "")
    return i18n.tr(subject_fmt) % summary, i18n.tr(body_fmt) % summary, ics


def fold(line, width=74):
    """Dobra linhas compridas como o iCalendar pede (continuação começa com espaço)."""
    if len(line) <= width:
        return line
    out = [line[:width]]
    rest = line[width:]
    while rest:
        out.append(" " + rest[:width - 1])
        rest = rest[width - 1:]
    return "\r\n".join(out)


def reminder_for(invite, now=None):
    """O lembrete para o Calendário do AudioMail, ou None se a reunião já passou."""
    start = invite.get("dtstart")
    if start is None:
        return None
    if not isinstance(start, datetime.datetime):
        start = datetime.datetime.combine(start, datetime.time(8, 0))
    if start <= (now or datetime.datetime.now()):
        return None
    title = invite.get("summary", "")
    if invite.get("location"):
        title = "%s (%s)" % (title, invite["location"])
    return {"title": title, "when": start.isoformat(timespec="minutes")}
