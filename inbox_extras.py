"""Boletim falado da caixa, notificação com botões e assinatura por conta.
MainFrame herda InboxExtrasMixin."""
import sys
import threading

import wx
import wx.adv

import i18n
import bulletin
import speech
from common import find_account, save_config

EVT_NOTIFICATION_ACTION = wx.PyEventBinder(wx.adv.wxEVT_NOTIFICATION_MESSAGE_ACTION, 1)
EVT_NOTIFICATION_CLICK = wx.PyEventBinder(wx.adv.wxEVT_NOTIFICATION_MESSAGE_CLICK, 1)
APP_ID = "MartimTech.AudioMail"


def enable_toasts():
    """Notificações modernas do Windows (com botões). Só no AudioMail.exe: rodando
    pelo Python, o Windows mostraria o Python como dono da notificação."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        return bool(wx.adv.NotificationMessage.MSWUseToasts("AudioMail", APP_ID))
    except Exception:
        return False


class InboxExtrasMixin:
    # ---------- assinatura por conta ----------
    def signature_for(self, acc):
        entry = find_account(self.cfg, acc.email) if acc else None
        own = (entry or {}).get("signature", "").strip()
        return own or self.setting("signature").strip()

    def edit_account_signature(self):
        acc = self.active
        if not acc:
            return
        entry = find_account(self.cfg, acc.email)
        if entry is None:
            return
        dlg = wx.TextEntryDialog(
            self, i18n.tr("Assinatura usada só na conta %s. Deixe vazio para usar a assinatura geral "
                          "das Configurações.") % acc.email,
            i18n.tr("Assinatura desta conta"), entry.get("signature", ""),
            style=wx.TextEntryDialogStyle | wx.TE_MULTILINE)
        if dlg.ShowModal() == wx.ID_OK:
            entry["signature"] = dlg.GetValue().strip()
            save_config(self.cfg)
            self.announce("Assinatura da conta salva." if entry["signature"]
                          else "Esta conta vai usar a assinatura geral.")
        dlg.Destroy()

    # ---------- boletim falado ----------
    def speak_bulletin(self):
        accounts = [a for a in self.accounts if a.client]
        if not accounts:
            self.announce("Nenhuma conta conectada.")
            return
        self.announce("Preparando o boletim.")

        def tabs_of(acc):
            return [(f["display"], (acc.counts.get(f["raw"]) or (0, 0))[0])
                    for f in acc.folders if (f.get("filter") or "").startswith("category:")]

        jobs = [(acc, acc.client.side(), tabs_of(acc)) for acc in accounts]
        many = len(accounts) > 1

        def work():
            parts = []
            for acc, client, tabs in jobs:
                try:
                    msgs, _ = client.search_query("INBOX", "is:unread", 300)
                    parts.append((acc.email if many else "", bulletin.account_part(msgs, tabs)))
                except Exception:
                    parts.append((acc.email if many else "",
                                  i18n.tr("Não foi possível ver a caixa de entrada agora.")))
            wx.CallAfter(done, parts)

        def done(parts):
            if not self:
                return
            text = bulletin.build(parts, bulletin.reminders_today(self.cfg.get("reminders", [])),
                                  bulletin.scheduled_today(self.scheduled.items))
            self.SetStatusText(text)
            speech.speak(text)

        threading.Thread(target=work, daemon=True).start()

    # ---------- notificação com botões ----------
    def toast_new(self, acc, new, title, text):
        """Notificação de mensagem nova com Responder, Arquivar e Marcar como lida."""
        self.last_new = (acc, [m["uid"] for m in new])
        if not getattr(self, "toasts", False):
            self.toast(title, text)
            return
        try:
            nm = wx.adv.NotificationMessage(i18n.tr(title), i18n.tr(text), parent=self)
            for ident, label in bulletin.notification_actions(len(new)):
                nm.AddAction(ident, i18n.tr(label))
            uids = [m["uid"] for m in new]
            nm.Bind(EVT_NOTIFICATION_ACTION, lambda e: self.notification_action(acc, uids, e.GetId()))
            nm.Bind(EVT_NOTIFICATION_CLICK, lambda e: self.restore())
            nm.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
            self._toast = nm
        except Exception:
            self.toast(title, text)

    def notification_action(self, acc, uids, action):
        if acc not in self.accounts or not acc.client or not uids:
            return
        client = acc.client
        if action == bulletin.ACTION_REPLY:
            self.restore()
            if acc is not self.active:
                self.activate(acc)
            self.run(lambda: client.fetch_message("INBOX", uids[0]),
                     lambda full: self.reply_to(full, False), "Preparando resposta")
            return
        if action == bulletin.ACTION_READ:
            def work():
                for u in uids:
                    client.set_seen("INBOX", u, True)
            said = "Marcada como lida." if len(uids) == 1 else i18n.tr("%d marcadas como lidas.") % len(uids)
        elif action == bulletin.ACTION_ARCHIVE:
            def work():
                client.move("INBOX", uids, client.archive_folder())
            said = "Arquivada." if len(uids) == 1 else i18n.tr("%d mensagens arquivadas.") % len(uids)
        else:
            return

        def done(_):
            speech.speak(i18n.tr(said))
            if acc is self.active and acc.current_raw == "INBOX" and not acc.view_filter:
                self.refresh()
            else:
                self.check_account(acc)
            self.refresh_counts(acc, force=True)

        self.run(work, done, "Atualizando")

    def last_new_action(self, action):
        acc, uids = getattr(self, "last_new", (None, []))
        if acc is None:
            self.announce("Nenhuma mensagem nova recente.")
            return
        self.notification_action(acc, uids, action)
