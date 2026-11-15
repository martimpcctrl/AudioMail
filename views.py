"""A lista de mensagens como nos programas oficiais: várias selecionadas,
carregar as mais antigas, não lidas ao lado de cada pasta, prévia do texto,
marcadores do Gmail e busca avançada. MainFrame herda ViewsMixin.
"""
import threading
import time

import wx

import i18n
import mail_core as mc
import organize
import views_dialogs as vd
from common import save_config

PAGE = 100            # mensagens por vez
COUNTS_EVERY = 30     # segundos entre uma contagem de não lidas e outra


def folder_label(folder, counts):
    """O nome da pasta com as não lidas e o total, para o leitor de tela falar
    ao passar pelas pastas: 'Aba Social, 3 não lidas, 120 mensagens'."""
    name = i18n.tr(folder["display"])
    value = counts.get(folder["raw"])
    if value is None:
        return name
    unread, total = value if isinstance(value, tuple) else (value, None)
    parts = [name]
    if unread:
        parts.append(i18n.tr("1 não lida") if unread == 1 else i18n.tr("%d não lidas") % unread)
    if total is not None:
        parts.append(i18n.tr("1 mensagem") if total == 1 else i18n.tr("%d mensagens") % total)
    return ", ".join(parts)


def user_labels(folders):
    """Pastas que no Gmail são marcadores criados pela pessoa: [(servidor, nome)]."""
    out = []
    for f in folders:
        if organize.is_virtual(f) or f["raw"].upper() == "INBOX" or f["raw"].startswith("[Gmail]"):
            continue
        if any(flag in f["flags"] for flag in ("\\sent", "\\drafts", "\\trash", "\\junk", "\\all",
                                               "\\flagged", "\\archive", "\\important")):
            continue
        out.append((f["raw"], mc.decode_imap_utf7(f["raw"])))
    return out


def label_state(rows, labels):
    """Marcadores que todas as linhas têm e os que só algumas têm (nomes do servidor)."""
    names = {name: raw for raw, name in labels}
    sets = [set(r.get("labels") or []) for r in rows]
    every = set.intersection(*sets) if sets else set()
    some = set.union(*sets) if sets else set()
    return ({names[n] for n in every if n in names}, {names[n] for n in some - every if n in names})


def can_load_more(shown, total):
    return total > shown


class ViewsMixin:
    # ---------- várias selecionadas ----------
    def selected_rows(self):
        """[(índice, linha)] de todas as linhas selecionadas (ou a que tem o foco)."""
        out, i = [], self.list.GetFirstSelected()
        while i != -1:
            if i < len(self.view):
                out.append((i, self.view[i]))
            i = self.list.GetNextSelected(i)
        if not out:
            i = self.list.GetFocusedItem()
            if 0 <= i < len(self.view):
                out.append((i, self.view[i]))
        return out

    def focused_text(self):
        win = wx.Window.FindFocus()
        return win if isinstance(win, wx.TextCtrl) else None

    def select_all(self):
        text = self.focused_text()
        if text is not None:
            text.SelectAll()
            return
        if not self.view:
            return
        for i in range(len(self.view)):
            self.list.Select(i)
        self.list.SetFocus()
        self.announce(i18n.tr("%d mensagens selecionadas.") % len(self.view))

    def on_delete_key(self):
        """Delete apaga a mensagem; num campo de texto, apaga a letra."""
        text = self.focused_text()
        if text is None:
            self.delete_selected()
            return
        start, end = text.GetSelection()
        if start == end:
            end = start + 1
        text.Remove(start, end)

    def on_undo_key(self):
        text = self.focused_text()
        if text is not None:
            text.Undo()
        else:
            self.undo_action()

    # ---------- carregar mais ----------
    def on_list_key(self, evt):
        key = evt.GetKeyCode()
        acc = self.active
        if key in (wx.WXK_DOWN, wx.WXK_PAGEDOWN, wx.WXK_END) and acc and self.view \
                and not evt.ShiftDown() and self.list.GetFocusedItem() == len(self.view) - 1 \
                and can_load_more(len(self.messages), acc.total):
            self.load_more()
            return
        evt.Skip()

    def on_item_focused(self, evt):
        """Chegou na última mensagem da lista: carrega as mais antigas sozinho,
        como a rolagem infinita dos programas oficiais. (A lista do Windows nem
        sempre avisa a seta para baixo na última linha, mas sempre avisa o foco.)"""
        evt.Skip()
        acc = self.active
        if acc and self.view and evt.GetIndex() == len(self.view) - 1 and not acc.loading_more \
                and can_load_more(len(self.messages), acc.total):
            wx.CallAfter(self.load_more)

    def load_more(self):
        acc = self.active
        if not acc or not acc.client or acc.loading_more:
            return
        if not can_load_more(len(self.messages), acc.total):
            self.announce(i18n.tr("Não há mais mensagens nesta pasta. São %d.") % len(self.messages))
            return
        before = len(self.messages)
        acc.limit = max(acc.limit, before) + PAGE
        acc.loading_more = True
        self.announce("Carregando mais mensagens.")

        def after():
            acc.loading_more = False
            got = len(self.messages) - before
            if got <= 0:
                acc.total = len(self.messages)    # o servidor não tinha mais: não tenta de novo
            self.announce(i18n.tr("Mais %d mensagens carregadas. %d de %d.")
                          % (max(got, 0), len(self.messages), max(acc.total, len(self.messages))))

        self.refresh(after=after, failed=lambda: setattr(acc, "loading_more", False))

    # ---------- não lidas ao lado das pastas ----------
    def update_folder_labels(self, acc):
        if acc is not self.active or self.choice.GetCount() != len(acc.folders):
            return
        for i, f in enumerate(acc.folders):
            label = folder_label(f, acc.counts)
            if self.choice.GetString(i) != label:
                self.choice.SetString(i, label)

    def refresh_counts(self, acc, force=False):
        if not acc or not acc.client or acc.counting:
            return
        if not force and time.time() - acc.counts_at < COUNTS_EVERY:
            return
        acc.counting, acc.counts_at = True, time.time()
        client, folders = acc.client.side(), list(acc.folders)

        def work():
            try:
                counts = client.folder_counts(folders)
            except Exception:
                counts = None
            wx.CallAfter(done, counts)

        def done(counts):
            acc.counting = False
            if not self or counts is None:
                return
            acc.counts = counts
            self.update_folder_labels(acc)

        threading.Thread(target=work, daemon=True).start()

    # ---------- prévia ----------
    def preview_on(self):
        return bool(self.setting("show_preview"))

    def on_toggle_preview(self, evt=None):
        self.cfg["show_preview"] = self.preview_item.IsChecked()
        save_config(self.cfg)
        self.list.SetColumnWidth(3, 320 if self.preview_on() else 0)
        _, row = self.selected()
        self.render(row["uids"][0] if row else None)
        if self.preview_on():
            self.load_snippets(self.active)
        self.announce("Prévia do texto ligada." if self.preview_on() else "Prévia do texto desligada.")

    def snippet_for(self, acc, raw, row):
        if not self.preview_on() or not acc:
            return ""
        return acc.snippets.get((raw, row["uids"][0]), "")

    def load_snippets(self, acc):
        if not self.preview_on() or not acc or not acc.client or acc.loading_snippets:
            return
        raw = acc.current_raw
        missing = [m["uid"] for m in self.messages if (raw, m["uid"]) not in acc.snippets][:50]
        if not missing:
            return
        acc.loading_snippets = True
        client = acc.client.side()

        def work():
            found = client.snippets(raw, missing)
            wx.CallAfter(done, found)

        def done(found):
            acc.loading_snippets = False
            if not self:
                return
            for uid in missing:
                acc.snippets[(raw, uid)] = found.get(uid, "")
            if acc is self.active and raw == acc.current_raw:
                for i, row in enumerate(self.view):
                    if i < self.list.GetItemCount():
                        self.list.SetItem(i, 3, self.snippet_for(acc, raw, row))
                self.load_snippets(acc)   # o que sobrou além das primeiras 100

        threading.Thread(target=work, daemon=True).start()

    # ---------- marcadores do Gmail ----------
    def open_labels(self, rows=None):
        acc = self.active
        if not acc or not acc.client:
            return
        if not acc.client.gmail:
            self.announce("Marcadores só existem no Gmail. Use Mover para a pasta.", box=True)
            return
        rows = rows or [r for _, r in self.selected_rows()]
        if not rows:
            return
        labels = user_labels(acc.folders)
        every, some = label_state(rows, labels)
        dlg = vd.LabelsDialog(self, labels, every, some)
        ok = dlg.ShowModal() == wx.ID_OK
        add, remove, new = dlg.add, dlg.remove, dlg.new_names
        dlg.Destroy()
        self.list.SetFocus()
        if not ok or not (add or remove or new):
            return
        client, raw = acc.client, acc.current_raw
        uids = organize.OrganizeMixin._uids(rows)

        def work():
            created = [client.create_folder(n) for n in new]
            client.change_labels(raw, uids, add=add + created, remove=remove)
            return created

        def done(created):
            names = {r: mc.decode_imap_utf7(r) for r in add + remove + created}
            wanted = set(uids)
            for m in self.messages:
                if m["uid"] in wanted:
                    current = [n for n in (m.get("labels") or []) if n not in
                               {names[r] for r in remove}]
                    current += [names[r] for r in add + created if names[r] not in current]
                    m["labels"] = current
            if created:
                self.reload_folders(acc)
            if raw in remove and acc is self.active:
                self.messages = [m for m in self.messages if m["uid"] not in wanted]
            if acc is self.active:
                self.render(uids[0] if raw not in remove else None, focus=True)
            self.announce("Marcadores alterados.")

        self.run(work, done, "Mudando os marcadores")

    # ---------- busca avançada ----------
    def open_advanced_search(self, all_folders=False):
        if not self.active:
            return
        dlg = vd.AdvancedSearchDialog(self, self.search_box.GetValue(), all_folders)
        ok = dlg.ShowModal() == wx.ID_OK
        query, everywhere = dlg.query, dlg.all_folders
        dlg.Destroy()
        if not ok:
            self.list.SetFocus()
            return
        if everywhere:
            self.search_all(query)
            return
        self.search_box.SetValue(query)
        self.do_search()
