"""Envio de chamados de suporte ao painel do AudioMail."""
import json
import urllib.error
import urllib.request


TICKET_URL = "https://martimtech.ddns.net/audiomail/painel/ticket.php"


class TicketError(Exception):
    pass


def _post(payload):
    request = urllib.request.Request(
        TICKET_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "AudioMail"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("message", "")
        except Exception:
            detail = ""
        raise TicketError(detail or "O servidor recusou a solicitação (HTTP %s)." % exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TicketError("Não foi possível conectar ao painel de suporte: %s" % exc)
    except (ValueError, UnicodeError) as exc:
        raise TicketError("O painel devolveu uma resposta que o AudioMail não reconheceu.") from exc
    if not data.get("ok"):
        raise TicketError(data.get("message") or "O painel não confirmou a solicitação.")
    return data


def submit_ticket(email, subject, category, message, app_version):
    payload = {
        "email": email.strip(),
        "subject": subject.strip(),
        "category": category,
        "message": message.strip(),
        "app_version": app_version,
        "website": "",
    }
    data = _post(payload)
    if not data.get("ticket_id") or not data.get("ticket_key"):
        raise TicketError(data.get("message") or "O painel não confirmou o recebimento do chamado.")
    return data["ticket_id"], data["ticket_key"]


def complete_ticket(ticket_id, ticket_key):
    _post({"action": "complete", "ticket_id": ticket_id, "ticket_key": ticket_key})
