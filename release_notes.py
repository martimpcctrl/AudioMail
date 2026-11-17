"""Notas da versão. A fonte é o texto de cada versão publicada no GitHub.

O programa (Ajuda, Notas da versão) e a página Novidades do site buscam as notas
direto do GitHub, então uma versão publicada aparece nos dois na mesma hora.
Sem internet, valem as notas que vão dentro do programa (notas_versao.txt), que
são copiadas do GitHub antes de compilar: python release_notes.py --atualizar
"""
import datetime
import json
import os
import re
import sys

import wx

import i18n
from common import SITE, save_config
from version import APP_VERSION

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "martimpcctrl/AudioMail"
API = "https://api.github.com/repos/%s/releases?per_page=60" % REPO
MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro")
FILE_HEADER = """# Notas da versão do AudioMail

Copiado das versões publicadas no GitHub (python release_notes.py --atualizar).
Vai dentro do programa, para as notas aparecerem mesmo sem internet.
"""

SOURCE_NAME = "notas_versao.txt"
HEADER = re.compile(r"^## (\S+)\s*·\s*(.+)$")


def parse(text):
    """[{"version", "date", "lines"}] da mais nova para a mais antiga."""
    out = []
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        m = HEADER.match(line.strip())
        if m:
            out.append({"version": m.group(1), "date": m.group(2).strip(), "lines": []})
        elif out:
            out[-1]["lines"].append(line.rstrip())
    for v in out:
        while v["lines"] and not v["lines"][-1]:
            v["lines"].pop()
    return out


def version_key(v):
    try:
        return tuple(int(p) for p in str(v).split("."))
    except ValueError:
        return (0,)


def clean(line):
    """Tira a marcação (** e `) para o texto ser lido como frase."""
    return re.sub(r"\*\*|`", "", line).strip()


def to_plain(text, newer_than=None, up_to=None, only=None):
    """O texto para ler com as setas. ``newer_than``: só as versões depois dela
    (o que mudou desde a versão que você tinha); ``up_to``: nenhuma depois desta;
    ``only``: só esta versão."""
    parts = []
    for v in parse(text):
        key = version_key(v["version"])
        if only and v["version"] != only:
            continue
        if newer_than and key <= version_key(newer_than):
            continue
        if up_to and key > version_key(up_to):
            continue
        block = [i18n.tr("Versão %s, %s") % (v["version"], v["date"])]
        for line in v["lines"]:
            if not line.strip():
                continue
            if line.startswith("### "):
                block.append("")
                block.append(clean(line[4:]))
            elif line.startswith("- "):
                block.append("• " + clean(line[2:]))
            else:
                block.append(clean(line))
        parts.append("\n".join(block))
    return "\n\n\n".join(parts)


def should_offer(cfg, current):
    """(perguntar?, versão que você tinha). Na primeira vez de um computador novo
    (sem conta ainda) não pergunta; quem já usava e acabou de atualizar, sim."""
    seen = cfg.get("notes_seen_version")
    if seen is None:
        return bool(cfg.get("accounts")), None
    return version_key(current) > version_key(seen), seen


def find(app_dir):
    for folder in (getattr(sys, "_MEIPASS", None), app_dir,
                   os.path.dirname(os.path.abspath(sys.executable))):
        if folder and os.path.isfile(os.path.join(folder, SOURCE_NAME)):
            return os.path.join(folder, SOURCE_NAME)
    return None


# ---------- GitHub ----------

def body_lines(body):
    """O texto de uma versão do GitHub sem as linhas de download (só servem lá)."""
    out = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("**Para baixar:**") or "são usados pelo atualizador automático" in line:
            continue
        if line.startswith("## "):
            line = "### " + line[3:]
        out.append(line.rstrip())
    while out and not out[-1].strip():
        out.pop()
    while out and not out[0].strip():
        out.pop(0)
    return out


def date_text(iso):
    try:
        d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except (AttributeError, ValueError):
        return ""
    return "%d de %s de %d" % (d.day, MONTHS[d.month - 1], d.year)


def from_github(releases):
    """As versões publicadas (resposta da API do GitHub) no formato do notas_versao.txt."""
    parts = []
    for r in releases or []:
        if not isinstance(r, dict) or r.get("draft") or r.get("prerelease"):
            continue
        version = str(r.get("tag_name", "")).lstrip("vV")
        if not re.fullmatch(r"\d+(\.\d+)*", version):
            continue
        parts.append((version, "## %s · %s\n%s" % (version, date_text(r.get("published_at", "")),
                                                    "\n".join(body_lines(r.get("body"))))))
    parts.sort(key=lambda p: version_key(p[0]), reverse=True)
    return "\n\n".join(text for _, text in parts) + ("\n" if parts else "")


def fetch_github(timeout=8):
    """O texto das notas buscado do GitHub (levanta erro sem internet)."""
    import updater
    resp = updater._open(API, timeout, True)
    try:
        data = json.loads(resp.read(3 * 1024 * 1024).decode("utf-8"))
    finally:
        resp.close()
    text = from_github(data)
    if not parse(text):
        raise ValueError("O GitHub não devolveu notas.")
    return text


def load(app_dir):
    path = find(app_dir)
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


class NotesDialog(wx.Dialog):
    """Texto só de leitura, com Copiar tudo, Abrir no site e Fechar (Esc fecha)."""

    def __init__(self, parent, title, text, site_url, open_url):
        super().__init__(parent, title=i18n.tr(title), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        from ai_features import copy_text
        from common import set_name
        self.output = set_name(wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2),
                               i18n.tr(title))
        row = wx.BoxSizer(wx.HORIZONTAL)
        copy = wx.Button(self, label=i18n.tr("Copiar tudo"))
        site = wx.Button(self, label=i18n.tr("Abrir no site"))
        close = wx.Button(self, wx.ID_OK, i18n.tr("Fechar"))
        copy.Bind(wx.EVT_BUTTON, lambda e: copy_text(text))
        site.Bind(wx.EVT_BUTTON, lambda e: open_url(site_url))
        for b in (copy, site, close):
            row.Add(b, 0, wx.RIGHT, 8)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.output, 1, wx.EXPAND | wx.ALL, 10)
        layout.Add(row, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(layout)
        self.SetSize((720, 540))
        self.SetEscapeId(wx.ID_OK)
        self.CentreOnParent()
        self.output.SetInsertionPoint(0)
        self.output.SetFocus()


class ReleaseNotesMixin:
    """Para a janela principal."""

    def open_release_notes(self, newer_than=None, only=None):
        """Busca as notas do GitHub; sem internet, usa as que vieram no programa."""
        def show(source):
            text = to_plain(source, newer_than, None if only else APP_VERSION, only)
            if not text:
                text = to_plain(load(HERE), newer_than, APP_VERSION, only)
            if not text:
                text = i18n.tr("As notas da versão não foram encontradas. Veja no site: %s") % (
                    SITE + "novidades.html")
            title = "O que mudou no AudioMail" if (newer_than or only) else "Notas da versão"
            dlg = NotesDialog(self, title, text, SITE + "novidades.html", self.open_site)
            dlg.ShowModal()
            dlg.Destroy()

        self.run(fetch_github, show, "Buscando as notas da versão", lambda err: show(load(HERE)))

    def open_site(self, url=None):
        import webbrowser
        try:
            webbrowser.open(url or SITE)
        except Exception:
            pass

    def offer_release_notes(self):
        """Depois de atualizar, pergunta uma vez se quer ver o que mudou."""
        if not self or not self.IsShown():
            return   # escondido na bandeja: pergunta quando a janela aparecer
        if getattr(self, "login_open", False) or any(
                isinstance(w, wx.Dialog) and w.IsShown() for w in wx.GetTopLevelWindows()):
            wx.CallLater(5000, self.offer_release_notes)   # não pergunta por cima de outra janela
            return
        offer, seen = should_offer(self.cfg, APP_VERSION)
        if self.cfg.get("notes_seen_version") != APP_VERSION:
            self.cfg["notes_seen_version"] = APP_VERSION
            save_config(self.cfg)
        if not offer:
            return
        answer = i18n.message_box(i18n.tr("O AudioMail foi atualizado para a versão %s. Quer ver o que mudou?")
                                  % APP_VERSION, "Notas da versão", wx.YES_NO | wx.ICON_INFORMATION, self)
        if answer == wx.YES:
            # sem saber de qual versão você veio, mostra só a nova
            self.open_release_notes(newer_than=seen) if seen else self.open_release_notes(only=APP_VERSION)


if __name__ == "__main__":
    if "--atualizar" in sys.argv:
        notes = fetch_github(timeout=20)
        with open(os.path.join(HERE, SOURCE_NAME), "w", encoding="utf-8", newline="\n") as f:
            f.write(FILE_HEADER + "\n" + notes)
        print("%s atualizado com %d versões." % (SOURCE_NAME, len(parse(notes))))
    else:
        print(__doc__)
