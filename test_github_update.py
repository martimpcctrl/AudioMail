"""Testes da atualização pelo GitHub (1.0.9). Rodar: python test_github_update.py

Não usam a internet: só as regras de endereço do atualizador e o version.json
gerado por gerar_version_json.py.
"""
import hashlib
import json
import os
import tempfile
import unittest

import gerar_version_json as gerar
import updater

GOOD = "https://github.com/martimpcctrl/AudioMail/releases/download/v1.0.10/AudioMail-1.0.10-exe.zip"


class Enderecos(unittest.TestCase):
    def test_o_version_json_vem_da_release_mais_recente(self):
        self.assertEqual(updater.BASE_URL + updater.MANIFEST_NAME,
                         "https://github.com/martimpcctrl/AudioMail/releases/latest/download/version.json")

    def test_pacote_das_releases_do_repositorio_e_aceito(self):
        updater._check_url(GOOD, updater.BASE_URL, True)

    def test_pacote_de_outro_lugar_e_recusado(self):
        for url in (
            "https://github.com/outra-pessoa/AudioMail/releases/download/v1.0.10/AudioMail-1.0.10-exe.zip",
            "https://github.com/martimpcctrl/AudioMail-falso/releases/download/v1/x.zip",
            "https://github.com/martimpcctrl/AudioMail/archive/refs/heads/main.zip",
            "http://github.com/martimpcctrl/AudioMail/releases/download/v1.0.10/x.zip",
            "https://martimtech.ddns.net/audiomail/AudioMail-1.0.10-exe.zip",
            "https://github.com/martimpcctrl/AudioMail/releases/download/../../../outra/x.zip",
            GOOD + "?x=1",
        ):
            with self.subTest(url=url), self.assertRaises(updater.UpdateError):
                updater._check_url(url, updater.BASE_URL, True)

    def test_outro_servidor_de_teste_continua_com_a_regra_antiga(self):
        updater._check_url("http://127.0.0.1:8000/x.zip", "http://127.0.0.1:8000/", False)


class GerarVersionJson(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "saida_portatil"))
        self.exe = os.path.join(self.dir, "saida_portatil", "AudioMail-1.0.10-exe.zip")
        with open(self.exe, "wb") as f:
            f.write(b"conteudo do zip")

    def test_gera_o_manifesto_que_o_atualizador_aceita(self):
        self.assertEqual(gerar.main(["1.0.10", "--tipo", "urgente", "--notas", "Correções"], folder=self.dir), 0)
        out = os.path.join(self.dir, "release", "1.0.10")
        self.assertTrue(os.path.isfile(os.path.join(out, "AudioMail-1.0.10-exe.zip")))
        with open(os.path.join(out, "version.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["exe_url"], GOOD)
        self.assertEqual(data["exe_sha256"], hashlib.sha256(b"conteudo do zip").hexdigest())
        self.assertEqual((data["type"], data["notes"], data["mandatory"]), ("urgente", "Correções", False))
        self.assertNotIn("source_url", data)

    def test_sem_o_zip_do_executavel_nao_gera(self):
        os.remove(self.exe)
        self.assertEqual(gerar.main(["1.0.10"], folder=self.dir), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "release")))

    def test_obrigatoria_e_versao_minima(self):
        data = gerar.build_manifest("1.0.10", {"exe": self.exe}, mandatory=True, min_version="1.0.9")
        self.assertTrue(data["mandatory"])
        self.assertEqual(data["min_version"], "1.0.9")

    def test_versao_invalida_e_recusada(self):
        with self.assertRaises(updater.UpdateError):
            gerar.build_manifest("1.x", {"exe": self.exe})


if __name__ == "__main__":
    unittest.main()
