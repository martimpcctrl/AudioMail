"""Janelas para organizar os contatos: criar, corrigir, apagar e montar grupos."""
import wx

import i18n
from common import set_name
from compose_extras import _buttons
from contacts import Contacts, group_label


class ContactEditor(wx.Dialog):
    """Nome e endereço de um contato. self.name e self.addr no fim."""

    def __init__(self, parent, contacts, contact=None):
        super().__init__(parent, title=i18n.tr("Editar contato" if contact else "Novo contato"))
        self.contacts = contacts
        self.old = contact["addr"] if contact else ""
        sizer = wx.BoxSizer(wx.VERTICAL)

        def field(label, value):
            label = i18n.tr(label)
            sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
            ctrl = set_name(wx.TextCtrl(self, value=value, size=(360, -1)), label)
            sizer.Add(ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            return ctrl

        self.name_ctrl = field("Nome", contact["name"] if contact else "")
        self.addr_ctrl = field("E-mail", contact["addr"] if contact else "")
        ok, _ = _buttons(self, sizer, [("Salvar", self.on_ok, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
        ok.SetDefault()
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.name_ctrl.SetFocus()

    def on_ok(self, evt=None):
        err = self.contacts.set_contact(self.old, self.name_ctrl.GetValue(), self.addr_ctrl.GetValue())
        if err:
            i18n.message_box(err, "Contatos", wx.OK | wx.ICON_WARNING, self)
            self.addr_ctrl.SetFocus()
            return
        self.EndModal(wx.ID_OK)


class GroupEditor(wx.Dialog):
    """Nome do grupo e quem faz parte. Na lista, Espaço marca ou desmarca a pessoa."""

    def __init__(self, parent, contacts, group=None):
        super().__init__(parent, title=i18n.tr("Editar grupo" if group else "Novo grupo"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.contacts = contacts
        self.old = group["name"] if group else ""
        self.people = contacts.all_contacts()
        chosen = set(group["members"]) if group else set()
        known = {c["addr"].lower() for c in self.people}
        # quem está no grupo mas já não está nos contatos continua aparecendo
        for addr in sorted(chosen - known):
            self.people.append({"name": "", "addr": addr})
        self.checked = {c["addr"].lower(): c["addr"].lower() in chosen for c in self.people}
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Nome do grupo")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.name_ctrl = set_name(wx.TextCtrl(self, value=self.old, size=(420, -1)), label)
        sizer.Add(self.name_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        label = i18n.tr("Pessoas do grupo (Espaço marca ou desmarca)")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(420, 280)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Marcar ou desmarcar", self.on_toggle, wx.ID_ANY)])
        ok, _ = _buttons(self, sizer, [("Salvar", self.on_ok, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_toggle)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.refresh(0)
        self.name_ctrl.SetFocus()

    def text(self, c):
        shown = Contacts.display(c)
        return i18n.tr("%s, marcado") % shown if self.checked[c["addr"].lower()] \
            else i18n.tr("%s, não marcado") % shown

    def refresh(self, select=None):
        self.list.Set([self.text(c) for c in self.people] or
                      [i18n.tr("Nenhum contato ainda. Crie contatos antes de montar um grupo.")])
        if select is not None and self.list.GetCount():
            self.list.SetSelection(max(0, min(select, self.list.GetCount() - 1)))

    def on_toggle(self, evt=None):
        i = self.list.GetSelection()
        if not 0 <= i < len(self.people):
            return
        key = self.people[i]["addr"].lower()
        self.checked[key] = not self.checked[key]
        self.list.SetString(i, self.text(self.people[i]))

    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_SPACE:
            self.on_toggle()
            return
        evt.Skip()

    def on_ok(self, evt=None):
        members = [c["addr"] for c in self.people if self.checked[c["addr"].lower()]]
        err = self.contacts.set_group(self.old, self.name_ctrl.GetValue(), members)
        if err:
            i18n.message_box(err, "Contatos", wx.OK | wx.ICON_WARNING, self)
            return
        self.EndModal(wx.ID_OK)


class ContactsDialog(wx.Dialog):
    """Ferramentas > Contatos: a lista de contatos e a de grupos, cada uma com seus botões.
    Enter edita e Delete apaga o item da lista onde está o foco."""

    def __init__(self, parent, contacts, announce):
        super().__init__(parent, title=i18n.tr("Contatos"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.contacts = contacts
        self.announce = announce
        self.shown = []
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Buscar contato")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.query = set_name(wx.TextCtrl(self), label)
        sizer.Add(self.query, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        label = i18n.tr("Contatos")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.people = set_name(wx.ListBox(self, size=(480, 220)), label)
        sizer.Add(self.people, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Novo contato", self.on_new, wx.ID_ANY),
                               ("Editar contato", self.on_edit, wx.ID_ANY),
                               ("Apagar contato", self.on_delete, wx.ID_ANY)])
        label = i18n.tr("Grupos")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.group_list = set_name(wx.ListBox(self, size=(480, 110)), label)
        sizer.Add(self.group_list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Novo grupo", self.on_new_group, wx.ID_ANY),
                               ("Editar grupo", self.on_edit_group, wx.ID_ANY),
                               ("Apagar grupo", self.on_delete_group, wx.ID_ANY)])
        _buttons(self, sizer, [("Fechar", None, wx.ID_CANCEL)])
        self.query.Bind(wx.EVT_TEXT, lambda e: self.refresh())
        self.query.Bind(wx.EVT_KEY_DOWN, self.on_query_key)
        self.people.Bind(wx.EVT_KEY_DOWN, lambda e: self.on_list_key(e, self.on_edit, self.on_delete))
        self.people.Bind(wx.EVT_LISTBOX_DCLICK, self.on_edit)
        self.group_list.Bind(wx.EVT_KEY_DOWN,
                             lambda e: self.on_list_key(e, self.on_edit_group, self.on_delete_group))
        self.group_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_edit_group)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.refresh()
        self.refresh_groups()
        self.people.SetFocus()

    # ---- listas ----
    def refresh(self, select_addr=None):
        text = self.query.GetValue().strip()
        self.shown = self.contacts.search(text, limit=5000) if text else self.contacts.all_contacts()
        self.people.Set([Contacts.display(c) for c in self.shown] or [i18n.tr("Nenhum contato.")])
        index = 0
        if select_addr:
            index = next((i for i, c in enumerate(self.shown)
                          if c["addr"].lower() == select_addr.lower()), 0)
        if self.people.GetCount():
            self.people.SetSelection(min(index, self.people.GetCount() - 1))

    def refresh_groups(self, select_name=None):
        groups = self.contacts.groups
        self.group_list.Set([i18n.tr(group_label(g)) for g in groups] or
                            [i18n.tr("Nenhum grupo. Use o botão Novo grupo.")])
        index = 0
        if select_name:
            index = next((i for i, g in enumerate(groups) if g["name"] == select_name), 0)
        if self.group_list.GetCount():
            self.group_list.SetSelection(min(index, self.group_list.GetCount() - 1))

    def current(self):
        i = self.people.GetSelection()
        return self.shown[i] if 0 <= i < len(self.shown) else None

    def current_group(self):
        i = self.group_list.GetSelection()
        return self.contacts.groups[i] if 0 <= i < len(self.contacts.groups) else None

    def on_query_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_DOWN and self.shown:
            self.people.SetFocus()
        else:
            evt.Skip()

    @staticmethod
    def on_list_key(evt, edit, delete):
        code = evt.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            edit()
        elif code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            delete()
        else:
            evt.Skip()

    # ---- contatos ----
    def edit_contact(self, contact):
        dlg = ContactEditor(self, self.contacts, contact)
        ok = dlg.ShowModal() == wx.ID_OK
        addr = dlg.addr_ctrl.GetValue().strip()
        dlg.Destroy()
        if ok:
            self.contacts.save()
            self.refresh(addr)
            self.refresh_groups()
            self.announce("Contato salvo.")
        self.people.SetFocus()

    def on_new(self, evt=None):
        self.edit_contact(None)

    def on_edit(self, evt=None):
        contact = self.current()
        if contact is None:
            wx.Bell()
            return
        self.edit_contact(contact)

    def on_delete(self, evt=None):
        contact = self.current()
        if contact is None:
            wx.Bell()
            return
        answer = i18n.message_box(i18n.tr("Apagar o contato %s?") % Contacts.display(contact),
                                  "Contatos", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
        if answer == wx.YES:
            i = self.people.GetSelection()
            self.contacts.remove(contact["addr"])
            self.contacts.save()
            self.refresh()
            if self.shown:
                self.people.SetSelection(min(i, len(self.shown) - 1))
            self.refresh_groups()
            self.announce("Contato apagado.")
        self.people.SetFocus()

    # ---- grupos ----
    def edit_group(self, group):
        if not self.contacts.data and group is None:
            i18n.message_box("Nenhum contato ainda. Crie contatos antes de montar um grupo.",
                             "Contatos", wx.OK | wx.ICON_INFORMATION, self)
            return
        dlg = GroupEditor(self, self.contacts, group)
        ok = dlg.ShowModal() == wx.ID_OK
        name = dlg.name_ctrl.GetValue().strip()
        dlg.Destroy()
        if ok:
            self.contacts.save()
            self.refresh_groups(name)
            self.announce("Grupo salvo.")
        self.group_list.SetFocus()

    def on_new_group(self, evt=None):
        self.edit_group(None)

    def on_edit_group(self, evt=None):
        group = self.current_group()
        if group is None:
            wx.Bell()
            return
        self.edit_group(group)

    def on_delete_group(self, evt=None):
        group = self.current_group()
        if group is None:
            wx.Bell()
            return
        answer = i18n.message_box(i18n.tr("Apagar o grupo %s? Os contatos continuam na lista.")
                                  % group["name"], "Contatos",
                                  wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
        if answer == wx.YES:
            self.contacts.remove_group(group["name"])
            self.contacts.save()
            self.refresh_groups()
            self.announce("Grupo apagado.")
        self.group_list.SetFocus()
