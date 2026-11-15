"""Prepara uma Release do GitHub: copia os pacotes e escreve o version.json.

Uso (depois de compilar.py e, se quiser, empacotar.py):
    python gerar_version_json.py 1.0.10 --tipo importante --notas "O que mudou"
    python gerar_version_json.py 1.0.10 --obrigatoria          (todos abaixo dela precisam atualizar)
    python gerar_version_json.py 1.0.10 --min-versao 1.0.9     (só quem está abaixo da 1.0.9 é obrigado)

Cria a pasta release/<versão>/ com AudioMail-<versão>-exe.zip, o
AudioMail-<versão>-source.zip (se existir) e o version.json. Depois é só criar a
Release "v<versão>" no GitHub e anexar os arquivos dessa pasta, por exemplo:
    gh release create v1.0.10 release/1.0.10/* --title "AudioMail 1.0.10" --notes "O que mudou"
O version.json precisa ir junto: é ele que o atualizador lê.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

import updater

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = {
    "exe": os.path.join("saida_portatil", "AudioMail-%s-exe.zip"),
    "source": os.path.join("dist_update", "AudioMail-%s-source.zip"),
}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_url(version, filename):
    return "%sv%s/%s" % (updater.PACKAGE_PREFIX, version, filename)


def build_manifest(version, packages, kind="importante", notes="", mandatory=False, min_version=None):
    """O conteúdo do version.json. ``packages`` é {"exe"|"source": caminho do zip}."""
    updater.parse_version(version)
    if kind not in ("novidade", "importante", "urgente"):
        raise ValueError("Tipo inválido: %s" % kind)
    if "exe" not in packages:
        raise ValueError("Falta o zip do executável (AudioMail-%s-exe.zip)." % version)
    data = {"version": version, "type": kind, "notes": notes, "mandatory": bool(mandatory)}
    if min_version:
        updater.parse_version(min_version)
        data["min_version"] = min_version
    for name in ("source", "exe"):
        path = packages.get(name)
        if path:
            data[name + "_url"] = package_url(version, os.path.basename(path))
            data[name + "_sha256"] = sha256_of(path)
    for name in ("source", "exe"):  # a mesma checagem que o atualizador faz
        if data.get(name + "_url"):
            updater._check_url(data[name + "_url"], updater.BASE_URL, True)
    return data


def main(argv=None, folder=HERE):
    parser = argparse.ArgumentParser(description="Prepara uma Release do AudioMail no GitHub.")
    parser.add_argument("versao")
    parser.add_argument("--tipo", default="importante", choices=("novidade", "importante", "urgente"))
    parser.add_argument("--notas", default="")
    parser.add_argument("--obrigatoria", action="store_true")
    parser.add_argument("--min-versao")
    args = parser.parse_args(argv)
    packages = {}
    for name, pattern in SOURCES.items():
        path = os.path.join(folder, pattern % args.versao)
        if os.path.isfile(path):
            packages[name] = path
    try:
        data = build_manifest(args.versao, packages, args.tipo, args.notas, args.obrigatoria, args.min_versao)
    except (ValueError, updater.UpdateError) as e:
        print("Erro:", e)
        return 1
    out = os.path.join(folder, "release", args.versao)
    os.makedirs(out, exist_ok=True)
    for path in packages.values():
        shutil.copy2(path, out)
    with open(os.path.join(out, updater.MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Pronto: %s" % out)
    for name in sorted(os.listdir(out)):
        print("  " + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
