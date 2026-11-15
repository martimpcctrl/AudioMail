"""Testes de encaminhar, mover, estrela, regras e bloqueio (sem rede e sem janelas).
Rodar: python test_organizar.py"""
import threading
import unittest

import mail_core as mc
import rules as rl


def msg(uid, sender="Loja <ofertas@loja.com>", subject="Promoção", to="eu@x.com", unread=True):
    return {"uid": str(uid), "from_raw": sender, "from": mc.short_sender(sender),
            "to_raw": to, "subject": subject, "unread": unread}


class Regras(unittest.TestCase):
    def test_mover_e_marcar_como_lida(self):
        rule = rl.new_rule(field="from", contains="loja.com", folder="Ofertas", read=True)
        p = rl.plan([msg(1), msg(2, sender="ana@x.com")], [rule], [])
        self.assertEqual(p["moves"], {"Ofertas": ["1"]})
        self.assertEqual(p["read"], ["1"])
        self.assertEqual(p["quiet"], {"1"})

    def test_assunto_sem_diferenca_de_maiusculas(self):
        rule = rl.new_rule(field="subject", contains="FATURA", star=True)
        p = rl.plan([msg(1, subject="Sua fatura chegou")], [rule], [])
        self.assertEqual(p["star"], ["1"])
        self.assertEqual(p["quiet"], set())   # só estrela: continua avisando

    def test_a_primeira_regra_que_move_vale(self):
        a = rl.new_rule(contains="loja", folder="A")
        b = rl.new_rule(contains="loja", folder="B", star=True)
        p = rl.plan([msg(1)], [a, b], [])
        self.assertEqual(p["moves"], {"A": ["1"]})
        self.assertEqual(p["star"], ["1"])

    def test_apagar_vai_para_a_lixeira(self):
        rule = rl.new_rule(contains="loja", delete=True, folder="X")
        self.assertEqual(rule["folder"], "")
        p = rl.plan([msg(1)], [rule], [])
        self.assertEqual(p["moves"], {"\\trash": ["1"]})

    def test_som_proprio(self):
        rule = rl.new_rule(field="from", contains="chefe@", sound="C:/sons/chefe.wav")
        p = rl.plan([msg(5, sender="Chefe <chefe@empresa.com>")], [rule], [])
        self.assertEqual(p["sounds"], {"5": "C:/sons/chefe.wav"})
        self.assertFalse(rl.has_work(p))

    def test_destinatario(self):
        rule = rl.new_rule(field="to", contains="lista@grupo.org", read=True)
        p = rl.plan([msg(1, to="lista@grupo.org")], [rule], [])
        self.assertEqual(p["read"], ["1"])

    def test_desativada_vazia_ou_sem_acao_nao_faz_nada(self):
        rules = [rl.new_rule(contains="loja", read=True, enabled=False),
                 rl.new_rule(contains="", read=True), rl.new_rule(contains="loja")]
        p = rl.plan([msg(1)], rules, [])
        self.assertFalse(rl.has_work(p))

    def test_arquivo_estranho_nao_derruba(self):
        cfg = {"rules": [{"field": "xyz", "contains": "a", "read": 1}, "lixo", None]}
        rules = rl.load_rules(cfg)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["field"], "from")
        self.assertTrue(rules[0]["read"])

    def test_descricao(self):
        rule = rl.new_rule(field="from", contains="loja", folder="raw", read=True)
        field, text, actions = rl.describe(rule, lambda raw: "Ofertas")
        self.assertEqual((field, text), ("remetente", "loja"))
        self.assertEqual(actions, ["mover para Ofertas", "marcar como lida"])


class Bloqueio(unittest.TestCase):
    def test_endereco_e_dominio(self):
        blocked = rl.load_blocked({"blocked": ["Chato@X.com", "@spam.net", "lixo", "chato@x.com"]})
        self.assertEqual(blocked, ["chato@x.com", "@spam.net"])
        self.assertTrue(rl.is_blocked(msg(1, sender="Fulano <CHATO@x.com>"), blocked))
        self.assertTrue(rl.is_blocked(msg(2, sender="a@spam.net"), blocked))
        self.assertFalse(rl.is_blocked(msg(3, sender="a@x.com"), blocked))

    def test_bloqueado_vence_as_regras_e_nao_avisa(self):
        rule = rl.new_rule(contains="spam.net", folder="Pasta", star=True)
        p = rl.plan([msg(1, sender="a@spam.net")], [rule], ["@spam.net"])
        self.assertEqual(p["moves"], {"\\trash": ["1"]})
        self.assertEqual(p["star"], [])
        self.assertEqual(p["blocked"], 1)
        self.assertEqual(p["quiet"], {"1"})


class Encaminhar(unittest.TestCase):
    full = {"from": "Ana <ana@x.com>", "date": "10/11/2026 14:00", "subject": "Relatório",
            "to": "eu@x.com", "cc": "", "body": "Segue o relatório."}

    def test_assunto_e_cabecalho(self):
        out = mc.build_forward(self.full)
        self.assertEqual(out["subject"], "Enc: Relatório")
        self.assertIn("Mensagem encaminhada", out["body"])
        self.assertIn("De: Ana <ana@x.com>", out["body"])
        self.assertTrue(out["body"].rstrip().endswith("Segue o relatório."))
        self.assertNotIn("Cópia:", out["body"])

    def test_nao_repete_o_prefixo(self):
        for s in ("Enc: Oi", "FWD: Oi", "Fw: Oi", "RV: Oi"):
            self.assertEqual(mc.build_forward(dict(self.full, subject=s))["subject"], s)


class Lista(unittest.TestCase):
    def test_estado(self):
        self.assertEqual(mc.state_text({"unread": True, "flagged": True}), "Não lida, Com estrela")
        self.assertEqual(mc.state_text({"unread": False, "flagged": False}), "")

    def test_cabecalho_traz_estrela_e_para(self):
        data = [(b'1 (UID 42 FLAGS (\\Seen \\Flagged) BODY[HEADER.FIELDS (FROM TO SUBJECT DATE)] {60}',
                 b"From: Ana <ana@x.com>\r\nTo: eu@x.com\r\nSubject: Oi\r\n\r\n"), b")"]
        m = mc.parse_header_fetch(data)[0]
        self.assertTrue(m["flagged"])
        self.assertFalse(m["unread"])
        self.assertEqual(m["to_raw"], "eu@x.com")
        row = mc.build_rows([m], False)[0]
        self.assertTrue(row["flagged"])
        self.assertEqual(row["from_raw"], "Ana <ana@x.com>")

    def test_nome_de_pasta_com_acento_vai_e_volta(self):
        for name in ("Notas fiscais", "Ofertas & cupons", "Família", "Trabalho/Relatórios"):
            encoded = mc.encode_imap_utf7(name)
            self.assertTrue(all(32 <= ord(c) < 127 for c in encoded), encoded)
            self.assertEqual(mc.decode_imap_utf7(encoded), name)
        self.assertEqual(mc.encode_imap_utf7("Família"), "Fam&AO0-lia")


class FakeIMAP:
    def __init__(self, move_ok=True):
        self.calls = []
        self.move_ok = move_ok

    def noop(self):
        return "OK", []

    def select(self, name):
        self.calls.append(("SELECT", name))
        return "OK", [b"1"]

    def uid(self, *args):
        self.calls.append(args)
        if args[0] == "MOVE" and not self.move_ok:
            return "NO", []
        return "OK", []

    def expunge(self):
        self.calls.append(("EXPUNGE",))
        return "OK", []


def client(imap, can_move):
    c = mc.MailClient.__new__(mc.MailClient)
    c.imap, c.selected, c.lock, c.can_move = imap, None, threading.RLock(), can_move
    c.folders, c.gmail = [], False
    return c


class Mover(unittest.TestCase):
    def test_usa_move_quando_o_servidor_tem(self):
        imap = FakeIMAP()
        client(imap, True).move("INBOX", ["3", "4"], "Ofertas")
        self.assertIn(("MOVE", "3,4", '"Ofertas"'), imap.calls)
        self.assertNotIn(("EXPUNGE",), imap.calls)

    def test_sem_move_copia_e_apaga(self):
        imap = FakeIMAP()
        client(imap, False).move("INBOX", ["3"], "Ofertas")
        self.assertIn(("COPY", "3", '"Ofertas"'), imap.calls)
        self.assertIn(("STORE", "3", "+FLAGS", "(\\Deleted)"), imap.calls)
        self.assertIn(("EXPUNGE",), imap.calls)

    def test_move_recusado_cai_para_copia(self):
        imap = FakeIMAP(move_ok=False)
        client(imap, True).move("INBOX", ["3"], "Ofertas")
        self.assertIn(("COPY", "3", '"Ofertas"'), imap.calls)

    def test_mesma_pasta_nao_faz_nada(self):
        imap = FakeIMAP()
        client(imap, True).move("INBOX", ["3"], "INBOX")
        self.assertEqual(imap.calls, [])

    def test_estrela(self):
        imap = FakeIMAP()
        client(imap, True).set_flagged("INBOX", "9", False)
        self.assertIn(("STORE", "9", "-FLAGS", "(\\Flagged)"), imap.calls)

    def test_pastas_especiais(self):
        c = client(FakeIMAP(), True)
        c.folders = [{"raw": "INBOX", "flags": set()}, {"raw": "[Gmail]/Spam", "flags": {"\\junk"}},
                     {"raw": "[Gmail]/Todos os e-mails", "flags": {"\\all"}}]
        self.assertEqual(c.junk_folder(), "[Gmail]/Spam")
        self.assertIsNone(c.archive_folder(create=False))
        c.gmail = True
        self.assertEqual(c.archive_folder(create=False), "[Gmail]/Todos os e-mails")

    def test_busca_so_com_estrela(self):
        imap = FakeIMAP()
        imap.uid = lambda *a: (imap.calls.append(a), ("OK", [b""]))[1]
        client(imap, True).search("INBOX", "", flagged=True)
        self.assertIn(("SEARCH", None, "FLAGGED"), imap.calls)


class PastaDeEstrela(unittest.TestCase):
    def test_so_entra_se_o_servidor_nao_tiver(self):
        import organize
        inbox = {"raw": "INBOX", "flags": set(), "display": "Caixa de entrada"}
        sent = {"raw": "Sent", "flags": {"\\sent"}, "display": "Enviados"}
        out = organize.with_starred([inbox, sent])
        self.assertEqual(out[1]["raw"], organize.STARRED)
        gmail = [inbox, {"raw": "[Gmail]/Com estrela", "flags": {"\\flagged"}, "display": "Com estrela"}]
        self.assertEqual(organize.with_starred(gmail), gmail)

    def test_esconde_o_que_espera_o_desfazer(self):
        import organize
        a, b = object(), object()
        pending = [{"acc": a, "raw": "INBOX", "uids": ["1", "2"]},
                   {"acc": b, "raw": "INBOX", "uids": ["3"]},
                   {"acc": a, "raw": "Sent", "uids": ["4"]}]
        self.assertEqual(organize.hidden_uids(pending, a, "INBOX"), {"1", "2"})


if __name__ == "__main__":
    unittest.main()
