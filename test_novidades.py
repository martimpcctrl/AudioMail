"""Testes da 1.0.11: HTML legível, links, cancelar inscrição, contatos, agendadas
e provedores. Rodar: python test_novidades.py

Só lógica: nenhum teste abre janela nem usa a internet.
"""
import json
import os
import tempfile
import time
import unittest

import contacts as ct
import message_text as mt
import outbox
import providers

NEWSLETTER = """<html><head><style>p{color:red}</style><title>Oferta</title></head><body>
<div style="display:none">texto escondido do pré-cabeçalho&zwnj;&nbsp;&zwnj;</div>
<h1>Promoção de verão</h1>
<p>Olá, Martim!<br>Veja as <a href="https://loja.exemplo.com/ofertas?utm=1">ofertas da semana</a>.</p>
<ul><li>Camiseta</li><li>Boné</li></ul>
<table><tr><td><a href="https://loja.exemplo.com/ofertas?utm=1">Ver de novo</a></td></tr></table>
<a href="https://www.exemplo.com/x"><img src="logo.png" alt="Logo da loja"></a>
<a href="javascript:alert(1)">perigoso</a>
<img src="https://rastreio.exemplo.com/pixel.gif" width="1" height="1">
<p><a href="https://loja.exemplo.com/sair">Cancelar inscrição</a></p>
<script>var x = 1;</script>
</body></html>"""


class LeituraDeHtml(unittest.TestCase):
    def setUp(self):
        self.text, self.links = mt.html_to_readable(NEWSLETTER)

    def test_titulo_paragrafos_e_lista(self):
        self.assertIn("Promoção de verão", self.text)
        self.assertIn("Olá, Martim!\nVeja as ofertas da semana [link 1].", self.text)
        self.assertIn("• Camiseta\n• Boné", self.text)

    def test_esconde_o_que_nao_e_para_ler(self):
        for hidden in ("pré-cabeçalho", "color:red", "var x", "Oferta\n", "javascript", "‌"):
            self.assertNotIn(hidden, self.text)

    def test_links_numerados_sem_repetir(self):
        self.assertEqual(self.links[0], ("ofertas da semana", "https://loja.exemplo.com/ofertas?utm=1"))
        self.assertIn("Ver de novo [link 1]", self.text)  # o mesmo endereço reaproveita o número
        self.assertIn(("Logo da loja", "https://www.exemplo.com/x"), self.links)
        self.assertFalse(any(u.startswith("javascript") for _, u in self.links))
        self.assertIn("perigoso", self.text)

    def test_rotulo_da_lista_diz_o_site(self):
        self.assertEqual(mt.link_label(1, "ofertas da semana", "https://loja.exemplo.com/ofertas?utm=1"),
                         "1. ofertas da semana (loja.exemplo.com)")
        self.assertEqual(mt.link_label(2, "https://www.exemplo.com/x", "https://www.exemplo.com/x"),
                         "2. exemplo.com")

    def test_link_da_linha(self):
        self.assertEqual(mt.link_on_line("Veja as ofertas [link 1].", self.links), self.links[0][1])
        self.assertEqual(mt.link_on_line("acesse www.site.com.br/a, obrigado", []), "https://www.site.com.br/a")
        self.assertIsNone(mt.link_on_line("sem link aqui", self.links))
        self.assertIsNone(mt.link_on_line("[link 99]", self.links))

    def test_links_no_texto_puro(self):
        links = mt.links_in_text("Veja https://a.com/x. E também (https://b.org/y) e https://a.com/x")
        self.assertEqual([u for _, u in links], ["https://a.com/x", "https://b.org/y"])

    def test_conversa_renumera_os_links(self):
        bodies, links = mt.merge_links([("um [link 1]", [("a", "https://a.com")]),
                                        ("dois [link 1] e [link 2]", [("b", "https://b.com"),
                                                                      ("c", "https://c.com")])])
        self.assertEqual(bodies, ["um [link 1]", "dois [link 2] e [link 3]"])
        self.assertEqual([u for _, u in links], ["https://a.com", "https://b.com", "https://c.com"])

    def test_html_quebrado_nao_trava(self):
        text, links = mt.html_to_readable("<div><p>sem fechar <a href='https://x.com'>link")
        self.assertIn("sem fechar", text)
        self.assertEqual(links, [("link", "https://x.com")])


class CancelarInscricao(unittest.TestCase):
    def test_um_clique_pelo_cabecalho(self):
        o = mt.unsubscribe_options("<mailto:sair@x.com?subject=sair>, <https://x.com/u?id=1>",
                                   "List-Unsubscribe=One-Click")
        self.assertEqual((o["one_click"], o["https"], o["mailto"]), (True, "https://x.com/u?id=1",
                                                                     "mailto:sair@x.com?subject=sair"))

    def test_so_mailto(self):
        o = mt.unsubscribe_options("<mailto:sair@x.com>")
        self.assertFalse(o["one_click"])
        self.assertEqual(mt.mailto_parts(o["mailto"], "unsubscribe"), ("sair@x.com", "unsubscribe", "unsubscribe"))

    def test_sem_cabecalho_usa_o_link_do_texto(self):
        o = mt.unsubscribe_options("", "", [("Ver loja", "https://x.com"),
                                            ("Cancelar inscrição", "https://x.com/sair")])
        self.assertEqual(o["link"], "https://x.com/sair")

    def test_nada_para_cancelar(self):
        self.assertIsNone(mt.unsubscribe_options("", "", [("Ver loja", "https://x.com")]))

    def test_um_clique_manda_o_post_certo(self):
        sent = {}

        class Answer:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(request, timeout):
            sent.update(method=request.get_method(), data=request.data, url=request.full_url)
            return Answer()

        self.assertTrue(mt.one_click_unsubscribe("https://x.com/u", opener=opener))
        self.assertEqual(sent, {"method": "POST", "data": b"List-Unsubscribe=One-Click",
                                "url": "https://x.com/u"})
        self.assertFalse(mt.one_click_unsubscribe("http://x.com/u", opener=opener))


class ContatosTeste(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "contatos.json")
        self.c = ct.Contacts(self.path)
        self.c.add_header('"Ana Souza" <ana@exemplo.com>, Bruno <bruno@x.com>', 1)
        self.c.add_header("ana@exemplo.com", 3)
        self.c.add_header("noreply@loja.com", 5)

    def test_busca_por_nome_ou_endereco(self):
        self.assertEqual([x["addr"] for x in self.c.search("sou")], ["ana@exemplo.com"])
        self.assertEqual([x["addr"] for x in self.c.search("bru")], ["bruno@x.com"])
        self.assertEqual(self.c.search("")[0]["addr"], "ana@exemplo.com")  # o mais usado primeiro

    def test_nao_guarda_endereco_sem_resposta(self):
        self.assertEqual(self.c.search("noreply"), [])

    def test_completa_so_o_ultimo_endereco(self):
        self.assertEqual(self.c.completions("bruno@x.com, an"),
                         ["bruno@x.com, Ana Souza <ana@exemplo.com>"])
        self.assertEqual(self.c.completions("ana@exemplo.com, ana"), [])  # já está no campo
        self.assertEqual(self.c.completions(""), [])

    def test_acrescentar_no_campo(self):
        self.assertEqual(ct.append_address("", "a@x.com"), "a@x.com")
        self.assertEqual(ct.append_address("b@x.com,", "a@x.com"), "b@x.com, a@x.com")

    def test_salva_e_carrega(self):
        self.c.meta["sent_imported:eu@x.com"] = True
        self.c.save()
        again = ct.Contacts(self.path)
        self.assertEqual(again.data["ana@exemplo.com"]["name"], "Ana Souza")
        self.assertEqual(again.data["ana@exemplo.com"]["count"], 4)
        self.assertTrue(again.meta["sent_imported:eu@x.com"])


class Agendadas(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.file = os.path.join(self.dir, "anexo.txt")
        with open(self.file, "w") as f:
            f.write("oi")
        self.s = outbox.Scheduled(self.dir)
        self.fields = {"to": "a@x.com", "cc": "", "bcc": "", "subject": "Oi", "body": "Texto",
                       "in_reply_to": None, "references": None, "attachments": [self.file]}

    def test_guarda_copia_dos_anexos_e_sai_na_hora(self):
        item = self.s.add("eu@x.com", self.fields, when=1000)
        self.assertNotEqual(item["attachments"][0], self.file)
        self.assertTrue(os.path.isfile(item["attachments"][0]))
        self.assertEqual(self.s.due(["EU@x.com"], now=999), [])
        self.assertEqual([i["id"] for i in self.s.due(["eu@x.com"], now=1000)], [item["id"]])
        self.assertEqual(self.s.due(["outra@x.com"], now=2000), [])  # conta não conectada

    def test_argumentos_do_envio_na_ordem(self):
        item = self.s.add("eu@x.com", self.fields, when=1000)
        args = outbox.message_args(item)
        self.assertEqual(args[:5], ("a@x.com", "", "", "Oi", "Texto"))
        self.assertEqual(len(args), 8)

    def test_falha_espera_cinco_minutos(self):
        item = self.s.add("eu@x.com", self.fields, when=1000)
        self.s.failed(item["id"], "sem internet", now=1000)
        self.assertEqual(self.s.due(["eu@x.com"], now=1100), [])
        self.assertEqual(len(self.s.due(["eu@x.com"], now=1000 + outbox.RETRY_SECONDS)), 1)

    def test_remover_apaga_os_anexos_e_persiste(self):
        item = self.s.add("eu@x.com", self.fields, when=1000)
        copy = item["attachments"][0]
        self.s.remove(item["id"])
        self.assertFalse(os.path.exists(copy))
        self.assertEqual(outbox.Scheduled(self.dir).items, [])


class Provedores(unittest.TestCase):
    def test_adivinha_pelo_dominio(self):
        self.assertEqual(providers.guess("fulano@yahoo.com.br"), "yahoo")
        self.assertEqual(providers.guess("fulano@uol.com.br"), "uol")
        self.assertIsNone(providers.guess("fulano@empresa.com"))

    def test_microsoft_nao_entra(self):
        self.assertTrue(providers.is_microsoft("x@hotmail.com"))
        self.assertFalse(providers.is_microsoft("x@gmail.com"))
        self.assertNotIn("outlook", providers.KEYS)

    def test_conta_antiga_continua_no_gmail(self):
        self.assertEqual(providers.server_for({"email": "x@gmail.com"})["imap_host"], "imap.gmail.com")

    def test_servidor_escrito_a_mao(self):
        server = {"imap_host": "mail.empresa.com", "imap_port": 993, "smtp_host": "smtp.empresa.com",
                  "smtp_port": 587, "security": "starttls"}
        self.assertTrue(providers.valid_server(server))
        self.assertEqual(providers.server_for({"provider": "other", "server": server}), server)
        self.assertFalse(providers.valid_server(dict(server, imap_host="sem ponto")))


if __name__ == "__main__":
    unittest.main()
