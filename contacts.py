"""Contatos do AudioMail: endereços com quem você troca e-mails. Sem interface.

A lista se forma sozinha, só neste computador (contatos.json na pasta de
dados): remetentes das mensagens recebidas, quem aparece nas mensagens que
você abre e, com mais peso, para quem você escreve. Serve para sugerir
endereços nos campos Para, Cópia e Cópia oculta.
"""
import json
import os
import re
import time
from email.utils import formataddr, getaddresses

MAX_CONTACTS = 3000
_SEPARATORS = re.compile(r"[,;]")


def parse_addresses(*values):
    """[(nome, endereço)] de um ou mais campos (Para, Cópia, Cópia oculta).

    O getaddresses do Python 3.12 ficou rigoroso: com um campo vazio na lista,
    ou uma vírgula sobrando, ele descarta TODOS os endereços. Por isso cada
    campo é lido separado, sem vazios, e um campo que ele recusa é lido
    endereço por endereço."""
    found = []
    for value in values:
        value = (value or "").replace(";", ",").strip().strip(",").strip()
        if not value:
            continue
        parsed = [(n, a) for n, a in getaddresses([value]) if a]
        if not parsed:
            for piece in value.split(","):
                parsed.extend((n, a) for n, a in getaddresses([piece.strip()]) if a)
        found.extend(parsed)
    return found


def _clean_name(name, addr):
    name = re.sub(r"\s+", " ", (name or "").strip().strip('"\'')).strip()
    return "" if name.lower() == addr.lower() else name


class Contacts:
    def __init__(self, path):
        self.path = path
        self.data = {}           # endereço minúsculo -> {"name", "addr", "count", "last"}
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            raw = {}
        items = raw.get("contacts", []) if isinstance(raw, dict) else []
        self.meta = raw.get("meta", {}) if isinstance(raw, dict) else {}
        self.data = {}
        for item in items:
            if isinstance(item, dict) and "@" in str(item.get("addr", "")):
                self.data[item["addr"].lower()] = {
                    "name": str(item.get("name", "")), "addr": str(item["addr"]),
                    "count": int(item.get("count", 1) or 1), "last": float(item.get("last", 0) or 0)}

    def save(self):
        items = sorted(self.data.values(), key=lambda c: (-c["count"], -c["last"]))[:MAX_CONTACTS]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"contacts": items, "meta": self.meta}, f, ensure_ascii=False)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def add(self, name, addr, weight=1, now=None):
        addr = (addr or "").strip()
        if "@" not in addr or " " in addr or len(addr) > 254:
            return False
        lowered = addr.lower()
        if lowered.startswith(("no-reply", "noreply", "do-not-reply", "donotreply", "mailer-daemon")):
            return False
        entry = self.data.get(lowered)
        name = _clean_name(name, addr)
        if entry is None:
            entry = self.data[lowered] = {"name": name, "addr": addr, "count": 0, "last": 0.0}
        elif name and not entry["name"]:
            entry["name"] = name
        entry["count"] += weight
        entry["last"] = now if now is not None else time.time()
        return True

    def add_header(self, value, weight=1, skip=()):
        """Acrescenta todos os endereços de um cabeçalho (From, To, Cc...)."""
        skip = {s.lower() for s in skip}
        added = False
        for name, addr in parse_addresses(value):
            if addr and addr.lower() not in skip:
                added = self.add(name, addr, weight) or added
        return added

    def search(self, text, limit=50):
        """Contatos cujo nome ou endereço tem uma palavra começando com ``text``."""
        text = (text or "").strip().lower()
        found = []
        for c in self.data.values():
            words = re.split(r"[\s.@_\-+]+", (c["name"] + " " + c["addr"]).lower())
            if not text or c["addr"].lower().startswith(text) or c["name"].lower().startswith(text) \
                    or any(w.startswith(text) for w in words if w):
                found.append(c)
        found.sort(key=lambda c: (-c["count"], -c["last"], c["addr"].lower()))
        return found[:limit]

    @staticmethod
    def display(contact):
        return formataddr((contact["name"], contact["addr"])) if contact["name"] else contact["addr"]

    def completions(self, field_text, limit=15):
        """Sugestões para o campo inteiro: o que já foi digitado antes da última
        vírgula fica, e só o último endereço é completado."""
        parts = _SEPARATORS.split(field_text or "")
        typed = parts[-1].strip()
        if len(typed) < 1:
            return []
        head = field_text[:len(field_text) - len(parts[-1])]
        if head and not head.endswith(" "):
            head += " "
        already = {a.lower() for _, a in parse_addresses(head)}
        return [head + self.display(c) for c in self.search(typed, limit + len(already))
                if c["addr"].lower() not in already][:limit]


def append_address(field_text, contact_text):
    """O campo com mais um endereço no fim, separado por vírgula."""
    current = (field_text or "").strip().rstrip(",;").strip()
    return (current + ", " + contact_text) if current else contact_text
