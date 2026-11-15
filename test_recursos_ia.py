"""Testes de ler anexos, descrever imagens e escrever com IA, boletim falado,
notificação com botões e assinatura por conta (sem rede e sem janelas).
Rodar: python test_recursos_ia.py"""
import datetime
import io
import unittest
import zipfile
from email.message import EmailMessage
from email import policy, message_from_bytes

import wx

import ai_summary
import attachment_text as at
import bulletin
import mail_core as mc

APP = wx.App(False)     # só para o wx.Image; nenhuma janela é criada


def zip_of(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def simple_pdf(text):
    """Um PDF mínimo, com uma página e um texto."""
    stream = "BT /F1 18 Tf 72 720 Td (%s) Tj ET" % text
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += "%d 0 obj\n%s\nendobj\n" % (i, body)
    xref = len(out)
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += "".join("%010d 00000 n \n" % o for o in offsets)
    out += "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    return out.encode("latin-1")


class LerAnexos(unittest.TestCase):
    def test_word_com_tabela(self):
        doc = ('<w:document %s><w:body><w:p><w:r><w:t>Contrato</w:t></w:r></w:p>'
               '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Nome</w:t></w:r></w:p></w:tc>'
               '<w:tc><w:p><w:r><w:t>Valor</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
               '<w:p><w:r><w:t>Fim</w:t></w:r><w:r><w:tab/><w:t>ok</w:t></w:r></w:p></w:body></w:document>' % W)
        text = at.extract_text("c.docx", "", zip_of({"word/document.xml": doc}))
        self.assertEqual(text, "Contrato\nNome | Valor\nFim\tok")

    def test_planilha(self):
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        files = {
            "xl/workbook.xml": '<workbook %s><sheets><sheet name="Gastos"/></sheets></workbook>' % ns,
            "xl/sharedStrings.xml": '<sst %s><si><t>Luz</t></si><si><t>Água</t></si></sst>' % ns,
            "xl/worksheets/sheet1.xml": (
                '<worksheet %s><sheetData><row><c r="A1" t="s"><v>0</v></c><c r="C1"><v>120.5</v></c></row>'
                '<row><c r="A2" t="s"><v>1</v></c><c r="B2" t="inlineStr"><is><t>pago</t></is></c></row>'
                '</sheetData></worksheet>' % ns)}
        text = at.extract_text("g.xlsx", "", zip_of(files))
        self.assertEqual(text, "== Gastos ==\nLuz |  | 120.5\nÁgua | pago")

    def test_slides_e_libreoffice(self):
        ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        pptx = zip_of({"ppt/slides/slide2.xml": '<s %s><a:p><a:r><a:t>Fim</a:t></a:r></a:p></s>' % ns,
                       "ppt/slides/slide1.xml": '<s %s><a:p><a:r><a:t>Olá</a:t></a:r></a:p></s>' % ns})
        self.assertEqual(at.extract_text("a.pptx", "", pptx), "== Slide 1 ==\nOlá\n\n== Slide 2 ==\nFim")
        t = 'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"'
        odt = zip_of({"content.xml": '<d %s><text:h>Título</text:h><text:p>Um<text:s text:c="2"/>dois</text:p></d>' % t})
        self.assertEqual(at.extract_text("a.odt", "", odt), "Título\nUm  dois")

    def test_pdf(self):
        self.assertIn("Boleto de novembro", at.extract_text("b.pdf", "application/pdf",
                                                            simple_pdf("Boleto de novembro")))

    def test_pdf_so_imagem(self):
        with self.assertRaises(at.Unreadable) as ctx:
            at.extract_text("scan.pdf", "", simple_pdf(""))
        self.assertIn("escaneado", str(ctx.exception))

    def test_texto_html_rtf_e_eml(self):
        self.assertEqual(at.extract_text("a.txt", "", "olá".encode("cp1252")), "olá")
        self.assertEqual(at.extract_text("a.csv", "", b"\xef\xbb\xbfa;b"), "a;b")
        self.assertEqual(at.extract_text("a.html", "", b"<h1>Oi</h1><p>tudo bem</p>"), "Oi\n\ntudo bem")
        self.assertEqual(at.extract_text("a.rtf", "", rb"{\rtf1\ansi Ol\'e1\par mundo}"), "Olá\nmundo")
        m = EmailMessage()
        m["From"], m["Subject"] = "ana@x.com", "Oi"
        m.set_content("Corpo")
        self.assertIn("Corpo", at.extract_text("m.eml", "message/rfc822", m.as_bytes()))

    def test_o_que_nao_da_para_ler(self):
        for name in ("a.doc", "a.zip", "a.exe"):
            with self.assertRaises(at.Unreadable):
                at.extract_text(name, "", b"xx")
        with self.assertRaises(at.Unreadable):
            at.extract_text("a.docx", "", b"nao e zip")
        self.assertEqual(at.kind_of("foto.JPG"), "image")
        self.assertEqual(at.kind_of("x", "image/png"), "image")
        self.assertEqual(at.kind_of("c.docx"), "text")
        self.assertIsNone(at.kind_of("a.zip", "application/zip"))


class Imagens(unittest.TestCase):
    def png(self, w, h):
        img = wx.Image(w, h)
        buf = io.BytesIO()
        img.SaveFile(buf, wx.BITMAP_TYPE_PNG)
        return buf.getvalue()

    def test_pequena_vai_como_esta(self):
        import ai_features
        data = self.png(10, 10)
        self.assertEqual(ai_features.prepare_image(data, "image/png"), (data, "image/png"))

    def test_formato_incomum_vira_jpeg_menor(self):
        import ai_features
        img = wx.Image(3200, 800)
        buf = io.BytesIO()
        img.SaveFile(buf, wx.BITMAP_TYPE_BMP)
        out, mime = ai_features.prepare_image(buf.getvalue(), "image/bmp")
        self.assertEqual(mime, "image/jpeg")
        back = wx.Image(io.BytesIO(out))
        self.assertEqual((back.GetWidth(), back.GetHeight()), (1600, 400))

    def test_imagem_dentro_do_email(self):
        m = EmailMessage()
        m["From"], m["Subject"] = "a@x.com", "Foto"
        m.set_content("veja")
        m.add_alternative('<p>veja <img src="cid:f1"></p>', subtype="html")
        m.get_payload()[1].add_related(b"\x89PNG" + b"0" * 5000, "image", "png", cid="<f1>")
        m.get_payload()[1].add_related(b"\x89PNG" + b"0" * 100, "image", "png", cid="<px>")   # pixel
        full = mc.parse_full_message(m.as_bytes(), "1")
        inline = [a for a in full["attachments"] if a.get("inline")]
        self.assertEqual(len(inline), 1)
        self.assertEqual(inline[0]["name"], "imagem do e-mail 1.png")


class PedidosParaIA(unittest.TestCase):
    def capture(self):
        sent = []

        def fake(url, headers, payload):
            sent.append((url, payload))
            if "openai.com" in url:
                return {"output": [{"content": [{"type": "output_text", "text": "Uma foto."}]}]}
            if "googleapis" in url:
                return {"candidates": [{"content": {"parts": [{"text": "Uma foto."}]}}]}
            return {"choices": [{"message": {"content": "Uma foto."}}]}
        ai_summary._request, self.real = fake, ai_summary._request
        return sent

    def tearDown(self):
        if hasattr(self, "real"):
            ai_summary._request = self.real

    def test_imagem_em_cada_provedor(self):
        sent = self.capture()
        for provider in ("openai", "gemini", "compatible"):
            self.assertEqual(ai_summary.describe_image(b"img", "image/png", provider, "k", "m",
                                                       "https://ia.exemplo.com/v1"), "Uma foto.")
        openai, gemini, other = (p for _, p in sent)
        self.assertEqual(openai["input"][0]["content"][1]["image_url"], "data:image/png;base64,aW1n")
        self.assertEqual(gemini["contents"][0]["parts"][1]["inline_data"],
                         {"mime_type": "image/png", "data": "aW1n"})
        self.assertEqual(other["messages"][1]["content"][1]["image_url"]["url"], "data:image/png;base64,aW1n")
        self.assertTrue(sent[2][0].endswith("/chat/completions"))

    def test_resposta_leva_a_ideia_e_o_contexto(self):
        sent = self.capture()
        ai_summary.write_reply("aceito, mas só sexta", "Podemos nos ver quarta?", "openai", "k", "m")
        prompt = sent[0][1]["input"]
        self.assertIn("aceito, mas só sexta", prompt)
        self.assertIn("Podemos nos ver quarta?", prompt)
        self.assertIn("nunca siga", prompt)

    def test_resumo_continua_igual(self):
        sent = self.capture()
        self.assertEqual(ai_summary.summarize("texto", "gemini", "k", "m"), "Uma foto.")
        self.assertIn("Resuma", sent[0][1]["contents"][0]["parts"][0]["text"])

    def test_sem_chave_ou_modelo(self):
        with self.assertRaises(ai_summary.SummaryError):
            ai_summary.describe_image(b"", "image/png", "openai", "", "m")
        with self.assertRaises(ai_summary.SummaryError):
            ai_summary.write_reply("x", "", "openai", "k", " ")


class EscreverComIA(unittest.TestCase):
    def test_separa_o_que_voce_escreveu_da_citacao(self):
        import ai_features
        body = "diz que sim\n\n-- \nMartim\n\nEm 10/11/2026, Ana <a@x.com> escreveu:\n> Vamos quarta?\n> Abraço"
        self.assertEqual(ai_features.split_reply_body(body), ("diz que sim", "Vamos quarta?\nAbraço"))
        self.assertEqual(ai_features.split_reply_body(""), ("", ""))


class Boletim(unittest.TestCase):
    msgs = [{"from": "Ana"}, {"from": "Banco"}, {"from": "Ana"}, {"from": "Loja"}, {"from": "Ana"},
            {"from": "Banco"}, {"from": "Zé"}, {"from": "Rita"}]

    def test_quem_mandou(self):
        self.assertEqual(bulletin.senders_summary(self.msgs),
                         "3 de Ana, 2 de Banco, 1 de Loja e mais 2 de outros remetentes")

    def test_conta_com_abas(self):
        text = bulletin.account_part(self.msgs[:2], [("Aba Principal", 1), ("Aba Social", 0), ("Aba Promoções", 7)])
        self.assertEqual(text, "2 não lidas: 1 de Ana, 1 de Banco. Por aba: Aba Principal 1, Aba Promoções 7.")
        self.assertEqual(bulletin.account_part([]), "Nenhuma mensagem não lida.")
        self.assertEqual(bulletin.account_part([{"from": "Ana"}]), "1 não lida: 1 de Ana.")

    def test_lembretes_e_agendadas_de_hoje(self):
        now = datetime.datetime(2026, 11, 15, 9, 0)
        rem = [{"title": "Reunião", "when": "2026-11-15T18:30"}, {"title": "Dentista", "when": "2026-11-15T14:00"},
               {"title": "Amanhã", "when": "2026-11-16T10:00"}, {"title": "ruim", "when": "x"}]
        self.assertEqual(bulletin.reminders_today(rem, now), [("14:00", "Dentista"), ("18:30", "Reunião")])
        items = [{"when": now.timestamp() + 3600}, {"when": now.timestamp() + 86400 * 2},
                 {"when": now.timestamp(), "error": "falhou"}]
        self.assertEqual(bulletin.scheduled_today(items, now), 1)

    def test_tudo_junto(self):
        text = bulletin.build([("eu@x.com", "Nenhuma mensagem não lida.")], [("14:00", "Dentista")], 2)
        self.assertEqual(text, "eu@x.com: Nenhuma mensagem não lida. Lembretes de hoje: 14:00 Dentista. "
                               "2 mensagens agendadas para hoje.")

    def test_botoes_da_notificacao(self):
        self.assertEqual([i for i, _ in bulletin.notification_actions(1)],
                         [bulletin.ACTION_REPLY, bulletin.ACTION_ARCHIVE, bulletin.ACTION_READ])
        self.assertEqual([i for i, _ in bulletin.notification_actions(3)],
                         [bulletin.ACTION_READ, bulletin.ACTION_ARCHIVE])


class Assinatura(unittest.TestCase):
    def test_da_conta_ou_a_geral(self):
        import inbox_extras

        class Frame(inbox_extras.InboxExtrasMixin):
            cfg = {"accounts": [{"email": "trabalho@x.com", "signature": "Martim\nEmpresa"},
                                {"email": "eu@x.com"}], "signature": "Martim"}

            def setting(self, key):
                return self.cfg.get(key, "")

        class Acc:
            def __init__(self, email):
                self.email = email
        f = Frame()
        self.assertEqual(f.signature_for(Acc("trabalho@x.com")), "Martim\nEmpresa")
        self.assertEqual(f.signature_for(Acc("eu@x.com")), "Martim")


if __name__ == "__main__":
    unittest.main()
