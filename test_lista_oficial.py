"""Testes da lista como nos programas oficiais: busca avançada, prévia, anexo
esquecido, abas e marcadores do Gmail, não lidas por pasta (sem rede e sem janelas).
Rodar: python test_lista_oficial.py"""
import base64
import datetime
import threading
import unittest

import mail_core as mc
import message_text as mt
import organize
import search_query as sq
import views

TODAY = datetime.date(2026, 11, 15)


class Busca(unittest.TestCase):
    def test_chaves_em_ingles_e_portugues(self):
        c = sq.parse_query('from:ana assunto:"nota fiscal" has:attachment é:não-lida boleto', TODAY)
        self.assertEqual(c["from"], "ana")
        self.assertEqual(c["subject"], "nota fiscal")
        self.assertTrue(c["attachment"] and c["unread"])
        self.assertFalse(c["starred"])
        self.assertEqual(c["words"], ["boleto"])

    def test_datas(self):
        c = sq.parse_query("newer_than:7d before:2026/11/10", TODAY)
        self.assertEqual(c["after"], datetime.date(2026, 11, 8))
        self.assertEqual(c["before"], datetime.date(2026, 11, 10))
        self.assertEqual(sq.parse_query("depois:31/01/2026")["after"], datetime.date(2026, 1, 31))

    def test_link_nao_vira_chave(self):
        c = sq.parse_query("https://loja.com")
        self.assertEqual(c["words"], ["https://loja.com"])

    def test_gmail_recebe_tudo_junto(self):
        c = sq.parse_query('from:ana subject:"nota fiscal" is:starred newer_than:1y', TODAY)
        self.assertEqual(sq.to_gmail_raw(c, "category:primary"),
                         'category:primary from:ana subject:"nota fiscal" is:starred after:2025/11/15')

    def test_imap_comum(self):
        c = sq.parse_query("from:ana is:unread after:2026/11/01 boleto", TODAY)
        keys, literal, check = sq.to_imap(c)
        self.assertEqual(keys, ["UNSEEN", "SINCE", "01-Nov-2026", "FROM", '"ana"', "TEXT", '"boleto"'])
        self.assertIsNone(literal)
        self.assertEqual(check, [])
        self.assertEqual(sq.to_imap(sq.empty()), (["ALL"], None, []))

    def test_acentos_um_vai_como_literal_o_resto_e_conferido(self):
        c = sq.parse_query("from:joão subject:reunião", TODAY)
        keys, literal, check = sq.to_imap(c, flagged=True)
        self.assertEqual(keys, ["FLAGGED"])
        self.assertEqual(literal, ("FROM", "joão"))
        self.assertEqual(check, [("subject", "reunião")])
        self.assertTrue(sq.passes({"subject": "Reunião de sexta"}, check))
        self.assertFalse(sq.passes({"subject": "Almoço"}, check))

    def test_janela_monta_o_texto(self):
        text = sq.build("Ana Souza", "", "boleto", "vencido", attachment=True, period="newer_than:30d")
        self.assertEqual(text, 'from:"Ana Souza" subject:boleto has:attachment newer_than:30d vencido')
        c = sq.parse_query(text, TODAY)
        self.assertEqual((c["from"], c["subject"], c["words"]), ("Ana Souza", "boleto", ["vencido"]))


class AnexoEsquecido(unittest.TestCase):
    def test_fala_de_anexo(self):
        for text in ("Segue em anexo o contrato.", "Anexei as fotos", "Please see attached", "Te mando el adjunto"):
            self.assertTrue(mt.mentions_attachment(text), text)

    def test_nao_conta_assinatura_nem_citacao(self):
        self.assertFalse(mt.mentions_attachment("Oi, tudo bem?\n\n-- \nAnexos só por e-mail"))
        self.assertFalse(mt.mentions_attachment("Combinado!\n> segue o anexo"))
        self.assertFalse(mt.mentions_attachment("Ok.\n\nEm 10/11/2026 Ana escreveu:\nanexo aqui"))
        self.assertFalse(mt.mentions_attachment("Obrigado\n\n---------- Mensagem encaminhada ----------\nem anexo"))
        self.assertFalse(mt.mentions_attachment("Reanexo não é palavra"))


class Previa(unittest.TestCase):
    def test_texto_puro(self):
        header = b"Content-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: 8bit\r\n"
        self.assertEqual(mc.snippet_from_raw(header, "Olá, a reunião mudou.\n\nAbraço".encode()),
                         "Olá, a reunião mudou. Abraço")

    def test_html_sem_links(self):
        header = b"Content-Type: text/html; charset=utf-8\r\n"
        body = b'<style>p{}</style><p>Ofertas da semana <a href="https://x.com">aqui</a></p>'
        self.assertEqual(mc.snippet_from_raw(header, body), "Ofertas da semana aqui")

    def test_multipart_cortado_no_meio(self):
        text = "Bom dia! O pedido saiu para entrega. " * 20
        b64 = base64.b64encode(text.encode()).decode()
        header = b'Content-Type: multipart/alternative; boundary="XX"\r\nMIME-Version: 1.0\r\n'
        body = ("--XX\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: base64\r\n\r\n"
                + b64[:301]).encode()
        snippet = mc.snippet_from_raw(header, body, limit=60)
        self.assertTrue(snippet.startswith("Bom dia! O pedido saiu"), snippet)
        self.assertTrue(snippet.endswith("…") and len(snippet) <= 61)

    def test_resposta_para_antes_da_citacao(self):
        header = b"Content-Type: text/plain\r\n"
        self.assertEqual(mc.snippet_from_raw(header, b"Pode ser.\n\nOn Mon, Ana wrote:\n> oi"), "Pode ser.")

    def test_lixo_nao_derruba(self):
        self.assertEqual(mc.snippet_from_raw(b"", b""), "")
        self.assertIsInstance(mc.snippet_from_raw(b"Content-Type: x/y\r\n", b"\xff\xfe"), str)

    def test_resposta_do_fetch_com_varias_partes(self):
        data = [(b"1 (UID 7 BODY[HEADER.FIELDS (CONTENT-TYPE)] {26}", b"Content-Type: text/plain\r\n"),
                (b" BODY[TEXT]<0> {3}", b"oi!"), b")",
                (b"2 (UID 8 BODY[HEADER.FIELDS (CONTENT-TYPE)] {2}", b"\r\n"),
                (b" BODY[TEXT]<0> {2}", b"ok"), b")"]
        items = mc.parse_fetch_items(data)
        self.assertEqual(set(items), {"7", "8"})
        self.assertEqual(items["7"]["parts"]["TEXT"], b"oi!")
        self.assertIn("HEADER.FIELDS (CONTENT-TYPE)", items["8"]["parts"])


class Marcadores(unittest.TestCase):
    def test_le_os_marcadores_sem_os_do_sistema(self):
        meta = r'1 (X-GM-THRID 9 X-GM-LABELS ("\\Important" "\\Inbox" Trabalho "Fam&AO0-lia" "A b") UID 3'
        self.assertEqual(mc.parse_labels(meta), ["Trabalho", "Família", "A b"])
        self.assertEqual(mc.parse_labels("1 (UID 3 FLAGS ())"), [])
        self.assertEqual(mc.parse_labels("X-GM-LABELS ()"), [])

    def test_aparecem_no_estado(self):
        row = mc.build_rows([{"uid": "1", "from": "a", "subject": "s", "date": "", "unread": True,
                              "flagged": False, "labels": ["Trabalho"]}], False)[0]
        self.assertEqual(mc.state_text(row), "Não lida, Trabalho")

    def test_quais_pastas_sao_marcadores(self):
        folders = [{"raw": "INBOX", "flags": set()}, {"raw": "[Gmail]/Spam", "flags": {"\\junk"}},
                   {"raw": "Trabalho", "flags": set()}, {"raw": "Fam&AO0-lia", "flags": set()},
                   {"raw": "\x00category:social", "flags": {"\\virtual"}}]
        self.assertEqual(views.user_labels(folders), [("Trabalho", "Trabalho"), ("Fam&AO0-lia", "Família")])

    def test_todas_ou_so_algumas(self):
        labels = [("Trabalho", "Trabalho"), ("Casa", "Casa")]
        rows = [{"labels": ["Trabalho", "Casa"]}, {"labels": ["Trabalho"]}]
        self.assertEqual(views.label_state(rows, labels), ({"Trabalho"}, {"Casa"}))


class Pastas(unittest.TestCase):
    inbox = {"raw": "INBOX", "flags": set(), "display": "Caixa de entrada"}

    def test_abas_do_gmail_depois_da_caixa_de_entrada(self):
        star = {"raw": "[Gmail]/Com estrela", "flags": {"\\flagged"}, "display": "Com estrela"}
        out = organize.with_virtual([self.inbox, star], gmail=True)
        self.assertEqual([f.get("filter") for f in out[1:6]],
                         ["category:primary", "category:promotions", "category:social",
                          "category:updates", "category:forums"])
        self.assertEqual(len(out), 7)        # o Gmail já tem estrela: sem a de mentira
        self.assertEqual(organize.real_folders(out), [self.inbox, star])

    def test_outros_servidores_so_ganham_a_estrela(self):
        out = organize.with_virtual([self.inbox], gmail=False)
        self.assertEqual([f.get("filter") for f in out], [None, "flagged"])

    def test_nome_com_nao_lidas_e_total(self):
        self.assertEqual(views.folder_label(self.inbox, {"INBOX": (3, 120)}),
                         "Caixa de entrada, 3 não lidas, 120 mensagens")
        self.assertEqual(views.folder_label(self.inbox, {"INBOX": (1, 1)}),
                         "Caixa de entrada, 1 não lida, 1 mensagem")
        self.assertEqual(views.folder_label(self.inbox, {"INBOX": (0, 40)}), "Caixa de entrada, 40 mensagens")
        self.assertEqual(views.folder_label(self.inbox, {}), "Caixa de entrada")
        tab = {"raw": "\x00category:social", "flags": {"\\virtual"}, "display": "Aba Social"}
        self.assertEqual(views.folder_label(tab, {tab["raw"]: (3, 57)}), "Aba Social, 3 não lidas, 57 mensagens")

    def test_carregar_mais(self):
        self.assertTrue(views.can_load_more(100, 350))
        self.assertFalse(views.can_load_more(350, 350))


class FakeIMAP:
    def __init__(self, uids=b"1 2 3"):
        self.calls, self.literal, self.uids = [], None, uids
        self.literals = []

    def noop(self):
        return "OK", []

    def select(self, name):
        return "OK", [b"1"]

    def uid(self, *args):
        self.calls.append(args)
        if args[0] == "SEARCH":
            self.literals.append(self.literal)
            return "OK", [self.uids]
        return "OK", []

    def status(self, name, what):
        self.calls.append(("STATUS", name, what))
        return "OK", [name.encode() + b" (MESSAGES 9 UNSEEN 4)"]


def client(imap, gmail):
    c = mc.MailClient.__new__(mc.MailClient)
    c.imap, c.selected, c.lock, c.gmail, c.can_move, c.folders = imap, None, threading.RLock(), gmail, True, []
    c._headers_for = lambda uids: [{"uid": u.decode(), "subject": "Reunião", "from_raw": "x"} for u in uids]
    return c


class SegundaConexao(unittest.TestCase):
    def test_trabalho_de_fundo_nao_divide_a_conexao_da_lista(self):
        main = mc.MailClient("eu@gmail.com", "abcd efgh", "imap.gmail.com", 993, "smtp.gmail.com", 465)
        main.imap, main.gmail, main.folders = object(), True, [{"raw": "INBOX", "flags": set()}]
        side = main.side()
        self.assertIs(main.side(), side)                 # uma só, reaproveitada
        self.assertIsNone(side.imap)                     # conecta sozinha quando usada
        self.assertIsNot(side.lock, main.lock)           # a lista nunca espera por ela
        self.assertEqual((side.email, side.password, side.imap_host), ("eu@gmail.com", "abcdefgh", "imap.gmail.com"))
        self.assertEqual(side.folders, main.folders)
        self.assertIsNot(side.folders, main.folders)
        closed = []
        side.close = lambda: closed.append(1)
        main.imap = None
        main.close()
        self.assertEqual(closed, [1])
        self.assertIsNot(main.side(), side)              # reconectou: conexão nova


class Servidor(unittest.TestCase):
    def test_total_e_limite(self):
        msgs, total = client(FakeIMAP(b"1 2 3 4 5"), False).fetch_headers("INBOX", limit=2, with_total=True)
        self.assertEqual(([m["uid"] for m in msgs], total), (["4", "5"], 5))

    def test_gmail_busca_pelo_buscador_dele(self):
        imap = FakeIMAP()
        msgs, total = client(imap, True).search_query("INBOX", "from:ana", 100, "category:social")
        self.assertEqual(imap.calls[-1], ("SEARCH", "CHARSET", "UTF-8", "X-GM-RAW"))
        self.assertEqual(imap.literals[-1], "category:social from:ana".encode())
        self.assertEqual(total, 3)

    def test_outro_servidor_confere_o_que_sobrou(self):
        imap = FakeIMAP()
        msgs, total = client(imap, False).search_query("INBOX", "from:joão subject:reunião almoço", 100)
        self.assertEqual(imap.calls[-1][:3], ("SEARCH", "CHARSET", "UTF-8"))
        self.assertEqual(imap.literals[-1], "joão".encode())
        self.assertEqual(total, 0)    # "almoço" não está no remetente nem no assunto

    def test_sem_busca_na_estrela_de_mentira(self):
        imap = FakeIMAP()
        client(imap, False).search_query("INBOX", "", 100, "flagged")
        self.assertEqual(imap.calls[-1], ("SEARCH", None, "FLAGGED"))

    def test_nao_lidas_por_pasta(self):
        imap = FakeIMAP(b"8 9")
        folders = [{"raw": "INBOX", "flags": set()}, {"raw": "Enviados", "flags": {"\\sent"}},
                   {"raw": "\x00category:social", "flags": {"\\virtual"}, "filter": "category:social"},
                   {"raw": "\x00flagged", "flags": {"\\virtual"}, "filter": "flagged"}]
        counts = client(imap, True).folder_counts(folders)
        self.assertEqual(counts, {"INBOX": (4, 9), "Enviados": (4, 9),
                                  "\x00category:social": (2, 2), "\x00flagged": (2, 2)})
        self.assertIn(b"category:social is:unread", imap.literals)
        self.assertIn(b"category:social", imap.literals)
        self.assertIn(("SEARCH", None, "FLAGGED", "UNSEEN"), imap.calls)

    def test_marcadores_no_servidor(self):
        imap = FakeIMAP()
        client(imap, True).change_labels("INBOX", ["1", "2"], add=["Trabalho"], remove=["Casa"])
        self.assertIn(("STORE", "1,2", "+X-GM-LABELS", '("Trabalho")'), imap.calls)
        self.assertIn(("STORE", "1,2", "-X-GM-LABELS", '("Casa")'), imap.calls)


if __name__ == "__main__":
    unittest.main()
