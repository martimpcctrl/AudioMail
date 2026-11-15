"""Atualizador do AudioMail: confere, baixa, verifica e instala novas versoes.

Desde a 1.0.9 as versoes saem nas Releases do GitHub (martimpcctrl/AudioMail).
Cada release traz:
  version.json                      (informa a versao mais nova e os pacotes)
  AudioMail-X.Y.Z-source.zip        (arquivos .py, para quem roda com Python)
  AudioMail-X.Y.Z-exe.zip           (AudioMail.exe, para quem usa o executavel)
O version.json e lido da release mais recente (releases/latest/download/) e os
pacotes so sao aceitos se vierem das releases deste repositorio. O arquivo e
gerado por gerar_version_json.py.
"""
import hashlib
import json
import os
import posixpath
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from urllib.parse import urlparse

from version import APP_VERSION

REPO = "martimpcctrl/AudioMail"
BASE_URL = "https://github.com/%s/releases/latest/download/" % REPO
#: Os pacotes so podem vir das releases deste repositorio (nao de qualquer
#: endereco do github.com). O GitHub redireciona o download para um servidor
#: dele (HTTPS); o SHA-256 do version.json confere o arquivo de qualquer jeito.
PACKAGE_PREFIX = "https://github.com/%s/releases/download/" % REPO
MANIFEST_NAME = "version.json"
MAX_DOWNLOAD = 150 * 1024 * 1024
MAX_FILE = 30 * 1024 * 1024
ALLOWED_EXT = {".py", ".txt"}


class UpdateError(Exception):
    pass


# ---------- versoes ----------

def parse_version(text):
    text = str(text).strip()
    if not re.fullmatch(r"\d+(\.\d+){1,3}", text):
        raise UpdateError("Número de versão inválido: %r" % text)
    return tuple(int(x) for x in text.split("."))


def is_newer(remote, local=APP_VERSION):
    a, b = parse_version(remote), parse_version(local)
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) > b + (0,) * (size - len(b))


# ---------- rede ----------

def _open(url, timeout, require_https):
    req = urllib.request.Request(url, headers={
        "User-Agent": "AudioMail/" + APP_VERSION, "Cache-Control": "no-cache"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout,
                                      context=ssl.create_default_context())
    except Exception as e:
        raise UpdateError("Não foi possível falar com o servidor de atualizações: %s" % e)
    if require_https and not resp.geturl().startswith("https://"):
        resp.close()
        raise UpdateError("O servidor tentou sair do HTTPS; atualização recusada.")
    return resp


def _check_url(url, base_url, require_https):
    u, b = urlparse(url), urlparse(base_url)
    outside = u.netloc != b.netloc or (require_https and u.scheme != "https")
    if base_url == BASE_URL:
        clean = posixpath.normpath(u.path) == u.path and not (u.query or u.fragment)
        outside = outside or not url.startswith(PACKAGE_PREFIX) or not clean
    if outside:
        raise UpdateError("Endereço de pacote fora do servidor oficial: %s" % url)


def fetch_manifest(base_url=BASE_URL, require_https=True, timeout=15):
    resp = _open(base_url + MANIFEST_NAME, timeout, require_https)
    try:
        raw = resp.read(1024 * 1024)
    finally:
        resp.close()
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        raise UpdateError("O arquivo version.json do servidor está inválido.")
    if not isinstance(data, dict):
        raise UpdateError("O arquivo version.json do servidor está inválido.")
    parse_version(data.get("version", ""))
    data["notes"] = str(data.get("notes", ""))
    kind = str(data.get("type", "importante")).lower()
    data["type"] = kind if kind in ("novidade", "importante", "urgente") else "importante"
    data["mandatory"] = bool(data.get("mandatory", False))
    min_version = str(data.get("min_version") or (data["version"] if data["mandatory"] else "0.0"))
    parse_version(min_version)
    data["min_version"] = min_version
    found = False
    for kind in ("source", "exe"):
        url, digest = data.get(kind + "_url"), data.get(kind + "_sha256")
        if url or digest:
            if not url or not re.fullmatch(r"[0-9a-fA-F]{64}", str(digest or "")):
                raise UpdateError("Dados do pacote %s estão incompletos." % kind)
            _check_url(url, base_url, require_https)
            found = True
    if not found and is_newer(data["version"]):
        raise UpdateError("O servidor não informou nenhum pacote de atualização.")
    return data


def is_forced(manifest, local=APP_VERSION):
    """True se a versao instalada esta abaixo da versao minima exigida (atualizacao obrigatoria)."""
    return is_newer(manifest.get("min_version", "0.0"), local)


def pick_package(manifest, frozen):
    kind = "exe" if frozen else "source"
    url, digest = manifest.get(kind + "_url"), manifest.get(kind + "_sha256")
    if not url:
        raise UpdateError("Esta versão não tem pacote para o seu tipo de instalação.")
    return url, digest


def download(url, dest, sha256, progress=None, require_https=True, timeout=30):
    """Baixa e confere o SHA-256; so entrega o arquivo se estiver integro."""
    resp = _open(url, timeout, require_https)
    part = dest + ".part"
    digest = hashlib.sha256()
    done = 0
    try:
        total = int(resp.headers.get("Content-Length") or 0)
        if total > MAX_DOWNLOAD:
            raise UpdateError("O pacote é grande demais.")
        with open(part, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                done += len(chunk)
                if done > MAX_DOWNLOAD:
                    raise UpdateError("O pacote é grande demais.")
                digest.update(chunk)
                f.write(chunk)
                if progress:
                    progress(done, total)
    except UpdateError:
        _remove(part)
        raise
    except Exception as e:
        _remove(part)
        raise UpdateError("Falha ao baixar a atualização: %s" % e)
    finally:
        resp.close()
    if digest.hexdigest().lower() != sha256.lower():
        _remove(part)
        raise UpdateError("O arquivo baixado está corrompido (o SHA-256 não confere).")
    os.replace(part, dest)
    return dest


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


# ---------- instalacao (rodando com Python) ----------

def _safe_member(name):
    name = name.replace("\\", "/")
    norm = posixpath.normpath(name)
    parts = norm.split("/")
    if name.startswith("/") or ".." in parts or (parts and re.match(r"^[A-Za-z]:", parts[0])):
        raise UpdateError("O pacote tem um caminho perigoso: %s" % name)
    return norm


def install_source(zip_path, app_dir, old_version=APP_VERSION):
    """Troca os arquivos do programa pelos do pacote, com backup e retorno se falhar."""
    staging = tempfile.mkdtemp(prefix="audiomail_stage_")
    try:
        try:
            z = zipfile.ZipFile(zip_path)
        except zipfile.BadZipFile:
            raise UpdateError("O pacote de atualização não é um zip válido.")
        with z:
            infos = [i for i in z.infolist() if not i.filename.endswith("/")]
            names = {i.filename.replace("\\", "/"): i for i in infos}
            for n in names:
                _safe_member(n)
            if "audiomail.py" in names:
                prefix = ""
            else:
                roots = {n.split("/")[0] for n in names if "/" in n}
                if len(roots) == 1 and (list(roots)[0] + "/audiomail.py") in names:
                    prefix = list(roots)[0] + "/"
                else:
                    raise UpdateError("O pacote não contém o audiomail.py.")
            files = []
            for n, info in names.items():
                rel = n[len(prefix):]
                if not n.startswith(prefix) or not rel:
                    continue
                if "/" in rel or os.path.splitext(rel)[1].lower() not in ALLOWED_EXT:
                    raise UpdateError("O pacote contém um arquivo não permitido: %s" % rel)
                if info.file_size > MAX_FILE:
                    raise UpdateError("Arquivo grande demais no pacote: %s" % rel)
                with z.open(info) as src, open(os.path.join(staging, rel), "wb") as dst:
                    shutil.copyfileobj(src, dst)
                files.append(rel)

        backup_root = os.path.join(app_dir, "_backup")
        shutil.rmtree(backup_root, ignore_errors=True)
        backup = os.path.join(backup_root, old_version)
        os.makedirs(backup, exist_ok=True)
        existed = set()
        for rel in files:
            current = os.path.join(app_dir, rel)
            if os.path.isfile(current):
                shutil.copy2(current, os.path.join(backup, rel))
                existed.add(rel)
        try:
            for rel in files:
                shutil.copy2(os.path.join(staging, rel), os.path.join(app_dir, rel))
        except Exception as e:
            for rel in files:  # volta tudo como estava
                target = os.path.join(app_dir, rel)
                try:
                    if rel in existed:
                        shutil.copy2(os.path.join(backup, rel), target)
                    elif os.path.exists(target):
                        os.remove(target)
                except OSError:
                    pass
            raise UpdateError("Falha ao instalar; a versão anterior foi restaurada. (%s)" % e)
        return files
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def relaunch_source(main_script):
    """Abre o AudioMail de novo; o novo processo espera o antigo fechar."""
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.isfile(pyw):
        exe = pyw
    env = dict(os.environ, AUDIOMAIL_RESTART="1")
    subprocess.Popen([exe, main_script], env=env, cwd=os.path.dirname(main_script),
                     close_fds=True)


# ---------- instalacao (executavel) ----------

def exe_helper_script(pid, new_exe, target_exe):
    """Texto do .bat que espera o programa fechar, troca o .exe e abre de novo."""
    return "\r\n".join([
        "@echo off",
        'set "_MEIPASS2="',
        ":wait",
        'tasklist /FI "PID eq %d" 2>nul | find " %d " >nul' % (pid, pid),
        "if errorlevel 1 goto go",
        "ping -n 2 127.0.0.1 >nul",
        "goto wait",
        ":go",
        "set TRIES=0",
        ":move",
        'move /Y "%s" "%s" >nul 2>nul' % (new_exe, target_exe),
        "if not errorlevel 1 goto done",
        "set /a TRIES+=1",
        "if %TRIES% GEQ 15 goto fail",
        "ping -n 2 127.0.0.1 >nul",
        "goto move",
        ":done",
        'start "" "%s"' % target_exe,
        ":fail",
        '(goto) 2>nul & del "%~f0"',
        ""])


def prepare_exe_update(zip_path, target_exe, pid):
    """Extrai o novo AudioMail.exe e cria o .bat que faz a troca depois que o programa fechar."""
    try:
        z = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise UpdateError("O pacote de atualização não é um zip válido.")
    with z:
        member = None
        for info in z.infolist():
            if posixpath.basename(info.filename.replace("\\", "/")).lower() == "audiomail.exe":
                member = info
                break
        if member is None:
            raise UpdateError("O pacote não contém o AudioMail.exe.")
        if member.file_size > MAX_DOWNLOAD * 2:
            raise UpdateError("O AudioMail.exe do pacote é grande demais.")
        new_exe = os.path.join(os.path.dirname(target_exe), "AudioMail.new")
        with z.open(member) as src, open(new_exe, "wb") as dst:
            shutil.copyfileobj(src, dst)
    bat = os.path.join(tempfile.mkdtemp(prefix="audiomail_up_"), "atualizar.bat")
    with open(bat, "w", encoding="mbcs" if os.name == "nt" else "utf-8", newline="") as f:
        f.write(exe_helper_script(pid, new_exe, target_exe))
    return bat


def launch_detached(bat):
    flags = 0x08000000 | 0x00000200  # sem janela, em grupo proprio
    env = os.environ.copy()
    # PyInstaller's one-file bootloader may leave this extraction path in child envs.
    # The old _MEI directory disappears when this process exits, breaking the new app.
    env.pop("_MEIPASS2", None)
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True, env=env)
