"""Regras automáticas e remetentes bloqueados do AudioMail. Sem interface.

Uma regra olha cada mensagem nova da caixa de entrada: se o campo escolhido
(remetente, assunto ou destinatário) contém o texto, faz as ações marcadas
(mover para uma pasta, marcar como lida, pôr estrela, apagar, tocar um som).
Remetentes bloqueados vão direto para a lixeira, sem aviso.

Tudo fica na configuração (cfg["rules"] e cfg["blocked"]), só neste computador.
"""
import uuid
from email.utils import parseaddr

FIELDS = [("from", "Remetente"), ("subject", "Assunto"), ("to", "Destinatário")]
FIELD_KEYS = [k for k, _ in FIELDS]


def new_rule(**values):
    rule = {"id": uuid.uuid4().hex[:12], "name": "", "field": "from", "contains": "",
            "folder": "", "read": False, "star": False, "delete": False, "sound": "",
            "enabled": True}
    rule.update(values)
    return clean_rule(rule)


def clean_rule(rule):
    """Regra com todos os campos e tipos certos (aceita o que veio do arquivo)."""
    out = {"id": str(rule.get("id") or uuid.uuid4().hex[:12]),
           "name": str(rule.get("name") or "").strip(),
           "field": rule.get("field") if rule.get("field") in FIELD_KEYS else "from",
           "contains": str(rule.get("contains") or "").strip(),
           "folder": str(rule.get("folder") or ""),
           "read": bool(rule.get("read")), "star": bool(rule.get("star")),
           "delete": bool(rule.get("delete")), "sound": str(rule.get("sound") or ""),
           "enabled": rule.get("enabled", True) is not False}
    if out["delete"]:
        out["folder"] = ""     # apagar já tira da caixa de entrada
    return out


def load_rules(cfg):
    return [clean_rule(r) for r in cfg.get("rules") or [] if isinstance(r, dict)]


def has_action(rule):
    return bool(rule["folder"] or rule["read"] or rule["star"] or rule["delete"] or rule["sound"])


def _text_of(msg, field):
    if field == "from":
        return msg.get("from_raw") or msg.get("from") or ""
    if field == "to":
        return msg.get("to_raw") or ""
    return msg.get("subject") or ""


def matches(rule, msg):
    if not rule["enabled"] or not rule["contains"] or not has_action(rule):
        return False
    return rule["contains"].lower() in _text_of(msg, rule["field"]).lower()


def sender_address(value):
    return parseaddr(value or "")[1].strip().lower()


def load_blocked(cfg):
    out = []
    for addr in cfg.get("blocked") or []:
        addr = str(addr).strip().lower()
        if "@" in addr and addr not in out:
            out.append(addr)
    return out


def is_blocked(msg, blocked):
    """Bloqueio por endereço exato ou pelo domínio inteiro (@loja.com)."""
    addr = sender_address(msg.get("from_raw") or msg.get("from"))
    if not addr:
        return False
    domain = "@" + addr.split("@")[-1]
    return addr in blocked or domain in blocked


def describe(rule, folder_name=lambda raw: raw):
    """Frase da regra para a lista: 'Se o remetente contém loja: mover para Ofertas, marcar como lida'."""
    field = dict(FIELDS)[rule["field"]].lower()
    actions = []
    if rule["delete"]:
        actions.append("apagar")
    if rule["folder"]:
        actions.append("mover para %s" % folder_name(rule["folder"]))
    if rule["read"]:
        actions.append("marcar como lida")
    if rule["star"]:
        actions.append("pôr estrela")
    if rule["sound"]:
        actions.append("tocar um som próprio")
    return field, rule["contains"], actions


def plan(msgs, rules, blocked):
    """O que fazer com as mensagens novas.

    Devolve um dict com:
      moves:   {pasta: [uids]}  (a lixeira entra com a chave "\\trash")
      read:    [uids]  que ficam lidas
      star:    [uids]  que ganham estrela
      quiet:   set de uids que não devem avisar (bloqueadas, apagadas, movidas, lidas)
      sounds:  {uid: arquivo de som}
      blocked: quantas eram de remetente bloqueado
    A primeira regra que move ou apaga uma mensagem é a que vale para ela;
    marcar como lida, estrela e som somam de todas as regras."""
    result = {"moves": {}, "read": [], "star": [], "quiet": set(), "sounds": {}, "blocked": 0}
    for m in msgs:
        uid = m["uid"]
        if is_blocked(m, blocked):
            result["moves"].setdefault("\\trash", []).append(uid)
            result["quiet"].add(uid)
            result["blocked"] += 1
            continue
        destination = None
        for rule in rules:
            if not matches(rule, m):
                continue
            if destination is None and rule["delete"]:
                destination = "\\trash"
            elif destination is None and rule["folder"]:
                destination = rule["folder"]
            if rule["read"] and uid not in result["read"]:
                result["read"].append(uid)
            if rule["star"] and uid not in result["star"]:
                result["star"].append(uid)
            if rule["sound"] and uid not in result["sounds"]:
                result["sounds"][uid] = rule["sound"]
        if destination:
            result["moves"].setdefault(destination, []).append(uid)
            result["quiet"].add(uid)
        if uid in result["read"]:
            result["quiet"].add(uid)
    return result


def has_work(p):
    return bool(p["moves"] or p["read"] or p["star"])
