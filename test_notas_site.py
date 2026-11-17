"""Testes das notas da versão (GitHub, arquivo dentro do programa, aviso depois de
atualizar) e do gerador do site (sem rede e sem janelas). Rodar: python test_notas_site.py"""
import os
import re
import shutil
import tempfile
import unittest

import gerar_site
import release_notes as rn

GITHUB = [
    {"tag_name": "v1.0.16", "published_at": "2026-11-15T21:25:37Z", "draft": False, "prerelease": False,
     "body": "## Novidades\r\n\r\n- **Imprimir (Ctrl+P na leitura).**\r\n\r\n"
             "**Para baixar:** `AudioMail-Portatil-1.0.16.zip`\r\n"
             "O `AudioMail-1.0.16-exe.zip` e o `version.json` são usados pelo atualizador automático.\r\n"},
    {"tag_name": "v1.0.9", "published_at": "2026-11-15T13:28:29Z", "body": "Primeira versão."},
    {"tag_name": "v1.0.12", "published_at": "2026-11-15T14:33:50Z", "body": "- Corrige o Para."},
    {"tag_name": "rascunho", "published_at": "2026-11-15T14:33:50Z", "body": "x"},
    {"tag_name": "v1.0.17", "published_at": "2026-11-16T10:00:00Z", "draft": True, "body": "secreto"},
]


class NotesTest(unittest.TestCase):
    def text(self):
        return rn.from_github(GITHUB)

    def test_from_github(self):
        versions = rn.parse(self.text())
        self.assertEqual([v["version"] for v in versions], ["1.0.16", "1.0.12", "1.0.9"])
        self.assertTrue(versions[0]["date"].endswith("de novembro de 2026"))
        self.assertEqual(versions[0]["lines"], ["### Novidades", "", "- **Imprimir (Ctrl+P na leitura).**"])
        self.assertNotIn("secreto", self.text())
        self.assertNotIn("Para baixar", self.text())

    def test_plain_text(self):
        plain = rn.to_plain(self.text())
        self.assertTrue(plain.startswith("Versão 1.0.16, "))
        self.assertIn("\nNovidades\n• Imprimir (Ctrl+P na leitura).", plain)
        self.assertNotIn("**", plain)
        self.assertEqual(rn.to_plain(self.text(), only="1.0.12").count("Versão "), 1)
        newer = rn.to_plain(self.text(), newer_than="1.0.9")
        self.assertIn("1.0.12", newer)
        self.assertNotIn("Versão 1.0.9", newer)
        self.assertNotIn("1.0.16", rn.to_plain(self.text(), up_to="1.0.12"))

    def test_should_offer(self):
        self.assertEqual(rn.should_offer({}, "1.0.17"), (False, None))           # computador novo
        self.assertEqual(rn.should_offer({"accounts": [{}]}, "1.0.17"), (True, None))   # já usava
        self.assertEqual(rn.should_offer({"notes_seen_version": "1.0.16"}, "1.0.17"), (True, "1.0.16"))
        self.assertEqual(rn.should_offer({"notes_seen_version": "1.0.17"}, "1.0.17"), (False, "1.0.17"))
        self.assertEqual(rn.version_key("1.0.10") > rn.version_key("1.0.9"), True)

    def test_bundled_file_matches_format(self):
        here = os.path.dirname(os.path.abspath(__file__))
        versions = rn.parse(rn.load(here))
        self.assertTrue(versions, "notas_versao.txt precisa existir ao lado do programa")
        from version import APP_VERSION
        self.assertEqual(versions[0]["version"], APP_VERSION,
                         "rode python release_notes.py --atualizar depois de publicar a versão")

    def test_open_release_notes_falls_back_without_internet(self):
        shown = []

        class Frame(rn.ReleaseNotesMixin):
            def run(self, work, done, busy="", on_error=None):
                on_error(OSError("sem internet"))

        old = rn.NotesDialog

        class FakeDialog:
            def __init__(self, parent, title, text, url, open_url):
                shown.append((title, text, url))

            def ShowModal(self):
                pass

            def Destroy(self):
                pass

        rn.NotesDialog = FakeDialog
        try:
            Frame().open_release_notes()
        finally:
            rn.NotesDialog = old
        title, text, url = shown[0]
        self.assertEqual(title, "Notas da versão")
        self.assertTrue(text.startswith("Versão "))
        self.assertTrue(url.endswith("/audiomail/docs/novidades.html"))


class SiteTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        gerar_site.build(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def read(self, name):
        with open(os.path.join(self.dir, name), encoding="utf-8") as f:
            return f.read()

    def test_pages_and_links(self):
        ids = {}
        for name in ("index.html", "manual.html", "novidades.html", "privacidade.html", "termos.html"):
            ids[name] = set(re.findall(r'id="([^"]+)"', self.read(name)))
        for name in ids:
            for href in re.findall(r'href="([^"]+)"', self.read(name)):
                if href.startswith(("http", "estilo")):
                    continue
                page, _, anchor = href.partition("#")
                page = page or name
                self.assertIn(page, ids, href)
                if anchor:
                    self.assertIn(anchor, ids[page], "%s em %s" % (href, name))

    def test_download_and_not_official(self):
        home = self.read("index.html")
        self.assertIn("releases/latest/download/AudioMail-Portatil-", home)
        self.assertIn("Não é um aplicativo oficial", home)
        self.assertIn("Não é um aplicativo oficial", self.read("termos.html"))   # rodapé em todas
        self.assertTrue(home.startswith("<!doctype html>"))

    def test_news_page_reads_github(self):
        news = self.read("novidades.html")
        self.assertIn('<script src="novidades.js"></script>', news)
        self.assertIn('id="versao-1-0-16"', news)
        self.assertIn("<strong>", news)
        self.assertNotIn("novidades.js", self.read("manual.html"))
        self.assertIn("api.github.com/repos/martimpcctrl/AudioMail/releases", self.read("novidades.js"))

    def test_keys_and_search_index(self):
        self.assertIn('<kbd>Ctrl</kbd><span class="plus">+</span><kbd>N</kbd>', self.read("manual.html"))
        index = self.read("busca-indice.js")
        self.assertIn('"p": "Novidades"', index)
        self.assertIn('"p": "Política de privacidade"', index)

    def test_artifact_home_has_no_doctype(self):
        other = tempfile.mkdtemp()
        try:
            gerar_site.build(other, artifact=True)
            with open(os.path.join(other, "index.html"), encoding="utf-8") as f:
                self.assertTrue(f.read().startswith("<title>AudioMail</title>"))
        finally:
            shutil.rmtree(other, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
