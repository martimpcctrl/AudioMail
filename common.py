"""Pecas compartilhadas do AudioMail: configuracao, senha, icone e nomes acessiveis."""
import base64
import json
import os
import sys

import wx

import secure
import sounds
import i18n

try:
    import keyring
except Exception:
    keyring = None

APP = "AudioMail"

DEFAULTS = {
    "check_seconds": 60,     # verificacao de reserva
    "realtime": True,        # receber na hora (IMAP IDLE)
    "notify": True,          # mostrar notificacao
    "sound": True,           # tocar som
    "sound_file": "",        # vazio = som padrao
    "speak": True,           # falar pelo leitor de tela
    "keep_tray": True,       # fechar a janela deixa o programa na bandeja
    "minimize_tray": True,   # minimizar esconde na bandeja
    "start_hidden": False,   # abrir ja escondido
    "autostart": False,      # iniciar com o Windows
    "signature": "",         # assinatura automatica
    "group_threads": False,  # agrupar por conversa
    "translate_to": "pt",         # idioma para o qual as mensagens sao traduzidas
    "compose_lang": "en",         # ultimo idioma usado para traduzir o que se escreve
    "translate_consent": False,   # ja autorizou enviar texto ao servico de traducao do Google
    "auto_update": True,     # verificar atualizacoes sozinho
    "skipped_version": "",   # versao que o usuario pediu para pular
    "ui_language": "",       # idioma da interface; vazio solicita escolha no primeiro uso
    "reminders": [],          # lembretes locais, sem sincronizacao externa
    "reminders_intro_shown": False,
    "ai_summary_provider": "openai",
    "ai_summary_model": "",
    "ai_summary_endpoint": "",
    "ai_api_keys_enc": {},
    "ai_summary_consent": {},
    "support_tickets": [],
    "show_preview": True,       # começo do texto na lista de mensagens
    "undo_send_seconds": 10,  # segundos para desfazer o envio (0 desliga)
    "compose_show_cc": False, # mostrar Copia e Copia oculta ao escrever
    "quick_replies": [],      # respostas prontas [{"title", "text"}]
}


# ---------- configuracao ----------

def app_dir():
    """Pasta do programa: a do .exe quando compilado, ou a do codigo."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Onde ficam configuracao, som e manual.

    Modo portatil: se existir o arquivo portable.flag ao lado do programa, tudo fica na pasta
    'dados' ao lado dele (da para levar em um pendrive). Senao, no perfil do Windows.
    """
    here = app_dir()
    if os.path.isfile(os.path.join(here, "portable.flag")):
        folder = os.path.join(here, "dados")
    else:
        folder = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP)
    os.makedirs(folder, exist_ok=True)
    return folder


def config_path():
    return os.path.join(data_dir(), "config.json")


def load_config():
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    if "accounts" not in cfg:  # migra a versao de conta unica
        cfg["accounts"] = []
        if cfg.get("email"):
            acc = {"email": cfg["email"], "remember": cfg.get("remember", True)}
            if "password_enc" in cfg:
                acc["password_enc"] = cfg.pop("password_enc")
            cfg["accounts"].append(acc)
            cfg["active_email"] = cfg["email"]
    return cfg


def save_config(cfg):
    try:
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def get_ai_api_key(cfg, provider):
    """Recupera a chave de IA cifrada com DPAPI para este usuário do Windows."""
    keys = cfg.get("ai_api_keys_enc", {})
    if not isinstance(keys, dict):
        return ""
    encoded = keys.get(provider, "")
    if not encoded:
        return ""
    try:
        return secure.decrypt(base64.b64decode(encoded)).decode("utf-8")
    except Exception:
        return ""


def set_ai_api_key(cfg, provider, api_key):
    """Cifra e guarda uma chave por provedor; None apaga a chave escolhida."""
    keys = cfg.setdefault("ai_api_keys_enc", {})
    if not isinstance(keys, dict):
        keys = cfg["ai_api_keys_enc"] = {}
    if api_key is None:
        keys.pop(provider, None)
        return True
    try:
        encrypted = secure.encrypt(api_key.encode("utf-8"))
        keys[provider] = base64.b64encode(encrypted).decode("ascii")
        return True
    except Exception:
        return False


def protect_local_value(value):
    try:
        return base64.b64encode(secure.encrypt(value.encode("utf-8"))).decode("ascii")
    except Exception:
        return ""


def unprotect_local_value(value):
    try:
        return secure.decrypt(base64.b64decode(value)).decode("utf-8")
    except Exception:
        return ""


def find_account(cfg, email):
    for acc in cfg.get("accounts", []):
        if acc["email"].lower() == email.lower():
            return acc
    return None


def default_sound_path():
    return os.path.join(os.path.dirname(config_path()), "notificacao.wav")


# ---------- senha ----------

def remember_password(acc, password):
    """Guarda a senha criptografada (DPAPI do Windows); usa o keyring se precisar."""
    try:
        enc = secure.encrypt(password.encode("utf-8"))
        acc["password_enc"] = base64.b64encode(enc).decode("ascii")
        return True
    except Exception:
        pass
    if keyring:
        try:
            keyring.set_password(APP, acc["email"], password)
            return True
        except Exception:
            pass
    return False


def recall_password(acc):
    enc = acc.get("password_enc")
    if enc:
        try:
            return secure.decrypt(base64.b64decode(enc)).decode("utf-8")
        except Exception:
            pass
    if keyring:
        try:
            return keyring.get_password(APP, acc["email"])
        except Exception:
            pass
    return None


def forget_password(acc):
    acc.pop("password_enc", None)
    if keyring:
        try:
            keyring.delete_password(APP, acc["email"])
        except Exception:
            pass


# ---------- sistema ----------

def set_autostart(enable):
    """Liga ou desliga o inicio com o Windows (registro do usuario)."""
    try:
        import winreg
        if getattr(sys, "frozen", False):
            command = '"%s"' % sys.executable
        else:
            pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            exe = pyw if os.path.isfile(pyw) else sys.executable
            main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audiomail.py")
            command = '"%s" "%s"' % (exe, main)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        try:
            if enable:
                winreg.SetValueEx(key, APP, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, APP)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False


def make_icon(size=32):
    """Desenha um icone simples de envelope."""
    bmp = wx.Bitmap(size, size)
    dc = wx.MemoryDC(bmp)
    dc.SetBackground(wx.Brush(wx.Colour(0, 102, 204)))
    dc.Clear()
    dc.SetPen(wx.Pen(wx.WHITE, max(2, size // 16)))
    dc.SetBrush(wx.TRANSPARENT_BRUSH)
    m = size // 6
    top = int(m * 1.5)
    dc.DrawRectangle(m, top, size - 2 * m, size - 3 * m)
    mid = (size // 2, size // 2 + 1)
    dc.DrawLine(m, top, mid[0], mid[1])
    dc.DrawLine(size - m, top, mid[0], mid[1])
    dc.SelectObject(wx.NullBitmap)
    icon = wx.Icon()
    icon.CopyFromBitmap(bmp)
    return icon


def pick_sound_file(parent):
    """Abre o seletor de arquivo e devolve um WAV valido, ou None."""
    dlg = wx.FileDialog(parent, i18n.tr("Escolher som de notificação"),
                        wildcard="Arquivos de som WAV (*.wav)|*.wav",
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    path = None
    if dlg.ShowModal() == wx.ID_OK:
        chosen = dlg.GetPath()
        if sounds.is_valid_wav(chosen):
            path = chosen
        else:
            i18n.message_box("Esse arquivo não é um WAV válido. Converta o som para WAV e tente de novo.",
                          "Aviso", wx.OK | wx.ICON_WARNING, parent)
    dlg.Destroy()
    return path


# ---------- acessibilidade ----------

class _Named(wx.Accessible):
    """Da um nome acessivel direto ao controle, sem depender da ordem dos rotulos."""

    def __init__(self, win, name):
        super().__init__(win)
        self._name = name

    def GetName(self, childId):
        if childId == 0:
            return (wx.ACC_OK, self._name)
        return (wx.ACC_NOT_IMPLEMENTED, "")


def set_name(win, name):
    win.SetName(name)
    try:
        acc = _Named(win, name)
        win.SetAccessible(acc)
        win._acc = acc  # evita que o objeto seja descartado
    except Exception:
        pass
    return win
