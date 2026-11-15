"""AudioMail: cliente de e-mail acessivel para Windows (wxPython, Gmail e outros provedores)."""
import os
import sys
import socket
import hashlib
import tempfile
import threading
import time

import wx
import wx.adv

import mail_core as mc
import manual
import sounds
import speech
import translator
import updater
import message_text as mt
import webbrowser
import i18n
import ai_summary
import legal
import outbox
import providers
import compose_extras as cx
import organize
import views
from contacts import Contacts
from common import data_dir
from common import (DEFAULTS, config_path, default_sound_path, find_account, forget_password,
                    get_ai_api_key, load_config, make_icon, pick_sound_file, recall_password,
                    protect_local_value, remember_password, save_config, set_ai_api_key,
                    set_autostart, set_name, unprotect_local_value)
from dialogs import (ComposeDialog, LoginDialog, MyTicketsDialog, ReadDialog, SettingsDialog, TicketDialog, UpdateDialog,
                     unique_path)
from version import APP_VERSION
from reminders import ReminderDialog

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SITE = "https://martimtech.ddns.net/"


class Account:
    """Tudo que pertence a uma conta conectada."""

    def __init__(self, email):
        self.email = email
        self.client = None
        self.watcher = None
        self.idle_active = False
        self.folders = []
        self.current_raw = "INBOX"
        self.messages = []
        self.view = []
        self.search = ""
        self.baseline = None      # maior UID da caixa de entrada que ja foi visto
        self.inbox_unread = 0
        self.checking = False
        self.recheck = False
        self.manual = False
        self.view_filter = None     # pasta de mentira: "flagged" ou "category:..." (aba do Gmail)
        self.limit = views.PAGE      # quantas mensagens mostrar (Carregar mais aumenta)
        self.total = 0               # quantas a pasta (ou a busca) tem no servidor
        self.counts = {}             # não lidas por pasta
        self.counts_at = 0.0
        self.counting = False
        self.snippets = {}           # (pasta, uid) -> começo do texto
        self.loading_snippets = False
        self.loading_more = False


def _active(name, default):
    """Propriedade da janela que le e grava na conta ativa."""
    def getter(self):
        return getattr(self.active, name) if self.active else default()

    def setter(self, value):
        if self.active:
            setattr(self.active, name, value)
    return property(getter, setter)


class TranslationService:
    """Liga o tradutor as configuracoes e a autorizacao do usuario."""

    def __init__(self, frame):
        self.frame = frame

    @property
    def target(self):
        return self.frame.setting("translate_to")

    @property
    def compose_lang(self):
        return self.frame.setting("compose_lang")

    def set_compose_lang(self, code):
        self.frame.cfg["compose_lang"] = code
        save_config(self.frame.cfg)

    def ask_consent(self, parent):
        """Pergunta uma vez se pode enviar texto ao servico de traducao do Google."""
        if self.frame.setting("translate_consent"):
            return True
        ask = i18n.message_box(
            "Traduzir envia o texto para o serviço de tradução do Google. Só vai o texto que "
            "você mandar traduzir, e só quando você pedir. Autorizar agora e nas próximas vezes?",
            "Autorizar tradução", wx.YES_NO | wx.ICON_QUESTION, parent)
        if ask != wx.YES:
            return False
        self.frame.cfg["translate_consent"] = True
        save_config(self.frame.cfg)
        return True

    def translate(self, text, target):
        return translator.translate_text(text, target)


class AISummaryService:
    """Usa a chave local da pessoa para resumir somente quando ela pede."""

    def __init__(self, frame):
        self.frame = frame

    @property
    def provider(self):
        return self.frame.setting("ai_summary_provider")

    def configured(self):
        return bool(get_ai_api_key(self.frame.cfg, self.provider))

    def summarize(self, text):
        language = {"pt": "português", "en": "English", "es": "español"}.get(
            self.frame.setting("ui_language"), "português")
        return ai_summary.summarize(
            text, self.provider, get_ai_api_key(self.frame.cfg, self.provider),
            self.frame.setting("ai_summary_model"), self.frame.setting("ai_summary_endpoint"),
            language=language)

    def ask_consent(self, parent):
        consents = self.frame.cfg.setdefault("ai_summary_consent", {})
        if consents.get(self.provider):
            return True
        provider_name = {"openai": "OpenAI", "gemini": "Gemini",
                         "compatible": "outro provedor configurado"}.get(self.provider, self.provider)
        if not self.configured():
            i18n.message_box("Configure primeiro sua chave de API em Configurações > Resumo com IA.",
                             "Resumo com IA", wx.OK | wx.ICON_INFORMATION, parent)
            return False
        answer = i18n.message_box(
            "O texto desta mensagem ou conversa será enviado ao %s usando sua chave de API. "
            "O provedor pode cobrar pelo uso; a assinatura do ChatGPT não inclui automaticamente "
            "o uso da API. Autorizar agora e nas próximas vezes?" % provider_name,
            "Enviar mensagem para resumo com IA", wx.YES_NO | wx.ICON_QUESTION, parent)
        if answer != wx.YES:
            return False
        consents[self.provider] = True
        save_config(self.frame.cfg)
        return True


class TrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        super().__init__(wx.adv.TBI_DEFAULT_TYPE)
        self.frame = frame
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_UP, lambda e: frame.restore())
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, lambda e: frame.restore())

    def CreatePopupMenu(self):
        menu = wx.Menu()
        for label, fn in (("Abrir AudioMail", self.frame.restore),
                          ("Verificar agora", self.frame.check_now),
                          ("Configurações", self.frame.open_settings),
                          ("Sair", self.frame.quit)):
            item = menu.Append(wx.ID_ANY, i18n.tr(label))
            menu.Bind(wx.EVT_MENU, lambda e, f=fn: f(), item)
        return menu


class MainFrame(views.ViewsMixin, organize.OrganizeMixin, wx.Frame):
    def SetStatusText(self, text, number=0):
        return super().SetStatusText(i18n.tr(text), number)

    client = _active("client", lambda: None)
    folders = _active("folders", list)
    messages = _active("messages", list)
    view = _active("view", list)
    current_raw = _active("current_raw", lambda: "INBOX")

    def __init__(self):
        super().__init__(None, title="AudioMail", size=(960, 640))
        self.cfg = load_config()
        i18n.set_language(self.cfg.get("ui_language", "pt"))
        self.accounts = []
        self.active = None
        self.login_open = False
        self.quitting = False
        self._toast = None
        self.updating = False
        self.update_dialog_open = False
        self.pending_update = None
        self.prompted_version = None
        self.translation = TranslationService(self)
        self.ai_summary = AISummaryService(self)
        self.contacts = Contacts(os.path.join(data_dir(), "contatos.json"))
        self.scheduled = outbox.Scheduled(data_dir())
        self.pending_sends = []    # envios esperando o tempo de desfazer
        self.pending_moves = []    # mover/apagar esperando o tempo de desfazer
        self.folder_timer = None   # espera parar numa pasta antes de carregar
        self.sending_scheduled = set()

        sounds.ensure_default(default_sound_path())
        self.icon = make_icon()
        self.SetIcon(self.icon)
        self.tray = TrayIcon(self)
        self.update_tray()
        self.timer = wx.Timer(self)
        self.reminder_timer = wx.Timer(self)
        self.update_timer = wx.Timer(self)

        panel = wx.Panel(self)
        self.panel = panel
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.lbl_account = wx.StaticText(panel, label=i18n.tr("Conta"))  # rotulos antes dos campos
        self.account_choice = set_name(wx.Choice(panel), i18n.tr("Conta"))
        lbl_folder = wx.StaticText(panel, label=i18n.tr("Pasta"))
        self.choice = set_name(wx.Choice(panel), i18n.tr("Pasta"))
        lbl_search = wx.StaticText(panel, label=i18n.tr("Buscar"))
        self.search_box = set_name(wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER), i18n.tr("Buscar"))
        lbl_list = wx.StaticText(panel, label=i18n.tr("Mensagens"))
        # várias selecionadas, como nos programas oficiais (Shift e Ctrl com as setas, Ctrl+A)
        self.list = set_name(wx.ListCtrl(panel, style=wx.LC_REPORT), i18n.tr("Mensagens"))
        self.list.InsertColumn(0, i18n.tr("Estado"), width=90)
        self.list.InsertColumn(1, i18n.tr("De"), width=220)
        self.list.InsertColumn(2, i18n.tr("Assunto"), width=380)
        self.list.InsertColumn(3, i18n.tr("Prévia"), width=320 if self.setting("show_preview") else 0)
        self.list.InsertColumn(4, i18n.tr("Data"), width=140)
        sizer.Add(self.lbl_account, 0, wx.LEFT | wx.TOP, 8)
        sizer.Add(self.account_choice, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(lbl_folder, 0, wx.LEFT | wx.TOP, 8)
        sizer.Add(self.choice, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(lbl_search, 0, wx.LEFT, 8)
        sizer.Add(self.search_box, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(lbl_list, 0, wx.LEFT, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(sizer)
        self.CreateStatusBar()
        self.update_account_ui()

        self.build_menu()
        self.account_choice.Bind(wx.EVT_CHOICE, self.on_account_choice)
        self.choice.Bind(wx.EVT_CHOICE, self.on_folder)
        self.search_box.Bind(wx.EVT_TEXT_ENTER, lambda e: self.do_search())
        self.search_box.Bind(wx.EVT_KEY_DOWN, self.on_search_key)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda e: self.open_selected())
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)
        self.list.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_item_focused)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.Bind(wx.EVT_TIMER, self.on_reminder_timer, self.reminder_timer)
        self.Bind(wx.EVT_TIMER, self.on_update_timer, self.update_timer)
        self.Bind(wx.EVT_ICONIZE, self.on_iconize)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_END_SESSION, self.on_end_session)
        self.activation_server = None
        self.start_activation_listener()
        self.Centre()
        self.apply_update_timer()
        self.reminder_timer.Start(15000)
        wx.CallAfter(self.start)
        if not self.cfg.get("reminders_intro_shown", False):
            self.cfg["reminders_intro_shown"] = True
            save_config(self.cfg)
            wx.CallAfter(self.show_reminders_intro)

    # ---- configuracoes ----
    def setting(self, key):
        return self.cfg.get(key, DEFAULTS[key])

    def sound_path(self):
        f = self.setting("sound_file")
        if f and os.path.isfile(f):
            return f
        return default_sound_path()

    def open_settings(self):
        dlg = SettingsDialog(self, {k: self.setting(k) for k in DEFAULTS})
        if dlg.ShowModal() == wx.ID_OK:
            new = dlg.get_settings()
            entered_api_key = new.pop("_ai_api_key", "")
            remove_api_key = new.pop("_ai_remove_key", False)
            selected_provider = new.get("ai_summary_provider", "openai")
            key_saved = True
            if entered_api_key:
                key_saved = set_ai_api_key(self.cfg, selected_provider, entered_api_key)
            elif remove_api_key:
                set_ai_api_key(self.cfg, selected_provider, None)
            old_autostart = self.setting("autostart")
            old_language = self.setting("ui_language")
            self.cfg.update(new)
            save_config(self.cfg)
            if not key_saved:
                i18n.message_box("Não consegui proteger a chave com a criptografia do Windows. A chave não foi salva.",
                                 "Resumo com IA", wx.OK | wx.ICON_ERROR, self)
            if new.get("ui_language", old_language) != old_language:
                i18n.message_box("Idioma salvo. Reinicie o AudioMail para aplicar a alteração.",
                                 "Idioma", wx.OK | wx.ICON_INFORMATION, self)
            for acc in self.accounts:
                self.stop_watcher(acc)
                self.start_watcher(acc)
            self.apply_timer()
            self.apply_update_timer()
            if new["autostart"] != old_autostart and not set_autostart(new["autostart"]):
                i18n.message_box("Não foi possível alterar o início com o Windows.",
                              "Aviso", wx.OK | wx.ICON_WARNING, self)
            self.announce("Configurações salvas.")
        dlg.Destroy()

    def choose_sound(self):
        path = pick_sound_file(self)
        if path:
            self.cfg["sound_file"] = path
            save_config(self.cfg)
            sounds.play(path)
            self.announce("Som de notificação alterado.")

    def test_sound(self):
        sounds.play(self.sound_path())

    def announce(self, text, box=False):
        """Mostra na barra de status e fala pelo leitor de tela; sem fala, pode abrir um aviso."""
        text = i18n.tr(text)
        self.SetStatusText(text)
        spoke = bool(self.setting("speak")) and speech.speak(text, interrupt=True)
        if box and not spoke:
            i18n.message_box(text, "AudioMail", wx.OK, wx.GetActiveWindow() or self)

    # ---- menu ----
    def add(self, menu, label, handler):
        item = menu.Append(wx.ID_ANY, i18n.tr(label))
        self.Bind(wx.EVT_MENU, handler, item)

    def build_menu(self):
        bar = wx.MenuBar()
        m = wx.Menu()
        self.add(m, "Nova mensagem\tCtrl+N", lambda e: self.compose())
        self.add(m, "Atualizar\tF5", lambda e: self.refresh())
        self.add(m, "Buscar\tCtrl+F", lambda e: self.search_box.SetFocus())
        self.add(m, "Busca avançada...\tCtrl+Shift+S", lambda e: self.open_advanced_search())
        self.add(m, "Carregar mais mensagens\tCtrl+Shift+M", lambda e: self.load_more())
        self.add(m, "Ir para as pastas\tF6", lambda e: self.choice.SetFocus())
        self.add(m, "Ir para as contas\tF7", lambda e: self.account_choice.SetFocus())
        self.add(m, "Adicionar conta", lambda e: self.ask_login(blank=True))
        self.add(m, "Remover conta atual", lambda e: self.remove_account())
        self.add(m, "Esconder na bandeja\tCtrl+M", lambda e: self.hide_to_tray())
        m.AppendSeparator()
        self.add(m, "Sair\tCtrl+Q", lambda e: self.quit())
        bar.Append(m, i18n.tr("&Arquivo"))

        m = wx.Menu()
        self.add(m, "Abrir", lambda e: self.open_selected())
        self.add(m, "Responder\tCtrl+R", lambda e: self.reply_selected(False))
        self.add(m, "Responder a todos\tCtrl+Shift+R", lambda e: self.reply_selected(True))
        self.add(m, "Encaminhar\tCtrl+Shift+F", lambda e: self.forward_selected())
        self.add(m, "Traduzir mensagem\tCtrl+T", lambda e: self.open_selected(auto_translate=True))
        m.AppendSeparator()
        self.add(m, "Arquivar\tCtrl+E", lambda e: self.archive_selected())
        self.add(m, "Mover para a pasta...\tCtrl+Shift+V", lambda e: self.move_selected())
        self.add(m, "Marcar como spam ou não spam\tCtrl+J", lambda e: self.spam_selected())
        self.add(m, "Apagar\tDel", lambda e: self.on_delete_key())
        self.add(m, "Desfazer\tCtrl+Z", lambda e: self.on_undo_key())
        m.AppendSeparator()
        self.add(m, "Pôr ou tirar estrela\tCtrl+S", lambda e: self.toggle_star_selected())
        self.add(m, "Marcadores...\tCtrl+B", lambda e: self.open_labels())
        self.add(m, "Selecionar tudo\tCtrl+A", lambda e: self.select_all())
        self.add(m, "Marcar como lida\tCtrl+Shift+L", lambda e: self.mark_selected(True))
        self.add(m, "Marcar como não lida\tCtrl+Shift+U", lambda e: self.mark_selected(False))
        self.add(m, "Bloquear remetente\tCtrl+Shift+B", lambda e: self.block_selected())
        self.add(m, "Criar regra a partir desta mensagem", lambda e: self.open_rules(from_selected=True))
        m.AppendSeparator()
        self.add(m, "Desfazer envio\tCtrl+Shift+Z", lambda e: self.undo_send())
        self.add(m, "Mensagens agendadas", lambda e: self.open_scheduled())
        self.group_item = m.AppendCheckItem(wx.ID_ANY, i18n.tr("Agrupar por conversa\tCtrl+G"))
        self.group_item.Check(bool(self.setting("group_threads")))
        self.Bind(wx.EVT_MENU, self.on_toggle_group, self.group_item)
        self.preview_item = m.AppendCheckItem(wx.ID_ANY, i18n.tr("Mostrar prévia do texto na lista"))
        self.preview_item.Check(bool(self.setting("show_preview")))
        self.Bind(wx.EVT_MENU, self.on_toggle_preview, self.preview_item)
        bar.Append(m, i18n.tr("&Mensagem"))

        m = wx.Menu()
        self.add(m, "Configurações\tCtrl+P", lambda e: self.open_settings())
        self.add(m, "Escolher som de notificação", lambda e: self.choose_sound())
        self.add(m, "Testar som", lambda e: self.test_sound())
        self.add(m, "Calendário", lambda e: self.open_reminders())
        self.add(m, "Regras\tCtrl+Shift+G", lambda e: self.open_rules())
        self.add(m, "Remetentes bloqueados", lambda e: self.open_blocked())
        bar.Append(m, i18n.tr("&Ferramentas"))

        m = wx.Menu()
        self.add(m, "Abrir manual\tF1", lambda e: self.open_manual())
        self.add(m, "Abrir chamado de suporte", lambda e: self.open_ticket())
        self.add(m, "Meus chamados", lambda e: self.open_my_tickets())
        self.add(m, "Privacidade e termos do AudioMail", lambda e: self.open_legal_documents())
        self.add(m, "Verificar atualizações", lambda e: self.check_updates(manual=True))
        self.add(m, "Sobre o AudioMail", lambda e: self.show_about())
        bar.Append(m, i18n.tr("A&juda"))
        self.SetMenuBar(bar)

    # ---- bandeja, janela e encerramento ----
    def update_tray(self):
        total = sum(a.inbox_unread for a in self.accounts)
        tip = "AudioMail"
        if total:
            tip += ", %d não lidas" % total
        self.tray.SetIcon(self.icon, tip)

    def start_activation_listener(self):
        """Recebe pedidos locais para mostrar esta janela quando o app for aberto de novo."""
        port = activation_port()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("127.0.0.1", port))
            server.listen(4)
            server.settimeout(1.0)
        except OSError:
            server.close()
            return
        self.activation_server = server

        def listen():
            while not self.quitting:
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return
                try:
                    with conn:
                        if conn.recv(32) == b"SHOW":
                            conn.sendall(b"OK")
                            wx.CallAfter(self.restore)
                except OSError:
                    pass

        threading.Thread(target=listen, daemon=True).start()

    def restore(self):
        self.Show()
        self.Iconize(False)
        self.Raise()
        self.list.SetFocus()
        if self.pending_update:
            manifest, self.pending_update = self.pending_update, None
            wx.CallAfter(self.show_update_dialog, manifest)

    def hide_to_tray(self):
        self.Hide()
        if not self.cfg.get("tray_hint_shown"):
            self.cfg["tray_hint_shown"] = True
            save_config(self.cfg)
            self.toast("AudioMail continua na bandeja",
                       "Para abrir de novo, aperte Windows mais B, escolha o ícone e aperte Enter.")

    def on_iconize(self, evt):
        if evt.IsIconized() and self.setting("minimize_tray"):
            wx.CallAfter(self.hide_to_tray)
        evt.Skip()

    def on_close(self, evt):
        if evt.CanVeto() and not self.quitting and self.setting("keep_tray"):
            evt.Veto()
            self.hide_to_tray()
            return
        self.shutdown()
        evt.Skip()

    def on_end_session(self, evt):
        self.quitting = True
        self.shutdown()

    def quit(self):
        self.quitting = True
        self.Close()

    def shutdown(self):
        self.timer.Stop()
        self.reminder_timer.Stop()
        self.flush_pending_sends()
        self.flush_pending_moves()
        for acc in self.accounts:
            self.stop_watcher(acc)
            if acc.client:
                threading.Thread(target=acc.client.close, daemon=True).start()
                acc.client = None
        if self.activation_server is not None:
            try:
                self.activation_server.close()
            except OSError:
                pass
            self.activation_server = None
        try:
            self.tray.RemoveIcon()
            self.tray.Destroy()
        except Exception:
            pass

    def toast(self, title, text):
        try:
            nm = wx.adv.NotificationMessage(i18n.tr(title), i18n.tr(text), parent=self)
            try:
                nm.UseTaskBarIcon(self.tray)
            except Exception:
                pass
            nm.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
            self._toast = nm  # guarda a referencia para nao ser descartada
        except Exception:
            pass

    def show_reminders_intro(self):
        i18n.message_box(
            "O AudioMail agora tem uma agenda de lembretes local. Os lembretes ficam salvos neste computador; não há integração nem sincronização com o Google.",
            "Novo recurso: lembretes", wx.OK | wx.ICON_INFORMATION, self)

    def open_reminders(self):
        items = self.cfg.setdefault("reminders", [])
        dlg = ReminderDialog(self, items)
        dlg.ShowModal()
        self.cfg["reminders"] = items
        save_config(self.cfg)
        dlg.Destroy()

    def on_reminder_timer(self, evt):
        now = time.time()
        pending = self.cfg.setdefault("reminders", [])
        due = []
        remaining = []
        for item in pending:
            try:
                if time.mktime(time.strptime(item["when"], "%Y-%m-%dT%H:%M")) <= now:
                    due.append(item)
                else:
                    remaining.append(item)
            except (KeyError, TypeError, ValueError):
                continue
        if due:
            self.cfg["reminders"] = remaining
            save_config(self.cfg)
            for item in due:
                self.toast("Lembrete", item.get("title", "AudioMail"))
                self.announce("Lembrete: %s" % item.get("title", ""))
        self.send_due_scheduled()

    # ---- tempo real e verificacao ----
    def apply_timer(self):
        # com o tempo real ativo em todas as contas, a verificacao vira rede de seguranca
        secs = max(15, int(self.setting("check_seconds")))
        connected = [a for a in self.accounts if a.client]
        if connected and all(a.idle_active for a in connected):
            secs = max(secs, 300)
        self.timer.Start(secs * 1000)

    def start_watcher(self, acc):
        self.stop_watcher(acc)
        c = acc.client
        if not c or not self.setting("realtime"):
            return
        acc.watcher = mc.IdleWatcher(
            c.imap_host, c.imap_port, c.email, c.password,
            on_event=lambda: wx.CallAfter(self.on_idle_event, acc),
            on_status=lambda ok: wx.CallAfter(self.on_idle_status, acc, ok))
        acc.watcher.start()

    def stop_watcher(self, acc):
        if acc.watcher:
            acc.watcher.stop()
            acc.watcher = None
        acc.idle_active = False

    def on_idle_event(self, acc):
        if self:
            self.check_account(acc)

    def on_idle_status(self, acc, ok):
        if not self or acc.watcher is None:
            return
        acc.idle_active = ok
        self.apply_timer()
        if acc is self.active:
            self.SetStatusText("Tempo real ativo" if ok else
                               "Tempo real desligado, verificando de tempos em tempos")

    def on_timer(self, evt):
        for acc in self.accounts:
            self.check_account(acc)

    def check_now(self):
        for acc in self.accounts:
            self.check_account(acc, manual=True)

    def check_account(self, acc, manual=False):
        if not acc.client:
            return
        if manual:
            acc.manual = True
        if acc.checking:
            acc.recheck = True  # chegou aviso no meio de uma verificacao: repete depois
            return
        acc.checking = True
        client = acc.client

        plain_inbox = acc.current_raw == "INBOX" and not acc.search and not acc.view_filter
        limit = max(acc.limit, views.PAGE) if plain_inbox else views.PAGE

        def work():
            try:
                msgs, err = client.fetch_headers("INBOX", limit=limit), None
            except Exception as e:
                msgs, err = None, e
            wx.CallAfter(self.after_check, acc, msgs, err)

        threading.Thread(target=work, daemon=True).start()

    def after_check(self, acc, msgs, err):
        acc.checking = False
        again, acc.recheck = acc.recheck, False
        if not self:
            return
        self.process_check(acc, msgs, err)
        if again:
            self.check_account(acc)

    def note_inbox(self, acc, msgs):
        acc.inbox_unread = sum(1 for m in msgs if m["unread"])
        if msgs:
            top = max(int(m["uid"]) for m in msgs)
            acc.baseline = max(acc.baseline or 0, top)
        elif acc.baseline is None:
            acc.baseline = 0
        self.update_tray()

    def process_check(self, acc, msgs, err):
        manual, acc.manual = acc.manual, False
        suffix = (" (%s)" % acc.email) if len(self.accounts) > 1 else ""
        if err is not None or msgs is None:
            if manual:
                self.toast("AudioMail", "Não foi possível verificar agora." + suffix)
                self.announce("Não foi possível verificar agora." + suffix)
            return
        new = mc.find_new(msgs, acc.baseline) if acc.baseline is not None else []
        if acc.baseline is None:
            # a caixa de entrada inteira so na primeira vez de cada conta; depois, so as novas
            key = "inbox_imported:" + acc.email.lower()
            if not self.contacts.meta.get(key):
                self.contacts.meta[key] = True
                self.contacts_from_headers(acc, msgs, force_save=True)
        else:
            self.contacts_from_headers(acc, new)
        self.note_inbox(acc, msgs)
        quiet, rule_sounds = set(), {}
        if new:
            quiet, rule_sounds = self.apply_rules(acc, new)
        if acc is self.active and acc.current_raw == "INBOX" and not acc.search \
                and not acc.view_filter:
            self.show_messages(msgs, keep=True)
        new = [m for m in new if m["uid"] not in quiet]
        if new:
            sound = next((rule_sounds[m["uid"]] for m in new if m["uid"] in rule_sounds), None)
            self.notify_new(acc, new, sound)
        elif manual:
            text = "Nenhuma mensagem nova. %d não lidas.%s" % (acc.inbox_unread, suffix)
            self.toast("AudioMail", text)
            self.announce(text)

    def notify_new(self, acc, new, sound=None):
        title, text = mc.format_notification(new)
        if len(self.accounts) > 1:
            text = "%s (%s)" % (text, acc.email)
        if self.setting("notify"):
            self.toast(title, text)
        if sound:
            sounds.play(sound)     # som próprio de uma regra
        elif self.setting("sound"):
            sounds.play(self.sound_path())
        if self.setting("speak"):
            speech.speak(i18n.tr("%s. %s" % (title, text)))
        self.SetStatusText(title)

    # ---- atualizacoes ----
    def open_manual(self):
        """Gera o manual atualizado na pasta de dados e abre no navegador."""
        try:
            folder = os.path.join(os.path.dirname(config_path()), "manual")
            os.startfile(manual.ensure_manual(folder, APP_DIR, APP_VERSION, self.setting("ui_language")))
        except Exception as e:
            i18n.message_box("Não consegui abrir o manual: %s" % e, "Manual",
                          wx.OK | wx.ICON_ERROR, self)

    def open_ticket(self):
        def save_ticket(ticket_id, ticket_key, subject):
            records = self.cfg.setdefault("support_tickets", [])
            records.append({"id": ticket_id, "key_enc": protect_local_value(ticket_key),
                            "subject": subject, "status": "aberto"})
            save_config(self.cfg)

        dlg = TicketDialog(self, self.announce, APP_VERSION, save_ticket)
        dlg.ShowModal()
        dlg.Destroy()

    def open_my_tickets(self):
        records = self.cfg.setdefault("support_tickets", [])
        tickets = []
        for record in records:
            ticket_key = unprotect_local_value(record.get("key_enc", ""))
            if ticket_key:
                tickets.append({"id": record.get("id", ""), "key": ticket_key,
                                "subject": record.get("subject", ""),
                                "status": record.get("status", "aberto")})
        if not tickets:
            i18n.message_box("Você ainda não abriu chamados neste computador.",
                             "Meus chamados", wx.OK | wx.ICON_INFORMATION, self)
            return

        def mark_completed(ticket_id):
            for record in records:
                if record.get("id") == ticket_id:
                    record["status"] = "resolvido"
                    break
            save_config(self.cfg)

        dlg = MyTicketsDialog(self, tickets, mark_completed)
        dlg.ShowModal()
        dlg.Destroy()

    def open_legal_documents(self):
        dlg = legal.LegalDialog(self, self.setting("ui_language"))
        dlg.ShowModal()
        dlg.Destroy()

    def show_about(self):
        i18n.message_box("AudioMail versão %s\nSite: %s" % (APP_VERSION, SITE),
                      "Sobre o AudioMail", wx.OK, self)

    def apply_update_timer(self):
        self.update_timer.Stop()
        if self.setting("auto_update"):
            self.update_timer.Start(6 * 3600 * 1000)
            if not getattr(self, "_first_update_check", False):
                self._first_update_check = True
                wx.CallLater(5000, self.on_update_timer, None)

    def on_update_timer(self, evt):
        if self.setting("auto_update"):
            self.check_updates()

    def check_updates(self, manual=False):
        if self.updating:
            return
        if manual:
            self.SetStatusText("Verificando atualizações")

        def work():
            try:
                manifest, err = updater.fetch_manifest(), None
            except Exception as e:
                manifest, err = None, e
            wx.CallAfter(self.on_manifest, manifest, err, manual)

        threading.Thread(target=work, daemon=True).start()

    def on_manifest(self, manifest, err, manual):
        if not self:
            return
        if err is not None:
            if manual:
                self.announce("Não foi possível verificar atualizações. %s" % err, box=True)
            return
        version, kind = manifest["version"], manifest["type"]
        if not updater.is_newer(version):
            if manual:
                self.announce("Você já está na versão mais recente, %s." % APP_VERSION, box=True)
            return
        forced = updater.is_forced(manifest)
        if forced:  # sem pacote para este tipo de instalacao, nao da para obrigar
            try:
                updater.pick_package(manifest, bool(getattr(sys, "frozen", False)))
            except updater.UpdateError:
                forced = False
        if forced or kind == "urgente":
            # abre na hora, mesmo escondido, e ignora "pular" e "ja perguntei"
            if self.updating or self.update_dialog_open:
                return
            active = wx.GetActiveWindow()
            if active is not None and active is not self:  # tem outra janela aberta: tenta depois
                wx.CallLater(10000, self.on_manifest, manifest, None, manual)
                return
            self.Show()
            self.Iconize(False)
            self.Raise()
            self.show_update_dialog(manifest, forced)
            return
        if not manual and (version == self.setting("skipped_version")
                           or version == self.prompted_version):
            return
        self.prompted_version = version
        if not self.IsShown() and not manual:
            self.pending_update = manifest  # escondido na bandeja: avisa e espera o usuario abrir
            self.toast("Atualização disponível",
                       "AudioMail versão %s. Abra o programa para atualizar." % version)
            if kind != "novidade" and self.setting("speak"):
                speech.speak(i18n.tr("Atualização do AudioMail disponível, versão %s." % version))
            return
        self.show_update_dialog(manifest)

    def show_update_dialog(self, manifest, forced=False):
        if self.setting("speak"):
            if forced:
                said = "Atualização obrigatória do AudioMail, versão %s." % manifest["version"]
            elif manifest["type"] == "urgente":
                said = "Atualização urgente do AudioMail, versão %s." % manifest["version"]
            else:
                said = "Atualização disponível, versão %s." % manifest["version"]
            speech.speak(i18n.tr(said), interrupt=True)
        dlg = UpdateDialog(self, APP_VERSION, manifest, forced)
        self.update_dialog_open = True
        try:
            dlg.ShowModal()
            result = dlg.result
        finally:
            self.update_dialog_open = False
            dlg.Destroy()
        if result == "update":
            self.install_update(manifest, forced)
        elif result == "skip":
            self.cfg["skipped_version"] = manifest["version"]
            save_config(self.cfg)
            self.announce("Versão %s ignorada." % manifest["version"])
        elif result == "quit" or forced:
            self.quit()

    def install_update(self, manifest, forced=False):
        frozen = bool(getattr(sys, "frozen", False))
        try:
            url, digest = updater.pick_package(manifest, frozen)
        except updater.UpdateError as e:
            i18n.message_box(str(e), "Atualização", wx.OK | wx.ICON_ERROR, self)
            if forced:
                wx.CallAfter(self.show_update_dialog, manifest, True)
            return
        self.updating = True
        self.announce("Baixando a atualização. Aguarde.")

        def work():
            zpath = os.path.join(tempfile.mkdtemp(prefix="audiomail_up_"), "update.zip")
            updater.download(url, zpath, digest)
            if frozen:
                return updater.prepare_exe_update(zpath, sys.executable, os.getpid())
            updater.install_source(zpath, APP_DIR)
            return None

        def done(helper):
            self.updating = False
            self.announce("Atualização instalada. O AudioMail vai reiniciar.")
            self.restart_after_update(helper)

        def fail(err):
            self.updating = False
            i18n.message_box("A atualização não foi instalada.\n\n%s" % err, "Atualização",
                          wx.OK | wx.ICON_ERROR, self)
            if forced:  # obrigatoria: volta a perguntar ate conseguir (ou o usuario fechar o programa)
                wx.CallAfter(self.show_update_dialog, manifest, True)

        self.run(work, done, "Baixando atualização", fail)

    def restart_after_update(self, helper):
        try:
            if helper:
                updater.launch_detached(helper)
            else:
                updater.relaunch_source(os.path.join(APP_DIR, "audiomail.py"))
        except Exception as e:
            i18n.message_box("A atualização foi instalada, mas não consegui reiniciar sozinho. "
                          "Feche e abra o AudioMail de novo.\n\n%s" % e, "Atualização",
                          wx.OK | wx.ICON_INFORMATION, self)
            return
        self.quit()

    # ---- trabalho em segundo plano ----
    def run(self, work, done, busy="Carregando", on_error=None):
        self.SetStatusText(busy)

        def target():
            try:
                result, err = work(), None
            except Exception as e:
                result, err = None, e
            wx.CallAfter(self.finish, done, result, err, on_error)

        threading.Thread(target=target, daemon=True).start()

    def finish(self, done, result, err, on_error):
        if not self:
            return
        if err is not None:
            self.SetStatusText("Erro")
            if on_error:
                on_error(err)
            else:
                i18n.message_box(str(err), "Erro", wx.OK | wx.ICON_ERROR, self)
            return
        done(result)

    # ---- contas ----
    def start(self):
        auto = []
        for a in self.cfg["accounts"]:
            if a.get("remember"):
                pw = recall_password(a)
                if pw:
                    auto.append((a, pw))
        if auto:
            if not self.setting("start_hidden"):
                self.Show()
            active = self.cfg.get("active_email")
            auto.sort(key=lambda t: t[0]["email"] != active)  # a ultima conta ativa primeiro
            for a, pw in auto:
                self.connect({"email": a["email"], "password": pw, "remember": True,
                              "provider": a.get("provider") or "gmail", "server": a.get("server")})
        else:
            self.Show()
            self.ask_login()

    def ask_login(self, email="", blank=False):
        if self.login_open:
            return
        self.login_open = True
        if not blank and not email:
            email = self.cfg.get("last_email") or self.cfg.get("active_email", "")
        saved = find_account(self.cfg, email) if email else None
        dlg = LoginDialog(self, email=email,
                          remember=saved.get("remember", True) if saved else True,
                          provider=saved.get("provider") if saved else None,
                          server=saved.get("server") if saved else None)
        ok = dlg.ShowModal() == wx.ID_OK
        values = dlg.get_values() if ok else None
        dlg.Destroy()
        self.login_open = False
        if ok:
            self.cfg["last_email"] = values["email"]  # guarda ja, mesmo que a entrada falhe
            save_config(self.cfg)
            self.connect(values, activate=True)
        elif not self.accounts:
            self.quit()

    def connect(self, v, activate=False):
        server = providers.server_for({"provider": v.get("provider") or "gmail",
                                       "server": v.get("server")})
        client = mc.MailClient(v["email"], v["password"], server["imap_host"], server["imap_port"],
                               server["smtp_host"], server["smtp_port"], server["security"])

        def work():
            client.connect()
            return client.list_folders()

        def done(folders):
            acc = next((a for a in self.accounts if a.email.lower() == v["email"].lower()), None)
            if acc is None:
                acc = Account(v["email"])
                self.accounts.append(acc)
            self.stop_watcher(acc)
            if acc.client:
                acc.client.close()
            acc.client, acc.folders = client, organize.with_virtual(folders, client.gmail)
            acc.baseline, acc.messages, acc.view = None, [], []
            acc.current_raw, acc.search, acc.view_filter = "INBOX", "", None
            acc.limit, acc.counts, acc.snippets, acc.counts_at = views.PAGE, {}, {}, 0.0
            entry = find_account(self.cfg, v["email"])
            if entry is None:
                entry = {"email": v["email"]}
                self.cfg["accounts"].append(entry)
            entry["remember"] = v["remember"]
            entry["provider"] = v.get("provider") or "gmail"
            if v.get("server"):
                entry["server"] = v["server"]
            else:
                entry.pop("server", None)
            if v["remember"]:
                if not remember_password(entry, v["password"]):
                    entry["remember"] = False
            else:
                forget_password(entry)
            save_config(self.cfg)
            self.update_account_ui()
            if self.active is None or activate or acc is self.active:
                self.activate(acc)
            self.start_watcher(acc)
            self.apply_timer()
            self.import_sent_contacts(acc)
            wx.CallLater(3000, self.send_due_scheduled)

        def fail(err):
            self.Show()
            i18n.message_box("Conta %s\n\n%s" % (v["email"], err), "Não foi possível entrar",
                          wx.OK | wx.ICON_ERROR, self)
            if not self.accounts:
                self.ask_login(email=v["email"])

        self.run(work, done, "Conectando " + v["email"], fail)

    def update_account_ui(self):
        many = len(self.accounts) > 1
        self.account_choice.Set([a.email for a in self.accounts])
        if self.active in self.accounts:
            self.account_choice.SetSelection(self.accounts.index(self.active))
        self.lbl_account.Show(many)
        self.account_choice.Show(many)
        self.panel.Layout()

    def activate(self, acc):
        self.active = acc
        self.update_account_ui()
        self.cfg["active_email"] = acc.email
        save_config(self.cfg)
        self.SetTitle("AudioMail " + acc.email)
        self.fill_folders(acc)
        self.search_box.SetValue(acc.search)
        self.refresh()

    def on_account_choice(self, evt):
        i = self.account_choice.GetSelection()
        if i != wx.NOT_FOUND and self.accounts[i] is not self.active:
            self.activate(self.accounts[i])

    def remove_account(self):
        acc = self.active
        if not acc:
            return
        ask = i18n.message_box("Remover a conta %s do AudioMail? As mensagens continuam no servidor do e-mail."
                            % acc.email, "Confirmar", wx.YES_NO | wx.ICON_QUESTION, self)
        if ask != wx.YES:
            return
        self.stop_watcher(acc)
        if acc.client:
            threading.Thread(target=acc.client.close, daemon=True).start()
        entry = find_account(self.cfg, acc.email)
        if entry:
            forget_password(entry)
            self.cfg["accounts"].remove(entry)
        save_config(self.cfg)
        self.accounts.remove(acc)
        self.active = None
        self.update_tray()
        if self.accounts:
            self.activate(self.accounts[0])
            self.announce("Conta removida.")
        else:
            self.list.DeleteAllItems()
            self.choice.Clear()
            self.update_account_ui()
            self.ask_login(blank=True)

    # ---- pastas, busca e lista ----
    def fill_folders(self, acc):
        self.choice.Clear()
        selected = 0
        for i, f in enumerate(acc.folders):
            self.choice.Append(views.folder_label(f, acc.counts))
            if acc.view_filter:
                if f.get("filter") == acc.view_filter:
                    selected = i
            elif f["raw"] == acc.current_raw or (
                    acc.current_raw == "INBOX" and f["raw"].upper() == "INBOX"):
                selected = i
        if acc.folders:
            self.choice.SetSelection(selected)
            if acc is self.active:
                self.choose_folder(acc.folders[selected])
            else:
                acc.view_filter = acc.folders[selected].get("filter")
                acc.current_raw = "INBOX" if acc.view_filter else acc.folders[selected]["raw"]

    def folder_has(self, flag):
        for f in self.folders:
            if f["raw"] == self.current_raw:
                return flag in f["flags"]
        return False

    def on_folder(self, evt):
        """Passar pelas pastas com as setas não carrega cada uma: a lista é
        esvaziada na hora (nada de agir na pasta errada) e só carrega quando
        você para numa pasta por um instante."""
        i = self.choice.GetSelection()
        if i == wx.NOT_FOUND or not self.active:
            return
        self.choose_folder(self.folders[i])
        self.messages, self.view = [], []
        self.list.DeleteAllItems()
        self.SetStatusText("Carregando mensagens")
        if self.folder_timer is not None and self.folder_timer.IsRunning():
            self.folder_timer.Stop()
        self.folder_timer = wx.CallLater(400, self.refresh)

    def do_search(self):
        if self.active:
            self.active.search = self.search_box.GetValue().strip()
            self.active.limit = views.PAGE
            self.refresh()

    def on_search_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_ESCAPE and self.active:
            self.search_box.SetValue("")
            if self.active.search:
                self.active.search = ""
                self.active.limit = views.PAGE
                self.refresh()
            else:
                self.list.SetFocus()
            return
        evt.Skip()

    def refresh(self, after=None, failed=None):
        acc = self.active
        if not acc or not acc.client:
            return
        raw, query, client, view_filter = acc.current_raw, acc.search, acc.client, acc.view_filter
        limit = acc.limit

        def work():
            if query or view_filter:
                return client.search_query(raw, query, limit, view_filter)
            return client.fetch_headers(raw, limit=limit, with_total=True)

        def done(result):
            if acc is not self.active or raw != acc.current_raw or query != acc.search \
                    or view_filter != acc.view_filter:
                return
            msgs, acc.total = result
            self.show_messages(msgs, keep=after is not None)
            if after:
                after()

        def error(err):
            if failed:
                failed()
            i18n.message_box(str(err), "Erro", wx.OK | wx.ICON_ERROR, self)

        self.run(work, done, "Buscando" if query else "Carregando mensagens", error)

    def show_messages(self, msgs, keep=False):
        acc = self.active
        hidden = organize.hidden_uids(self.pending_moves, acc, acc.current_raw)
        if hidden:
            msgs = [m for m in msgs if m["uid"] not in hidden]
        selected_uid = None
        if keep:
            _, row = self.selected()
            selected_uid = row["uids"][0] if row else None
            if [(m["uid"], m["unread"], m.get("flagged")) for m in msgs] == \
                    [(m["uid"], m["unread"], m.get("flagged")) for m in self.messages]:
                return
        self.messages = msgs
        if acc.current_raw == "INBOX" and not acc.search and not acc.view_filter:
            self.note_inbox(acc, msgs)
        self.render(selected_uid, focus=not keep)
        if acc.search:
            self.SetStatusText("%d resultados para %s" % (max(len(msgs), acc.total), acc.search))
        else:
            unread = sum(1 for m in msgs if m["unread"])
            if acc.total > len(msgs):
                self.SetStatusText("%d de %d mensagens, %d não lidas" % (len(msgs), acc.total, unread))
            else:
                self.SetStatusText("%d mensagens, %d não lidas" % (len(msgs), unread))
        self.refresh_counts(acc)
        self.load_snippets(acc)

    def render(self, selected_uid=None, focus=False):
        rows = mc.build_rows(self.messages, bool(self.setting("group_threads")))
        self.view = rows
        self.list.DeleteAllItems()
        for i, r in enumerate(rows):
            self.list.InsertItem(i, mc.state_text(r))
            self.list.SetItem(i, 1, r["from"])
            self.list.SetItem(i, 2, r["subject"])
            self.list.SetItem(i, 3, self.snippet_for(self.active, self.active.current_raw, r))
            self.list.SetItem(i, 4, r["date"])
        if rows:
            index = 0
            if selected_uid:
                for i, r in enumerate(rows):
                    if selected_uid in r["uids"]:
                        index = i
                        break
            self.select(index)
        if focus:
            self.list.SetFocus()

    def on_toggle_group(self, evt):
        self.cfg["group_threads"] = self.group_item.IsChecked()
        save_config(self.cfg)
        _, row = self.selected()
        self.render(row["uids"][0] if row else None)
        self.announce("Agrupando por conversa." if self.group_item.IsChecked()
                      else "Mostrando cada mensagem separada.")

    def select(self, index):
        self.list.Select(index)
        self.list.Focus(index)
        self.list.EnsureVisible(index)

    def selected(self):
        """A linha com o foco (com várias selecionadas, é a que o leitor de tela leu por último)."""
        i = self.list.GetFocusedItem()
        if i == -1 or not self.list.IsSelected(i):
            i = self.list.GetFirstSelected()
        if i == -1 or i >= len(self.view):
            return None, None
        return i, self.view[i]

    def set_unread(self, uids, unread):
        acc = self.active
        wanted = set(uids)
        for m in self.messages:
            if m["uid"] in wanted:
                m["unread"] = unread
        for i, r in enumerate(self.view):
            if wanted & set(r["uids"]):
                r["unread"] = any(m["unread"] for m in self.messages if m["uid"] in r["uids"])
                self.list.SetItem(i, 0, mc.state_text(r))
        if acc.current_raw == "INBOX" and not acc.search and not acc.view_filter:
            acc.inbox_unread = sum(1 for m in self.messages if m["unread"])
            self.update_tray()

    # ---- ler ----
    def open_selected(self, auto_translate=False):
        i, row = self.selected()
        if row is None or not self.active:
            return
        acc = self.active
        client, raw, uids = acc.client, acc.current_raw, list(row["uids"])
        if self.folder_has("\\drafts") and len(uids) == 1:
            self.edit_draft(client, raw, uids[0])
            return
        oldest_first = sorted(uids, key=int)

        def work():
            return [client.fetch_message(raw, u) for u in oldest_first]

        def done(fulls):
            if acc is self.active:
                self.set_unread(uids, False)
            newest = fulls[-1]
            attachments = [a for f in fulls for a in f["attachments"]]
            bodies, links = mt.merge_links([(f["body"], f.get("links", [])) for f in fulls])
            sections = [(mc.message_header(f), body) for f, body in zip(fulls, bodies)]
            self.contacts_from_message(newest)
            prefix = "" if len(fulls) == 1 else "Conversa com %d mensagens, assunto %s" % (
                len(fulls), mc.normalize_subject(newest["subject"]) or newest["subject"])
            text = mc.render_text(prefix, sections)
            self.SetStatusText("Mensagem aberta")
            dlg = ReadDialog(self, newest["subject"], text, attachments, self.announce,
                             sections=sections, prefix=prefix, translation=self.translation,
                             auto_translate=auto_translate, ai_summary=self.ai_summary,
                             links=links, unsubscribe=self.unsubscribe_action(acc, newest),
                             organize=True, flagged=bool(row.get("flagged")))
            dlg.ShowModal()
            result, mailto = dlg.result, dlg.link_to_open
            dlg.Destroy()
            if result == "mailto" and mailto:
                address, subject, body = mt.mailto_parts(mailto)
                self.compose(to=address, subject=subject, body=body)
            elif result == "forward":
                self.forward_full(newest)
            elif result == "archive":
                self.archive_selected(rows=[row])
            elif result == "delete":
                self.delete_selected(rows=[row])
            elif result == "star":
                self.toggle_star_selected(rows=[row])
            elif result:
                self.reply_to(newest, result == "replyall")
            self.list.SetFocus()

        self.run(work, done, "Abrindo mensagem")

    def unsubscribe_action(self, acc, full):
        """O que o botão Cancelar inscrição faz nesta mensagem, ou None se não der."""
        options = mt.unsubscribe_options(full.get("list_unsubscribe"),
                                         full.get("list_unsubscribe_post"), full.get("links", []))
        if not options:
            return None
        sender = mc.short_sender(full["from"])

        def open_page(parent):
            url = options["https"] or options["link"]
            if not url:
                return False
            try:
                webbrowser.open(url)
            except Exception:
                return False
            self.announce("A página de cancelamento foi aberta no navegador. Se ela pedir, "
                          "confirme por lá.", box=True)
            return True

        def run(parent):
            ask = i18n.message_box("Cancelar a inscrição e parar de receber os e-mails de %s?" % sender,
                                   "Cancelar inscrição", wx.YES_NO | wx.ICON_QUESTION, parent)
            if ask != wx.YES:
                return
            if options["one_click"]:
                def done(ok):
                    if ok:
                        self.announce("Pronto. O pedido de cancelamento foi enviado para %s." % sender,
                                      box=True)
                    elif not open_page(parent):
                        self.announce("O site não aceitou o cancelamento automático.", box=True)

                self.run(lambda: mt.one_click_unsubscribe(options["https"]), done,
                         "Cancelando a inscrição", lambda err: done(False))
            elif options["mailto"] and acc.client:
                address, subject, body = mt.mailto_parts(options["mailto"], "unsubscribe")
                self.run(lambda: acc.client.send(address, "", "", subject, body),
                         lambda _: self.announce("Pronto. O e-mail de cancelamento foi enviado.",
                                                 box=True),
                         "Cancelando a inscrição")
            elif not open_page(parent):
                self.announce("Não foi possível cancelar a inscrição.", box=True)

        return run

    def edit_draft(self, client, raw, uid):
        def work():
            full = client.fetch_message(raw, uid)
            paths = []
            if full["attachments"]:
                folder = tempfile.mkdtemp(prefix="audiomail_")
                for att in full["attachments"]:
                    path = unique_path(folder, att["name"])
                    mc.save_attachment(att, path)
                    paths.append(path)
            return full, paths

        def done(result):
            full, paths = result
            self.compose(to=full["to"], cc=full["cc"], bcc=full["bcc"],
                         subject=full["subject"], body=full["body"],
                                                  attachments=paths, draft=(raw, uid), add_signature=False)

        self.run(work, done, "Abrindo rascunho")

    # ---- escrever ----
    def reply_selected(self, reply_all):
        i, row = self.selected()
        if row is None or not self.active:
            return
        client, raw, uid = self.active.client, self.active.current_raw, row["uids"][0]
        self.run(lambda: client.fetch_message(raw, uid),
                 lambda full: self.reply_to(full, reply_all), "Preparando resposta")

    def reply_to(self, full, reply_all):
        if self.client:
            self.compose(**mc.build_reply(full, self.client.email, reply_all))

    def save_quick_replies(self, replies):
        self.cfg["quick_replies"] = [dict(r) for r in replies]
        save_config(self.cfg)

    def compose(self, to="", cc="", bcc="", subject="", body="", in_reply_to=None,
                references=None, attachments=None, draft=None, add_signature=True):
        acc = self.active
        if not acc or not acc.client:
            return
        signature = self.setting("signature").strip()
        if add_signature and signature:
            body = "\n\n-- \n" + signature + body
        dlg = ComposeDialog(self, acc.client, self.announce, to=to, cc=cc, bcc=bcc,
                            subject=subject, body=body, in_reply_to=in_reply_to,
                            references=references, attachments=attachments, draft=draft,
                            translation=self.translation, contacts=self.contacts,
                            replies=self.setting("quick_replies"),
                            save_replies=self.save_quick_replies,
                            show_cc=self.setting("compose_show_cc"),
                            undo_seconds=int(self.setting("undo_send_seconds") or 0))
        dlg.ShowModal()
        result, outgoing, when, cc_shown = dlg.result, dlg.outgoing, dlg.when, dlg.cc_shown
        draft, typed = dlg.draft, dlg.fields()
        dlg.Destroy()
        if cc_shown != bool(self.setting("compose_show_cc")):
            self.cfg["compose_show_cc"] = cc_shown
            save_config(self.cfg)
        if result in ("sent", "queued", "scheduled"):
            self.contacts_from_outgoing(outbox.from_fields(outgoing or typed))
        if result == "queued":
            self.queue_send(acc, outbox.from_fields(outgoing), draft)
        elif result == "scheduled":
            self.schedule_send(acc, outbox.from_fields(outgoing), draft, when)
        if result == "sent":
            self.announce("Mensagem enviada.", box=True)
        if result and acc is self.active and (self.folder_has("\\drafts")
                                              or self.folder_has("\\sent")):
            self.refresh()
        self.list.SetFocus()

    # ---- contatos ----
    def contacts_from_headers(self, acc, msgs, force_save=False):
        changed = [self.contacts.add_header(m.get("from_raw", ""), 1, skip=[acc.email]) for m in msgs]
        if any(changed) or force_save:
            self.contacts.save()

    def contacts_from_message(self, full):
        me = self.client.email if self.client else ""
        changed = False
        for name in ("from", "to", "cc"):
            changed = self.contacts.add_header(full.get(name, ""), 1, skip=[me]) or changed
        if changed:
            self.contacts.save()

    def contacts_from_outgoing(self, fields):
        changed = False
        for name in ("to", "cc", "bcc"):
            changed = self.contacts.add_header((fields.get(name) or "").replace(";", ","), 3) or changed
        if changed:
            self.contacts.save()

    def import_sent_contacts(self, acc):
        """Na primeira vez de cada conta, aprende os contatos das mensagens enviadas."""
        key = "sent_imported:" + acc.email.lower()
        if self.contacts.meta.get(key) or not acc.client:
            return
        client = acc.client

        def work():
            try:
                values = client.recent_recipients()
            except Exception:
                values = None
            wx.CallAfter(done, values)

        def done(values):
            if not self or values is None:
                return
            for value in values:
                self.contacts.add_header(value, 2, skip=[acc.email])
            self.contacts.meta[key] = True
            self.contacts.save()

        threading.Thread(target=work, daemon=True).start()

    # ---- desfazer envio ----
    def queue_send(self, acc, fields, draft):
        seconds = int(self.setting("undo_send_seconds") or 0)
        item = {"acc": acc, "fields": fields, "draft": draft}
        item["timer"] = wx.CallLater(seconds * 1000, self.send_pending, item)
        self.pending_sends.append(item)
        self.announce("Enviando em %d segundos. Para desfazer, Ctrl+Shift+Z." % seconds)

    def undo_send(self):
        if not self.pending_sends:
            self.announce("Não há envio para desfazer.")
            return
        item = self.pending_sends.pop()
        item["timer"].Stop()
        self.announce("Envio desfeito.")
        self.reopen(item)

    def reopen(self, item):
        f = item["fields"]
        if item["acc"] is not self.active and item["acc"] in self.accounts:
            self.activate(item["acc"])
        self.compose(to=f["to"], cc=f["cc"], bcc=f["bcc"], subject=f["subject"], body=f["body"],
                     in_reply_to=f["in_reply_to"], references=f["references"],
                     attachments=f["attachments"], draft=item["draft"], add_signature=False)

    def deliver(self, client, fields, draft):
        client.send(*outbox.message_args(fields))
        if draft:
            try:
                client.delete_permanent(*draft)
            except Exception:
                pass

    def send_pending(self, item):
        if item not in self.pending_sends:
            return
        self.pending_sends.remove(item)
        acc = item["acc"]
        if not acc.client:
            self.send_failed(item, mc.MailError("A conta está desconectada."))
            return

        def done(_):
            self.announce("Mensagem enviada.")
            if acc is self.active and self.folder_has("\\sent"):
                self.refresh()

        self.run(lambda: self.deliver(acc.client, item["fields"], item["draft"]), done,
                 "Enviando mensagem", lambda err: self.send_failed(item, err))

    def send_failed(self, item, err):
        ask = i18n.message_box("A mensagem não foi enviada.\n\n%s\n\nAbrir a mensagem de novo para "
                               "tentar outra vez?" % err, "Erro ao enviar",
                               wx.YES_NO | wx.ICON_ERROR, self)
        if ask == wx.YES:
            self.reopen(item)

    def flush_pending_sends(self):
        """Ao fechar o AudioMail, o que estava esperando o tempo de desfazer sai na hora."""
        for item in list(self.pending_sends):
            item["timer"].Stop()
            self.pending_sends.remove(item)
            if item["acc"].client:
                try:
                    self.deliver(item["acc"].client, item["fields"], item["draft"])
                except Exception:
                    pass

    # ---- envio agendado ----
    def schedule_send(self, acc, fields, draft, when):
        try:
            self.scheduled.add(acc.email, fields, time.mktime(when.timetuple()), draft)
        except OSError as e:
            i18n.message_box("Não foi possível agendar: %s" % e, "Erro", wx.OK | wx.ICON_ERROR, self)
            return
        self.announce("Mensagem agendada para %s." % when.strftime("%d/%m/%Y %H:%M"), box=True)

    def send_due_scheduled(self):
        if not self:
            return
        connected = {a.email.lower(): a for a in self.accounts if a.client}
        for item in self.scheduled.due(connected):
            if item["id"] in self.sending_scheduled:
                continue
            self.sending_scheduled.add(item["id"])
            self.send_scheduled(connected[item["account"].lower()], item)

    def send_scheduled(self, acc, item):
        client = acc.client

        def work():
            try:
                self.deliver(client, item, item.get("draft"))
                err = None
            except Exception as e:
                err = e
            wx.CallAfter(done, err)

        def done(err):
            self.sending_scheduled.discard(item["id"])
            if not self:
                return
            to = item.get("to") or item.get("cc") or item.get("bcc") or ""
            if err is None:
                self.scheduled.remove(item["id"])
                self.toast("Mensagem agendada enviada", "Para %s: %s" % (to, item.get("subject") or ""))
                self.announce("Mensagem agendada enviada para %s." % to)
            else:
                first = not item.get("error")
                self.scheduled.failed(item["id"], err)
                if first:
                    self.toast("Mensagem agendada não saiu", "Nova tentativa em 5 minutos. %s" % err)

        threading.Thread(target=work, daemon=True).start()

    def open_scheduled(self):
        many = len({it["account"] for it in self.scheduled.items}) > 1
        items = [dict(it, show_account=many) for it in self.scheduled.items]
        dlg = cx.ScheduledDialog(self, items)
        action = dlg.action if dlg.ShowModal() == wx.ID_OK else None
        dlg.Destroy()
        if not action:
            return
        what, chosen = action
        item = self.scheduled.get(chosen["id"])
        if item is None or item["id"] in self.sending_scheduled:
            return
        acc = next((a for a in self.accounts if a.email.lower() == item["account"].lower()), None)
        if acc is None or not acc.client:
            i18n.message_box("A conta %s não está conectada." % item["account"], "Aviso",
                             wx.OK | wx.ICON_WARNING, self)
            return
        if what == "send":
            self.sending_scheduled.add(item["id"])
            self.send_scheduled(acc, item)
        elif what == "edit":
            self.scheduled.remove(item["id"], keep_files=True)
            if acc is not self.active:
                self.activate(acc)
            self.compose(to=item["to"], cc=item["cc"], bcc=item["bcc"], subject=item["subject"],
                         body=item["body"], in_reply_to=item["in_reply_to"],
                         references=item["references"], attachments=item["attachments"],
                         draft=item.get("draft"), add_signature=False)
        elif what == "cancel":
            def keep_draft():
                acc.client.save_draft(*outbox.message_args(item), old=item.get("draft"))

            def done(_):
                self.scheduled.remove(item["id"])
                self.announce("Agendamento cancelado. A mensagem está nos rascunhos.")

            self.run(keep_draft, done, "Cancelando o agendamento")

    # ---- marcar (apagar, mover e estrela ficam em organize.py) ----
    def mark_selected(self, seen):
        rows = [r for _, r in self.selected_rows()]
        if not rows or not self.active:
            return
        acc = self.active
        client, raw, uids = acc.client, acc.current_raw, self._uids(rows)

        def work():
            for u in uids:
                client.set_seen(raw, u, seen)

        def done(_):
            self.set_unread(uids, not seen)
            self.refresh_counts(acc, force=True)
            if len(rows) > 1:
                self.announce(i18n.tr("%d marcadas como lidas." if seen else "%d marcadas como não lidas.")
                              % len(rows))
            else:
                self.announce("Marcada como lida." if seen else "Marcada como não lida.")

        self.run(work, done, "Atualizando")


def activation_port():
    identity = "AudioMail-" + wx.GetUserId()
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return 49152 + int.from_bytes(digest[:4], "big") % 16000


def activate_existing_instance():
    """Asks the running copy to show its main window."""
    address = ("127.0.0.1", activation_port())
    for _ in range(12):
        try:
            with socket.create_connection(address, timeout=0.4) as connection:
                connection.sendall(b"SHOW")
                return connection.recv(2) == b"OK"
        except OSError:
            time.sleep(0.15)
    return False


def acquire_instance_lock():
    """Garante uma unica copia aberta. Apos uma atualizacao, espera a copia antiga fechar."""
    name = "AudioMail-" + wx.GetUserId()
    attempts = 60 if os.environ.get("AUDIOMAIL_RESTART") else 1
    for _ in range(attempts):
        checker = wx.SingleInstanceChecker(name)
        if not checker.IsAnotherRunning():
            return checker
        time.sleep(0.25)
    return None


def choose_interface_language(cfg, first_run=False):
    """Solicita idioma na primeira execução e permite confirmá-lo antes de abrir a janela."""
    if cfg.get("ui_language"):
        i18n.set_language(cfg["ui_language"])
        return
    dlg = wx.Dialog(None, title="AudioMail — idioma / language / idioma")
    panel = wx.Panel(dlg)
    sizer = wx.BoxSizer(wx.VERTICAL)
    prompt = wx.StaticText(panel, label="Escolha o idioma para usar no AudioMail.\n"
                           "Choose the language to use in AudioMail.\n"
                           "Elige el idioma que se usará en AudioMail.")
    choice = wx.Choice(panel, choices=[label for _, label in i18n.LANGUAGES])
    choice.SetSelection(0)
    sizer.Add(prompt, 0, wx.ALL, 14)
    sizer.Add(choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
    panel.SetSizer(sizer)
    outer = wx.BoxSizer(wx.VERTICAL)
    outer.Add(panel, 1, wx.EXPAND)
    buttons = dlg.CreateStdDialogButtonSizer(wx.OK)
    dlg.FindWindowById(wx.ID_OK).SetLabel("Continuar / Continue / Continuar")
    outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dlg.SetSizerAndFit(outer)
    dlg.Centre()
    dlg.ShowModal()
    cfg["ui_language"] = i18n.LANGUAGES[max(0, choice.GetSelection())][0]
    save_config(cfg)
    i18n.set_language(cfg["ui_language"])
    dlg.Destroy()


if __name__ == "__main__":
    app = wx.App(False)
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        if not activate_existing_instance():
            i18n.message_box("O AudioMail já está aberto, mas não consegui trazer a janela para frente.",
                             "AudioMail", wx.OK | wx.ICON_INFORMATION)
    else:
        config = load_config()
        choose_interface_language(config)
        if legal.require_acceptance(config):
            if legal.show_acceptance(config):
                if not save_config(config):
                    i18n.message_box(
                        "Não foi possível salvar seu aceite. O AudioMail será fechado; verifique se a pasta de dados permite gravação e tente novamente.",
                        "Aceite não salvo", wx.OK | wx.ICON_ERROR)
                else:
                    frame = MainFrame()
                    app.MainLoop()
            # Recusar encerra sem abrir a caixa de entrada.
        else:
            frame = MainFrame()
            app.MainLoop()
