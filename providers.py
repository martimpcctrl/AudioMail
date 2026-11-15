"""Provedores de e-mail que o AudioMail conhece. Sem interface.

Cada um diz os servidores IMAP (receber) e SMTP (enviar). Contas da Microsoft
(Outlook, Hotmail, Live) não entram: a Microsoft só aceita entrar pelo site
dela (OAuth), não com senha de app.
"""

# chave: (nome, servidor IMAP, porta, servidor SMTP, porta, segurança, pede senha de app, site, domínios)
PROVIDERS = [
    ("gmail", "Gmail", "imap.gmail.com", 993, "smtp.gmail.com", 465, "ssl", True,
     "https://myaccount.google.com/apppasswords", ("gmail.com", "googlemail.com")),
    ("yahoo", "Yahoo", "imap.mail.yahoo.com", 993, "smtp.mail.yahoo.com", 465, "ssl", True,
     "https://login.yahoo.com/account/security", ("yahoo.com", "yahoo.com.br", "ymail.com", "rocketmail.com")),
    ("icloud", "iCloud", "imap.mail.me.com", 993, "smtp.mail.me.com", 587, "starttls", True,
     "https://account.apple.com", ("icloud.com", "me.com", "mac.com")),
    ("zoho", "Zoho Mail", "imap.zoho.com", 993, "smtp.zoho.com", 465, "ssl", True,
     "https://accounts.zoho.com", ("zoho.com", "zohomail.com")),
    ("uol", "UOL", "imap.uol.com.br", 993, "smtps.uol.com.br", 587, "starttls", False, "", ("uol.com.br",)),
    ("bol", "BOL", "imap.bol.com.br", 993, "smtps.bol.com.br", 587, "starttls", False, "", ("bol.com.br",)),
    ("terra", "Terra", "imap.terra.com.br", 993, "smtp.terra.com.br", 587, "starttls", False, "",
     ("terra.com.br",)),
    ("other", "Outro (escrever os servidores)", "", 993, "", 587, "starttls", False, "", ()),
]
KEYS = [p[0] for p in PROVIDERS]
MICROSOFT_DOMAINS = ("outlook.com", "hotmail.com", "live.com", "msn.com", "outlook.com.br",
                     "hotmail.com.br", "live.com.br", "passport.com")
SECURITY = ("ssl", "starttls")


def get(key):
    for p in PROVIDERS:
        if p[0] == key:
            return {"key": p[0], "name": p[1], "imap_host": p[2], "imap_port": p[3], "smtp_host": p[4],
                    "smtp_port": p[5], "security": p[6], "app_password": p[7], "site": p[8],
                    "domains": p[9]}
    return get("gmail")


def domain(email):
    return (email or "").rsplit("@", 1)[-1].strip().lower() if "@" in (email or "") else ""


def is_microsoft(email):
    return domain(email) in MICROSOFT_DOMAINS


def guess(email):
    """O provedor pelo domínio do e-mail, ou None se não der para saber."""
    d = domain(email)
    for p in PROVIDERS:
        if d in p[9]:
            return p[0]
    return None


def server_for(entry):
    """Servidores de uma conta salva. Contas antigas, sem 'provider', são do Gmail."""
    entry = entry or {}
    key = entry.get("provider") or "gmail"
    if key == "other":
        s = entry.get("server") or {}
        return {"imap_host": str(s.get("imap_host", "")), "imap_port": int(s.get("imap_port", 993) or 993),
                "smtp_host": str(s.get("smtp_host", "")), "smtp_port": int(s.get("smtp_port", 587) or 587),
                "security": s.get("security") if s.get("security") in SECURITY else "starttls"}
    p = get(key)
    return {k: p[k] for k in ("imap_host", "imap_port", "smtp_host", "smtp_port", "security")}


def valid_server(server):
    try:
        ok_ports = 0 < int(server["imap_port"]) < 65536 and 0 < int(server["smtp_port"]) < 65536
    except (KeyError, TypeError, ValueError):
        return False
    hosts = [server.get("imap_host", ""), server.get("smtp_host", "")]
    return ok_ports and all(h and " " not in h and "." in h for h in hosts) \
        and server.get("security") in SECURITY
