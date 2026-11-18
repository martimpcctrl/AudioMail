"""Ler sem internet: a janela principal usando o mensagens.db (local_store.py).

- A lista de cada pasta é guardada quando chega do servidor, e na próxima vez
  aparece na hora, antes de o servidor responder.
- O texto de cada mensagem aberta é guardado; sem conexão, abre do computador.
- Sem conexão, o AudioMail avisa, mostra o que está guardado e tenta de novo
  a cada minuto. Se nem deu para entrar na conta, a conta abre do mesmo jeito,
  com o que está guardado, e entra sozinha quando a internet voltar.
"""
import os
import threading

import wx

import i18n
import local_store as ls
import mail_core as mc
import organize
import secure
from common import data_dir

RETRY_MS = 60000


class OfflineMixin:
    # ---- o arquivo ----
    @property
    def store(self):
        if not self.setting("offline_enabled"):
            return None
        if getattr(self, "_store", None) is None:
            self._store = ls.LocalStore(os.path.join(data_dir(), "mensagens.db"),
                                        secure.encrypt, secure.decrypt)
        return self._store

    def cached_list(self, acc, raw, view_filter):
        store = self.store
        if store is None:
            return []
        try:
            return store.list(acc.email, ls.folder_key(raw, view_filter))
        except Exception:
            return []

    # ---- chamados nas threads de trabalho ----
    def fetch_list(self, email, client, raw, query, view_filter, limit):
        """(mensagens, total, sem_conexão): do servidor, ou do computador se não houver conexão."""
        store = self.store
        try:
            if query or view_filter:
                msgs, total = client.search_query(raw, query, limit, view_filter)
            else:
                msgs, total = client.fetch_headers(raw, limit=limit, with_total=True)
        except Exception as e:
            if store is None or not mc.is_offline_error(e):
                raise
            key = ls.folder_key(raw, view_filter)
            msgs = store.search(email, key, raw, query) if query else store.list(email, key)
            if not msgs and not store.folders(email).get("folders"):
                raise
            return msgs, len(msgs), True
        if store is not None and not query:
            try:
                store.save_list(email, ls.folder_key(raw, view_filter), msgs)
            except Exception:
                pass
        return msgs, total, False

    def fetch_full(self, email, client, raw, uid):
        """A mensagem aberta: do servidor (e guardada), ou a guardada, sem conexão."""
        store = self.store
        try:
            data = client.fetch_raw(raw, uid)
        except Exception as e:
            if store is None or not mc.is_offline_error(e):
                raise
            full = store.message(email, raw, uid)
            if full is None:
                raise mc.MailError(
                    "Sem conexão, e esta mensagem ainda não foi guardada no computador. "
                    "As mensagens ficam guardadas depois que você as abre uma vez com internet.")
            full["offline"] = True
            return full
        full = mc.parse_full_message(data, uid)
        if store is not None:
            # a mensagem inteira (com anexos) só se não tiver anexo ou se a opção estiver ligada
            keep_raw = not full["attachments"] or self.setting("offline_attachments")
            try:
                store.save_message(email, raw, uid, full, data if keep_raw else None)
            except Exception:
                pass
        return full

    def cache_inbox(self, email, msgs):
        store = self.store
        if store is not None and msgs:
            try:
                store.save_list(email, ls.folder_key("INBOX"), msgs)
            except Exception:
                pass

    def cache_folders(self, acc, folders, gmail):
        store = self.store
        if store is not None:
            try:
                store.save_folders(acc.email, {"folders": folders, "gmail": bool(gmail)})
            except Exception:
                pass

    # ---- sem conexão ----
    def set_offline(self, acc, offline):
        if offline and not acc.offline:
            acc.offline = True
            self.announce("Sem conexão. Mostrando as mensagens guardadas no computador.")
            self.start_offline_timer()
        elif not offline and acc.offline:
            acc.offline = False
            self.announce("A conexão voltou.")
        if acc.offline and acc is self.active:
            self.SetStatusText(i18n.tr("Sem conexão, mostrando as mensagens guardadas"))

    def start_offline_timer(self):
        if getattr(self, "offline_timer", None) is None:
            self.offline_timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_offline_timer, self.offline_timer)
        if not self.offline_timer.IsRunning():
            self.offline_timer.Start(RETRY_MS)

    def on_offline_timer(self, evt=None):
        waiting = [a for a in self.accounts if a.offline]
        if not waiting:
            self.offline_timer.Stop()
            return
        for acc in waiting:
            if acc.pending_login:
                self.connect(acc.pending_login, quiet=True)
            elif acc is self.active:
                self.refresh(quiet=True)

    def start_offline(self, v, client, err):
        """Não deu para entrar por falta de conexão: abre a conta com o que está guardado.
        Devolve False se não houver nada guardado dela."""
        store = self.store
        if store is None or not mc.is_offline_error(err):
            return False
        try:
            saved = store.folders(v["email"])
        except Exception:
            return False
        folders = saved.get("folders") if isinstance(saved, dict) else None
        if not folders:
            return False
        acc = self.account_for(v["email"])
        if acc.client is None:
            acc.client = client
            acc.folders = organize.with_virtual(folders, saved.get("gmail"))
        acc.pending_login = v
        self.update_account_ui()
        if self.active is None or acc is self.active:
            self.activate(acc)
        self.set_offline(acc, True)
        return True

    # ---- limpeza e configurações ----
    def prune_store_later(self):
        store, days = self.store, int(self.setting("offline_days") or 0)
        if store is None or not days:
            return

        def work():
            try:
                store.prune(days)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def apply_offline_settings(self, was_enabled, clear):
        """Depois de salvar as Configurações: apagar o guardado, se pedido, e fechar o arquivo
        quando o recurso foi desligado (perguntando se apaga o que já está guardado)."""
        store = getattr(self, "_store", None) or ls.LocalStore(os.path.join(data_dir(), "mensagens.db"))
        if clear:
            store.clear()
            self._store = None
            self.announce("As mensagens guardadas no computador foram apagadas.")
        elif was_enabled and not self.setting("offline_enabled") and store.size():
            answer = i18n.message_box("Apagar também as mensagens que já estão guardadas no computador?",
                                      "Mensagens guardadas no computador",
                                      wx.YES_NO | wx.ICON_QUESTION, self)
            if answer == wx.YES:
                store.clear()
                self._store = None
        if not self.setting("offline_enabled") and getattr(self, "_store", None) is not None:
            self._store.close()
            self._store = None
        self.prune_store_later()

    def offline_store_size(self):
        try:
            return os.path.getsize(os.path.join(data_dir(), "mensagens.db"))
        except OSError:
            return 0
