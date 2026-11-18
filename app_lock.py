"""Bloqueio do AudioMail com PIN e, se você quiser, Windows Hello.

O PIN não fica guardado: só um código derivado dele (PBKDF2), que não dá para
desfazer. O Windows Hello é a verificação do próprio Windows (rosto com câmera
infravermelha, digital ou o PIN do Windows); o AudioMail só pergunta ao Windows
se a pessoa foi confirmada.

O bloqueio é uma tranca de tela: impede que outra pessoa abra o AudioMail com
o Windows desbloqueado. Os dados já ficam criptografados pela conta do Windows.
"""
import asyncio
import base64
import hashlib
import hmac
import os
import threading
import time

import wx

import i18n
from common import set_name

ITERATIONS = 200_000
MAX_TRIES = 5                    # erros seguidos antes de esperar
LOCK_AFTER = (0, 5, 15, 60, -1)  # minutos escondido antes de pedir de novo; 0 sempre, -1 só ao abrir
WARNING = ("O PIN impede que outra pessoa abra o AudioMail neste computador com o Windows desbloqueado. "
           "Seus dados já ficam criptografados pela sua conta do Windows; o PIN não protege contra quem "
           "sabe a senha do Windows. Se esquecer o PIN e não usar o Windows Hello, será preciso apagar "
           "as contas salvas e entrar de novo.")


# ---------- PIN ----------

def valid_pin(pin):
    return (pin or "").isdigit() and 4 <= len(pin) <= 8


def hash_pin(pin, salt=None, iterations=ITERATIONS):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    return {"salt": base64.b64encode(salt).decode("ascii"),
            "hash": base64.b64encode(digest).decode("ascii"), "iter": iterations}


def check_pin(pin, stored):
    try:
        salt = base64.b64decode(stored["salt"])
        expected = base64.b64decode(stored["hash"])
        digest = hashlib.pbkdf2_hmac("sha256", (pin or "").encode("utf-8"), salt, int(stored["iter"]))
    except (KeyError, TypeError, ValueError):
        return False
    return hmac.compare_digest(digest, expected)


def wait_seconds(fails):
    """Quanto esperar depois de ``fails`` erros: nada até 5, depois 30 s, 60 s, 2 min... até 15 min."""
    if fails < MAX_TRIES:
        return 0
    return min(30 * 2 ** ((fails - MAX_TRIES) // MAX_TRIES), 900)


def lock_after_label(minutes):
    if minutes == 0:
        return i18n.tr("Sempre que a janela voltar da bandeja")
    if minutes < 0:
        return i18n.tr("Só ao abrir o AudioMail")
    return i18n.tr("Depois de %d minutos escondido") % minutes


def should_lock_on_restore(enabled, minutes, hidden_at, now=None):
    if not enabled or hidden_at is None or minutes < 0:
        return False
    return (now or time.time()) - hidden_at >= minutes * 60


# ---------- Windows Hello ----------

def _run(coro_factory):
    result = {}

    def work():
        try:
            result["value"] = asyncio.run(coro_factory())
        except Exception as e:      # sem o pacote, Windows antigo, serviço desligado...
            result["error"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(120)
    return result


def hello_available():
    """True se o Windows Hello (rosto, digital ou PIN do Windows) está pronto neste computador."""
    try:
        from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerifierAvailability
    except Exception:
        return False

    async def check():
        return await UserConsentVerifier.check_availability_async()

    r = _run(check)
    return "value" in r and r["value"] == UserConsentVerifierAvailability.AVAILABLE


def hello_verify(message):
    """Pede ao Windows para confirmar a pessoa. True só se o Windows disser que confirmou."""
    try:
        from winrt.windows.security.credentials.ui import UserConsentVerifier, UserConsentVerificationResult
    except Exception:
        return False

    async def verify():
        return await UserConsentVerifier.request_verification_async(message)

    r = _run(verify)
    return "value" in r and r["value"] == UserConsentVerificationResult.VERIFIED


# ---------- janelas ----------

class PinSetupDialog(wx.Dialog):
    """Criar ou trocar o PIN: digitar duas vezes. self.pin no fim."""

    def __init__(self, parent):
        super().__init__(parent, title=i18n.tr("Criar PIN"))
        self.pin = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=i18n.tr("O PIN tem de 4 a 8 números.")), 0, wx.ALL, 10)

        def field(label):
            label = i18n.tr(label)
            sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.RIGHT, 10)
            ctrl = set_name(wx.TextCtrl(self, style=wx.TE_PASSWORD, size=(260, -1)), label)
            sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            return ctrl

        self.first = field("Novo PIN")
        self.second = field("Digite o PIN de novo")
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel(i18n.tr("Salvar"))
        self.FindWindowById(wx.ID_CANCEL).SetLabel(i18n.tr("Cancelar"))
        self.FindWindowById(wx.ID_OK).Bind(wx.EVT_BUTTON, self.on_ok)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.first.SetFocus()

    def on_ok(self, evt=None):
        pin, again = self.first.GetValue().strip(), self.second.GetValue().strip()
        if not valid_pin(pin):
            i18n.message_box("O PIN precisa ter de 4 a 8 números, sem letras.", "Criar PIN",
                             wx.OK | wx.ICON_WARNING, self)
            self.first.SetFocus()
            return
        if pin != again:
            i18n.message_box("Os dois PINs não são iguais. Digite de novo.", "Criar PIN",
                             wx.OK | wx.ICON_WARNING, self)
            self.second.SetValue("")
            self.second.SetFocus()
            return
        self.pin = pin
        self.EndModal(wx.ID_OK)


class LockDialog(wx.Dialog):
    """A janela "AudioMail bloqueado". self.result: "unlocked", "forgot" ou None (fechou)."""

    def __init__(self, parent, cfg, save, hello=False):
        super().__init__(parent, title=i18n.tr("AudioMail bloqueado"))
        self.cfg, self.save = cfg, save
        self.result = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=i18n.tr("Digite o PIN para abrir o AudioMail.")), 0, wx.ALL, 10)
        label = i18n.tr("PIN")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.RIGHT, 10)
        self.pin = set_name(wx.TextCtrl(self, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, size=(260, -1)), label)
        sizer.Add(self.pin, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.status = wx.StaticText(self, label="")
        sizer.Add(self.status, 0, wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.unlock_btn = wx.Button(self, wx.ID_OK, i18n.tr("Desbloquear"))
        self.unlock_btn.Bind(wx.EVT_BUTTON, self.on_unlock)
        row.Add(self.unlock_btn, 0, wx.RIGHT, 8)
        self.hello_btn = None
        if hello:
            self.hello_btn = wx.Button(self, label=i18n.tr("Usar Windows Hello"))
            self.hello_btn.Bind(wx.EVT_BUTTON, self.on_hello)
            row.Add(self.hello_btn, 0, wx.RIGHT, 8)
        forgot = wx.Button(self, label=i18n.tr("Esqueci o PIN"))
        forgot.Bind(wx.EVT_BUTTON, lambda e: self.finish("forgot"))
        row.Add(forgot, 0, wx.RIGHT, 8)
        close = wx.Button(self, wx.ID_CANCEL, i18n.tr("Fechar"))
        row.Add(close, 0)
        sizer.Add(row, 0, wx.ALL, 10)
        self.pin.Bind(wx.EVT_TEXT_ENTER, self.on_unlock)
        self.unlock_btn.SetDefault()
        self.SetSizerAndFit(sizer)
        self.CentreOnScreen()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: self.update_wait(), self.timer)
        self.update_wait()
        self.pin.SetFocus()

    def finish(self, result):
        self.timer.Stop()
        self.result = result
        self.EndModal(wx.ID_OK if result else wx.ID_CANCEL)

    def remaining_wait(self):
        return max(0, int(self.cfg.get("lock_until", 0) - time.time() + 0.999))

    def update_wait(self):
        left = self.remaining_wait()
        self.pin.Enable(left == 0)
        self.unlock_btn.Enable(left == 0)
        if left:
            self.status.SetLabel(i18n.tr("Muitas tentativas erradas. Aguarde %d segundos.") % left)
            if not self.timer.IsRunning():
                self.timer.Start(1000)
        else:
            if self.timer.IsRunning():
                self.timer.Stop()
                self.status.SetLabel(i18n.tr("Pode tentar de novo."))
                self.pin.SetFocus()
        return left

    def on_unlock(self, evt=None):
        if self.update_wait():
            return
        if check_pin(self.pin.GetValue().strip(), self.cfg.get("lock_pin") or {}):
            self.cfg["lock_fails"] = 0
            self.cfg["lock_until"] = 0
            self.save()
            self.finish("unlocked")
            return
        fails = int(self.cfg.get("lock_fails", 0)) + 1
        self.cfg["lock_fails"] = fails
        wait = wait_seconds(fails) if fails % MAX_TRIES == 0 else 0
        if wait:
            self.cfg["lock_until"] = time.time() + wait
        self.save()
        self.pin.SetValue("")
        left = MAX_TRIES - fails % MAX_TRIES
        if wait:
            self.update_wait()
        else:
            self.status.SetLabel(i18n.tr("PIN errado. Restam %d tentativas.") % left if left > 1
                                 else i18n.tr("PIN errado. Resta 1 tentativa."))
        self.pin.SetFocus()

    def on_hello(self, evt=None):
        self.status.SetLabel(i18n.tr("Confirme no Windows Hello."))
        if hello_verify(i18n.tr("Desbloquear o AudioMail")):
            self.cfg["lock_fails"] = 0
            self.cfg["lock_until"] = 0
            self.save()
            self.finish("unlocked")
        else:
            self.status.SetLabel(i18n.tr("O Windows Hello não confirmou. Use o PIN."))
            self.pin.SetFocus()


# ---------- janela principal ----------

class AppLockMixin:
    """Para a janela principal: bloquear, desbloquear e esconder o conteúdo enquanto bloqueado."""

    def lock_enabled(self):
        return bool(self.cfg.get("lock_enabled") and self.cfg.get("lock_pin"))

    def lock_now(self, ask=True):
        """Bloqueia e, com a janela aparecendo, pede o PIN na hora."""
        if not self.lock_enabled():
            if ask:
                i18n.message_box("Para bloquear, crie um PIN em Configurações, Bloqueio com PIN.",
                                 "Bloquear", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.locked = True
        self.panel.Hide()                       # nada da caixa aparece por trás
        self.SetTitle(i18n.tr("AudioMail (bloqueado)"))
        if self.IsShown():
            wx.CallAfter(self.ask_unlock)

    def note_hidden(self):
        self.hidden_at = time.time()

    def lock_if_due(self):
        """Ao voltar da bandeja: bloqueia se passou do tempo escolhido."""
        if self.lock_enabled() and not self.locked and should_lock_on_restore(
                True, int(self.cfg.get("lock_after", 0)), getattr(self, "hidden_at", None)):
            self.lock_now(ask=False)
        return self.locked

    def ask_unlock(self):
        if not self.locked or getattr(self, "_asking_unlock", False):
            return
        self._asking_unlock = True
        try:
            while self.locked:
                dlg = LockDialog(self, self.cfg, lambda: self.save_cfg(),
                                 hello=bool(self.cfg.get("lock_hello")) and hello_available())
                dlg.ShowModal()
                result = dlg.result
                dlg.Destroy()
                if result == "unlocked":
                    self.unlock()
                elif result == "forgot":
                    if self.forgot_pin():
                        break
                else:
                    self.hide_to_tray() if self.setting("keep_tray") else self.quit()
                    break
        finally:
            self._asking_unlock = False

    def unlock(self):
        self.locked = False
        self.panel.Show()
        self.Layout()
        self.SetTitle("AudioMail " + self.active.email if self.active else "AudioMail")
        self.announce("AudioMail desbloqueado.")
        self.list.SetFocus()

    def forgot_pin(self):
        """Com o Windows Hello, dá para criar outro PIN. Sem ele, só apagando os dados salvos."""
        if self.cfg.get("lock_hello") and hello_available():
            if hello_verify(i18n.tr("Confirme para criar um PIN novo no AudioMail")):
                dlg = PinSetupDialog(self)
                if dlg.ShowModal() == wx.ID_OK:
                    self.cfg["lock_pin"] = hash_pin(dlg.pin)
                    self.cfg["lock_fails"] = self.cfg["lock_until"] = 0
                    self.save_cfg()
                    dlg.Destroy()
                    self.unlock()
                    return True
                dlg.Destroy()
                return False
        answer = i18n.message_box(
            "Sem o PIN não dá para abrir o AudioMail. A única saída é apagar deste computador as contas "
            "salvas e as senhas, as mensagens guardadas, os contatos, os lembretes, as mensagens agendadas "
            "e as chaves de IA. As mensagens continuam no servidor do e-mail; depois é só entrar de novo. "
            "Apagar e tirar o PIN?", "Esqueci o PIN", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self)
        if answer != wx.YES:
            return False
        self.erase_for_forgotten_pin()
        self.unlock()
        self.announce("Os dados salvos foram apagados e o PIN foi tirado. Entre de novo na sua conta.")
        wx.CallAfter(self.ask_login, "", True)
        return True

    def save_cfg(self):
        from common import save_config
        save_config(self.cfg)

    def erase_for_forgotten_pin(self):
        """Apaga o que não pode ficar ao alcance de quem não sabe o PIN."""
        import threading as _t
        from common import forget_password
        for acc in list(self.accounts):
            self.stop_watcher(acc)
            if acc.client:
                _t.Thread(target=acc.client.close, daemon=True).start()
        self.accounts, self.active = [], None
        for entry in self.cfg.get("accounts", []):
            forget_password(entry)
        self.cfg.update({"accounts": [], "ai_api_keys_enc": {}, "reminders": [], "lock_enabled": False,
                         "lock_pin": None, "lock_hello": False, "lock_fails": 0, "lock_until": 0})
        self.save_cfg()
        try:
            store = getattr(self, "_store", None)
            if store is None:
                import local_store
                from common import data_dir
                store = local_store.LocalStore(os.path.join(data_dir(), "mensagens.db"))
            store.clear()
            self._store = None
        except Exception:
            pass
        self.contacts.data, self.contacts.groups, self.contacts.meta = {}, [], {}
        self.contacts.save()
        self.scheduled.items = []
        self.scheduled.save()
        self.list.DeleteAllItems()
        self.choice.Clear()
        self.update_account_ui()
        self.update_tray()
