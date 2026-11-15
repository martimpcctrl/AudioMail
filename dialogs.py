"""Janelas do AudioMail: entrada, configuracoes, leitura e escrita de mensagens."""
import os
import tempfile
import threading
import webbrowser

import wx

import mail_core as mc
import message_text as mt
import sounds
import translator
import i18n
import support
import compose_extras as cx
import providers
import contacts as ct
from common import default_sound_path, get_ai_api_key, pick_sound_file, set_name


# ---------- entrada ----------

APP_PASSWORD_URL = "https://myaccount.google.com/apppasswords"

class LoginDialog(wx.Dialog):
    """Entrada: provedor, e-mail e senha (de app). "Outro" pede os servidores."""

    def __init__(self, parent, email="", remember=True, title="Adicionar conta de e-mail",
                 provider=None, server=None):
        super().__init__(parent, title=i18n.tr(title))
        self.SetMinSize((460, -1))
        self.provider_keys = providers.KEYS
        self.typed_provider = bool(provider)
        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        def row(label, make, target=grid, parent_win=self):
            label = i18n.tr(label)
            lbl = wx.StaticText(parent_win, label=label)  # rotulo criado antes do campo
            ctrl = set_name(make(parent_win), label)
            target.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            target.Add(ctrl, 1, wx.EXPAND)
            return lbl, ctrl

        _, self.provider = row("Provedor", lambda p: wx.Choice(
            p, choices=[i18n.tr(providers.get(k)["name"]) for k in self.provider_keys]))
        _, self.email = row("E-mail", lambda p: wx.TextCtrl(p, value=email))
        self.password_label, self.password = row("Senha de app",
                                                 lambda p: wx.TextCtrl(p, style=wx.TE_PASSWORD))

        # servidores, so para "Outro"
        self.server_panel = wx.Panel(self)
        sgrid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        sgrid.AddGrowableCol(1, 1)
        server = server or {}
        _, self.imap_host = row("Servidor IMAP (receber)", lambda p: wx.TextCtrl(
            p, value=server.get("imap_host", "")), sgrid, self.server_panel)
        _, self.imap_port = row("Porta IMAP", lambda p: wx.SpinCtrl(
            p, min=1, max=65535, initial=int(server.get("imap_port", 993) or 993)), sgrid, self.server_panel)
        _, self.smtp_host = row("Servidor SMTP (enviar)", lambda p: wx.TextCtrl(
            p, value=server.get("smtp_host", "")), sgrid, self.server_panel)
        _, self.smtp_port = row("Porta SMTP", lambda p: wx.SpinCtrl(
            p, min=1, max=65535, initial=int(server.get("smtp_port", 587) or 587)), sgrid, self.server_panel)
        self.security_codes = list(providers.SECURITY)
        _, self.security = row("Segurança do envio", lambda p: wx.Choice(
            p, choices=[i18n.tr("SSL (porta 465)"), i18n.tr("STARTTLS (porta 587)")]),
            sgrid, self.server_panel)
        self.security.SetSelection(self.security_codes.index(server.get("security", "starttls"))
                                   if server.get("security") in self.security_codes else 1)
        self.server_panel.SetSizer(sgrid)

        self.remember = wx.CheckBox(self, label=i18n.tr("Lembrar a senha neste computador"))
        self.remember.SetValue(bool(remember))
        self.site_btn = wx.Button(self, label=i18n.tr("Criar senha de app (abre o site do Google)"))
        self.site_btn.Bind(wx.EVT_BUTTON, self.on_open_site)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel(i18n.tr("Entrar"))
        self.FindWindowById(wx.ID_CANCEL).SetLabel(i18n.tr("Cancelar"))
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        sizer.Add(self.server_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        sizer.Add(self.remember, 0, wx.LEFT | wx.RIGHT, 12)
        sizer.Add(self.site_btn, 0, wx.ALL, 12)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.SetSizer(sizer)

        key = provider or providers.guess(email) or "gmail"
        self.provider.SetSelection(self.provider_keys.index(key) if key in self.provider_keys else 0)
        self.provider.Bind(wx.EVT_CHOICE, lambda e: self.on_provider(manual=True))
        self.email.Bind(wx.EVT_TEXT, self.on_email_text)
        self.on_provider()
        self.CentreOnParent()
        (self.password if email else self.provider).SetFocus()

    def current(self):
        return providers.get(self.provider_keys[self.provider.GetSelection()])

    def on_email_text(self, evt):
        evt.Skip()
        if self.typed_provider:
            return
        key = providers.guess(self.email.GetValue())
        if key and self.provider_keys[self.provider.GetSelection()] != key:
            self.provider.SetSelection(self.provider_keys.index(key))
            self.on_provider()

    def on_provider(self, manual=False):
        if manual:
            self.typed_provider = True
        p = self.current()
        label = i18n.tr("Senha de app" if p["app_password"] else "Senha")
        self.password_label.SetLabel(label)
        set_name(self.password, label)
        self.server_panel.Show(p["key"] == "other")
        if p["key"] == "gmail":
            self.site_btn.SetLabel(i18n.tr("Criar senha de app (abre o site do Google)"))
        else:
            self.site_btn.SetLabel(i18n.tr("Criar senha de app (abre o site do %s)") % p["name"])
        self.site_btn.Show(bool(p["site"]))
        self.Fit()
        self.Layout()

    def on_open_site(self, evt=None):
        """Abre no navegador a pagina onde o provedor cria as senhas de app."""
        url = self.current()["site"] or APP_PASSWORD_URL
        try:
            opened = webbrowser.open(url)
        except Exception:
            opened = False
        if not opened:
            i18n.message_box("Não consegui abrir o navegador. Abra este endereço você mesmo:\n\n%s"
                          % url, "Senha de app", wx.OK | wx.ICON_INFORMATION, self)

    def server(self):
        return {"imap_host": self.imap_host.GetValue().strip(), "imap_port": self.imap_port.GetValue(),
                "smtp_host": self.smtp_host.GetValue().strip(), "smtp_port": self.smtp_port.GetValue(),
                "security": self.security_codes[self.security.GetSelection()]}

    def on_ok(self, evt):
        address = self.email.GetValue()
        if "@" not in address:
            i18n.message_box("Informe o e-mail completo, com o arroba.", "Aviso",
                          wx.OK | wx.ICON_WARNING, self)
            self.email.SetFocus()
            return
        if providers.is_microsoft(address):
            i18n.message_box("Contas da Microsoft (Outlook, Hotmail, Live) ainda não funcionam no "
                             "AudioMail: a Microsoft só deixa entrar pelo site dela.", "Aviso",
                             wx.OK | wx.ICON_WARNING, self)
            self.email.SetFocus()
            return
        if not self.password.GetValue().strip():
            i18n.message_box("Informe a senha.", "Aviso", wx.OK | wx.ICON_WARNING, self)
            self.password.SetFocus()
            return
        if self.current()["key"] == "other" and not providers.valid_server(self.server()):
            i18n.message_box("Confira os servidores IMAP e SMTP e as portas.", "Aviso",
                             wx.OK | wx.ICON_WARNING, self)
            self.imap_host.SetFocus()
            return
        evt.Skip()

    def get_values(self):
        key = self.current()["key"]
        return {
            "email": self.email.GetValue().strip(),
            "password": self.password.GetValue(),
            "remember": self.remember.GetValue(),
            "provider": key,
            "server": self.server() if key == "other" else None,
        }


# ---------- configuracoes ----------

class SettingsDialog(wx.Dialog):
    INTERVALS = [(30, "30 segundos"), (60, "1 minuto"), (120, "2 minutos"),
                 (300, "5 minutos"), (600, "10 minutos")]

    def __init__(self, parent, settings):
        super().__init__(parent, title=i18n.tr("Configurações"))
        self.SetMinSize((560, -1))
        self.settings = settings
        self.sound_file = settings.get("sound_file", "")
        outer = wx.BoxSizer(wx.VERTICAL)
        scroll = wx.ScrolledWindow(self, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 12)
        content = wx.BoxSizer(wx.VERTICAL)

        def section(title, expanded=False):
            pane = wx.CollapsiblePane(scroll, label=i18n.tr(title))
            pane.Collapse(not expanded)
            panel = pane.GetPane()
            group = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(group)
            content.Add(pane, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

            def on_collapse(evt):
                scroll.FitInside()
                scroll.Layout()
                evt.Skip()

            pane.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, on_collapse)
            return panel, group

        def check(parent, parent_sizer, label, key):
            box = wx.CheckBox(parent, label=i18n.tr(label))
            box.SetValue(bool(settings.get(key)))
            parent_sizer.Add(box, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            return box

        panel, group = section("Idioma e tradução", expanded=True)
        label = i18n.tr("Idioma da interface")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.ui_language = set_name(wx.Choice(panel, choices=[name for _, name in i18n.LANGUAGES]), label)
        lang_codes = [code for code, _ in i18n.LANGUAGES]
        selected_lang = settings.get("ui_language", "pt")
        self.ui_language.SetSelection(lang_codes.index(selected_lang) if selected_lang in lang_codes else 0)
        group.Add(self.ui_language, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        label = i18n.tr("Traduzir mensagens para")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.translate_to = set_name(wx.Choice(panel, choices=[i18n.tr(name) for _, name in translator.LANGS]), label)
        codes = [code for code, _ in translator.LANGS]
        wanted = settings.get("translate_to", "pt")
        self.translate_to.SetSelection(codes.index(wanted) if wanted in codes else 0)
        group.Add(self.translate_to, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.translate_consent = check(
            panel, group,
            "Traduzir sem perguntar (autoriza enviar o texto ao serviço de tradução do Google)",
            "translate_consent")

        panel, group = section("Resumo com IA", expanded=False)
        group.Add(wx.StaticText(panel, label=i18n.tr(
            "O conteúdo só é enviado quando você pede o resumo. O uso da API pode ser cobrado à parte; a senha ou assinatura do ChatGPT não é uma chave de API.")),
            0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        label = i18n.tr("Provedor de IA")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.ai_provider = set_name(wx.Choice(panel, choices=[
            i18n.tr("OpenAI"), i18n.tr("Gemini"), i18n.tr("Outro compatível com OpenAI")]), label)
        provider_codes = ["openai", "gemini", "compatible"]
        provider = settings.get("ai_summary_provider", "openai")
        if provider not in provider_codes:
            provider = "openai"
        self.ai_provider.SetSelection(provider_codes.index(provider) if provider in provider_codes else 0)
        self.ai_provider_codes = provider_codes
        group.Add(self.ai_provider, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        label = i18n.tr("Modelo de IA")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        default_models = {"openai": "gpt-6-luna", "gemini": "gemini-3.8-flash",
                          "compatible": ""}
        self.ai_model = set_name(wx.TextCtrl(
            panel, value=settings.get("ai_summary_model") or default_models[provider]), label)
        group.Add(self.ai_model, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._last_ai_model = default_models[provider]
        self.ai_provider.Bind(wx.EVT_CHOICE, self.on_ai_provider)
        label = i18n.tr("Endereço base do serviço compatível")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.ai_endpoint = set_name(wx.TextCtrl(
            panel, value=settings.get("ai_summary_endpoint", "")), label)
        self.ai_endpoint.Enable(provider == "compatible")
        group.Add(self.ai_endpoint, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        label = i18n.tr("Chave de API")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.ai_api_key = set_name(wx.TextCtrl(panel, style=wx.TE_PASSWORD), label)
        group.Add(self.ai_api_key, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.ai_key_status = wx.StaticText(panel)
        self.ai_remove_key = wx.CheckBox(panel, label=i18n.tr("Apagar a chave salva deste provedor"))
        group.Add(self.ai_key_status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        group.Add(self.ai_remove_key, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)
        self.refresh_ai_key_status()

        panel, group = section("Avisos de mensagens novas", expanded=False)
        label = i18n.tr("Verificar novas mensagens a cada")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.interval = set_name(wx.Choice(panel, choices=[i18n.tr(text) for _, text in self.INTERVALS]), label)
        secs = [value for value, _ in self.INTERVALS]
        current = settings.get("check_seconds", 60)
        self.interval.SetSelection(secs.index(current) if current in secs else 1)
        group.Add(self.interval, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.realtime = check(panel, group, "Receber mensagens na hora (tempo real)", "realtime")
        self.notify = check(panel, group, "Mostrar notificação quando chegar mensagem nova", "notify")
        self.sound = check(panel, group, "Tocar som quando chegar mensagem nova", "sound")
        self.speak = check(panel, group, "Falar com o leitor de tela quando chegar mensagem nova", "speak")
        label = i18n.tr("Som de notificação")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.sound_text = set_name(wx.TextCtrl(panel, style=wx.TE_READONLY), label)
        group.Add(self.sound_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.show_sound()
        row = wx.BoxSizer(wx.HORIZONTAL)
        for button_label, handler in (("Escolher som", self.on_choose),
                                      ("Usar som padrão", self.on_default),
                                      ("Testar som", self.on_test)):
            button = wx.Button(panel, label=i18n.tr(button_label))
            button.Bind(wx.EVT_BUTTON, handler)
            row.Add(button, 0, wx.RIGHT, 8)
        group.Add(row, 0, wx.ALL, 8)

        panel, group = section("Janela e inicialização", expanded=False)
        self.keep_tray = check(panel, group, "Ao fechar a janela, continuar rodando na bandeja", "keep_tray")
        self.minimize_tray = check(panel, group, "Ao minimizar, esconder na bandeja", "minimize_tray")
        self.start_hidden = check(panel, group, "Abrir já escondido na bandeja", "start_hidden")
        self.autostart = check(panel, group, "Iniciar junto com o Windows", "autostart")

        panel, group = section("Outras opções", expanded=False)
        self.auto_update = check(panel, group, "Verificar atualizações automaticamente", "auto_update")
        label = i18n.tr("Assinatura")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.signature = set_name(wx.TextCtrl(panel, value=settings.get("signature", ""),
                               style=wx.TE_MULTILINE, size=(-1, 70)), label)
        group.Add(self.signature, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 8)
        label = i18n.tr("Tempo para desfazer o envio")
        group.Add(wx.StaticText(panel, label=label), 0, wx.LEFT | wx.TOP, 8)
        self.undo_choices = [0, 5, 10, 20, 30]
        self.undo_send = set_name(wx.Choice(panel, choices=[
            i18n.tr("Desligado") if n == 0 else i18n.tr("%d segundos") % n for n in self.undo_choices]),
            label)
        current = settings.get("undo_send_seconds", 10)
        self.undo_send.SetSelection(self.undo_choices.index(current) if current in self.undo_choices else 2)
        group.Add(self.undo_send, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        scroll.SetSizer(content)
        outer.Add(scroll, 1, wx.EXPAND | wx.ALL, 8)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel(i18n.tr("Salvar"))
        self.FindWindowById(wx.ID_CANCEL).SetLabel(i18n.tr("Cancelar"))
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)
        self.SetSize((600, 680))
        self.SetMinSize((560, 500))
        self.CentreOnParent()
        self.ui_language.SetFocus()

    def show_sound(self):
        self.sound_text.SetValue(self.sound_file if self.sound_file else i18n.tr("Padrão"))

    def on_ai_provider(self, evt):
        provider = self.ai_provider_codes[self.ai_provider.GetSelection()]
        defaults = {"openai": "gpt-6-luna", "gemini": "gemini-3.8-flash", "compatible": ""}
        if self.ai_model.GetValue().strip() == self._last_ai_model:
            self.ai_model.SetValue(defaults[provider])
        self._last_ai_model = defaults[provider]
        self.ai_endpoint.Enable(provider == "compatible")
        self.refresh_ai_key_status()
        evt.Skip()

    def refresh_ai_key_status(self, evt=None):
        provider = self.ai_provider_codes[self.ai_provider.GetSelection()]
        saved = get_ai_api_key(self.settings, provider)
        self.ai_key_status.SetLabel(i18n.tr("Já existe uma chave salva para este provedor.") if saved
                                    else i18n.tr("Nenhuma chave salva para este provedor."))
        self.ai_remove_key.Enable(bool(saved))

    def effective_sound(self):
        if self.sound_file and os.path.isfile(self.sound_file):
            return self.sound_file
        return default_sound_path()

    def on_choose(self, evt):
        path = pick_sound_file(self)
        if path:
            self.sound_file = path
            self.show_sound()
            sounds.play(path)

    def on_default(self, evt):
        self.sound_file = ""
        self.show_sound()
        sounds.play(default_sound_path())

    def on_test(self, evt):
        sounds.play(self.effective_sound())

    def get_settings(self):
        return {
            "check_seconds": self.INTERVALS[self.interval.GetSelection()][0],
            "realtime": self.realtime.GetValue(),
            "notify": self.notify.GetValue(),
            "sound": self.sound.GetValue(),
            "sound_file": self.sound_file,
            "speak": self.speak.GetValue(),
            "keep_tray": self.keep_tray.GetValue(),
            "minimize_tray": self.minimize_tray.GetValue(),
            "start_hidden": self.start_hidden.GetValue(),
            "autostart": self.autostart.GetValue(),
            "auto_update": self.auto_update.GetValue(),
            "translate_to": translator.LANGS[self.translate_to.GetSelection()][0],
            "translate_consent": self.translate_consent.GetValue(),
            "ui_language": i18n.LANGUAGES[self.ui_language.GetSelection()][0],
            "signature": self.signature.GetValue().strip(),
            "undo_send_seconds": self.undo_choices[self.undo_send.GetSelection()],
            "ai_summary_provider": self.ai_provider_codes[self.ai_provider.GetSelection()],
            "ai_summary_model": self.ai_model.GetValue().strip(),
            "ai_summary_endpoint": self.ai_endpoint.GetValue().strip(),
            "_ai_api_key": self.ai_api_key.GetValue().strip(),
            "_ai_remove_key": self.ai_remove_key.GetValue(),
        }


# ---------- leitura ----------

def unique_path(folder, name):
    base, ext = os.path.splitext(mc.safe_filename(name))
    path = os.path.join(folder, base + ext)
    n = 1
    while os.path.exists(path):
        path = os.path.join(folder, "%s (%d)%s" % (base, n, ext))
        n += 1
    return path


class ReadDialog(wx.Dialog):
    """Mostra uma mensagem (ou conversa) e permite responder e mexer nos anexos."""

    def __init__(self, parent, title, text, attachments, announce, sections=None,
                 prefix="", translation=None, auto_translate=False, ai_summary=None,
                 links=None, unsubscribe=None, organize=False, flagged=False):
        super().__init__(parent, title=i18n.tr(title),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.result = None
        self.attachments = attachments
        self.announce = announce
        self.sections = sections
        self.prefix = prefix
        self.translation = translation
        self.ai_summary = ai_summary
        self.original_text = text
        self.translated_text = None
        self.showing_translation = False
        self.busy = False
        self.translate_btn = None
        self.summary_btn = None
        self.links = list(links or [])
        self.unsubscribe = unsubscribe   # funcao(parent) ou None
        self.link_to_open = None          # mailto: escolhido (o AudioMail abre a escrita)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.text = set_name(
            wx.TextCtrl(self, value=text,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2), "Mensagem")
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)
        self.text.Bind(wx.EVT_KEY_DOWN, self.on_text_key)

        # Links da mensagem: no texto aparecem como "[link N]"; aqui, com o site
        # de destino, para abrir com Enter sem copiar nada.
        self.link_list = None
        if self.links:
            lbl = wx.StaticText(self, label=i18n.tr("Links"))
            self.link_list = set_name(
                wx.ListBox(self, choices=[mt.link_label(n, t, u)
                                          for n, (t, u) in enumerate(self.links, 1)],
                           size=(-1, 90)), i18n.tr("Links"))
            self.link_list.SetSelection(0)
            self.link_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_link)
            self.link_list.Bind(wx.EVT_KEY_DOWN, self.on_link_key)
            sizer.Add(lbl, 0, wx.LEFT, 10)
            sizer.Add(self.link_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.att_list = None
        if attachments:
            lbl = wx.StaticText(self, label=i18n.tr("Anexos"))
            self.att_list = set_name(
                wx.ListBox(self, choices=["%s, %s" % (a["name"], mc.format_size(a["size"]))
                                          for a in attachments]), "Anexos")
            self.att_list.SetSelection(0)
            sizer.Add(lbl, 0, wx.LEFT, 10)
            sizer.Add(self.att_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)

        def button(label, handler, ident=wx.ID_ANY):
            b = wx.Button(self, ident, i18n.tr(label))
            if handler:
                b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, 0, wx.RIGHT, 8)
            return b

        button("Responder", lambda e: self.finish("reply"))
        button("Responder a todos", lambda e: self.finish("replyall"))
        if organize:
            button("Encaminhar", lambda e: self.finish("forward"))
        if translation and sections:
            self.translate_btn = button("Traduzir", self.on_translate)
        if ai_summary:
            self.summary_btn = button("Resumir com IA", self.on_summary)
        if self.links:
            button("Abrir link", self.on_open_link)
        if unsubscribe:
            button("Cancelar inscrição", lambda e: self.unsubscribe(self))
        if attachments:
            button("Abrir anexo", self.on_open_att)
            button("Salvar anexo", self.on_save_att)
            button("Salvar todos os anexos", self.on_save_all)
        if organize:
            button("Tirar estrela" if flagged else "Pôr estrela", lambda e: self.finish("star"))
            button("Arquivar", lambda e: self.finish("archive"))
            button("Apagar", lambda e: self.finish("delete"))
            # os mesmos atalhos da janela principal, como nos programas de e-mail
            keys = [(wx.ACCEL_CTRL, ord("R"), "reply"),
                    (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("R"), "replyall"),
                    (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("F"), "forward"),
                    (wx.ACCEL_CTRL, ord("E"), "archive"),
                    (wx.ACCEL_CTRL, ord("S"), "star"),
                    (wx.ACCEL_NORMAL, wx.WXK_DELETE, "delete")]
            table = []
            for flags, code, what in keys:
                ident = wx.NewIdRef()
                self.Bind(wx.EVT_MENU, lambda e, w=what: self.finish(w), id=ident)
                table.append((flags, code, ident))
            self.SetAcceleratorTable(wx.AcceleratorTable(table))
        button("Fechar", None, wx.ID_CANCEL)
        sizer.Add(row, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        self.SetSize((780, 600))
        self.CentreOnParent()
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()
        if auto_translate and self.translate_btn is not None:
            wx.CallAfter(self.on_translate)

    def finish(self, what):
        self.result = what
        self.EndModal(wx.ID_OK)

    # ---- links ----
    def open_url(self, url):
        """Abre o link no navegador; um mailto: abre a escrita do AudioMail."""
        if not url:
            return
        if url.lower().startswith("mailto:"):
            self.link_to_open = url
            self.finish("mailto")
            return
        if not mt.is_safe_link(url):
            self.announce("Este link não pode ser aberto.")
            return
        try:
            opened = webbrowser.open(url)
        except Exception:
            opened = False
        if opened:
            self.announce("Abrindo %s no navegador." % mt.domain_of(url))
        else:
            i18n.message_box("Não consegui abrir o navegador. Abra este endereço você mesmo:\n\n%s"
                             % url, "Links", wx.OK | wx.ICON_INFORMATION, self)

    def on_open_link(self, evt=None):
        if self.link_list is None:
            return
        i = self.link_list.GetSelection()
        if i != wx.NOT_FOUND:
            self.open_url(self.links[i][1])

    def on_link_key(self, evt):
        if evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_open_link()
        else:
            evt.Skip()

    def on_text_key(self, evt):
        """Ctrl+Enter no texto abre o link da linha onde o cursor está."""
        if evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and evt.ControlDown():
            _, _, line_no = self.text.PositionToXY(self.text.GetInsertionPoint())
            url = mt.link_on_line(self.text.GetLineText(line_no), self.links)
            if url:
                self.open_url(url)
            else:
                self.announce("Esta linha não tem link.")
            return
        evt.Skip()

    # ---- traducao ----
    def show_text(self, text):
        self.text.SetValue(text)
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()

    def on_translate(self, evt=None):
        if self.busy or self.translate_btn is None:
            return
        if self.translated_text is not None:  # ja traduziu: alterna entre original e traducao
            self.showing_translation = not self.showing_translation
            self.show_text(self.translated_text if self.showing_translation else self.original_text)
            self.translate_btn.SetLabel(i18n.tr("Ver original") if self.showing_translation else i18n.tr("Ver tradução"))
            self.announce("Mostrando a tradução." if self.showing_translation
                          else "Mostrando o original.")
            return
        if not self.translation.ask_consent(self):
            return
        self.busy = True
        self.translate_btn.Enable(False)
        self.announce("Traduzindo. Aguarde.")
        target, sections = self.translation.target, self.sections

        def work():
            try:
                bodies, detected = [], ""
                for _, body in sections:
                    if body.strip():
                        translated, lang = self.translation.translate(body, target)
                        detected = detected or lang
                    else:
                        translated = body
                    bodies.append(translated)
                outcome = (bodies, detected, None)
            except Exception as e:
                outcome = (None, "", e)
            wx.CallAfter(self.after_translate, target, *outcome)

        threading.Thread(target=work, daemon=True).start()

    def on_summary(self, evt=None):
        if self.busy or self.summary_btn is None:
            return
        if not self.ai_summary.ask_consent(self):
            return
        if self.sections:
            text = "\n\n".join("%s\n%s" % (header, body)
                                  for header, body in self.sections if header or body)
        else:
            text = self.original_text
        if not text.strip():
            i18n.message_box("Esta mensagem não tem texto para resumir.",
                             "Resumo com IA", wx.OK | wx.ICON_INFORMATION, self)
            return
        self.busy = True
        self.summary_btn.Enable(False)
        self.announce("Gerando resumo com IA. Aguarde.")

        def work():
            try:
                result, err = self.ai_summary.summarize(text), None
            except Exception as exc:
                result, err = "", exc
            wx.CallAfter(self.after_summary, result, err)

        threading.Thread(target=work, daemon=True).start()

    def after_summary(self, result, err):
        if not self:
            return
        self.busy = False
        self.summary_btn.Enable(True)
        if err is not None:
            i18n.message_box(str(err), "Resumo com IA", wx.OK | wx.ICON_ERROR, self)
            self.text.SetFocus()
            return
        dlg = wx.Dialog(self, title=i18n.tr("Resumo da mensagem"),
                        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        output = set_name(wx.TextCtrl(dlg, value=result,
                                      style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2),
                          i18n.tr("Resumo da mensagem"))
        close = wx.Button(dlg, wx.ID_OK, i18n.tr("Fechar"))
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(output, 1, wx.EXPAND | wx.ALL, 10)
        layout.Add(close, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        dlg.SetSizer(layout)
        dlg.SetSize((650, 460))
        dlg.CentreOnParent()
        output.SetInsertionPoint(0)
        output.SetFocus()
        dlg.ShowModal()
        dlg.Destroy()


    def after_translate(self, target, bodies, detected, err):
        if not self:
            return
        self.busy = False
        self.translate_btn.Enable(True)
        if err is not None:
            i18n.message_box(str(err), "Tradução", wx.OK | wx.ICON_ERROR, self)
            self.text.SetFocus()
            return
        if detected and translator.same_language(detected, target):
            self.announce("A mensagem já está em %s." % translator.lang_name(target).lower())
            self.text.SetFocus()
            return
        note = "Tradução automática de %s para %s." % (
            translator.lang_name(detected).lower() if detected else "outro idioma",
            translator.lang_name(target).lower())
        prefix = (self.prefix + "\n" if self.prefix else "") + "[" + note + "]"
        self.translated_text = mc.render_text(prefix, self.sections, bodies)
        self.showing_translation = True
        self.translate_btn.SetLabel(i18n.tr("Ver original"))
        self.show_text(self.translated_text)
        self.announce(note)

    def current_att(self):
        i = self.att_list.GetSelection()
        return self.attachments[i] if i != wx.NOT_FOUND else self.attachments[0]

    def on_open_att(self, evt):
        att = self.current_att()
        try:
            folder = tempfile.mkdtemp(prefix="audiomail_")
            path = unique_path(folder, att["name"])
            mc.save_attachment(att, path)
            os.startfile(path)
        except Exception as e:
            i18n.message_box("Não foi possível abrir o anexo: %s" % e, "Erro",
                          wx.OK | wx.ICON_ERROR, self)

    def on_save_att(self, evt):
        att = self.current_att()
        dlg = wx.FileDialog(self, i18n.tr("Salvar anexo"), defaultFile=mc.safe_filename(att["name"]),
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                mc.save_attachment(att, dlg.GetPath())
                self.announce("Anexo salvo.", box=True)
            except OSError as e:
                i18n.message_box("Não foi possível salvar: %s" % e, "Erro",
                              wx.OK | wx.ICON_ERROR, self)
        dlg.Destroy()

    def on_save_all(self, evt):
        dlg = wx.DirDialog(self, i18n.tr("Escolha a pasta para salvar os anexos"))
        if dlg.ShowModal() == wx.ID_OK:
            try:
                for att in self.attachments:
                    mc.save_attachment(att, unique_path(dlg.GetPath(), att["name"]))
                self.announce("%d anexos salvos." % len(self.attachments), box=True)
            except OSError as e:
                i18n.message_box("Não foi possível salvar: %s" % e, "Erro",
                              wx.OK | wx.ICON_ERROR, self)
        dlg.Destroy()


class TicketDialog(wx.Dialog):
    """Formulário acessível de chamado; só envia os campos preenchidos pela pessoa."""

    CATEGORIES = ["Problema", "Dúvida", "Sugestão"]

    def __init__(self, parent, announce, app_version, on_ticket):
        super().__init__(parent, title=i18n.tr("Abrir chamado de suporte"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.announce = announce
        self.app_version = app_version
        self.on_ticket = on_ticket
        self.busy = False
        layout = wx.BoxSizer(wx.VERTICAL)
        hint = wx.StaticText(self, label=i18n.tr("Não inclua senhas. E-mails e anexos não são enviados."))
        layout.Add(hint, 0, wx.EXPAND | wx.ALL, 10)

        def field(label, control, proportion=0):
            translated = i18n.tr(label)
            layout.Add(wx.StaticText(self, label=translated), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
            control.SetName(translated)
            layout.Add(control, proportion, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
            return control

        self.subject = field("Assunto do chamado", wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_RICH2), 1)
        self.category = field("Tipo do chamado", wx.Choice(self, choices=[
            i18n.tr(category) for category in self.CATEGORIES]))
        self.category.SetSelection(0)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.send_button = wx.Button(self, label=i18n.tr("Enviar chamado"))
        close = wx.Button(self, wx.ID_CANCEL, i18n.tr("Cancelar"))
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)
        row.Add(self.send_button, 0, wx.RIGHT, 8)
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizer(layout)
        self.SetSize((560, 340))
        self.SetMinSize((480, 300))
        self.CentreOnParent()
        self.subject.SetFocus()

    def on_send(self, evt=None):
        if self.busy:
            return
        subject = self.subject.GetValue().strip()
        message = subject
        if not subject:
            i18n.message_box("Informe o assunto do chamado.",
                             "Chamado incompleto", wx.OK | wx.ICON_WARNING, self)
            return
        category = self.CATEGORIES[max(0, self.category.GetSelection())]
        self.busy = True
        self.send_button.Enable(False)
        self.announce("Enviando chamado de suporte.")

        def work():
            try:
                ticket_id, ticket_key = support.submit_ticket(
                    "", subject, category, message, self.app_version)
                error = None
            except Exception as exc:
                ticket_id, ticket_key, error = None, None, exc
            wx.CallAfter(self.after_send, ticket_id, ticket_key, subject, error)

        threading.Thread(target=work, daemon=True).start()

    def after_send(self, ticket_id, ticket_key, subject, error):
        if not self:
            return
        self.busy = False
        self.send_button.Enable(True)
        if error:
            i18n.message_box(str(error), "Falha ao enviar chamado", wx.OK | wx.ICON_ERROR, self)
            self.subject.SetFocus()
            return
        self.on_ticket(ticket_id, ticket_key, subject)
        i18n.message_box("Chamado enviado. Número de protocolo: %s" % ticket_id,
                         "Chamado enviado", wx.OK | wx.ICON_INFORMATION, self)
        self.EndModal(wx.ID_OK)


class MyTicketsDialog(wx.Dialog):
    def __init__(self, parent, tickets, on_completed):
        super().__init__(parent, title=i18n.tr("Meus chamados"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.tickets = tickets
        self.on_completed = on_completed
        self.busy = False
        layout = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(self, choices=[
            "%s — %s" % (t.get("subject", ""), i18n.tr("Concluído") if t.get("status") == "resolvido" else i18n.tr("Aberto"))
            for t in tickets])
        self.list.SetName(i18n.tr("Meus chamados"))
        layout.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.complete_button = wx.Button(self, label=i18n.tr("Marcar como concluído"))
        close = wx.Button(self, wx.ID_CANCEL, i18n.tr("Fechar"))
        self.complete_button.Bind(wx.EVT_BUTTON, self.complete_selected)
        self.list.Bind(wx.EVT_LISTBOX, self.update_button)
        row.Add(self.complete_button, 0, wx.RIGHT, 8)
        row.Add(close, 0)
        layout.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizer(layout)
        self.SetSize((560, 360))
        self.update_button()
        self.CentreOnParent()

    def update_button(self, evt=None):
        index = self.list.GetSelection()
        enabled = index != wx.NOT_FOUND and self.tickets[index].get("status") != "resolvido" and not self.busy
        self.complete_button.Enable(enabled)

    def complete_selected(self, evt=None):
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND or self.busy:
            return
        ticket = self.tickets[index]
        self.busy = True
        self.update_button()

        def work():
            try:
                support.complete_ticket(ticket["id"], ticket["key"])
                error = None
            except Exception as exc:
                error = exc
            wx.CallAfter(self.after_complete, index, error)

        threading.Thread(target=work, daemon=True).start()

    def after_complete(self, index, error):
        self.busy = False
        if error:
            i18n.message_box(str(error), "Falha ao concluir chamado", wx.OK | wx.ICON_ERROR, self)
            self.update_button()
            return
        self.tickets[index]["status"] = "resolvido"
        self.on_completed(self.tickets[index]["id"])
        self.list.SetString(index, "%s — %s" % (self.tickets[index].get("subject", ""), i18n.tr("Concluído")))
        self.update_button()



# ---------- escrita ----------

class ComposeDialog(wx.Dialog):
    def __init__(self, parent, client, announce, to="", cc="", bcc="", subject="",
                 body="", in_reply_to=None, references=None, attachments=None, draft=None,
                 translation=None, contacts=None, replies=None, save_replies=None,
                 show_cc=False, undo_seconds=0):
        super().__init__(parent, title=i18n.tr("Nova mensagem"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.client = client
        self.announce = announce
        self.in_reply_to = in_reply_to
        self.references = references
        self.attach = list(attachments or [])
        self.draft = draft          # (pasta, uid) do rascunho que esta sendo editado
        self.translation = translation
        self.translate_btn = None
        self.undo_btn = None
        self.undo_texts = None      # (assunto, texto) de antes da traducao
        self.busy = False
        self.result = None          # "sent", "queued", "scheduled", "draft" ou None
        self.outgoing = None        # o que sai, quando result e "queued" ou "scheduled"
        self.when = None            # horario do envio agendado (datetime)
        self.contacts = contacts
        self.replies = replies if replies is not None else []
        self.save_replies = save_replies
        self.undo_seconds = undo_seconds
        self.labels = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = sizer

        def field(label, make, proportion=0):
            label = i18n.tr(label)
            lbl = wx.StaticText(self, label=label)  # rotulo criado antes do campo
            ctrl = set_name(make(), label)
            sizer.Add(lbl, 0, wx.LEFT | wx.TOP, 10)
            sizer.Add(ctrl, proportion, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            self.labels[ctrl] = lbl
            return ctrl

        self.to = field("Para", lambda: wx.TextCtrl(self, value=to))
        # Contatos e cópia/cópia oculta logo depois do Para, na ordem do Tab.
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.contacts_btn = wx.Button(self, label=i18n.tr("Contatos (Ctrl+K)"))
        self.cc_btn = wx.Button(self, label=i18n.tr("Mostrar cópia e cópia oculta (Ctrl+Shift+C)"))
        self.contacts_btn.Bind(wx.EVT_BUTTON, self.on_contacts)
        self.cc_btn.Bind(wx.EVT_BUTTON, self.on_toggle_cc)
        row.Add(self.contacts_btn, 0, wx.RIGHT, 8)
        row.Add(self.cc_btn, 0)
        sizer.Add(row, 0, wx.LEFT | wx.TOP, 10)
        self.contacts_btn.Show(contacts is not None)
        self.cc = field("Cópia", lambda: wx.TextCtrl(self, value=cc))
        self.bcc = field("Cópia oculta", lambda: wx.TextCtrl(self, value=bcc))
        self.address_field = self.to
        for ctrl in (self.to, self.cc, self.bcc):
            ctrl.Bind(wx.EVT_SET_FOCUS, self.on_address_focus)
            if contacts is not None:
                try:
                    ctrl.AutoComplete(cx.AddressCompleter(contacts))
                except Exception:
                    pass
        self.subject = field("Assunto", lambda: wx.TextCtrl(self, value=subject))
        self.body = field("Texto da mensagem",
                          lambda: wx.TextCtrl(self, value=body,
                                              style=wx.TE_MULTILINE | wx.TE_RICH2), 1)
        self.att_list = field("Anexos", lambda: wx.ListBox(self, size=(-1, 70)))
        row = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self, label=i18n.tr("Adicionar anexo"))
        self.remove_btn = wx.Button(self, label=i18n.tr("Remover anexo"))
        add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove)
        row.Add(add_btn, 0, wx.RIGHT, 8)
        row.Add(self.remove_btn, 0)
        sizer.Add(row, 0, wx.LEFT | wx.TOP, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.replies_btn = wx.Button(self, label=i18n.tr("Respostas prontas (Ctrl+Shift+P)"))
        self.replies_btn.Bind(wx.EVT_BUTTON, self.on_replies)
        row.Add(self.replies_btn, 0)
        sizer.Add(row, 0, wx.LEFT | wx.TOP, 10)

        if translation:
            row = wx.BoxSizer(wx.HORIZONTAL)
            self.translate_btn = wx.Button(self, label=i18n.tr("Traduzir texto"))
            self.undo_btn = wx.Button(self, label=i18n.tr("Desfazer tradução"))
            self.undo_btn.Enable(False)
            self.translate_btn.Bind(wx.EVT_BUTTON, self.on_translate)
            self.undo_btn.Bind(wx.EVT_BUTTON, self.on_undo_translation)
            row.Add(self.translate_btn, 0, wx.RIGHT, 8)
            row.Add(self.undo_btn, 0)
            sizer.Add(row, 0, wx.LEFT | wx.TOP, 10)

        self.send_btn = wx.Button(self, label=i18n.tr("Enviar"))
        self.schedule_btn = wx.Button(self, label=i18n.tr("Agendar envio"))
        self.draft_btn = wx.Button(self, label=i18n.tr("Salvar rascunho"))
        cancel = wx.Button(self, wx.ID_CANCEL, i18n.tr("Cancelar"))
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send)
        self.schedule_btn.Bind(wx.EVT_BUTTON, self.on_schedule)
        self.draft_btn.Bind(wx.EVT_BUTTON, self.on_save_draft)
        cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(wx.EVT_CLOSE, self.on_cancel)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for b in (self.send_btn, self.schedule_btn, self.draft_btn, cancel):
            row.Add(b, 0, wx.RIGHT, 8)
        sizer.Add(row, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        self.SetSize((760, 700))
        self.CentreOnParent()
        self.refresh_attachments()

        # Ctrl+Enter envia, Ctrl+S salva o rascunho, Ctrl+K contatos,
        # Ctrl+Shift+C cópia e cópia oculta, Ctrl+Shift+P respostas prontas
        self.Bind(wx.EVT_MENU, self.on_send, id=self.send_btn.GetId())
        self.Bind(wx.EVT_MENU, self.on_save_draft, id=self.draft_btn.GetId())
        self.Bind(wx.EVT_MENU, self.on_contacts, id=self.contacts_btn.GetId())
        self.Bind(wx.EVT_MENU, self.on_toggle_cc, id=self.cc_btn.GetId())
        self.Bind(wx.EVT_MENU, self.on_replies, id=self.replies_btn.GetId())
        self.SetAcceleratorTable(wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, self.send_btn.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("S"), self.draft_btn.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("K"), self.contacts_btn.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("C"), self.cc_btn.GetId()),
            wx.AcceleratorEntry(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord("P"), self.replies_btn.GetId())]))
        # Cópia e cópia oculta ficam escondidas, a não ser que já tenham algo
        # ou que a pessoa tenha deixado aparecendo da última vez.
        self.set_cc_visible(bool(show_cc or cc.strip() or bcc.strip()))

        self.snapshot = self.state()
        if not to:
            self.to.SetFocus()
        else:
            self.body.SetFocus()
            self.body.SetInsertionPoint(0)

    # ---- copia, contatos e respostas prontas ----
    def set_cc_visible(self, visible):
        self.cc_shown = visible
        for ctrl in (self.cc, self.bcc):
            ctrl.Show(visible)
            self.labels[ctrl].Show(visible)
        self.cc_btn.SetLabel(i18n.tr("Esconder cópia e cópia oculta (Ctrl+Shift+C)") if visible
                             else i18n.tr("Mostrar cópia e cópia oculta (Ctrl+Shift+C)"))
        self.Layout()

    def on_toggle_cc(self, evt=None):
        if self.cc_shown and (self.cc.GetValue().strip() or self.bcc.GetValue().strip()):
            self.announce("Os campos Cópia e Cópia oculta têm endereços; apague-os antes de esconder.")
            self.cc.SetFocus()
            return
        self.set_cc_visible(not self.cc_shown)
        if self.cc_shown:
            self.cc.SetFocus()
            self.announce("Campos Cópia e Cópia oculta mostrados.")
        else:
            if self.address_field in (self.cc, self.bcc):
                self.address_field = self.to
            self.to.SetFocus()
            self.announce("Campos Cópia e Cópia oculta escondidos.")

    def on_address_focus(self, evt):
        self.address_field = evt.GetEventObject()
        evt.Skip()

    def on_contacts(self, evt=None):
        if self.contacts is None:
            return
        target = self.address_field
        name = self.labels[target].GetLabel()
        dlg = cx.ContactPickerDialog(self, self.contacts, name)
        chosen = dlg.chosen if dlg.ShowModal() == wx.ID_OK else None
        dlg.Destroy()
        if chosen:
            target.SetValue(ct.append_address(target.GetValue(), chosen))
            target.SetInsertionPointEnd()
            self.announce("%s adicionado em %s." % (chosen, name))
        target.SetFocus()

    def on_replies(self, evt=None):
        if self.save_replies is None:
            return
        start, end = self.body.GetSelection()
        selected = self.body.GetStringSelection() if end > start else ""
        dlg = cx.QuickRepliesDialog(self, self.replies, self.save_and_keep_replies, selected)
        chosen = dlg.chosen if dlg.ShowModal() == wx.ID_OK else None
        dlg.Destroy()
        if chosen:
            self.body.WriteText(chosen)
            self.announce("Resposta pronta inserida.")
        self.body.SetFocus()

    def save_and_keep_replies(self, replies):
        self.replies = [dict(r) for r in replies]
        self.save_replies(self.replies)

    # ---- estado ----
    def state(self):
        return (self.to.GetValue(), self.cc.GetValue(), self.bcc.GetValue(),
                self.subject.GetValue(), self.body.GetValue(), tuple(self.attach))

    def dirty(self):
        return self.state() != self.snapshot

    def set_busy(self, busy):
        self.busy = busy
        for b in (self.send_btn, self.schedule_btn, self.draft_btn, self.translate_btn):
            if b is not None:
                b.Enable(not busy)

    # ---- traducao do que esta sendo escrito ----
    def on_translate(self, evt=None):
        if self.busy or not self.translation:
            return
        subject, body = self.subject.GetValue(), self.body.GetValue()
        if not subject.strip() and not body.strip():
            self.announce("Não há texto para traduzir.")
            return
        codes = [c for c, _ in translator.LANGS]
        chooser = wx.SingleChoiceDialog(self, i18n.tr("Traduzir o assunto e o texto para qual idioma?"),
                                        i18n.tr("Traduzir texto"), [i18n.tr(n) for _, n in translator.LANGS])
        last = self.translation.compose_lang
        chooser.SetSelection(codes.index(last) if last in codes else 1)
        if chooser.ShowModal() != wx.ID_OK:
            chooser.Destroy()
            return
        code = codes[chooser.GetSelection()]
        chooser.Destroy()
        if not self.translation.ask_consent(self):
            return
        self.translation.set_compose_lang(code)
        self.set_busy(True)
        self.announce("Traduzindo. Aguarde.")

        def work():
            try:
                new_body, lang = (self.translation.translate(body, code) if body.strip()
                                  else (body, ""))
                new_subject = (self.translation.translate(subject, code)[0]
                               if subject.strip() else subject)
                outcome = (new_subject, new_body, lang, None)
            except Exception as e:
                outcome = ("", "", "", e)
            wx.CallAfter(self.after_translate, code, subject, body, *outcome)

        threading.Thread(target=work, daemon=True).start()

    def after_translate(self, code, old_subject, old_body, new_subject, new_body, lang, err):
        if not self:
            return
        self.set_busy(False)
        if err is not None:
            i18n.message_box(str(err), "Tradução", wx.OK | wx.ICON_ERROR, self)
            return
        if lang and translator.same_language(lang, code):
            self.announce("O texto já está em %s." % translator.lang_name(code).lower())
            return
        self.undo_texts = (old_subject, old_body)
        self.subject.SetValue(new_subject)
        self.body.SetValue(new_body)
        self.body.SetInsertionPoint(0)
        self.undo_btn.Enable(True)
        self.announce("Texto traduzido para %s." % translator.lang_name(code).lower())
        self.body.SetFocus()

    def on_undo_translation(self, evt=None):
        if self.undo_texts is None:
            return
        self.subject.SetValue(self.undo_texts[0])
        self.body.SetValue(self.undo_texts[1])
        self.undo_texts = None
        self.undo_btn.Enable(False)
        self.announce("Tradução desfeita.")
        self.body.SetFocus()

    # ---- anexos ----
    def refresh_attachments(self, select=None):
        self.att_list.Set(["%s, %s" % (os.path.basename(p), mc.format_size(self.size_of(p)))
                           for p in self.attach])
        if self.attach:
            self.att_list.SetSelection(select if select is not None else 0)
        self.remove_btn.Enable(bool(self.attach))

    @staticmethod
    def size_of(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def on_add(self, evt):
        dlg = wx.FileDialog(self, i18n.tr("Escolher arquivos para anexar"),
                            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            for p in dlg.GetPaths():
                if p not in self.attach:
                    self.attach.append(p)
            total = sum(self.size_of(p) for p in self.attach)
            self.refresh_attachments(len(self.attach) - 1)
            if total > mc.MAX_ATTACH:
                i18n.message_box("Os anexos passam do limite de envio (cerca de 18 MB no total). "
                              "Remova algum antes de enviar.", "Aviso",
                              wx.OK | wx.ICON_WARNING, self)
            else:
                self.announce("%d anexos, %s no total." % (
                    len(self.attach), mc.format_size(total)))
        dlg.Destroy()
        self.att_list.SetFocus()

    def on_remove(self, evt):
        i = self.att_list.GetSelection()
        if i != wx.NOT_FOUND:
            del self.attach[i]
            self.refresh_attachments(min(i, len(self.attach) - 1) if self.attach else None)
            self.announce("Anexo removido.")
        self.att_list.SetFocus()

    # ---- enviar ----
    def fields(self):
        return (self.to.GetValue(), self.cc.GetValue(), self.bcc.GetValue(),
                self.subject.GetValue(), self.body.GetValue(),
                self.in_reply_to, self.references, list(self.attach))

    def ready_to_send(self):
        """Confere destinatário e assunto antes de enviar ou agendar."""
        if not (self.to.GetValue().strip() or self.cc.GetValue().strip()
                or self.bcc.GetValue().strip()):
            i18n.message_box("Informe o destinatário.", "Aviso", wx.OK | wx.ICON_WARNING, self)
            self.to.SetFocus()
            return False
        if not self.subject.GetValue().strip():
            ask = i18n.message_box("A mensagem está sem assunto. Enviar assim mesmo?",
                                "Confirmar", wx.YES_NO | wx.ICON_QUESTION, self)
            if ask != wx.YES:
                self.subject.SetFocus()
                return False
        if not self.attach and mt.mentions_attachment(self.body.GetValue()):
            ask = i18n.message_box("O texto fala de anexo, mas a mensagem não tem nenhum arquivo "
                                   "anexado. Enviar assim mesmo?\n\nEscolha Não para anexar agora.",
                                   "Anexo esquecido?", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
            if ask != wx.YES:
                self.on_add(None)
                return False
        return True

    def on_schedule(self, evt=None):
        if self.busy or not self.ready_to_send():
            return
        when = cx.ask_schedule(self)
        if when is None:
            self.schedule_btn.SetFocus()
            return
        self.outgoing, self.when, self.result = self.fields(), when, "scheduled"
        self.EndModal(wx.ID_OK)

    def on_send(self, evt):
        if self.busy or not self.ready_to_send():
            return
        if self.undo_seconds > 0:
            # quem envia e a janela principal, depois do tempo de desfazer
            self.outgoing, self.result = self.fields(), "queued"
            self.EndModal(wx.ID_OK)
            return
        self.set_busy(True)
        self.send_btn.SetLabel(i18n.tr("Enviando"))
        args, draft = self.fields(), self.draft

        def work():
            try:
                self.client.send(*args)
                if draft:
                    try:
                        self.client.delete_permanent(*draft)
                    except Exception:
                        pass
                err = None
            except Exception as e:
                err = e
            wx.CallAfter(self.after_send, err)

        threading.Thread(target=work, daemon=True).start()

    def after_send(self, err):
        if not self:
            return
        self.set_busy(False)
        self.send_btn.SetLabel(i18n.tr("Enviar"))
        if err is None:
            self.result = "sent"
            self.EndModal(wx.ID_OK)
            return
        i18n.message_box(str(err), "Erro ao enviar", wx.OK | wx.ICON_ERROR, self)
        self.send_btn.SetFocus()

    # ---- rascunho ----
    def on_save_draft(self, evt=None, close_after=False):
        if self.busy:
            return
        self.set_busy(True)
        args, old = self.fields(), self.draft

        def work():
            try:
                res, err = self.client.save_draft(*args, old=old), None
            except Exception as e:
                res, err = None, e
            wx.CallAfter(self.after_draft, res, err, close_after)

        threading.Thread(target=work, daemon=True).start()

    def after_draft(self, res, err, close_after):
        if not self:
            return
        self.set_busy(False)
        if err is not None:
            i18n.message_box(str(err), "Erro ao salvar o rascunho", wx.OK | wx.ICON_ERROR, self)
            return
        raw, uid = res
        self.draft = (raw, uid) if uid else None
        self.snapshot = self.state()
        self.result = "draft"
        self.announce("Rascunho salvo.", box=not close_after)
        if close_after:
            self.EndModal(wx.ID_CANCEL)

    def on_cancel(self, evt):
        if self.busy:
            return
        if self.dirty():
            ask = i18n.message_box("Salvar como rascunho antes de sair?", "Sair da mensagem",
                                wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION, self)
            if ask == wx.CANCEL:
                return
            if ask == wx.YES:
                self.on_save_draft(close_after=True)
                return
        self.EndModal(wx.ID_CANCEL)


# ---------- atualizacao ----------

class UpdateDialog(wx.Dialog):
    """Avisa de uma versao nova e pergunta o que fazer. result: update, skip ou None."""

    def __init__(self, parent, current, manifest, forced=False):
        kind = manifest.get("type", "importante")
        if forced:
            title, level = "Atualização obrigatória", "ATUALIZAÇÃO OBRIGATÓRIA: o AudioMail não pode continuar sem atualizar."
        elif kind == "urgente":
            title, level = "Atualização urgente", "ATUALIZAÇÃO URGENTE: atualize o quanto antes."
        elif kind == "novidade":
            title, level = "Novidades do AudioMail", "Só novidades: você pode atualizar quando quiser."
        else:
            title, level = "Atualização disponível", "Atualização recomendada."
        super().__init__(parent, title=i18n.tr(title), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.result = None
        text = "%s\n\nNova versão: %s\nVersão instalada: %s\n\nNovidades:\n%s" % (
            level, manifest["version"], current, manifest.get("notes") or "(sem descrição)")
        sizer = wx.BoxSizer(wx.VERTICAL)
        lbl = wx.StaticText(self, label=i18n.tr("Novidades"))  # rotulo criado antes do campo
        self.text = set_name(
            wx.TextCtrl(self, value=text,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2), "Novidades")
        sizer.Add(lbl, 0, wx.LEFT | wx.TOP, 10)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        update = wx.Button(self, label=i18n.tr("Atualizar agora"))
        update.Bind(wx.EVT_BUTTON, lambda e: self.finish("update"))
        row.Add(update, 0, wx.RIGHT, 8)
        if forced:  # obrigatoria: so atualizar ou fechar o programa
            leave = wx.Button(self, wx.ID_CANCEL, i18n.tr("Fechar o AudioMail"))
            leave.Bind(wx.EVT_BUTTON, lambda e: self.finish("quit"))
            row.Add(leave, 0, wx.RIGHT, 8)
            self.Bind(wx.EVT_CLOSE, lambda e: self.finish("quit"))
        else:
            if kind != "urgente":  # urgente nao pode ser pulada
                skip = wx.Button(self, label=i18n.tr("Pular esta versão"))
                skip.Bind(wx.EVT_BUTTON, lambda e: self.finish("skip"))
                row.Add(skip, 0, wx.RIGHT, 8)
            row.Add(wx.Button(self, wx.ID_CANCEL, i18n.tr("Depois")), 0, wx.RIGHT, 8)
        sizer.Add(row, 0, wx.ALL, 10)
        self.SetSizer(sizer)
        self.SetSize((600, 420))
        self.CentreOnParent()
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()

    def finish(self, what):
        self.result = what
        self.EndModal(wx.ID_OK)
