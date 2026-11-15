"""Janelas de apoio à escrita: contatos, respostas prontas e envio agendado."""
import datetime

import wx
import wx.adv

import i18n
from common import set_name
from contacts import Contacts, group_label


def _buttons(dialog, sizer, specs):
    row = wx.BoxSizer(wx.HORIZONTAL)
    made = []
    for label, handler, ident in specs:
        b = wx.Button(dialog, ident, i18n.tr(label))
        if handler:
            b.Bind(wx.EVT_BUTTON, handler)
        row.Add(b, 0, wx.RIGHT, 8)
        made.append(b)
    sizer.Add(row, 0, wx.ALL, 10)
    return made


# ---------- contatos ----------

class AddressCompleter(wx.TextCompleterSimple):
    """Sugestões nativas do Windows enquanto se digita um endereço."""

    def __init__(self, contacts):
        super().__init__()
        self.contacts = contacts

    def GetCompletions(self, prefix):
        try:
            return self.contacts.completions(prefix)
        except Exception:
            return []


class ContactPickerDialog(wx.Dialog):
    """Busca um contato e devolve o endereço escolhido (self.chosen)."""

    def __init__(self, parent, contacts, field_name):
        super().__init__(parent, title=i18n.tr("Contatos"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.contacts = contacts
        self.chosen = None
        self.chosen_name = None
        self.found = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Buscar contato")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.query = set_name(wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER), label)
        sizer.Add(self.query, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        label = i18n.tr("Contatos")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(-1, 260)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        ok, _ = _buttons(self, sizer, [(i18n.tr("Adicionar em %s") % i18n.tr(field_name), self.on_ok, wx.ID_OK),
                                       ("Cancelar", None, wx.ID_CANCEL)])
        ok.SetDefault()
        self.query.Bind(wx.EVT_TEXT, lambda e: self.refresh())
        self.query.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
        self.query.Bind(wx.EVT_KEY_DOWN, self.on_query_key)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        self.SetSizer(sizer)
        self.SetSize((520, 440))
        self.CentreOnParent()
        self.refresh()
        self.query.SetFocus()

    def refresh(self):
        # os grupos ("Família, 4 pessoas") vêm antes, e escolher um põe todos de uma vez
        text = self.query.GetValue()
        self.found = [("group", g) for g in self.contacts.search_groups(text)] + \
                     [("contact", c) for c in self.contacts.search(text, limit=200)]
        self.list.Set([i18n.tr(group_label(item)) if kind == "group" else Contacts.display(item)
                       for kind, item in self.found])
        if self.found:
            self.list.SetSelection(0)

    def on_query_key(self, evt):
        # seta para baixo no campo de busca vai direto para a lista
        if evt.GetKeyCode() == wx.WXK_DOWN and self.found:
            self.list.SetFocus()
        else:
            evt.Skip()

    def on_ok(self, evt=None):
        i = self.list.GetSelection()
        if i == wx.NOT_FOUND or not self.found:
            text = self.query.GetValue().strip()
            if "@" in text:  # endereço digitado que ainda não está nos contatos
                self.chosen = self.chosen_name = text
                self.EndModal(wx.ID_OK)
            else:
                wx.Bell()
            return
        kind, item = self.found[i]
        self.chosen = self.contacts.group_text(item) if kind == "group" else Contacts.display(item)
        # o que a escrita fala: o nome do grupo, não a lista inteira de endereços
        self.chosen_name = item["name"] if kind == "group" else self.chosen
        self.EndModal(wx.ID_OK)


# ---------- respostas prontas ----------

class ReplyEditor(wx.Dialog):
    def __init__(self, parent, title_text="", body=""):
        super().__init__(parent, title=i18n.tr("Resposta pronta"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Nome da resposta")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.name = set_name(wx.TextCtrl(self, value=title_text), label)
        sizer.Add(self.name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        label = i18n.tr("Texto")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.body = set_name(wx.TextCtrl(self, value=body, style=wx.TE_MULTILINE), label)
        sizer.Add(self.body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Salvar", self.on_ok, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
        self.SetSizer(sizer)
        self.SetSize((560, 420))
        self.CentreOnParent()
        (self.body if title_text else self.name).SetFocus()

    def on_ok(self, evt):
        if not self.body.GetValue().strip():
            i18n.message_box("Escreva o texto da resposta.", "Aviso", wx.OK | wx.ICON_WARNING, self)
            self.body.SetFocus()
            return
        if not self.name.GetValue().strip():
            self.name.SetValue(self.body.GetValue().strip().splitlines()[0][:50])
        evt.Skip()

    def value(self):
        return {"title": self.name.GetValue().strip(), "text": self.body.GetValue()}


class QuickRepliesDialog(wx.Dialog):
    """Lista de respostas prontas. Enter insere a escolhida (self.chosen)."""

    def __init__(self, parent, replies, save, selection_text=""):
        super().__init__(parent, title=i18n.tr("Respostas prontas"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.replies = [dict(r) for r in replies]
        self.save = save
        self.selection_text = selection_text
        self.chosen = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Respostas prontas")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(-1, 220)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        label = i18n.tr("Texto da resposta")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.preview = set_name(wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY,
                                            size=(-1, 90)), label)
        sizer.Add(self.preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.insert_btn, self.new_btn, self.edit_btn, self.delete_btn, _ = _buttons(self, sizer, [
            ("Inserir", self.on_insert, wx.ID_OK), ("Nova resposta", self.on_new, wx.ID_ANY),
            ("Editar", self.on_edit, wx.ID_ANY), ("Apagar", self.on_delete, wx.ID_ANY),
            ("Fechar", None, wx.ID_CANCEL)])
        self.insert_btn.SetDefault()
        self.list.Bind(wx.EVT_LISTBOX, lambda e: self.show_preview())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_insert)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)
        self.SetSizer(sizer)
        self.SetSize((560, 480))
        self.CentreOnParent()
        self.refresh(0)
        (self.list if self.replies else self.new_btn).SetFocus()

    def refresh(self, select=None):
        self.list.Set([r["title"] for r in self.replies])
        if self.replies:
            self.list.SetSelection(min(select or 0, len(self.replies) - 1))
        for b in (self.insert_btn, self.edit_btn, self.delete_btn):
            b.Enable(bool(self.replies))
        self.show_preview()

    def show_preview(self):
        i = self.list.GetSelection()
        self.preview.SetValue(self.replies[i]["text"] if i != wx.NOT_FOUND and self.replies else "")

    def on_list_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_DELETE:
            self.on_delete()
        elif evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_insert()
        else:
            evt.Skip()

    def on_insert(self, evt=None):
        i = self.list.GetSelection()
        if i != wx.NOT_FOUND and self.replies:
            self.chosen = self.replies[i]["text"]
            self.EndModal(wx.ID_OK)

    def on_new(self, evt=None):
        dlg = ReplyEditor(self, body=self.selection_text)
        if dlg.ShowModal() == wx.ID_OK:
            self.replies.append(dlg.value())
            self.save(self.replies)
            self.refresh(len(self.replies) - 1)
            self.list.SetFocus()
        dlg.Destroy()

    def on_edit(self, evt=None):
        i = self.list.GetSelection()
        if i == wx.NOT_FOUND or not self.replies:
            return
        dlg = ReplyEditor(self, self.replies[i]["title"], self.replies[i]["text"])
        if dlg.ShowModal() == wx.ID_OK:
            self.replies[i] = dlg.value()
            self.save(self.replies)
            self.refresh(i)
            self.list.SetFocus()
        dlg.Destroy()

    def on_delete(self, evt=None):
        i = self.list.GetSelection()
        if i == wx.NOT_FOUND or not self.replies:
            return
        ask = i18n.message_box("Apagar a resposta pronta \"%s\"?" % self.replies[i]["title"],
                               "Confirmar", wx.YES_NO | wx.ICON_QUESTION, self)
        if ask == wx.YES:
            del self.replies[i]
            self.save(self.replies)
            self.refresh(i)
            (self.list if self.replies else self.new_btn).SetFocus()


# ---------- envio agendado ----------

def ask_schedule(parent, initial=None):
    """Pergunta dia e hora do envio. Devolve um datetime futuro ou None."""
    start = initial or (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(
        minute=0, second=0, microsecond=0)
    dlg = wx.Dialog(parent, title=i18n.tr("Agendar envio"))
    sizer = wx.BoxSizer(wx.VERTICAL)
    label = i18n.tr("Dia do envio")
    sizer.Add(wx.StaticText(dlg, label=label), 0, wx.LEFT | wx.TOP, 10)
    date = set_name(wx.adv.DatePickerCtrl(dlg, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY), label)
    date.SetValue(wx.DateTime.FromDMY(start.day, start.month - 1, start.year))
    sizer.Add(date, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
    row = wx.BoxSizer(wx.HORIZONTAL)
    hour = set_name(wx.SpinCtrl(dlg, min=0, max=23, initial=start.hour), i18n.tr("Hora"))
    minute = set_name(wx.SpinCtrl(dlg, min=0, max=59, initial=start.minute), i18n.tr("Minuto"))
    row.Add(wx.StaticText(dlg, label=i18n.tr("Hora")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    row.Add(hour, 0, wx.RIGHT, 12)
    row.Add(wx.StaticText(dlg, label=i18n.tr("Minuto")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    row.Add(minute)
    sizer.Add(row, 0, wx.ALL, 10)
    note = wx.StaticText(dlg, label=i18n.tr(
        "A mensagem sai no horário escolhido se o AudioMail estiver aberto (pode estar na bandeja). "
        "Se estiver fechado, ela sai assim que você abrir o programa."))
    note.Wrap(420)
    sizer.Add(note, 0, wx.LEFT | wx.RIGHT, 10)
    _buttons(dlg, sizer, [("Agendar", None, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
    dlg.SetSizerAndFit(sizer)
    dlg.CentreOnParent()
    date.SetFocus()
    result = None
    while dlg.ShowModal() == wx.ID_OK:
        d = date.GetValue()
        moment = datetime.datetime(d.GetYear(), d.GetMonth() + 1, d.GetDay(),
                                   hour.GetValue(), minute.GetValue())
        if moment > datetime.datetime.now():
            result = moment
            break
        i18n.message_box("Escolha uma data e hora futuras.", "Aviso", wx.OK | wx.ICON_WARNING, dlg)
    dlg.Destroy()
    return result


class ScheduledDialog(wx.Dialog):
    """Mensagens agendadas: enviar agora, editar ou cancelar. self.action = (ação, item)."""

    def __init__(self, parent, items):
        super().__init__(parent, title=i18n.tr("Mensagens agendadas"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.items = sorted(items, key=lambda it: it["when"])
        self.action = None
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Mensagens agendadas")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(-1, 260)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        buttons = _buttons(self, sizer, [
            ("Enviar agora", lambda e: self.finish("send"), wx.ID_ANY),
            ("Editar", lambda e: self.finish("edit"), wx.ID_ANY),
            ("Cancelar agendamento", lambda e: self.finish("cancel"), wx.ID_ANY),
            ("Fechar", None, wx.ID_CANCEL)])
        for b in buttons[:3]:
            b.Enable(bool(self.items))
        self.list.Set([describe_scheduled(it) for it in self.items])
        if self.items:
            self.list.SetSelection(0)
        else:
            self.list.Set([i18n.tr("Nenhuma mensagem agendada.")])
        self.SetSizer(sizer)
        self.SetSize((640, 420))
        self.CentreOnParent()
        self.list.SetFocus()

    def finish(self, action):
        i = self.list.GetSelection()
        if i == wx.NOT_FOUND or not self.items:
            return
        if action == "cancel":
            ask = i18n.message_box("Cancelar o envio desta mensagem? Ela volta para os rascunhos.",
                                   "Confirmar", wx.YES_NO | wx.ICON_QUESTION, self)
            if ask != wx.YES:
                return
        self.action = (action, self.items[i])
        self.EndModal(wx.ID_OK)


def describe_scheduled(item):
    when = datetime.datetime.fromtimestamp(item["when"]).strftime("%d/%m/%Y %H:%M")
    to = item.get("to") or item.get("cc") or item.get("bcc") or ""
    subject = item.get("subject") or i18n.tr("(sem assunto)")
    text = i18n.tr("%s, para %s: %s") % (when, to, subject)
    if item.get("account") and item.get("show_account"):
        text += " (%s)" % item["account"]
    if item.get("error"):
        text += " — " + i18n.tr("ainda não saiu: %s") % item["error"]
    return text
