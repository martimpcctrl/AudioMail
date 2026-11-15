"""Mensagens esperando para sair: desfazer envio e envio agendado. Sem interface.

As agendadas ficam em agendadas.json na pasta de dados, com uma cópia dos
anexos (o arquivo original pode mudar ou sumir até a hora do envio).
"""
import json
import os
import shutil
import time
import uuid

FIELDS = ("to", "cc", "bcc", "subject", "body", "in_reply_to", "references", "attachments")
RETRY_SECONDS = 5 * 60
UNDO_CHOICES = (0, 5, 10, 20, 30)


def message_args(item):
    """Os argumentos de MailClient.send, na ordem."""
    return tuple(item.get(name) if name != "attachments" else list(item.get(name) or [])
                 for name in FIELDS)


def from_fields(args):
    """dict a partir da tupla de ComposeDialog.fields()."""
    return dict(zip(FIELDS, args))


class Scheduled:
    def __init__(self, folder):
        self.folder = folder
        self.path = os.path.join(folder, "agendadas.json")
        self.files = os.path.join(folder, "agendadas")
        self.items = self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                items = json.load(f)
        except (OSError, ValueError):
            return []
        return [it for it in items if isinstance(it, dict) and "id" in it and "when" in it]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def add(self, account, fields, when, draft=None):
        """Agenda. ``fields`` é um dict com FIELDS; ``when`` é o horário (epoch)."""
        ident = uuid.uuid4().hex
        item = {name: fields.get(name) for name in FIELDS}
        item.update({"id": ident, "account": account, "when": float(when), "draft": draft,
                     "retry_at": 0, "error": ""})
        copies = []
        for path in fields.get("attachments") or []:
            target_dir = os.path.join(self.files, ident)
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, os.path.basename(path))
            shutil.copy2(path, target)
            copies.append(target)
        item["attachments"] = copies
        self.items.append(item)
        self.save()
        return item

    def remove(self, ident, keep_files=False):
        self.items = [it for it in self.items if it["id"] != ident]
        self.save()
        if not keep_files:
            shutil.rmtree(os.path.join(self.files, ident), ignore_errors=True)

    def due(self, accounts, now=None):
        """As que já deviam ter saído, de contas conectadas e sem espera de nova tentativa."""
        now = time.time() if now is None else now
        accounts = {a.lower() for a in accounts}
        return [it for it in sorted(self.items, key=lambda it: it["when"])
                if it["when"] <= now and it.get("retry_at", 0) <= now
                and str(it.get("account", "")).lower() in accounts]

    def failed(self, ident, error, now=None):
        now = time.time() if now is None else now
        for it in self.items:
            if it["id"] == ident:
                it["retry_at"] = now + RETRY_SECONDS
                it["error"] = str(error)[:200]
        self.save()

    def get(self, ident):
        return next((it for it in self.items if it["id"] == ident), None)
