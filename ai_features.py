"""Ler anexos dentro do AudioMail, descrever imagens e escrever respostas com IA.

AttachmentReaderMixin vai na janela de leitura (botão Ler anexo) e
AIWriterMixin na janela de escrita (botão Escrever com IA). A IA é a mesma
configurada para o resumo, com a chave da própria pessoa.
"""
import io
import re
import threading

import wx

import i18n
import attachment_text as at
from common import set_name

API_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE = 4 * 1024 * 1024
MAX_SIDE = 1600


def prepare_image(data, mime):
    """A imagem num formato e tamanho que as IAs aceitam: as grandes ou em formato
    incomum (BMP, TIFF...) viram JPEG de até 1600 pontos no lado maior."""
    mime = (mime or "").lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime in API_IMAGE_TYPES and len(data) <= MAX_IMAGE:
        return data, mime
    img = wx.Image(io.BytesIO(data))
    if not img.IsOk():
        raise at.Unreadable("Não foi possível abrir esta imagem.")
    w, h = img.GetWidth(), img.GetHeight()
    scale = min(1.0, MAX_SIDE / float(max(w, h)))
    if scale < 1.0:
        img = img.Scale(max(1, int(w * scale)), max(1, int(h * scale)), wx.IMAGE_QUALITY_HIGH)
    if img.HasAlpha():
        img.ClearAlpha()
    img.SetOption(wx.IMAGE_OPTION_QUALITY, "85")
    out = io.BytesIO()
    if not img.SaveFile(out, wx.BITMAP_TYPE_JPEG):
        raise at.Unreadable("Não foi possível preparar esta imagem.")
    return out.getvalue(), "image/jpeg"


def show_text_window(parent, title, text):
    """Janela só de leitura (setas leem, Esc fecha), como a do resumo."""
    dlg = wx.Dialog(parent, title=i18n.tr(title), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    output = set_name(wx.TextCtrl(dlg, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2),
                      i18n.tr(title))
    close = wx.Button(dlg, wx.ID_OK, i18n.tr("Fechar"))
    copy = wx.Button(dlg, label=i18n.tr("Copiar tudo"))
    copy.Bind(wx.EVT_BUTTON, lambda e: copy_text(text))
    layout = wx.BoxSizer(wx.VERTICAL)
    layout.Add(output, 1, wx.EXPAND | wx.ALL, 10)
    row = wx.BoxSizer(wx.HORIZONTAL)
    row.Add(copy, 0, wx.RIGHT, 8)
    row.Add(close, 0)
    layout.Add(row, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
    dlg.SetSizer(layout)
    dlg.SetSize((700, 520))
    dlg.SetEscapeId(wx.ID_OK)
    dlg.CentreOnParent()
    output.SetInsertionPoint(0)
    output.SetFocus()
    return dlg


def copy_text(text):
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()


class AttachmentReaderMixin:
    """Botão Ler anexo da janela de leitura: texto dos documentos e, nas imagens,
    a descrição feita pela IA."""

    def on_read_att(self, evt=None):
        if getattr(self, "reading_att", False):
            return
        att = self.current_att()
        kind = at.kind_of(att["name"], att.get("type", ""))
        if kind is None:
            i18n.message_box("O AudioMail não sabe ler esse tipo de arquivo. Use Abrir anexo.",
                             "Ler anexo", wx.OK | wx.ICON_INFORMATION, self)
            return
        ai = self.ai_summary
        if kind == "image":
            if ai is None or not ai.configured():
                i18n.message_box("Para descrever imagens, configure a IA em Configurações > Resumo com IA.",
                                 "Descrever imagem", wx.OK | wx.ICON_INFORMATION, self)
                return
            if not ai.ask_consent_for(self, "image"):
                return
            self.announce("Pedindo a descrição da imagem à IA. Aguarde.")
            title = i18n.tr("Descrição de %s") % att["name"]
        else:
            self.announce("Lendo o anexo.")
            title = att["name"]
        self.reading_att = True
        from mail_core import part_bytes

        def work():
            try:
                data = part_bytes(att["part"])
                if kind == "image":
                    image, mime = prepare_image(data, att.get("type", ""))
                    text = ai.describe_image(image, mime)
                else:
                    text = at.extract_text(att["name"], att.get("type", ""), data)
                result = (text, None)
            except Exception as exc:
                result = (None, exc)
            wx.CallAfter(self.after_read_att, title, *result)

        threading.Thread(target=work, daemon=True).start()

    def after_read_att(self, title, text, err):
        if not self:
            return
        self.reading_att = False
        if err is not None:
            i18n.message_box(str(err), "Ler anexo", wx.OK | wx.ICON_WARNING, self)
            return
        dlg = show_text_window(self, title, text)
        dlg.ShowModal()
        dlg.Destroy()


def split_reply_body(body):
    """(o que você escreveu, a mensagem respondida sem os >) do corpo da escrita."""
    mine, quoted, in_quote = [], [], False
    for line in (body or "").replace("\r", "").split("\n"):
        stripped = line.strip()
        if re.match(r"(?i)^(em|on|el) .{5,160}(escreveu|wrote|escribió):$", stripped) or \
                stripped.startswith("---------- "):
            in_quote = True
            continue
        if in_quote or stripped.startswith(">"):
            quoted.append(re.sub(r"^>\s?", "", line))
        else:
            mine.append(line)
    text = "\n".join(mine)
    cut = re.search(r"(?m)^-- $", text)
    if cut:
        text = text[:cut.start()]
    return text.strip(), "\n".join(quoted).strip()


class IdeaDialog(wx.Dialog):
    """Pergunta o que a pessoa quer dizer (self.idea)."""

    def __init__(self, parent, value=""):
        super().__init__(parent, title=i18n.tr("Escrever com IA"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("O que você quer dizer? (por exemplo: diz que aceito, mas só na sexta)")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)
        self.text = set_name(wx.TextCtrl(self, value=value, style=wx.TE_MULTILINE, size=(480, 120)), label)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)
        ok = wx.Button(self, wx.ID_OK, i18n.tr("Escrever"))
        cancel = wx.Button(self, wx.ID_CANCEL, i18n.tr("Cancelar"))
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(ok, 0, wx.RIGHT, 8)
        row.Add(cancel, 0)
        sizer.Add(row, 0, wx.ALL, 10)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.SetAcceleratorTable(wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RETURN, wx.ID_OK)]))
        self.Bind(wx.EVT_MENU, lambda e: self.EndModal(wx.ID_OK), id=wx.ID_OK)
        self.text.SetFocus()

    @property
    def idea(self):
        return self.text.GetValue().strip()


class AIWriterMixin:
    """Botão Escrever com IA da janela de escrita."""

    def on_ai_write(self, evt=None):
        ai = getattr(self, "ai", None)
        if getattr(self, "ai_busy", False):
            return
        if ai is None or not ai.configured():
            i18n.message_box("Para escrever com IA, configure a IA em Configurações > Resumo com IA.",
                             "Escrever com IA", wx.OK | wx.ICON_INFORMATION, self)
            return
        mine, context = split_reply_body(self.body.GetValue())
        dlg = IdeaDialog(self, mine)
        ok = dlg.ShowModal() == wx.ID_OK
        idea = dlg.idea
        dlg.Destroy()
        if not ok or not idea:
            self.body.SetFocus()
            return
        if not ai.ask_consent_for(self, "reply"):
            return
        self.ai_busy = True
        self.announce("A IA está escrevendo. Aguarde.")

        def work():
            try:
                result = (ai.write_reply(idea, context), None)
            except Exception as exc:
                result = (None, exc)
            wx.CallAfter(self.after_ai_write, mine, *result)

        threading.Thread(target=work, daemon=True).start()

    def after_ai_write(self, mine, text, err):
        if not self:
            return
        self.ai_busy = False
        if err is not None:
            i18n.message_box(str(err), "Escrever com IA", wx.OK | wx.ICON_ERROR, self)
            self.body.SetFocus()
            return
        body = self.body.GetValue()
        rest = body
        if mine and body.lstrip().startswith(mine):
            rest = body.lstrip()[len(mine):]     # a ideia escrita no corpo vira o texto da IA
        self.body.SetValue(text.strip() + "\n" + (rest if rest.startswith("\n") else "\n" + rest))
        self.body.SetInsertionPoint(0)
        self.body.SetFocus()
        self.announce("Pronto. O texto da IA está no começo da mensagem. Revise antes de enviar.")
