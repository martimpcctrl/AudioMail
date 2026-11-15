"""Janelas de marcadores do Gmail e de busca avançada."""
import wx

import i18n
import search_query as sq
from common import set_name
from compose_extras import _buttons
from organize_dialogs import ask_text


class LabelsDialog(wx.Dialog):
    """Marca e desmarca marcadores do Gmail. Uma lista simples (Espaço marca ou
    desmarca), que o leitor de tela lê como "Trabalho, marcado".

    ``labels``: [(nome no servidor, nome para mostrar)]; ``checked``: nomes no servidor.
    No fim: self.add, self.remove (nomes no servidor) e self.new_names (marcadores a criar)."""

    def __init__(self, parent, labels, checked, partial=()):
        super().__init__(parent, title=i18n.tr("Marcadores"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.labels = list(labels)
        self.start = set(checked)
        self.partial = set(partial) - self.start   # marcado em só algumas das selecionadas
        self.state = {raw: (raw in self.start) for raw, _ in self.labels}
        self.touched = set()
        self.new_names = []
        self.add, self.remove = [], []
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Marcadores (Espaço marca ou desmarca)")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(380, 260)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Marcar ou desmarcar", self.on_toggle, wx.ID_ANY),
                               ("Novo marcador...", self.on_new, wx.ID_ANY)])
        _buttons(self, sizer, [("Salvar", self.on_ok, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_toggle)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.refresh(0)
        self.list.SetFocus()

    def text(self, raw, name):
        if raw in self.partial and raw not in self.touched:
            return i18n.tr("%s, em algumas") % name
        return i18n.tr("%s, marcado") % name if self.state[raw] else i18n.tr("%s, não marcado") % name

    def refresh(self, select=None):
        self.list.Clear()
        if not self.labels:
            self.list.Append(i18n.tr("Nenhum marcador. Use o botão Novo marcador."))
        for raw, name in self.labels:
            self.list.Append(self.text(raw, name))
        if select is not None and self.list.GetCount():
            self.list.SetSelection(max(0, min(select, self.list.GetCount() - 1)))

    def on_toggle(self, evt=None):
        i = self.list.GetSelection()
        if not self.labels or not 0 <= i < len(self.labels):
            return
        raw, name = self.labels[i]
        self.state[raw] = not self.state[raw] if raw in self.touched or raw not in self.partial else True
        self.touched.add(raw)
        self.list.SetString(i, self.text(raw, name))

    def on_new(self, evt=None):
        name = ask_text(self, "Nome do novo marcador", "Novo marcador")
        if not name:
            return
        self.new_names.append(name)
        raw = "\x00new:" + name
        self.labels.append((raw, name))
        self.state[raw] = True
        self.touched.add(raw)
        self.refresh(len(self.labels) - 1)

    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_SPACE:
            self.on_toggle()
            return
        evt.Skip()

    def result(self):
        add = [raw for raw, _ in self.labels if self.state[raw] and raw in self.touched
               and (raw not in self.start or raw in self.partial) and not raw.startswith("\x00")]
        remove = [raw for raw, _ in self.labels if not self.state[raw] and raw in self.touched
                  and (raw in self.start or raw in self.partial)]
        return add, remove

    def on_ok(self, evt=None):
        self.add, self.remove = self.result()
        self.new_names = [n for n in self.new_names if self.state.get("\x00new:" + n)]
        self.EndModal(wx.ID_OK)


class AdvancedSearchDialog(wx.Dialog):
    """Monta o texto do campo Buscar (self.query) a partir de campos simples."""

    def __init__(self, parent, current="", all_folders=False):
        super().__init__(parent, title=i18n.tr("Buscar em todas as pastas" if all_folders else "Busca avançada"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        c = sq.parse_query(current)
        self.query = ""
        self.all_folders = all_folders
        sizer = wx.BoxSizer(wx.VERTICAL)

        def field(label, value=""):
            sizer.Add(wx.StaticText(self, label=i18n.tr(label)), 0, wx.LEFT | wx.TOP, 10)
            ctrl = set_name(wx.TextCtrl(self, value=value, style=wx.TE_PROCESS_ENTER), i18n.tr(label))
            ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
            sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            return ctrl

        self.from_ = field("De (nome ou endereço)", c["from"])
        self.to = field("Para", c["to"])
        self.subject = field("Assunto", c["subject"])
        self.words = field("Contém as palavras", " ".join(c["words"]))
        label = i18n.tr("Data")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.period = set_name(wx.Choice(self, choices=[i18n.tr(t) for _, t in sq.PERIODS]), label)
        self.period.SetSelection(0)
        sizer.Add(self.period, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.attachment = wx.CheckBox(self, label=i18n.tr("Só com anexo"))
        self.unread = wx.CheckBox(self, label=i18n.tr("Só não lidas"))
        self.starred = wx.CheckBox(self, label=i18n.tr("Só com estrela"))
        self.attachment.SetValue(c["attachment"])
        self.unread.SetValue(c["unread"])
        self.starred.SetValue(c["starred"])
        for box in (self.attachment, self.unread, self.starred):
            sizer.Add(box, 0, wx.LEFT | wx.TOP, 10)
        self.everywhere = wx.CheckBox(self, label=i18n.tr("Buscar em todas as pastas"))
        self.everywhere.SetValue(all_folders)
        sizer.Add(self.everywhere, 0, wx.LEFT | wx.TOP, 10)
        _buttons(self, sizer, [("Buscar", self.on_ok, wx.ID_OK), ("Limpar", self.on_clear, wx.ID_ANY),
                               ("Cancelar", None, wx.ID_CANCEL)])
        self.SetSizerAndFit(sizer)
        self.SetSize((440, -1))
        self.CentreOnParent()
        self.from_.SetFocus()

    def build(self):
        return sq.build(self.from_.GetValue(), self.to.GetValue(), self.subject.GetValue(),
                        self.words.GetValue(), self.attachment.GetValue(), self.unread.GetValue(),
                        self.starred.GetValue(), sq.PERIODS[max(0, self.period.GetSelection())][0])

    def on_clear(self, evt=None):
        for ctrl in (self.from_, self.to, self.subject, self.words):
            ctrl.SetValue("")
        for box in (self.attachment, self.unread, self.starred):
            box.SetValue(False)
        self.period.SetSelection(0)
        self.from_.SetFocus()

    def on_ok(self, evt=None):
        self.query = self.build()
        self.all_folders = self.everywhere.GetValue()
        self.EndModal(wx.ID_OK)
