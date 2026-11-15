"""Compila o AudioMail em um aplicativo portátil: uma pasta pronta para levar no pendrive.

Uso (no Windows, na pasta do AudioMail):  compilar.bat   (ou:  python compilar.py)

Saída em  saida_portatil\\
    AudioMail-Portatil\\          a pasta portátil (AudioMail.exe, manual, dados)
    AudioMail-Portatil-X.Y.Z.zip  a mesma pasta compactada, para distribuir (página do projeto)
    AudioMail-X.Y.Z-exe.zip       o executável + version.txt, para enviar no painel de versões

Para lançar uma versão nova:
    1) python empacotar.py --so-versao    2) compilar.bat    3) enviar o -exe.zip no painel.
"""
import argparse
import os
import shutil
import subprocess
import sys
import zipfile

import manual
from version import APP_VERSION

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = "AudioMail-Portatil"
OUT = "saida_portatil"
WORK = "build_portatil"

PORTABLE_FLAG = (
    "Este arquivo liga o modo portátil do AudioMail.\n"
    "Enquanto ele estiver ao lado do AudioMail.exe, os dados do programa ficam na pasta 'dados'\n"
    "e não no perfil do Windows. Apague este arquivo para voltar ao modo normal.\n")
DATA_README = (
    "Aqui ficam as configurações, o som e o manual do AudioMail (modo portátil).\n"
    "Para levar o programa para outro computador, copie a pasta AudioMail-Portatil inteira.\n"
    "A senha lembrada é protegida pelo Windows e só abre neste usuário e neste computador;\n"
    "em outro computador o programa pede a senha de app de novo.\n")


class BuildError(Exception):
    pass


def have_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def pyinstaller_command(here=HERE, python=None, collect_speech=True):
    cmd = [python or sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onefile", "--noconsole", "--name", "AudioMail",
           "--distpath", os.path.join(here, WORK, "dist"),
           "--workpath", os.path.join(here, WORK, "work"),
           "--specpath", os.path.join(here, WORK),
           "--add-data", os.path.join(here, manual.SOURCE_NAME) + os.pathsep + "."]
    if collect_speech:
        cmd += ["--collect-all", "accessible_output2"]
    cmd.append(os.path.join(here, "audiomail.py"))
    return cmd


def assemble_portable(exe_path, out_root, version, manual_source):
    """Monta a pasta portátil e o zip. Devolve (pasta, zip)."""
    if not os.path.isfile(exe_path):
        raise BuildError("Não achei o executável: %s" % exe_path)
    folder = os.path.join(out_root, FOLDER)
    shutil.rmtree(folder, ignore_errors=True)
    os.makedirs(os.path.join(folder, "dados"))
    shutil.copy2(exe_path, os.path.join(folder, "AudioMail.exe"))
    with open(os.path.join(folder, "portable.flag"), "w", encoding="utf-8") as f:
        f.write(PORTABLE_FLAG)
    with open(os.path.join(folder, "dados", "LEIA-ME.txt"), "w", encoding="utf-8-sig") as f:
        f.write(DATA_README)
    manual.write_manual(manual_source, folder, version)
    zip_path = os.path.join(out_root, "%s-%s.zip" % (FOLDER, version))
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                z.write(full, os.path.join(FOLDER, os.path.relpath(full, folder)))
    return folder, zip_path


def build_exe_zip(exe_path, out_root, version):
    """Zip para o painel: o AudioMail.exe + version.txt (o painel confere o numero da versao)."""
    path = os.path.join(out_root, "AudioMail-%s-exe.zip" % version)
    if os.path.exists(path):
        os.remove(path)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe_path, "AudioMail.exe")
        z.writestr("version.txt", version + "\n")
    return path


def run(cmd):
    print("> " + " ".join(cmd))
    if subprocess.call(cmd, cwd=HERE) != 0:
        raise BuildError("O comando falhou: " + " ".join(cmd[:4]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compila o AudioMail portátil.")
    parser.add_argument("--exe-pronto", help="usa um AudioMail.exe que já existe (não compila)")
    parser.add_argument("--sem-pip", action="store_true", help="não instala as bibliotecas")
    args = parser.parse_args(argv)

    out_root = os.path.join(HERE, OUT)
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(HERE, manual.SOURCE_NAME), encoding="utf-8") as f:
        source = f.read()

    if args.exe_pronto:
        exe = args.exe_pronto
    else:
        if os.name != "nt":
            raise BuildError("Este script compila o programa para Windows: rode no Windows.")
        if not args.sem_pip:
            print("Instalando as bibliotecas (pode demorar na primeira vez)...")
            run([sys.executable, "-m", "pip", "install", "--upgrade", "-r",
                 os.path.join(HERE, "requirements.txt"), "pyinstaller"])
        collect = have_module("accessible_output2")
        if not collect:
            print("Aviso: accessible-output2 não está instalado; o programa ficará sem a fala pelo NVDA.")
        print("Compilando o AudioMail %s (leva alguns minutos)..." % APP_VERSION)
        run(pyinstaller_command(collect_speech=collect))
        exe = os.path.join(HERE, WORK, "dist", "AudioMail.exe")
    folder, zip_path = assemble_portable(exe, out_root, APP_VERSION, source)
    exe_zip = build_exe_zip(exe, out_root, APP_VERSION)

    print("\nPronto! Versão %s." % APP_VERSION)
    print("Pasta portátil:  " + folder)
    print("Zip da pasta portátil (para a página do projeto):  " + zip_path)
    print("Zip do executável (para enviar no painel de versões):  " + exe_zip)
    return zip_path


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        print("\nErro: %s" % e)
        sys.exit(1)
