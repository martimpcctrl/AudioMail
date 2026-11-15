"""Colar arquivos como anexo: o que foi copiado no Explorador do Windows (Ctrl+C)
vira anexo com Ctrl+V na escrita. Texto copiado continua sendo colado como texto."""
import os

import wx

import i18n
import mail_core as mc


def clipboard_files():
    """Os arquivos copiados no Explorador, ou [] se a área de transferência tem outra coisa."""
    clipboard = wx.TheClipboard
    if not clipboard.Open():
        return []
    try:
        if not clipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            return []
        data = wx.FileDataObject()
        if not clipboard.GetData(data):
            return []
        return list(data.GetFilenames())
    finally:
        clipboard.Close()


def split_paths(paths, existing, isdir=os.path.isdir):
    """(arquivos novos, pastas, repetidos): pastas não viram anexo, e o mesmo
    arquivo não entra duas vezes."""
    known = {os.path.normcase(os.path.abspath(p)) for p in existing}
    new, folders, repeated = [], [], []
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if isdir(p):
            folders.append(p)
        elif key in known:
            repeated.append(p)
        else:
            known.add(key)
            new.append(p)
    return new, folders, repeated


class PasteFilesMixin:
    """Para a janela de escrita (precisa de self.attach, self.att_list,
    self.refresh_attachments, self.size_of e self.announce)."""

    def bind_paste(self, text_controls):
        for ctrl in text_controls:
            ctrl.Bind(wx.EVT_TEXT_PASTE, self.on_text_paste)
        self.att_list.Bind(wx.EVT_KEY_DOWN, self.on_attachments_key)

    def on_text_paste(self, evt):
        files = clipboard_files()
        if files:
            self.add_paths(files)
        else:
            evt.Skip()   # texto: cola normalmente

    def on_attachments_key(self, evt):
        code = evt.GetKeyCode()
        if evt.ControlDown() and code == ord("V"):
            files = clipboard_files()
            if files:
                self.add_paths(files)
            else:
                self.announce("Não há arquivos copiados para colar.")
        elif code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.on_remove(None)
        else:
            evt.Skip()

    def add_paths(self, paths):
        """Anexa os arquivos e fala o resultado. Devolve quantos entraram."""
        new, folders, repeated = split_paths(paths, self.attach)
        self.attach.extend(new)
        total = sum(self.size_of(p) for p in self.attach)
        if new:
            self.refresh_attachments(len(self.attach) - 1)
        if total > mc.MAX_ATTACH:
            i18n.message_box("Os anexos passam do limite de envio (cerca de 18 MB no total). "
                             "Remova algum antes de enviar.", "Aviso",
                             wx.OK | wx.ICON_WARNING, self)
        elif new:
            self.announce("%d anexos, %s no total." % (len(self.attach), mc.format_size(total)))
        if folders:
            self.announce("Pastas não podem ser anexadas. Compacte a pasta num arquivo zip e anexe o zip.")
        elif repeated and not new:
            self.announce("Esse arquivo já está nos anexos.")
        return len(new)
