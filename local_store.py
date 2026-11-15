"""Mensagens guardadas no computador (mensagens.db, na pasta de dados), para a
lista abrir na hora e para ler sem internet.

Guarda, por conta: a lista de pastas, a lista de mensagens de cada pasta (as
que já apareceram) e o texto das mensagens que você abriu. Os anexos só ficam
guardados se você ligar essa opção. Tudo é gravado criptografado com a
proteção do próprio Windows (a mesma das senhas): copiado para outro
computador ou outra conta do Windows, o arquivo não pode ser lido.
Nada daqui é enviado a lugar nenhum. Sem interface.
"""
import json
import os
import sqlite3
import threading
import time
import zlib

import i18n
import mail_core as mc

KEEP_PER_FOLDER = 2000          # mensagens guardadas na lista de cada pasta
MAX_RAW = 25 * 1024 * 1024      # mensagem com anexos maior que isso não é guardada inteira
FULL_KEYS = ("uid", "from", "to", "cc", "bcc", "reply_to", "subject", "date", "message_id",
             "references", "body", "links", "list_unsubscribe", "list_unsubscribe_post", "ts")


def folder_key(raw, view_filter=None):
    """A chave da lista: a pasta, ou a pasta de mentira (aba do Gmail, estrela)."""
    return "\x00" + view_filter if view_filter else raw


def merge_lists(old, new, keep=KEEP_PER_FOLDER):
    """A lista nova manda nas mensagens que ela cobre (do UID mais baixo dela para
    cima: o que sumiu dali foi apagado ou movido); as mais antigas guardadas ficam."""
    if not new:
        return list(old)[:keep]
    lowest = min(int(m["uid"]) for m in new)
    older = [m for m in old if int(m["uid"]) < lowest]
    merged = sorted(new, key=lambda m: int(m["uid"]), reverse=True) + \
        sorted(older, key=lambda m: int(m["uid"]), reverse=True)
    return merged[:keep]


def strip_full(full):
    """A mensagem aberta sem os anexos (que não cabem em JSON): só o texto e os nomes."""
    out = {k: full.get(k) for k in FULL_KEYS}
    out["attachments"] = [{"name": a.get("name", ""), "size": a.get("size", 0)}
                          for a in full.get("attachments", [])]
    return out


def full_from_store(data, raw=None):
    """A mensagem guardada pronta para a leitura. Com a mensagem inteira guardada,
    anexos e convite voltam também; sem ela, o texto avisa quais anexos ficaram de fora."""
    if raw:
        try:
            return mc.parse_full_message(raw, data.get("uid", ""))
        except Exception:
            pass
    full = dict(data)
    names = full.pop("attachments", []) or []
    full["attachments"], full["invite"] = [], None
    full.setdefault("links", [])
    if names:
        listed = ", ".join("%s (%s)" % (a["name"], mc.format_size(a.get("size", 0))) for a in names)
        full["body"] = (full.get("body") or "") + "\n\n" + \
            i18n.tr("[Anexos que não foram guardados no computador: %s]") % listed
    return full


def matches(msg, text, body=""):
    text = (text or "").strip().lower()
    if not text:
        return True
    hay = " ".join(str(msg.get(k) or "") for k in ("from_raw", "from", "to_raw", "subject")) + " " + body
    hay = hay.lower()
    return all(word in hay for word in text.split())


class LocalStore:
    def __init__(self, path, protect=None, unprotect=None):
        self.path = path
        self.protect = protect or (lambda b: b)
        self.unprotect = unprotect or (lambda b: b)
        self.lock = threading.RLock()
        self.db = None

    # ---- arquivo ----
    def _conn(self):
        if self.db is None:
            self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS folders (account TEXT PRIMARY KEY, data BLOB, saved REAL);
                CREATE TABLE IF NOT EXISTS lists (account TEXT, folder TEXT, data BLOB, saved REAL,
                                                  PRIMARY KEY (account, folder));
                CREATE TABLE IF NOT EXISTS bodies (account TEXT, folder TEXT, uid TEXT, ts REAL,
                                                   saved REAL, data BLOB, raw BLOB,
                                                   PRIMARY KEY (account, folder, uid));
            """)
        return self.db

    def close(self):
        with self.lock:
            if self.db is not None:
                try:
                    self.db.close()
                finally:
                    self.db = None

    def size(self):
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0

    def clear(self):
        """Apaga tudo que foi guardado (o arquivo inteiro)."""
        with self.lock:
            self.close()
            for suffix in ("", "-journal", "-wal", "-shm"):
                try:
                    os.remove(self.path + suffix)
                except OSError:
                    pass

    def forget_account(self, account):
        with self.lock:
            db = self._conn()
            for table in ("folders", "lists", "bodies"):
                db.execute("DELETE FROM %s WHERE account = ?" % table, (account.lower(),))
            db.commit()

    def _pack(self, obj):
        return self.protect(zlib.compress(json.dumps(obj, ensure_ascii=False, default=list).encode("utf-8")))

    def _unpack(self, blob):
        return json.loads(zlib.decompress(self.unprotect(bytes(blob))).decode("utf-8"))

    def _pack_bytes(self, data):
        return self.protect(zlib.compress(data))

    def _unpack_bytes(self, blob):
        return zlib.decompress(self.unprotect(bytes(blob)))

    # ---- pastas ----
    def save_folders(self, account, folders):
        with self.lock:
            db = self._conn()
            db.execute("REPLACE INTO folders VALUES (?, ?, ?)",
                       (account.lower(), self._pack(folders), time.time()))
            db.commit()

    def folders(self, account):
        with self.lock:
            row = self._conn().execute("SELECT data FROM folders WHERE account = ?",
                                       (account.lower(),)).fetchone()
        try:
            return self._unpack(row[0]) if row else {}
        except Exception:
            return {}

    # ---- listas de mensagens ----
    def save_list(self, account, key, msgs):
        with self.lock:
            merged = merge_lists(self.list(account, key), msgs)
            db = self._conn()
            db.execute("REPLACE INTO lists VALUES (?, ?, ?, ?)",
                       (account.lower(), key, self._pack(merged), time.time()))
            db.commit()

    def list(self, account, key):
        with self.lock:
            row = self._conn().execute("SELECT data FROM lists WHERE account = ? AND folder = ?",
                                       (account.lower(), key)).fetchone()
        try:
            return self._unpack(row[0]) if row else []
        except Exception:
            return []

    def search(self, account, key, folder_raw, text):
        """As mensagens guardadas da pasta com o texto no remetente, assunto ou no texto aberto."""
        bodies = {}
        with self.lock:
            rows = self._conn().execute("SELECT uid, data FROM bodies WHERE account = ? AND folder = ?",
                                        (account.lower(), folder_raw)).fetchall()
        for uid, blob in rows:
            try:
                bodies[uid] = self._unpack(blob).get("body") or ""
            except Exception:
                continue
        return [m for m in self.list(account, key) if matches(m, text, bodies.get(m["uid"], ""))]

    # ---- mensagens abertas ----
    def save_message(self, account, folder_raw, uid, full, raw=None):
        packed_raw = self._pack_bytes(raw) if raw and len(raw) <= MAX_RAW else None
        with self.lock:
            db = self._conn()
            db.execute("REPLACE INTO bodies VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (account.lower(), folder_raw, str(uid), float(full.get("ts") or 0),
                        time.time(), self._pack(strip_full(full)), packed_raw))
            db.commit()

    def message(self, account, folder_raw, uid):
        """A mensagem guardada pronta para ler, ou None."""
        with self.lock:
            row = self._conn().execute(
                "SELECT data, raw FROM bodies WHERE account = ? AND folder = ? AND uid = ?",
                (account.lower(), folder_raw, str(uid))).fetchone()
        if not row:
            return None
        try:
            data = self._unpack(row[0])
            raw = self._unpack_bytes(row[1]) if row[1] else None
        except Exception:
            return None
        return full_from_store(data, raw)

    def has_message(self, account, folder_raw, uid):
        with self.lock:
            return self._conn().execute(
                "SELECT 1 FROM bodies WHERE account = ? AND folder = ? AND uid = ?",
                (account.lower(), folder_raw, str(uid))).fetchone() is not None

    # ---- limpeza ----
    def prune(self, days, now=None):
        """Tira o que é mais antigo que ``days`` dias (pela data da mensagem). 0: sem limite."""
        if not days:
            return
        limit = (now or time.time()) - days * 86400
        with self.lock:
            db = self._conn()
            db.execute("DELETE FROM bodies WHERE ts > 0 AND ts < ?", (limit,))
            for account, key, blob in db.execute("SELECT account, folder, data FROM lists").fetchall():
                try:
                    msgs = self._unpack(blob)
                except Exception:
                    db.execute("DELETE FROM lists WHERE account = ? AND folder = ?", (account, key))
                    continue
                kept = [m for m in msgs if not (m.get("ts") or 0) or m["ts"] >= limit]
                if len(kept) != len(msgs):
                    db.execute("UPDATE lists SET data = ? WHERE account = ? AND folder = ?",
                               (self._pack(kept), account, key))
            db.commit()
            db.execute("VACUUM")
