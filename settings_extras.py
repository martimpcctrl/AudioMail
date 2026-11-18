"""Seções da janela Configurações que antes ficavam espalhadas pelo menu Ferramentas:
bloqueio com PIN, mensagens guardadas no computador e a assinatura da conta aberta."""
import wx

import app_lock
import i18n
import mail_core as mc
from common import set_name

OFFLINE_DAYS = (30, 90, 180, 365, 0)     # 0 = sem limite


def days_label(days):
    return i18n.tr("Sem limite") if not days else i18n.tr("Últimos %d dias") % days


class SettingsExtras:
    """Monta as seções dentro da janela Configurações. ``info``: store_size, hello,
    has_pin, account_email e account_signature."""

    def __init__(self, dialog, section, check, settings, info):
        self.dialog = dialog
        self.info = info
        self.new_pin = None
        self.clear_offline = False

        # ---- bloqueio ----
        panel, group = section("Bloqueio com PIN")
        self.lock_panel = panel
        self.lock = check(panel, group, "Pedir PIN para abrir o AudioMail", "lock_enabled")
        self.pin_btn = wx.Button(panel, label=i18n.tr("Trocar PIN..." if info.get("has_pin") else "Criar PIN..."))
        self.pin_btn.Bind(wx.EVT_BUTTON, self.on_pin)
        group.Add(self.pin_btn, 0, wx.LEFT | wx.TOP, 8)
        label = i18n.tr("Pedir o PIN de novo")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.lock_after = set_name(wx.Choice(panel, choices=[app_lock.lock_after_label(m)
                                                             for m in app_lock.LOCK_AFTER]), label)
        current = settings.get("lock_after", 0)
        self.lock_after.SetSelection(app_lock.LOCK_AFTER.index(current) if current in app_lock.LOCK_AFTER else 0)
        group.Add(self.lock_after, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.hello = check(panel, group,
                           "Também desbloquear com o Windows Hello (rosto, digital ou PIN do Windows)",
                           "lock_hello")
        if not info.get("hello"):
            self.hello.SetValue(False)
            self.hello.Enable(False)
            hint = i18n.tr("O Windows Hello não está configurado neste computador.")
        else:
            hint = i18n.tr("O rosto pelo Windows Hello usa câmera infravermelha e não se engana com foto.")
        group.Add(wx.StaticText(panel, label=hint), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        warning = wx.StaticText(panel, label=i18n.tr(app_lock.WARNING))
        warning.Wrap(480)
        group.Add(warning, 0, wx.ALL, 8)
        self.lock.Bind(wx.EVT_CHECKBOX, lambda e: self.update_lock())
        self.update_lock()

        # ---- mensagens guardadas ----
        panel, group = section("Mensagens guardadas no computador")
        self.offline = check(panel, group,
                             "Guardar as mensagens no computador, para a lista abrir na hora e para ler sem internet",
                             "offline_enabled")
        self.offline_att = check(panel, group,
                                 "Guardar também os anexos das mensagens abertas (ocupa mais espaço)",
                                 "offline_attachments")
        label = i18n.tr("Guardar as mensagens de")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.days = set_name(wx.Choice(panel, choices=[days_label(d) for d in OFFLINE_DAYS]), label)
        days = settings.get("offline_days", 90)
        self.days.SetSelection(OFFLINE_DAYS.index(days) if days in OFFLINE_DAYS else 1)
        group.Add(self.days, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        size = info.get("store_size", 0)
        group.Add(wx.StaticText(panel, label=i18n.tr("Espaço usado agora: %s") % mc.format_size(size)),
                  0, wx.LEFT | wx.TOP, 8)
        group.Add(wx.StaticText(panel, label=i18n.tr(
            "Tudo fica só neste computador, criptografado pelo Windows, e não é enviado a ninguém.")),
            0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.clear_btn = wx.Button(panel, label=i18n.tr("Apagar todas as mensagens guardadas"))
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.clear_btn.Enable(size > 0)
        group.Add(self.clear_btn, 0, wx.ALL, 8)
        self.offline.Bind(wx.EVT_CHECKBOX, lambda e: self.update_offline())
        self.update_offline()

        # ---- assinatura da conta aberta ----
        self.account_signature = None
        if info.get("account_email"):
            panel, group = section("Assinatura desta conta")
            label = i18n.tr("Assinatura só da conta %s (vazio usa a assinatura geral de Outras opções)") % \
                info["account_email"]
            group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
            self.account_signature = set_name(wx.TextCtrl(panel, value=info.get("account_signature", ""),
                                                          style=wx.TE_MULTILINE, size=(-1, 70)), label)
            group.Add(self.account_signature, 0, wx.EXPAND | wx.ALL, 8)

    # ---- bloqueio ----
    def update_lock(self):
        on = self.lock.GetValue()
        for ctrl in (self.lock_after, self.pin_btn):
            ctrl.Enable(on)
        self.hello.Enable(on and bool(self.info.get("hello")))

    def on_pin(self, evt=None):
        dlg = app_lock.PinSetupDialog(self.dialog)
        if dlg.ShowModal() == wx.ID_OK:
            self.new_pin = dlg.pin
            self.pin_btn.SetLabel(i18n.tr("Trocar PIN..."))
        dlg.Destroy()

    def validate(self):
        """Bloqueio ligado sem PIN: pede para criar agora. False mantém a janela aberta."""
        if self.lock.GetValue() and not self.info.get("has_pin") and not self.new_pin:
            self.on_pin()
            if not self.new_pin:
                i18n.message_box("Crie um PIN para ligar o bloqueio, ou desmarque a opção.",
                                 "Bloqueio com PIN", wx.OK | wx.ICON_INFORMATION, self.dialog)
                self.lock.SetFocus()
                return False
        return True

    # ---- mensagens guardadas ----
    def update_offline(self):
        on = self.offline.GetValue()
        self.offline_att.Enable(on)
        self.days.Enable(on)

    def on_clear(self, evt=None):
        answer = i18n.message_box("Apagar todas as mensagens guardadas no computador? As mensagens "
                                  "continuam no servidor; só a cópia deste computador é apagada.",
                                  "Mensagens guardadas no computador",
                                  wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self.dialog)
        if answer == wx.YES:
            self.clear_offline = True
            self.clear_btn.Enable(False)

    def values(self):
        out = {
            "lock_enabled": self.lock.GetValue(),
            "lock_after": app_lock.LOCK_AFTER[max(0, self.lock_after.GetSelection())],
            "lock_hello": self.hello.GetValue() and self.lock.GetValue(),
            "offline_enabled": self.offline.GetValue(),
            "offline_attachments": self.offline_att.GetValue(),
            "offline_days": OFFLINE_DAYS[max(0, self.days.GetSelection())],
            "_new_pin": self.new_pin,
            "_offline_clear": self.clear_offline,
        }
        if self.account_signature is not None:
            out["_account_signature"] = self.account_signature.GetValue().strip()
        return out
