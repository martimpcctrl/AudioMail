"""Organizar a caixa na janela principal: encaminhar, arquivar, mover, spam,
apagar com desfazer, estrela, regras automáticas e remetentes bloqueados.

MainFrame herda OrganizeMixin. Mover e apagar acontecem como no Gmail: a
mensagem some da lista na hora e o servidor só recebe a ordem depois do tempo
de desfazer (o mesmo do envio); Ctrl+Z traz de volta.
"""
import tempfile

import wx

import i18n
import mail_core as mc
import rules as rl
import organize_dialogs as od
from common import save_config

STARRED = "\x00flagged"     # pasta "Com estrela" de mentira, para servidores sem uma
GMAIL_TABS = [("category:primary", "Aba Principal"), ("category:promotions", "Aba Promoções"),
              ("category:social", "Aba Social"), ("category:updates", "Aba Atualizações"),
              ("category:forums", "Aba Fóruns")]


def is_virtual(folder):
    return "\\virtual" in folder["flags"]


def with_virtual(folders, gmail=False):
    """As pastas do servidor mais as de mentira, que buscam na caixa de entrada:
    as abas do Gmail logo depois dela e, se o servidor não tem pasta de estrela, a nossa."""
    out = list(folders)
    at = 1 if out and out[0]["raw"].upper() == "INBOX" else 0
    extra = []
    if gmail:
        extra = [{"raw": "\x00" + key, "flags": {"\\virtual"}, "display": name, "filter": key}
                 for key, name in GMAIL_TABS]
    if not any("\\flagged" in f["flags"] for f in folders):
        extra.append({"raw": STARRED, "flags": {"\\flagged", "\\virtual"}, "display": "Com estrela",
                      "filter": "flagged"})
    out[at:at] = extra
    return out


def with_starred(folders):
    return with_virtual(folders, False)


def real_folders(folders):
    return [f for f in folders if not is_virtual(f)]


def hidden_uids(pending, acc, raw):
    """UIDs que esperam o tempo de desfazer e não devem voltar para a lista."""
    gone = set()
    for item in pending:
        if item["acc"] is acc and item["raw"] == raw:
            gone.update(item["uids"])
    return gone


def save_attachments_temp(full):
    paths = []
    if full["attachments"]:
        folder = tempfile.mkdtemp(prefix="audiomail_")
        from dialogs import unique_path
        for att in full["attachments"]:
            path = unique_path(folder, att["name"])
            mc.save_attachment(att, path)
            paths.append(path)
    return paths


class OrganizeMixin:
    # ---------- pasta de estrela ----------
    def in_starred_view(self):
        acc = self.active
        return bool(acc and (acc.view_filter == "flagged" or self.folder_has("\\flagged")))

    def choose_folder(self, folder):
        """Troca de pasta; as de mentira (estrela, abas do Gmail) buscam na caixa de entrada."""
        acc = self.active
        acc.view_filter = folder.get("filter")
        acc.current_raw = "INBOX" if acc.view_filter else folder["raw"]
        acc.limit = 100

    def reload_folders(self, acc):
        if acc.client:
            acc.folders = with_virtual(acc.client.folders, acc.client.gmail)
            if acc is self.active:
                self.fill_folders(acc)

    # ---------- encaminhar ----------
    def forward_selected(self):
        i, row = self.selected()
        if row is None or not self.active:
            return
        client, raw, uid = self.active.client, self.active.current_raw, row["uids"][0]

        def work():
            full = client.fetch_message(raw, uid)
            return full, save_attachments_temp(full)

        self.run(work, lambda r: self.forward(*r), "Preparando o encaminhamento")

    def forward_full(self, full):
        self.run(lambda: save_attachments_temp(full), lambda paths: self.forward(full, paths),
                 "Preparando o encaminhamento")

    def forward(self, full, paths):
        parts = mc.build_forward(full)
        self.compose(subject=parts["subject"], body=parts["body"], attachments=paths)

    # ---------- mover, arquivar, spam, apagar ----------
    def stage(self, uids, action, done_text, raw=None):
        """Tira as mensagens da lista agora e manda a ação ao servidor depois do
        tempo de desfazer. ``action(client)`` roda numa thread."""
        acc = self.active
        raw = raw or acc.current_raw
        wanted = set(uids)
        picked = self.selected_rows()
        index = min(i for i, _ in picked) if picked else None
        removed = [m for m in self.messages if m["uid"] in wanted]
        self.messages = [m for m in self.messages if m["uid"] not in wanted]
        if raw == "INBOX" and not acc.search:
            self.note_inbox(acc, self.messages)
        self.render()
        if self.view and index is not None:
            self.select(min(index, len(self.view) - 1))
        self.list.SetFocus()
        item = {"acc": acc, "raw": raw, "uids": list(uids), "action": action,
                "removed": removed, "timer": None}
        seconds = int(self.setting("undo_send_seconds") or 0)
        if seconds > 0:
            item["timer"] = wx.CallLater(seconds * 1000, self.commit_staged, item)
            self.pending_moves.append(item)
            self.announce(i18n.tr(done_text) + " " + i18n.tr("Ctrl+Z desfaz."))
        else:
            self.pending_moves.append(item)
            self.commit_staged(item)
            self.announce(done_text)

    def commit_staged(self, item):
        if item not in self.pending_moves:
            return
        acc = item["acc"]
        if not acc.client:
            self.pending_moves.remove(item)
            return

        def finished(_=None):
            if item in self.pending_moves:
                self.pending_moves.remove(item)
            self.refresh_counts(acc, force=True)

        def failed(err):
            finished()
            i18n.message_box(str(err), "Erro", wx.OK | wx.ICON_ERROR, self)
            if acc is self.active:
                self.refresh()

        self.run(lambda: item["action"](acc.client), finished, "Atualizando", failed)

    def undo_action(self):
        waiting = [i for i in self.pending_moves if i["timer"] is not None and i["timer"].IsRunning()]
        if not waiting:
            self.announce("Não há nada para desfazer.")
            return
        item = waiting[-1]
        item["timer"].Stop()
        self.pending_moves.remove(item)
        acc = item["acc"]
        if acc is self.active and acc.current_raw == item["raw"]:
            back = {m["uid"] for m in self.messages}
            self.messages = sorted(self.messages + [m for m in item["removed"] if m["uid"] not in back],
                                   key=lambda m: int(m["uid"]), reverse=True)
            if item["raw"] == "INBOX" and not acc.search:
                self.note_inbox(acc, self.messages)
            self.render(item["uids"][0], focus=True)
        self.announce("Desfeito.")

    def flush_pending_moves(self):
        """Ao fechar, o que esperava o tempo de desfazer vai para o servidor na hora."""
        for item in list(self.pending_moves):
            if item["timer"] is not None:
                item["timer"].Stop()
            self.pending_moves.remove(item)
            if item["acc"].client:
                try:
                    item["action"](item["acc"].client)
                except Exception:
                    pass

    def _targets(self, rows=None):
        """Linhas em que a ação vale: as dadas, ou as selecionadas na lista."""
        if not self.active or not self.active.client:
            return []
        if rows is None:
            rows = [r for _, r in self.selected_rows()]
        return [r for r in rows if r is not None]

    @staticmethod
    def _uids(rows):
        out = []
        for r in rows:
            out.extend(u for u in r["uids"] if u not in out)
        return out

    @staticmethod
    def _done(rows, one, many):
        """Frase do resultado: ``one`` para uma linha, ``many`` (com %d) para várias."""
        return one if len(rows) == 1 else i18n.tr(many) % len(rows)

    def delete_selected(self, rows=None):
        rows = self._targets(rows)
        if not rows:
            return
        row = rows[0]
        raw, uids = self.active.current_raw, self._uids(rows)
        permanent = self.folder_has("\\trash")
        if permanent or int(self.setting("undo_send_seconds") or 0) <= 0:
            if len(rows) > 1:
                question = i18n.tr("Apagar as %d mensagens selecionadas?") % len(rows)
            elif row["count"] > 1:
                question = "Apagar a conversa com %d mensagens, assunto %s?" % (row["count"], row["subject"])
            else:
                question = "Apagar a mensagem de %s, assunto %s?" % (row["from"], row["subject"])
            if permanent:
                question += "\n\n" + i18n.tr("Ela está na lixeira, então vai embora de vez.")
            if i18n.message_box(question, "Confirmar", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
                self.list.SetFocus()
                return

        def action(client):
            for u in uids:
                client.delete(raw, u)

        one = "Apagada." if len(uids) == 1 else "Conversa apagada."
        self.stage(uids, action, self._done(rows, one, "%d mensagens apagadas."))

    def archive_selected(self, rows=None):
        rows = self._targets(rows)
        if not rows:
            return
        if self.folder_has("\\archive") or self.folder_has("\\all"):
            self.announce("Esta mensagem já está no arquivo.")
            return
        raw, uids = self.active.current_raw, self._uids(rows)
        self.stage(uids, lambda c: c.move(raw, uids, c.archive_folder()),
                   self._done(rows, "Arquivada.", "%d mensagens arquivadas."))

    def spam_selected(self, rows=None):
        rows = self._targets(rows)
        if not rows:
            return
        if self.folder_has("\\junk"):
            self.not_spam_selected(rows)
            return
        raw, uids = self.active.current_raw, self._uids(rows)

        def action(client):
            junk = client.junk_folder()
            if not junk:
                raise mc.MailError("Não encontrei a pasta de spam desta conta.")
            client.move(raw, uids, junk)

        self.stage(uids, action, self._done(rows, "Marcada como spam.", "%d mensagens marcadas como spam."))

    def not_spam_selected(self, rows):
        raw, uids = self.active.current_raw, self._uids(rows)
        self.stage(uids, lambda c: c.move(raw, uids, "INBOX"),
                   self._done(rows, "Não é spam. Voltou para a caixa de entrada.",
                              "%d mensagens voltaram para a caixa de entrada."))

    def move_selected(self, rows=None):
        rows = self._targets(rows)
        if not rows:
            return
        acc = self.active
        dlg = od.MoveDialog(self, real_folders(acc.folders), acc.current_raw)
        ok = dlg.ShowModal() == wx.ID_OK
        chosen, new_name = dlg.chosen, dlg.new_name
        dlg.Destroy()
        self.list.SetFocus()
        if not ok:
            return
        raw, uids = acc.current_raw, self._uids(rows)
        if new_name:
            def action(client):
                client.move(raw, uids, client.create_folder(new_name))
            label = new_name
            wx.CallLater(1500, self.reload_folders_later, acc)
        else:
            def action(client):
                client.move(raw, uids, chosen)
            label = od.folder_label(acc.folders, chosen)
        if len(rows) == 1:
            self.stage(uids, action, i18n.tr("Movida para %s.") % label)
        else:
            self.stage(uids, action, i18n.tr("%d mensagens movidas para %s.") % (len(rows), label))

    def reload_folders_later(self, acc):
        if not acc.client:
            return
        client = acc.client
        self.run(client.list_folders, lambda _: self.reload_folders(acc), "Atualizando as pastas",
                 lambda err: None)

    # ---------- estrela ----------
    def toggle_star_selected(self, rows=None):
        rows = self._targets(rows)
        if not rows:
            return
        acc = self.active
        raw, uids = acc.current_raw, self._uids(rows)
        flag = not all(r.get("flagged") for r in rows)
        picked = self.selected_rows()
        index = min(i for i, _ in picked) if picked else None

        def work():
            for u in uids:
                acc.client.set_flagged(raw, u, flag)

        def done(_):
            if acc is not self.active or raw != acc.current_raw:
                return
            wanted = set(uids)
            for m in self.messages:
                if m["uid"] in wanted:
                    m["flagged"] = flag
            if not flag and self.in_starred_view():
                self.messages = [m for m in self.messages if m["uid"] not in wanted]
                self.render()
                if self.view and index is not None:
                    self.select(min(index, len(self.view) - 1))
                self.list.SetFocus()
            else:
                self.render(uids[0])
            if len(rows) > 1:
                self.announce(i18n.tr("Estrela colocada em %d mensagens." if flag
                                      else "Estrela tirada de %d mensagens.") % len(rows))
            else:
                self.announce("Estrela colocada." if flag else "Estrela tirada.")

        self.run(work, done, "Atualizando")

    # ---------- bloquear ----------
    def block_selected(self, rows=None):
        _, row = self.selected()
        if row is None or not self.active or not self.active.client:
            return
        addr = rl.sender_address(row.get("from_raw") or row.get("from"))
        if not addr:
            self.announce("Não achei o endereço deste remetente.")
            return
        same = [m["uid"] for m in self.messages
                if rl.sender_address(m.get("from_raw") or m.get("from")) == addr]
        question = i18n.tr("Bloquear %s? As mensagens desse endereço vão direto para a lixeira, "
                           "sem aviso.") % addr
        if same:
            question += " " + i18n.tr("As %d desta pasta também vão.") % len(same)
        if i18n.message_box(question, "Bloquear remetente", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            self.list.SetFocus()
            return
        blocked = rl.load_blocked(self.cfg)
        if addr not in blocked:
            blocked.append(addr)
        self.cfg["blocked"] = blocked
        save_config(self.cfg)
        if not same or self.folder_has("\\trash"):
            self.announce(i18n.tr("%s bloqueado.") % addr)
            return
        raw = self.active.current_raw

        def action(client):
            for u in same:
                client.delete(raw, u)

        self.stage(same, action, i18n.tr("%s bloqueado.") % addr)

    def open_blocked(self):
        dlg = od.BlockedDialog(self, rl.load_blocked(self.cfg))
        dlg.ShowModal()
        self.cfg["blocked"] = dlg.blocked
        dlg.Destroy()
        save_config(self.cfg)
        self.list.SetFocus()

    # ---------- regras ----------
    def open_rules(self, from_selected=False):
        acc = self.active
        folders = real_folders(acc.folders if acc else [])
        prefill = None
        if from_selected:
            _, row = self.selected()
            if row is None:
                return
            prefill = od.rule_from_message(row)
        dlg = od.RulesDialog(self, rl.load_rules(self.cfg), folders, new_rule=prefill)
        ok = dlg.ShowModal() == wx.ID_OK
        new_rules, apply_now = dlg.rules, dlg.apply_now
        dlg.Destroy()
        self.list.SetFocus()
        if not ok:
            return
        self.cfg["rules"] = new_rules
        save_config(self.cfg)
        if apply_now:
            self.apply_rules_now()
        else:
            self.announce("Regras salvas.")

    def apply_rules_now(self):
        acc = self.active
        if not acc or not acc.client:
            return
        client = acc.client
        self.run(lambda: client.fetch_headers("INBOX"),
                 lambda msgs: self.apply_rules(acc, msgs, manual=True), "Aplicando as regras")

    def apply_rules(self, acc, msgs, manual=False):
        """Aplica regras e bloqueios nas mensagens da caixa de entrada.
        Devolve (uids que não devem avisar, {uid: som})."""
        plan = rl.plan(msgs, rl.load_rules(self.cfg), rl.load_blocked(self.cfg))
        if not rl.has_work(plan):
            if manual:
                self.announce("Nenhuma mensagem da caixa de entrada combina com as regras.")
            return plan["quiet"], plan["sounds"]
        client = acc.client
        touched = len({u for uids in plan["moves"].values() for u in uids}
                      | set(plan["read"]) | set(plan["star"]))

        def work():
            for u in plan["read"]:
                client.set_seen("INBOX", u, True)
            for u in plan["star"]:
                client.set_flagged("INBOX", u, True)
            for dest, uids in plan["moves"].items():
                target = client.trash_folder() if dest == "\\trash" else dest
                if not target or target == "INBOX":
                    for u in uids:
                        client.delete("INBOX", u)
                else:
                    client.move("INBOX", uids, target)

        def done(_):
            if manual:
                self.announce(i18n.tr("Regras aplicadas em %d mensagens.") % touched)
            if acc is self.active and acc.current_raw == "INBOX":
                self.refresh()
            else:
                self.check_account(acc)
            self.refresh_counts(acc, force=True)

        def failed(err):
            if manual:
                i18n.message_box(str(err), "Erro", wx.OK | wx.ICON_ERROR, self)

        self.run(work, done, "Aplicando as regras", failed)
        return plan["quiet"], plan["sounds"]
