"""Contatos do AudioMail: endereços com quem você troca e-mails. Sem interface.

A lista se forma sozinha, só neste computador (contatos.json na pasta de
dados): remetentes das mensagens recebidas, quem aparece nas mensagens que
você abre e, com mais peso, para quem você escreve. Serve para sugerir
endereços nos campos Para, Cópia e Cópia oculta.

Você também pode criar, corrigir e apagar contatos (os criados à mão nunca
saem da lista) e montar grupos, como "Família", que entram de uma vez na
escrita.
"""
import json
import os
import re
import time
from email.utils import getaddresses

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
        self.data = {}           # endereço minúsculo -> {"name", "addr", "count", "last", "manual"}
        self.groups = []         # [{"name", "members": [endereço minúsculo]}]
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
                    "count": int(item.get("count", 1) or 1), "last": float(item.get("last", 0) or 0),
                    "manual": bool(item.get("manual"))}
        self.groups = []
        for g in (raw.get("groups", []) if isinstance(raw, dict) else []):
            if isinstance(g, dict) and str(g.get("name", "")).strip():
                members = [str(a).lower() for a in g.get("members", []) if "@" in str(a)]
                self.groups.append({"name": str(g["name"]).strip(), "members": members})

    def save(self):
        # os criados à mão e os que estão em grupos nunca saem da lista
        kept = {a for g in self.groups for a in g["members"]}
        items = sorted(self.data.values(),
                       key=lambda c: (not (c.get("manual") or c["addr"].lower() in kept),
                                      -c["count"], -c["last"]))[:MAX_CONTACTS]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"contacts": items, "groups": self.groups, "meta": self.meta}, f,
                          ensure_ascii=False)
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
            entry = self.data[lowered] = {"name": name, "addr": addr, "count": 0, "last": 0.0,
                                          "manual": False}
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
        """'Nome <endereço>' legível. O formataddr do Python codificava nomes com
        acento (Zé virava =?utf-8?b?WsOp?=), e era isso que o leitor de tela lia."""
        return display_address(contact["name"], contact["addr"])

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


    # ---- edição à mão ----
    def all_contacts(self):
        """Todos os contatos em ordem de nome (ou endereço, sem nome)."""
        return sorted(self.data.values(), key=lambda c: ((c["name"] or c["addr"]).lower(), c["addr"]))

    def set_contact(self, old_addr, name, addr):
        """Cria (old_addr vazio) ou corrige um contato. Devolve o texto do erro, ou None."""
        addr = (addr or "").strip()
        name = re.sub(r"\s+", " ", (name or "").strip())
        if not valid_address(addr):
            return "Informe um endereço de e-mail válido."
        old = (old_addr or "").lower()
        new = addr.lower()
        if new != old and new in self.data:
            return "Já existe um contato com este endereço."
        entry = self.data.pop(old, None) if old else None
        if entry is None:
            entry = {"count": 1, "last": time.time()}
        entry.update({"name": _clean_name(name, addr), "addr": addr, "manual": True})
        self.data[new] = entry
        if old and old != new:
            for g in self.groups:
                g["members"] = [new if a == old else a for a in g["members"]]
        return None

    def remove(self, addr):
        lowered = (addr or "").lower()
        self.data.pop(lowered, None)
        for g in self.groups:
            g["members"] = [a for a in g["members"] if a != lowered]

    # ---- grupos ----
    def find_group(self, name):
        name = (name or "").strip().lower()
        return next((g for g in self.groups if g["name"].lower() == name), None)

    def set_group(self, old_name, name, members):
        """Cria ou corrige um grupo. Devolve o texto do erro, ou None."""
        name = re.sub(r"\s+", " ", (name or "").strip())
        if not name:
            return "Dê um nome ao grupo."
        other = self.find_group(name)
        current = self.find_group(old_name) if old_name else None
        if other is not None and other is not current:
            return "Já existe um grupo com este nome."
        members = list(dict.fromkeys(a.lower() for a in members if "@" in a))
        if not members:
            return "Escolha pelo menos uma pessoa para o grupo."
        if current is None:
            self.groups.append({"name": name, "members": members})
        else:
            current.update({"name": name, "members": members})
        self.groups.sort(key=lambda g: g["name"].lower())
        return None

    def remove_group(self, name):
        group = self.find_group(name)
        if group is not None:
            self.groups.remove(group)

    def group_text(self, group):
        """Os endereços do grupo prontos para o campo Para."""
        out = []
        for a in group["members"]:
            c = self.data.get(a)
            out.append(self.display(c) if c else a)
        return ", ".join(out)

    def search_groups(self, text):
        text = (text or "").strip().lower()
        return [g for g in self.groups
                if not text or any(w.startswith(text) for w in g["name"].lower().split())
                or g["name"].lower().startswith(text)]


def display_address(name, addr):
    if not name:
        return addr
    if re.search(r'[,;"()<>@\[\]:\\]', name):
        name = '"%s"' % name.replace("\\", "").replace('"', "")
    return "%s <%s>" % (name, addr)


def valid_address(addr):
    addr = (addr or "").strip()
    return bool(re.fullmatch(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+", addr)) and len(addr) <= 254


def group_label(group):
    n = len(group["members"])
    return ("Grupo %s, 1 pessoa" % group["name"]) if n == 1 else ("Grupo %s, %d pessoas" % (group["name"], n))


def append_address(field_text, contact_text):
    """O campo com mais um endereço no fim, separado por vírgula."""
    current = (field_text or "").strip().rstrip(",;").strip()
    return (current + ", " + contact_text) if current else contact_text
