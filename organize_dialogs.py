"""Janelas para organizar a caixa: mover para pasta, regras e remetentes bloqueados."""
import wx

import i18n
import rules as rl
import sounds
from common import pick_sound_file, set_name
from compose_extras import _buttons


def folder_label(folders, raw):
    for f in folders:
        if f["raw"] == raw:
            return f["display"]
    return raw


# ---------- mover ----------

class MoveDialog(wx.Dialog):
    """Escolhe a pasta de destino. self.chosen = pasta do servidor,
    ou self.new_name = nome de uma pasta nova para criar."""

    def __init__(self, parent, folders, current_raw, title="Mover para a pasta"):
        super().__init__(parent, title=i18n.tr(title),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.chosen = None
        self.new_name = None
        self.targets = [f for f in folders if f["raw"] != current_raw and "\\drafts" not in f["flags"]
                        and "\\all" not in f["flags"] and "\\flagged" not in f["flags"]]
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Pastas")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, choices=[f["display"] for f in self.targets],
                                        size=(-1, 260)), label)
        if self.targets:
            self.list.SetSelection(0)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Mover", self.on_ok, wx.ID_OK),
                               ("Nova pasta...", self.on_new, wx.ID_ANY),
                               ("Cancelar", None, wx.ID_CANCEL)])
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)
        self.SetSizerAndFit(sizer)
        self.SetSize((420, 420))
        self.CentreOnParent()
        self.list.SetFocus()

    def on_ok(self, evt=None):
        i = self.list.GetSelection()
        if i == wx.NOT_FOUND:
            return
        self.chosen = self.targets[i]["raw"]
        self.EndModal(wx.ID_OK)

    def on_new(self, evt=None):
        name = ask_text(self, "Nome da nova pasta", "Nova pasta")
        if name:
            self.new_name = name
            self.EndModal(wx.ID_OK)


def ask_text(parent, message, caption, value=""):
    dlg = wx.TextEntryDialog(parent, i18n.tr(message), i18n.tr(caption), value)
    text = dlg.GetValue().strip() if dlg.ShowModal() == wx.ID_OK else ""
    dlg.Destroy()
    return text


# ---------- regras ----------

def describe_rule(rule, folders):
    field, text, actions = rl.describe(rule, lambda raw: folder_label(folders, raw))
    shown = []
    for a in actions:
        if a.startswith("mover para "):
            shown.append(i18n.tr("mover para %s") % a[len("mover para "):])
        else:
            shown.append(i18n.tr(a))
    sentence = i18n.tr("Se %s contém %s: %s") % (i18n.tr(field), text, ", ".join(shown))
    if rule["name"]:
        sentence = rule["name"] + ". " + sentence
    if not rule["enabled"]:
        sentence += " " + i18n.tr("(desativada)")
    return sentence


class RuleEditor(wx.Dialog):
    """Cria ou edita uma regra. self.value() devolve a regra pronta."""

    def __init__(self, parent, folders, rule=None):
        super().__init__(parent, title=i18n.tr("Editar regra" if rule else "Nova regra"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.rule = rl.clean_rule(rule or {})
        self.folders = [f for f in folders if "\\drafts" not in f["flags"]
                        and "\\flagged" not in f["flags"] and f["raw"].upper() != "INBOX"]
        sizer = wx.BoxSizer(wx.VERTICAL)

        def labeled(text, control):
            sizer.Add(wx.StaticText(self, label=i18n.tr(text)), 0, wx.LEFT | wx.TOP, 10)
            set_name(control, i18n.tr(text))
            sizer.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
            return control

        self.name = labeled("Nome da regra (opcional)", wx.TextCtrl(self, value=self.rule["name"]))
        self.field = labeled("Quando o campo", wx.Choice(
            self, choices=[i18n.tr(label) for _, label in rl.FIELDS]))
        self.field.SetSelection(rl.FIELD_KEYS.index(self.rule["field"]))
        self.contains = labeled("Contém o texto", wx.TextCtrl(self, value=self.rule["contains"]))

        box = wx.StaticBoxSizer(wx.VERTICAL, self, i18n.tr("Fazer"))
        parent_box = box.GetStaticBox()
        self.move = wx.CheckBox(parent_box, label=i18n.tr("Mover para a pasta"))
        box.Add(self.move, 0, wx.ALL, 5)
        self.folder = set_name(wx.Choice(parent_box, choices=[f["display"] for f in self.folders]),
                               i18n.tr("Pasta de destino"))
        box.Add(self.folder, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self.read = wx.CheckBox(parent_box, label=i18n.tr("Marcar como lida"))
        self.star = wx.CheckBox(parent_box, label=i18n.tr("Pôr estrela"))
        self.delete = wx.CheckBox(parent_box, label=i18n.tr("Apagar (vai para a lixeira)"))
        self.play = wx.CheckBox(parent_box, label=i18n.tr("Tocar um som próprio ao chegar"))
        for c in (self.read, self.star, self.delete, self.play):
            box.Add(c, 0, wx.ALL, 5)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.pick = wx.Button(parent_box, label=i18n.tr("Escolher som..."))
        self.test = wx.Button(parent_box, label=i18n.tr("Testar som"))
        row.Add(self.pick, 0, wx.RIGHT, 8)
        row.Add(self.test, 0)
        box.Add(row, 0, wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 10)
        self.enabled = wx.CheckBox(self, label=i18n.tr("Regra ativa"))
        sizer.Add(self.enabled, 0, wx.LEFT | wx.RIGHT, 10)

        self.sound = self.rule["sound"]
        raws = [f["raw"] for f in self.folders]
        self.move.SetValue(bool(self.rule["folder"]))
        self.folder.SetSelection(raws.index(self.rule["folder"]) if self.rule["folder"] in raws
                                 else (0 if self.folders else wx.NOT_FOUND))
        self.read.SetValue(self.rule["read"])
        self.star.SetValue(self.rule["star"])
        self.delete.SetValue(self.rule["delete"])
        self.play.SetValue(bool(self.sound))
        self.enabled.SetValue(self.rule["enabled"])

        _buttons(self, sizer, [("Salvar", self.on_ok, wx.ID_OK), ("Cancelar", None, wx.ID_CANCEL)])
        for c in (self.move, self.delete, self.play):
            c.Bind(wx.EVT_CHECKBOX, self.sync)
        self.pick.Bind(wx.EVT_BUTTON, self.on_pick)
        self.test.Bind(wx.EVT_BUTTON, lambda e: self.sound and sounds.play(self.sound))
        self.sync()
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.contains.SetFocus()

    def sync(self, evt=None):
        if self.delete.GetValue():
            self.move.SetValue(False)
        self.move.Enable(not self.delete.GetValue() and bool(self.folders))
        self.folder.Enable(self.move.GetValue())
        self.pick.Enable(self.play.GetValue())
        self.test.Enable(self.play.GetValue() and bool(self.sound))
        if evt is not None and evt.GetEventObject() is self.play and self.play.GetValue() \
                and not self.sound:
            self.on_pick()

    def on_pick(self, evt=None):
        path = pick_sound_file(self)
        if path:
            self.sound = path
            sounds.play(path)
        elif not self.sound:
            self.play.SetValue(False)
        self.sync()

    def value(self):
        folder = ""
        i = self.folder.GetSelection()
        if self.move.GetValue() and i != wx.NOT_FOUND:
            folder = self.folders[i]["raw"]
        return rl.clean_rule({
            "id": self.rule["id"], "name": self.name.GetValue(),
            "field": rl.FIELD_KEYS[self.field.GetSelection()],
            "contains": self.contains.GetValue(), "folder": folder,
            "read": self.read.GetValue(), "star": self.star.GetValue(),
            "delete": self.delete.GetValue(),
            "sound": self.sound if self.play.GetValue() else "",
            "enabled": self.enabled.GetValue()})

    def on_ok(self, evt=None):
        rule = self.value()
        if not rule["contains"]:
            i18n.message_box("Escreva o texto que a regra deve procurar.", "Regra",
                             wx.OK | wx.ICON_WARNING, self)
            self.contains.SetFocus()
            return
        if not rl.has_action(rule):
            i18n.message_box("Marque pelo menos uma coisa para a regra fazer.", "Regra",
                             wx.OK | wx.ICON_WARNING, self)
            self.move.SetFocus()
            return
        self.EndModal(wx.ID_OK)


class RulesDialog(wx.Dialog):
    """Lista de regras. self.rules é a lista final; self.apply_now pede para
    aplicar as regras na caixa de entrada ao fechar."""

    def __init__(self, parent, rules, folders, new_rule=None):
        super().__init__(parent, title=i18n.tr("Regras"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.rules = [dict(r) for r in rules]
        self.folders = folders
        self.apply_now = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Regras, na ordem em que são testadas")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(560, 240)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.buttons = _buttons(self, sizer, [
            ("Nova regra", self.on_new, wx.ID_ANY), ("Editar", self.on_edit, wx.ID_ANY),
            ("Ativar ou desativar", self.on_toggle, wx.ID_ANY), ("Subir", lambda e: self.on_shift(-1), wx.ID_ANY),
            ("Descer", lambda e: self.on_shift(1), wx.ID_ANY), ("Apagar", self.on_delete, wx.ID_ANY)])
        _buttons(self, sizer, [("Aplicar agora na caixa de entrada", self.on_apply, wx.ID_ANY),
                               ("Salvar", lambda e: self.EndModal(wx.ID_OK), wx.ID_OK),
                               ("Cancelar", None, wx.ID_CANCEL)])
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_edit)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.refresh(0)
        self.list.SetFocus()
        if new_rule is not None:
            wx.CallAfter(self.on_new, None, new_rule)

    def refresh(self, select=None):
        self.list.Clear()
        if not self.rules:
            self.list.Append(i18n.tr("Nenhuma regra. Use o botão Nova regra."))
        for r in self.rules:
            self.list.Append(describe_rule(r, self.folders))
        if select is not None and self.list.GetCount():
            self.list.SetSelection(max(0, min(select, self.list.GetCount() - 1)))

    def current(self):
        i = self.list.GetSelection()
        return i if self.rules and 0 <= i < len(self.rules) else None

    def edit(self, rule=None, prefill=None):
        dlg = RuleEditor(self, self.folders, rule or prefill)
        if prefill is not None and rule is None:
            dlg.SetTitle(i18n.tr("Nova regra"))
        ok = dlg.ShowModal() == wx.ID_OK
        value = dlg.value() if ok else None
        dlg.Destroy()
        self.list.SetFocus()
        return value

    def on_new(self, evt=None, prefill=None):
        value = self.edit(prefill=prefill)
        if value:
            self.rules.append(value)
            self.refresh(len(self.rules) - 1)

    def on_edit(self, evt=None):
        i = self.current()
        if i is None:
            return
        value = self.edit(self.rules[i])
        if value:
            self.rules[i] = value
            self.refresh(i)

    def on_toggle(self, evt=None):
        i = self.current()
        if i is not None:
            self.rules[i]["enabled"] = not self.rules[i]["enabled"]
            self.refresh(i)

    def on_shift(self, step):
        i = self.current()
        if i is None or not 0 <= i + step < len(self.rules):
            return
        self.rules[i], self.rules[i + step] = self.rules[i + step], self.rules[i]
        self.refresh(i + step)

    def on_delete(self, evt=None):
        i = self.current()
        if i is None:
            return
        if i18n.message_box("Apagar esta regra?", "Regras", wx.YES_NO | wx.ICON_QUESTION,
                            self) == wx.YES:
            del self.rules[i]
            self.refresh(i)
        self.list.SetFocus()

    def on_apply(self, evt=None):
        self.apply_now = True
        self.EndModal(wx.ID_OK)

    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_DELETE:
            self.on_delete()
            return
        evt.Skip()


# ---------- bloqueados ----------

class BlockedDialog(wx.Dialog):
    """Lista de remetentes bloqueados, com Desbloquear. self.blocked é a lista final."""

    def __init__(self, parent, blocked):
        super().__init__(parent, title=i18n.tr("Remetentes bloqueados"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.blocked = list(blocked)
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = i18n.tr("Bloqueados (as mensagens deles vão direto para a lixeira)")
        sizer.Add(wx.StaticText(self, label=label), 0, wx.LEFT | wx.TOP, 10)
        self.list = set_name(wx.ListBox(self, size=(460, 240)), label)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        _buttons(self, sizer, [("Bloquear endereço ou domínio...", self.on_add, wx.ID_ANY),
                               ("Desbloquear", self.on_remove, wx.ID_ANY),
                               ("Fechar", lambda e: self.EndModal(wx.ID_OK), wx.ID_OK)])
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.refresh(0)
        self.list.SetFocus()

    def refresh(self, select=None):
        self.list.Clear()
        if not self.blocked:
            self.list.Append(i18n.tr("Nenhum remetente bloqueado."))
        for addr in self.blocked:
            self.list.Append(addr)
        if select is not None and self.list.GetCount():
            self.list.SetSelection(max(0, min(select, self.list.GetCount() - 1)))

    def on_add(self, evt=None):
        text = ask_text(self, "Endereço (fulano@site.com) ou domínio inteiro (@site.com)",
                        "Bloquear").lower()
        if not text:
            return
        if "@" not in text or " " in text:
            i18n.message_box("Isso não parece um endereço nem um domínio.", "Bloquear",
                             wx.OK | wx.ICON_WARNING, self)
            return
        if text not in self.blocked:
            self.blocked.append(text)
        self.refresh(self.blocked.index(text))

    def on_remove(self, evt=None):
        i = self.list.GetSelection()
        if not self.blocked or not 0 <= i < len(self.blocked):
            return
        del self.blocked[i]
        self.refresh(i)

    def on_key(self, evt):
        if evt.GetKeyCode() == wx.WXK_DELETE:
            self.on_remove()
            return
        evt.Skip()


def rule_from_message(row):
    """Regra começando pronta a partir da mensagem selecionada (remetente)."""
    addr = rl.sender_address(row.get("from_raw") or row.get("from"))
    return rl.new_rule(field="from", contains=addr or row.get("from", ""))
