"""Testes das mensagens guardadas no computador (ler sem internet), convites de
reunião, contatos e grupos, busca em todas as pastas, colar arquivos e imprimir
(sem rede e sem janelas). Rodar: python test_offline_convites.py"""
import datetime
import os
import shutil
import tempfile
import time
import unittest
from email.message import EmailMessage

import clipboard_files as cf
import contacts as ct
import invites
import local_store as ls
import mail_core as mc
import meetings
import offline
import settings_extras
import printing
import search_all

INVITE = (
    "BEGIN:VCALENDAR\r\nMETHOD:REQUEST\r\nBEGIN:VEVENT\r\n"
    "DTSTART:20261120T170000Z\r\nDTEND:20261120T180000Z\r\n"
    "SUMMARY:Reunião de equipe\\, semanal\r\nLOCATION:Sala 2\r\n"
    "ORGANIZER;CN=\"Carlos: TI\":mailto:carlos@x.com\r\n"
    "UID:abc123@google.com\r\nSEQUENCE:2\r\n"
    "ATTENDEE;PARTSTAT=NEEDS-ACTION:mailto:eu@y.com\r\n"
    "DESCRIPTION:uma linha muito comprida que foi dobrada\r\n  no meio\r\n"
    "END:VEVENT\r\nEND:VCALENDAR\r\n")


def xor(data):
    """Uma "criptografia" de teste: dá para ver que nada fica em texto puro."""
    return bytes(b ^ 0x5A for b in data)


class TempDir(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


# ---------- contatos e grupos ----------

class ContactsTest(TempDir):
    def make(self):
        return ct.Contacts(os.path.join(self.dir, "contatos.json"))

    def test_create_and_validate(self):
        c = self.make()
        self.assertIsNone(c.set_contact("", "Ana", "ana@x.com"))
        self.assertTrue(c.data["ana@x.com"]["manual"])
        self.assertEqual(c.set_contact("", "B", "sem-arroba"), "Informe um endereço de e-mail válido.")
        self.assertEqual(c.set_contact("", "Outra", "ANA@x.com"), "Já existe um contato com este endereço.")

    def test_rename_updates_groups_and_remove_cleans_them(self):
        c = self.make()
        c.set_contact("", "Ana", "ana@x.com")
        c.set_contact("", "Zé", "ze@y.com")
        self.assertIsNone(c.set_group("", "Família", ["ana@x.com", "ze@y.com"]))
        c.set_contact("ana@x.com", "Ana Paula", "anapaula@x.com")
        self.assertEqual(c.groups[0]["members"], ["anapaula@x.com", "ze@y.com"])
        self.assertEqual(c.group_text(c.groups[0]), "Ana Paula <anapaula@x.com>, Zé <ze@y.com>")
        c.remove("ze@y.com")
        self.assertEqual(c.groups[0]["members"], ["anapaula@x.com"])

    def test_group_errors_and_search(self):
        c = self.make()
        self.assertEqual(c.set_group("", "  ", ["a@x.com"]), "Dê um nome ao grupo.")
        self.assertEqual(c.set_group("", "Trabalho", []), "Escolha pelo menos uma pessoa para o grupo.")
        c.set_group("", "Trabalho", ["a@x.com"])
        self.assertEqual(c.set_group("", "trabalho", ["b@x.com"]), "Já existe um grupo com este nome.")
        self.assertIsNone(c.set_group("Trabalho", "Trabalho novo", ["b@x.com"]))
        self.assertEqual([g["name"] for g in c.search_groups("nov")], ["Trabalho novo"])
        self.assertEqual(ct.group_label(c.groups[0]), "Grupo Trabalho novo, 1 pessoa")
        c.remove_group("trabalho novo")
        self.assertEqual(c.groups, [])

    def test_save_and_load_keep_groups_and_manual(self):
        c = self.make()
        c.set_contact("", "Ana", "ana@x.com")
        c.set_group("", "Família", ["ana@x.com"])
        c.save()
        d = self.make()
        self.assertEqual(d.groups, [{"name": "Família", "members": ["ana@x.com"]}])
        self.assertTrue(d.data["ana@x.com"]["manual"])

    def test_display_keeps_accents_readable(self):
        self.assertEqual(ct.display_address("Zé", "ze@y.com"), "Zé <ze@y.com>")
        self.assertEqual(ct.display_address("Silva, Ana", "a@x.com"), '"Silva, Ana" <a@x.com>')
        self.assertEqual(ct.display_address("", "a@x.com"), "a@x.com")
        parsed = ct.parse_addresses('"Silva, Ana" <a@x.com>, Zé <ze@y.com>')
        self.assertEqual([a for _, a in parsed], ["a@x.com", "ze@y.com"])

    def test_manual_contacts_survive_trimming(self):
        old = ct.MAX_CONTACTS
        ct.MAX_CONTACTS = 2
        try:
            c = self.make()
            c.set_contact("", "Minha", "minha@x.com")
            for i in range(5):
                c.add("", "auto%d@x.com" % i, weight=10)
            c.save()
            self.assertIn("minha@x.com", self.make().data)
        finally:
            ct.MAX_CONTACTS = old


# ---------- colar arquivos e imprimir ----------

class PasteAndPrintTest(unittest.TestCase):
    def test_split_paths(self):
        folders = {"C:\\pasta"}
        new, dirs, repeated = cf.split_paths(
            ["C:\\a.txt", "C:\\pasta", "c:\\A.TXT", "C:\\b.pdf", "C:\\ja.doc"], ["C:\\ja.doc"],
            isdir=lambda p: p in folders)
        self.assertEqual(new, ["C:\\a.txt", "C:\\b.pdf"])
        self.assertEqual(dirs, ["C:\\pasta"])
        self.assertEqual(repeated, ["c:\\A.TXT", "C:\\ja.doc"])

    def test_add_paths_on_stub(self):
        said = []

        class Stub(cf.PasteFilesMixin):
            attach = []
            refreshed = None

            def refresh_attachments(self, select=None):
                self.refreshed = select

            def size_of(self, p):
                return 1000

            def announce(self, text, box=False):
                said.append(text)

        s = Stub()
        s.attach = []
        tmp = tempfile.mkdtemp()
        try:
            self.assertEqual(s.add_paths([os.path.join(tmp, "x.txt"), tmp]), 1)
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(s.refreshed, 0)
        self.assertTrue(said[0].startswith("1 anexos"))
        self.assertIn("Pastas não podem ser anexadas", said[1])

    def test_message_html_escapes(self):
        page = printing.message_html("<Oi>", "linha 1\nA & B <b>")
        self.assertIn("&lt;Oi&gt;", page)
        self.assertIn("linha 1<br>", page)
        self.assertIn("A &amp; B &lt;b&gt;", page)


# ---------- convites ----------

class InviteTest(unittest.TestCase):
    def test_parse(self):
        inv = invites.parse_ics(INVITE)
        self.assertEqual(inv["summary"], "Reunião de equipe, semanal")
        self.assertEqual(inv["organizer"], "carlos@x.com")
        self.assertEqual(inv["organizer_name"], "Carlos: TI")
        self.assertEqual(inv["method"], "REQUEST")
        expected = datetime.datetime(2026, 11, 20, 17, 0, tzinfo=datetime.timezone.utc).astimezone()
        self.assertEqual(inv["dtstart"], expected.replace(tzinfo=None))

    def test_all_day_and_unknown_zone(self):
        text = INVITE.replace("DTSTART:20261120T170000Z", "DTSTART;VALUE=DATE:20261120") \
                     .replace("DTEND:20261120T180000Z", "DTEND;TZID=Zona Inventada:20261121T090000")
        inv = invites.parse_ics(text)
        self.assertEqual(inv["dtstart"], datetime.date(2026, 11, 20))
        self.assertEqual(inv["dtend"], datetime.datetime(2026, 11, 21, 9, 0))
        self.assertIn("dia inteiro", invites.describe(inv))

    def test_no_event(self):
        self.assertIsNone(invites.parse_ics(""))
        self.assertIsNone(invites.parse_ics("BEGIN:VCALENDAR\nEND:VCALENDAR"))

    def test_describe_and_can_answer(self):
        inv = invites.parse_ics(INVITE)
        text = invites.describe(inv)
        self.assertTrue(text.startswith("Convite: Reunião de equipe, semanal, sexta-feira, 20/11/2026"))
        self.assertIn("local: Sala 2", text)
        self.assertIn("de: Carlos: TI", text)
        self.assertTrue(invites.can_answer(inv, "eu@y.com"))
        self.assertFalse(invites.can_answer(inv, "CARLOS@x.com"))
        cancel = invites.parse_ics(INVITE.replace("METHOD:REQUEST", "METHOD:CANCEL"))
        self.assertFalse(invites.can_answer(cancel, "eu@y.com"))
        self.assertTrue(invites.describe(cancel).startswith("Reunião cancelada"))

    def test_build_reply(self):
        inv = invites.parse_ics(INVITE)
        now = datetime.datetime(2026, 11, 15, 12, 0, tzinfo=datetime.timezone.utc)
        subject, body, ics = invites.build_reply(inv, "eu@y.com", "accept", "Eu", now=now)
        self.assertEqual(subject, "Aceito: Reunião de equipe, semanal")
        self.assertIn("Aceitei", body)
        self.assertIn("METHOD:REPLY\r\n", ics)
        self.assertIn("UID:abc123@google.com\r\n", ics)
        self.assertIn("SEQUENCE:2\r\n", ics)
        self.assertIn('ORGANIZER;CN="Carlos: TI":mailto:carlos@x.com', ics)
        self.assertIn('ATTENDEE;PARTSTAT=ACCEPTED;CN="Eu":mailto:eu@y.com', ics)
        self.assertIn("DTSTAMP:20261115T120000Z", ics)
        _, _, declined = invites.build_reply(inv, "eu@y.com", "decline")
        self.assertIn("PARTSTAT=DECLINED", declined)

    def test_fold_keeps_lines_short(self):
        folded = invites.fold("X" * 200)
        self.assertTrue(all(len(line) <= 74 for line in folded.split("\r\n")))
        self.assertEqual(invites.unfold(folded.replace("\r\n", "\n")), "X" * 200)

    def test_reminder(self):
        inv = invites.parse_ics(INVITE)
        r = invites.reminder_for(inv, now=datetime.datetime(2026, 11, 1))
        self.assertEqual(r["title"], "Reunião de equipe, semanal (Sala 2)")
        self.assertIsNone(invites.reminder_for(inv, now=datetime.datetime(2027, 1, 1)))
        items = []
        self.assertTrue(meetings.add_reminder(items, r))
        self.assertFalse(meetings.add_reminder(items, dict(r)))
        self.assertFalse(meetings.add_reminder(items, None))

    def test_found_in_email(self):
        msg = EmailMessage()
        msg["From"] = "carlos@x.com"
        msg["Subject"] = "Convite"
        msg.set_content("Você foi convidado")
        msg.add_alternative(INVITE, subtype="calendar", params={"method": "REQUEST"})
        full = mc.parse_full_message(msg.as_bytes(), "9")
        self.assertEqual(full["invite"]["uid"], "abc123@google.com")
        plain = EmailMessage()
        plain.set_content("nada")
        self.assertIsNone(mc.parse_full_message(plain.as_bytes(), "1")["invite"])

    def test_answer_invite_on_stub(self):
        sent, said = [], []

        class Client:
            def send_calendar_reply(self, to, subject, body, ics):
                sent.append((to, subject, ics))

        class Acc:
            email = "eu@y.com"
            client = Client()

        class Frame(meetings.MeetingMixin):
            cfg = {"reminders": []}

            def run(self, work, done, busy=None, on_error=None):
                done(work())

            def announce(self, text, box=False):
                said.append(text)

            def SetStatusText(self, text):
                pass

        frame = Frame()
        full = {"invite": invites.parse_ics(INVITE)}
        old = meetings.save_config
        meetings.save_config = lambda cfg: None
        try:
            frame.answer_invite(Acc(), full, "accept")
        finally:
            meetings.save_config = old
        self.assertEqual(sent[0][0], "carlos@x.com")
        if invites.reminder_for(full["invite"]):
            self.assertEqual(len(frame.cfg["reminders"]), 1)
            self.assertIn("Calendário", said[0])


# ---------- e-mail: conexão, resposta ao convite e busca em todas as pastas ----------

class MailCoreTest(unittest.TestCase):
    def test_offline_errors(self):
        self.assertTrue(mc.is_offline_error(mc.ConnectionFailed("x")))
        self.assertTrue(mc.is_offline_error(OSError("rede")))
        self.assertTrue(mc.is_offline_error(TimeoutError()))
        self.assertFalse(mc.is_offline_error(mc.MailError("senha errada")))
        self.assertTrue(issubclass(mc.ConnectionFailed, mc.MailError))

    def test_send_calendar_reply_builds_both_parts(self):
        stub = mc.MailClient.__new__(mc.MailClient)
        stub.email = "eu@y.com"
        got = []
        stub._deliver = lambda msg, rcpts: got.append((msg, rcpts))
        mc.MailClient.send_calendar_reply(stub, "carlos@x.com", "Aceito: X", "Aceitei.", "BEGIN:VCALENDAR\r\n")
        msg, rcpts = got[0]
        self.assertEqual(rcpts, ["carlos@x.com"])
        types = [p.get_content_type() for p in msg.walk()]
        self.assertIn("text/calendar", types)
        cal = next(p for p in msg.walk() if p.get_content_type() == "text/calendar")
        self.assertEqual(cal.get_param("method"), "REPLY")

    def test_count_matches(self):
        stub = mc.MailClient.__new__(mc.MailClient)
        totals = {"INBOX": 4, "Arquivo": 0, "Enviados": 2}

        def search_query(raw, query, limit=100, view_filter=None):
            if raw == "Erro":
                raise mc.MailError("x")
            return [], totals.get(raw, 0)

        stub.search_query = search_query
        folders = [{"raw": "INBOX", "flags": []}, {"raw": "Arquivo", "flags": []},
                   {"raw": "[Gmail]/Todos", "flags": ["\\all"]}, {"raw": "Erro", "flags": []},
                   {"raw": "INBOX", "filter": "flagged", "flags": []}, {"raw": "Enviados", "flags": []}]
        found = mc.MailClient.count_matches(stub, folders, "boleto")
        self.assertEqual([(f["raw"], n) for f, n in found], [("INBOX", 4), ("Enviados", 2)])

    def test_header_has_time(self):
        data = [(b"1 (UID 7 FLAGS (\\Seen) BODY[HEADER] {10}",
                 b"From: a@b.com\r\nSubject: Oi\r\nDate: Sun, 15 Nov 2026 10:00:00 -0300\r\n\r\n")]
        msg = mc.parse_header_fetch(data)[0]
        self.assertGreater(msg["ts"], 0)


class SearchAllTest(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(search_all.result_label("Caixa de entrada", 1), "Caixa de entrada: 1 resultado")
        self.assertEqual(search_all.result_label("Arquivo", 12), "Arquivo: 12 resultados")
        self.assertEqual(search_all.summary([]), "Nada encontrado em nenhuma pasta.")
        self.assertEqual(search_all.summary([({}, 1)]), "1 resultado em 1 pasta.")
        self.assertEqual(search_all.summary([({}, 4), ({}, 2)]), "6 resultados em 2 pastas.")


# ---------- mensagens guardadas no computador ----------

RAW = (b"From: Ana <a@b.com>\r\nTo: eu@y.com\r\nSubject: Ola\r\n"
       b"Date: Sun, 15 Nov 2026 10:00:00 -0300\r\n\r\ncorpo secreto aqui\r\n")


def with_attachment():
    msg = EmailMessage()
    msg["From"] = "a@b.com"
    msg["Subject"] = "Com anexo"
    msg["Date"] = "Sun, 15 Nov 2026 10:00:00 -0300"
    msg.set_content("veja o anexo")
    msg.add_attachment(b"x" * 5000, maintype="application", subtype="pdf", filename="nota.pdf")
    return msg.as_bytes()


class LocalStoreTest(TempDir):
    def store(self):
        return ls.LocalStore(os.path.join(self.dir, "mensagens.db"), xor, xor)

    def test_merge_lists(self):
        old = [{"uid": "9"}, {"uid": "5"}, {"uid": "2"}, {"uid": "1"}]
        new = [{"uid": "10"}, {"uid": "9"}, {"uid": "3"}]
        # 5 sumiu do trecho que a lista nova cobre (de 3 para cima): foi apagada; 2 e 1 ficam
        self.assertEqual([m["uid"] for m in ls.merge_lists(old, new)], ["10", "9", "3", "2", "1"])
        self.assertEqual(ls.merge_lists(old, [], keep=2), old[:2])
        self.assertEqual(len(ls.merge_lists([], [{"uid": str(i)} for i in range(10)], keep=3)), 3)

    def test_folders_and_lists(self):
        s = self.store()
        self.assertEqual(s.folders("a@x.com"), {})
        s.save_folders("A@x.com", {"folders": [{"raw": "INBOX", "flags": {"\\inbox"}}], "gmail": True})
        self.assertEqual(s.folders("a@x.com")["folders"][0]["flags"], ["\\inbox"])
        s.save_list("a@x.com", ls.folder_key("INBOX"), [{"uid": "5", "subject": "Oi", "from": "Ana"}])
        s.save_list("a@x.com", ls.folder_key("INBOX", "flagged"), [{"uid": "1", "subject": "Estrela"}])
        self.assertEqual([m["uid"] for m in s.list("a@x.com", "INBOX")], ["5"])
        self.assertEqual([m["uid"] for m in s.list("a@x.com", "\x00flagged")], ["1"])
        self.assertEqual(s.list("outra@x.com", "INBOX"), [])

    def test_message_roundtrip_is_encrypted(self):
        s = self.store()
        full = mc.parse_full_message(RAW, "5")
        s.save_message("a@x.com", "INBOX", "5", full, RAW)
        s.close()
        with open(os.path.join(self.dir, "mensagens.db"), "rb") as f:
            self.assertNotIn(b"secreto", f.read())
        back = self.store().message("a@x.com", "INBOX", "5")
        self.assertEqual(back["body"], "corpo secreto aqui")
        self.assertTrue(self.store().has_message("a@x.com", "INBOX", "5"))
        self.assertIsNone(self.store().message("a@x.com", "INBOX", "6"))

    def test_message_without_raw_lists_missing_attachments(self):
        s = self.store()
        full = mc.parse_full_message(with_attachment(), "8")
        s.save_message("a@x.com", "INBOX", "8", full)
        back = s.message("a@x.com", "INBOX", "8")
        self.assertEqual(back["attachments"], [])
        self.assertIn("nota.pdf", back["body"])
        self.assertIn("não foram guardados", back["body"])
        s.save_message("a@x.com", "INBOX", "8", full, with_attachment())
        self.assertEqual(s.message("a@x.com", "INBOX", "8")["attachments"][0]["name"], "nota.pdf")

    def test_search_looks_in_opened_text(self):
        s = self.store()
        s.save_list("a@x.com", "INBOX", [{"uid": "5", "subject": "Ola", "from_raw": "Ana <a@b.com>"},
                                         {"uid": "4", "subject": "Boleto", "from_raw": "Banco"}])
        s.save_message("a@x.com", "INBOX", "5", mc.parse_full_message(RAW, "5"))
        self.assertEqual([m["uid"] for m in s.search("a@x.com", "INBOX", "INBOX", "secreto")], ["5"])
        self.assertEqual([m["uid"] for m in s.search("a@x.com", "INBOX", "INBOX", "boleto")], ["4"])
        self.assertEqual(len(s.search("a@x.com", "INBOX", "INBOX", "")), 2)

    def test_prune_forget_and_clear(self):
        s = self.store()
        now = time.time()
        s.save_list("a@x.com", "INBOX", [{"uid": "2", "ts": now}, {"uid": "1", "ts": now - 200 * 86400}])
        old = dict(mc.parse_full_message(RAW, "1"), ts=now - 200 * 86400)
        s.save_message("a@x.com", "INBOX", "1", old)
        s.prune(90, now=now)
        self.assertEqual([m["uid"] for m in s.list("a@x.com", "INBOX")], ["2"])
        self.assertIsNone(s.message("a@x.com", "INBOX", "1"))
        s.forget_account("A@X.COM")
        self.assertEqual(s.list("a@x.com", "INBOX"), [])
        s.clear()
        self.assertFalse(os.path.exists(os.path.join(self.dir, "mensagens.db")))


class OfflineMixinTest(TempDir):
    def frame(self, settings=None):
        store = ls.LocalStore(os.path.join(self.dir, "mensagens.db"), xor, xor)
        values = {"offline_enabled": True, "offline_attachments": False}
        values.update(settings or {})

        class Frame(offline.OfflineMixin):
            _store = store

            def setting(self, key):
                return values[key]

        return Frame(), store

    def test_fetch_list_saves_and_falls_back(self):
        frame, store = self.frame()

        class Online:
            def fetch_headers(self, raw, limit=100, with_total=False):
                return [{"uid": "3", "subject": "Oi"}], 10

        class Offline:
            def fetch_headers(self, *args, **kwargs):
                raise mc.ConnectionFailed("sem rede")

            search_query = fetch_headers

        self.assertEqual(frame.fetch_list("a@x.com", Online(), "INBOX", "", None, 100),
                         ([{"uid": "3", "subject": "Oi"}], 10, False))
        # sem nada de pastas guardado: o erro continua aparecendo
        with self.assertRaises(mc.ConnectionFailed):
            frame.fetch_list("a@x.com", Offline(), "Outra", "", None, 100)
        store.save_folders("a@x.com", {"folders": [{"raw": "INBOX", "flags": []}], "gmail": False})
        msgs, total, off = frame.fetch_list("a@x.com", Offline(), "INBOX", "", None, 100)
        self.assertEqual((msgs[0]["uid"], total, off), ("3", 1, True))
        msgs, _, _ = frame.fetch_list("a@x.com", Offline(), "INBOX", "oi", None, 100)
        self.assertEqual(len(msgs), 1)

    def test_wrong_password_is_not_hidden(self):
        frame, store = self.frame()
        store.save_folders("a@x.com", {"folders": [{"raw": "INBOX", "flags": []}]})

        class Refused:
            def fetch_headers(self, raw, limit=100, with_total=False):
                raise mc.MailError("O servidor recusou")

        with self.assertRaises(mc.MailError):
            frame.fetch_list("a@x.com", Refused(), "INBOX", "", None, 100)

    def test_fetch_full_saves_and_falls_back(self):
        frame, store = self.frame()

        class Online:
            def fetch_raw(self, raw, uid):
                return RAW if uid == "5" else with_attachment()

        class Offline:
            def fetch_raw(self, raw, uid):
                raise OSError("sem rede")

        self.assertEqual(frame.fetch_full("a@x.com", Online(), "INBOX", "5")["body"], "corpo secreto aqui")
        frame.fetch_full("a@x.com", Online(), "INBOX", "8")
        back = frame.fetch_full("a@x.com", Offline(), "INBOX", "5")
        self.assertTrue(back["offline"])
        # com anexo e a opção desligada, só o texto fica guardado
        self.assertEqual(frame.fetch_full("a@x.com", Offline(), "INBOX", "8")["attachments"], [])
        with self.assertRaises(mc.MailError) as e:
            frame.fetch_full("a@x.com", Offline(), "INBOX", "99")
        self.assertIn("ainda não foi guardada", str(e.exception))

    def test_disabled_does_nothing(self):
        frame, store = self.frame({"offline_enabled": False})
        self.assertIsNone(frame.store)

        class Offline:
            def fetch_raw(self, raw, uid):
                raise OSError("sem rede")

        with self.assertRaises(OSError):
            frame.fetch_full("a@x.com", Offline(), "INBOX", "5")
        self.assertFalse(frame.start_offline({"email": "a@x.com"}, None, OSError()))

    def test_days_label(self):
        self.assertEqual(settings_extras.days_label(0), "Sem limite")
        self.assertEqual(settings_extras.days_label(90), "Últimos 90 dias")


if __name__ == "__main__":
    unittest.main()
