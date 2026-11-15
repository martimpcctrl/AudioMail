"""Prepara o zip do aplicativo para enviar no painel de versões.

Uso (na pasta do AudioMail):
    python empacotar.py                  soma 1 ao número da versão e gera o zip
    python empacotar.py --versao 1.2.0   escolhe o número da versão
    python empacotar.py --sem-mudar      usa a versão que já está no version.py
    python empacotar.py --so-versao      só muda o número da versão, sem gerar o zip do código
                                         (use quando você só distribui o executável)

Saída: dist_update\\AudioMail-X.Y.Z-source.zip (o zip do código, opcional no painel)
"""
import argparse
import os
import re
import sys
import zipfile

import updater

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRA = ("requirements.txt", "LEIA-ME.txt", "manual_fonte.txt")
TOOLS = {"empacotar.py", "compilar.py"}  # ferramenta do desenvolvedor, nao vai no pacote


class PackError(Exception):
    pass


def read_version(folder):
    with open(os.path.join(folder, "version.py"), encoding="utf-8") as f:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', f.read())
    if not m:
        raise PackError("Não achei APP_VERSION em version.py.")
    return m.group(1)


def next_version(current):
    parts = list(updater.parse_version(current))
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    return ".".join(str(p) for p in parts)


def write_version(folder, version):
    with open(os.path.join(folder, "version.py"), "w", encoding="utf-8") as f:
        f.write('APP_VERSION = "%s"\n' % version)


def source_files(folder):
    names = []
    for name in sorted(os.listdir(folder)):
        if not os.path.isfile(os.path.join(folder, name)):
            continue
        if name.endswith(".py") and not name.startswith("test_") and name not in TOOLS:
            names.append(name)
        elif name in EXTRA:
            names.append(name)
    return names


def build_zip(folder, out_dir, version):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "AudioMail-%s-source.zip" % version)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in source_files(folder):
            z.write(os.path.join(folder, name), name)
    return path


def main(argv=None, folder=HERE):
    parser = argparse.ArgumentParser(description="Gera o zip do AudioMail para o painel.")
    parser.add_argument("--versao", help="número da versão (padrão: soma 1 ao último número)")
    parser.add_argument("--sem-mudar", action="store_true", help="não mexe no número da versão")
    parser.add_argument("--so-versao", action="store_true",
                        help="só muda o número da versão, sem gerar o zip do código")
    args = parser.parse_args(argv)
    current = read_version(folder)
    if args.sem_mudar:
        version = current
    else:
        version = args.versao or next_version(current)
        if not updater.is_newer(version, current):
            raise PackError("A versão %s não é maior que a atual (%s)." % (version, current))
        write_version(folder, version)
    if args.so_versao:
        print("Versão %s definida em version.py." % version)
        print("Agora rode o compilar.bat e envie o zip do executável no painel.")
        return version
    path = build_zip(folder, os.path.join(folder, "dist_update"), version)
    print("Versão %s pronta: %s" % (version, path))
    print("Zip do código pronto. No painel ele é opcional: o principal é o zip do executável "
          "gerado pelo compilar.bat.")
    return path


if __name__ == "__main__":
    try:
        main()
    except PackError as e:
        print("Erro: %s" % e)
        sys.exit(1)
