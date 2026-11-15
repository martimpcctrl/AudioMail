"""Buscar em todas as pastas: a mesma busca em cada pasta da conta, com uma
lista de quantos resultados cada uma tem ("Caixa de entrada: 4"). Enter abre a
pasta já com a busca feita."""
import wx

import i18n
import organize
import views
from common import set_name
from compose_extras import _buttons


def result_label(name, count):
    return i18n.tr("%s: 1 resultado") % name if count == 1 else i18n.tr("%s: %d resultados") % (name, count)


def summary(found):
    total = sum(n for _, n in found)
    if not found:
        return i18n.tr("Nada encontrado em nenhuma pasta.")
    if len(found) == 1:
        return i18n.tr("%d resultados em 1 pasta.") % total if total != 1 else i18n.tr("1 resultado em 1 pasta.")
    return i18n.tr("%d resultados em %d pastas.") % (total, len(found))


class FolderResultsDialog(wx.Dialog):
    """A lista "Pasta: N resultados". self.choice é o índice escolhido."""

    def __init__(self, parent, query, rows):
        super().__init__(parent, title=i18n.tr("Resultados em todas as pastas"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.choice = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Pastas com resultados para %s (Enter abre a pasta)") % query
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)
        self.list = set_name(wx.ListBox(self, choices=rows, size=(440, 240)), label)
        self.list.SetSelection(0)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        ok, _ = _buttons(self, sizer, [("Abrir pasta", self.on_ok, wx.ID_OK), ("Fechar", None, wx.ID_CANCEL)])
        ok.SetDefault()
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.list.SetFocus()

    def on_ok(self, evt=None):
        self.choice = self.list.GetSelection()
        self.EndModal(wx.ID_OK)


class SearchAllMixin:
    def open_search_all(self):
        self.open_advanced_search(all_folders=True)

    def search_all(self, query):
        acc = self.active
        if not acc or not acc.client:
            return
        if not query.strip():
            self.announce("Escreva o que buscar.")
            return
        if acc.offline:
            self.announce("A busca em todas as pastas precisa de internet.")
            return
        client = acc.client.side()
        folders = organize.real_folders(acc.folders)

        def work():
            return client.count_matches(folders, query)

        def done(found):
            self.SetStatusText(summary(found))
            if not found:
                i18n.message_box(summary(found), "Buscar em todas as pastas",
                                 wx.OK | wx.ICON_INFORMATION, self)
                self.list.SetFocus()
                return
            self.announce(summary(found))
            rows = [result_label(i18n.tr(f["display"]), n) for f, n in found]
            dlg = FolderResultsDialog(self, query, rows)
            ok = dlg.ShowModal() == wx.ID_OK
            choice = dlg.choice
            dlg.Destroy()
            if not ok or choice is None or acc is not self.active:
                self.list.SetFocus()
                return
            self.open_folder_with_search(acc, found[choice][0], query)

        self.run(work, done, "Buscando em todas as pastas")

    def open_folder_with_search(self, acc, folder, query):
        index = next((i for i, f in enumerate(acc.folders) if f["raw"] == folder["raw"]
                      and not f.get("filter")), None)
        if index is not None:
            self.choice.SetSelection(index)
        self.choose_folder(folder)
        acc.search = query
        acc.limit = views.PAGE
        self.search_box.SetValue(query)
        self.refresh()
