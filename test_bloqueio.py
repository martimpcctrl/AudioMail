"""Testes do bloqueio com PIN e Windows Hello e das seções novas de Configurações
(sem rede e sem mostrar janelas). Rodar: python test_bloqueio.py"""
import os
import shutil
import tempfile
import time
import types
import unittest

import wx

APP = wx.App(False)       # as janelas são criadas, mas nunca mostradas

import app_lock
import audiomail
import contacts as ct
import dialogs
import i18n
import outbox
import settings_extras

boxes = []


def fake_box(message, caption="", *a, **k):
    boxes.append(i18n.tr(message))
    return wx.YES


for mod in (i18n, app_lock.i18n, settings_extras.i18n, dialogs.i18n):
    mod.message_box = fake_box


class PinTest(unittest.TestCase):
    def test_valid_pin(self):
        self.assertTrue(app_lock.valid_pin("1234"))
        self.assertTrue(app_lock.valid_pin("12345678"))
        for bad in ("123", "123456789", "12a4", "", None, "12 34"):
            self.assertFalse(app_lock.valid_pin(bad), bad)

    def test_hash_and_check(self):
        stored = app_lock.hash_pin("2468", iterations=1000)
        self.assertNotIn("2468", str(stored))
        self.assertTrue(app_lock.check_pin("2468", stored))
        self.assertFalse(app_lock.check_pin("2469", stored))
        self.assertFalse(app_lock.check_pin("2468", {}))
        self.assertFalse(app_lock.check_pin("2468", None))
        other = app_lock.hash_pin("2468", iterations=1000)
        self.assertNotEqual(stored["hash"], other["hash"])    # sal diferente a cada vez

    def test_wait_grows(self):
        self.assertEqual([app_lock.wait_seconds(n) for n in (0, 4, 5, 10, 15, 100)], [0, 0, 30, 60, 120, 900])

    def test_lock_on_restore(self):
        now = 10_000
        self.assertTrue(app_lock.should_lock_on_restore(True, 0, now - 1, now))
        self.assertFalse(app_lock.should_lock_on_restore(True, 5, now - 60, now))
        self.assertTrue(app_lock.should_lock_on_restore(True, 5, now - 301, now))
        self.assertFalse(app_lock.should_lock_on_restore(True, -1, now - 99999, now))
        self.assertFalse(app_lock.should_lock_on_restore(False, 0, now - 1, now))
        self.assertFalse(app_lock.should_lock_on_restore(True, 0, None, now))
        self.assertEqual(app_lock.lock_after_label(15), "Depois de 15 minutos escondido")

    def test_hello_without_package_says_no(self):
        old = app_lock._run
        app_lock._run = lambda factory: {"error": OSError("sem Windows Hello")}
        try:
            self.assertFalse(app_lock.hello_available())
            self.assertFalse(app_lock.hello_verify("teste"))
        finally:
            app_lock._run = old


class LockDialogTest(unittest.TestCase):
    def setUp(self):
        self.frame = wx.Frame(None)
        self.saved = []
        self.cfg = {"lock_pin": app_lock.hash_pin("1234", iterations=1000)}

    def tearDown(self):
        self.frame.Destroy()

    def dialog(self, hello=False):
        dlg = app_lock.LockDialog(self.frame, self.cfg, lambda: self.saved.append(dict(self.cfg)), hello)
        dlg.EndModal = lambda code: setattr(dlg, "ended", code)
        return dlg

    def test_right_pin_unlocks(self):
        dlg = self.dialog()
        dlg.pin.SetValue("1234")
        dlg.on_unlock()
        self.assertEqual(dlg.result, "unlocked")
        self.assertEqual(self.cfg["lock_fails"], 0)
        dlg.Destroy()

    def test_wrong_pins_then_wait(self):
        dlg = self.dialog()
        for _ in range(4):
            dlg.pin.SetValue("0000")
            dlg.on_unlock()
        self.assertEqual(dlg.status.GetLabel(), "PIN errado. Resta 1 tentativa.")
        dlg.pin.SetValue("0000")
        dlg.on_unlock()
        self.assertGreater(self.cfg["lock_until"], time.time())
        self.assertIn("Aguarde", dlg.status.GetLabel())
        self.assertFalse(dlg.pin.IsEnabled())
        dlg.pin.SetValue("1234")
        dlg.on_unlock()                       # esperando: nem o PIN certo entra
        self.assertIsNone(dlg.result)
        self.cfg["lock_until"] = 0
        dlg.update_wait()
        dlg.pin.SetValue("1234")
        dlg.on_unlock()
        self.assertEqual(dlg.result, "unlocked")
        dlg.timer.Stop()
        dlg.Destroy()

    def test_hello_button(self):
        dlg = self.dialog(hello=True)
        labels = [c.GetLabel() for c in dlg.GetChildren() if isinstance(c, wx.Button)]
        self.assertEqual(labels, ["Desbloquear", "Usar Windows Hello", "Esqueci o PIN", "Fechar"])
        old = app_lock.hello_verify
        app_lock.hello_verify = lambda message: True
        try:
            dlg.on_hello()
        finally:
            app_lock.hello_verify = old
        self.assertEqual(dlg.result, "unlocked")
        dlg.Destroy()
        plain = self.dialog(hello=False)
        self.assertNotIn("Usar Windows Hello", [c.GetLabel() for c in plain.GetChildren() if isinstance(c, wx.Button)])
        plain.Destroy()

    def test_pin_setup(self):
        dlg = app_lock.PinSetupDialog(self.frame)
        dlg.EndModal = lambda code: setattr(dlg, "ended", code)
        dlg.first.SetValue("12")
        dlg.on_ok()
        self.assertIsNone(dlg.pin)
        self.assertIn("4 a 8 números", boxes[-1])
        dlg.first.SetValue("5678")
        dlg.second.SetValue("5679")
        dlg.on_ok()
        self.assertIsNone(dlg.pin)
        self.assertIn("não são iguais", boxes[-1])
        dlg.second.SetValue("5678")
        dlg.on_ok()
        self.assertEqual(dlg.pin, "5678")
        dlg.Destroy()


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.frame = wx.Frame(None)

    def tearDown(self):
        self.frame.Destroy()

    def settings(self, **extra):
        values = {k: audiomail.DEFAULTS[k] for k in audiomail.DEFAULTS}
        values.update(extra)
        return values

    def test_sections_and_values(self):
        info = {"store_size": 2048, "hello": True, "has_pin": True,
                "account_email": "eu@x.com", "account_signature": "Abraço"}
        dlg = dialogs.SettingsDialog(self.frame, self.settings(lock_enabled=True, lock_after=15), info)
        labels = [c.GetLabel() for c in dlg.GetChildren()[0].GetChildren() if isinstance(c, wx.CollapsiblePane)]
        for wanted in ("Bloqueio com PIN", "Mensagens guardadas no computador", "Assinatura desta conta"):
            self.assertIn(wanted, labels)
        got = dlg.get_settings()
        self.assertEqual((got["lock_enabled"], got["lock_after"], got["offline_days"]), (True, 15, 90))
        self.assertEqual(got["_account_signature"], "Abraço")
        self.assertIsNone(got["_new_pin"])
        self.assertTrue(dlg.extras.validate())
        dlg.Destroy()

    def test_turning_lock_on_asks_for_a_pin(self):
        dlg = dialogs.SettingsDialog(self.frame, self.settings(), {"hello": False})
        self.assertFalse(dlg.extras.hello.IsEnabled())
        dlg.extras.lock.SetValue(True)
        old = app_lock.PinSetupDialog

        class Cancelled:
            pin = None

            def __init__(self, parent):
                pass

            def ShowModal(self):
                return wx.ID_CANCEL

            def Destroy(self):
                pass

        app_lock.PinSetupDialog = Cancelled
        try:
            self.assertFalse(dlg.extras.validate())
            self.assertIn("Crie um PIN", boxes[-1])
            Cancelled.pin = "4321"
            Cancelled.ShowModal = lambda self: wx.ID_OK
            self.assertTrue(dlg.extras.validate())
        finally:
            app_lock.PinSetupDialog = old
        self.assertEqual(dlg.get_settings()["_new_pin"], "4321")
        dlg.Destroy()

    def test_no_account_section_without_account(self):
        dlg = dialogs.SettingsDialog(self.frame, self.settings(), {})
        self.assertNotIn("_account_signature", dlg.get_settings())
        dlg.Destroy()


class MainWindowTest(unittest.TestCase):
    def make(self, **cfg):
        f = types.SimpleNamespace()
        f.cfg = dict(cfg)
        f.setting = lambda key: f.cfg.get(key, audiomail.DEFAULTS[key])
        f.spoken, f.toasts, f.titles = [], [], []
        f.announce = lambda text, box=False: f.spoken.append(i18n.tr(text))
        f.toast = lambda title, text: f.toasts.append((title, text))
        f.panel = types.SimpleNamespace(shown=True, Hide=lambda: setattr(f.panel, "shown", False),
                                        Show=lambda: setattr(f.panel, "shown", True))
        f.SetTitle = f.titles.append
        f.IsShown = lambda: False
        f.Layout = lambda: None
        f.list = types.SimpleNamespace(SetFocus=lambda: None, DeleteAllItems=lambda: None)
        f.choice = types.SimpleNamespace(Clear=lambda: None)
        f.active, f.accounts, f.locked, f.hidden_at = None, [], False, None
        for name in ("lock_enabled", "lock_now", "note_hidden", "lock_if_due", "unlock",
                     "erase_for_forgotten_pin", "save_cfg"):
            setattr(f, name, types.MethodType(getattr(app_lock.AppLockMixin, name), f))
        return f

    def test_lock_and_unlock(self):
        f = self.make(lock_enabled=True, lock_pin={"x": 1})
        f.lock_now()
        self.assertTrue(f.locked and not f.panel.shown)
        self.assertEqual(f.titles[-1], "AudioMail (bloqueado)")
        f.unlock()
        self.assertTrue(not f.locked and f.panel.shown)
        self.assertEqual(f.spoken[-1], "AudioMail desbloqueado.")

    def test_lock_now_without_pin_explains(self):
        f = self.make()
        f.lock_now()
        self.assertFalse(f.locked)
        self.assertIn("crie um PIN", boxes[-1])

    def test_lock_after_time_hidden(self):
        f = self.make(lock_enabled=True, lock_pin={"x": 1}, lock_after=5)
        f.hidden_at = time.time() - 60
        self.assertFalse(f.lock_if_due())
        f.hidden_at = time.time() - 400
        self.assertTrue(f.lock_if_due())

    def test_locked_notification_hides_sender(self):
        f = self.make(notify=True, sound=False, speak=False)
        f.locked = True
        f.accounts = [1]
        f.SetStatusText = lambda text: None
        audiomail.MainFrame.notify_new(f, None, [{"from": "Banco Secreto", "subject": "Fatura", "uid": "1"}])
        self.assertEqual(f.toasts, [("AudioMail", "Nova mensagem")])

    def test_locked_tray_menu(self):
        frame = types.SimpleNamespace(locked=True, restore=lambda: None, quit=lambda: None)
        tray = audiomail.TrayIcon.__new__(audiomail.TrayIcon)
        tray.frame = frame
        menu = audiomail.TrayIcon.CreatePopupMenu(tray)
        self.assertEqual([i.GetItemLabelText() for i in menu.GetMenuItems()], ["Abrir AudioMail", "Sair"])

    def test_forgotten_pin_erases_saved_data(self):
        tmp = tempfile.mkdtemp()
        try:
            f = self.make(lock_enabled=True, lock_pin={"x": 1}, accounts=[{"email": "eu@x.com"}],
                          ai_api_keys_enc={"openai": "x"}, reminders=[{"title": "a"}])
            f.contacts = ct.Contacts(os.path.join(tmp, "c.json"))
            f.contacts.set_contact("", "Ana", "ana@x.com")
            f.scheduled = outbox.Scheduled(tmp)
            f.scheduled.items = [{"x": 1}]
            f.stop_watcher = lambda acc: None
            f.update_account_ui = f.update_tray = lambda: None
            f._store = types.SimpleNamespace(clear=lambda: f.spoken.append("db apagado"))
            old = app_lock.__dict__.get("save_config")
            import common
            saved = []
            real = common.save_config
            common.save_config = lambda cfg: saved.append(dict(cfg))
            try:
                f.erase_for_forgotten_pin()
            finally:
                common.save_config = real
            self.assertEqual(f.cfg["accounts"], [])
            self.assertEqual(f.cfg["ai_api_keys_enc"], {})
            self.assertFalse(f.cfg["lock_enabled"])
            self.assertIsNone(f.cfg["lock_pin"])
            self.assertEqual(f.contacts.data, {})
            self.assertEqual(f.scheduled.items, [])
            self.assertIn("db apagado", f.spoken)
            self.assertTrue(saved)
            self.assertIsNone(old)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
