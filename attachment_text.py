"""Texto dos anexos para ler dentro do AudioMail. Sem interface.

PDF (com a biblioteca pypdf), Word (.docx), Excel (.xlsx), PowerPoint (.pptx),
LibreOffice (.odt, .ods, .odp), RTF, HTML, e-mails anexados (.eml) e
qualquer arquivo de texto. Os formatos do Office e do LibreOffice são arquivos
zip com XML dentro: são lidos aqui mesmo, sem programa nenhum instalado.
"""
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET

import i18n
import message_text as mt

MAX_XML = 40 * 1024 * 1024     # protege contra zip que "explode" ao descompactar
MAX_ROWS = 3000

TEXT_EXT = {".txt", ".csv", ".tsv", ".md", ".log", ".json", ".xml", ".ini", ".cfg", ".srt",
            ".vtt", ".py", ".js", ".css", ".yaml", ".yml"}
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/tiff",
               "image/heic", "image/heif"}


class Unreadable(Exception):
    """O anexo não tem texto que o AudioMail consiga ler (a mensagem diz por quê)."""


def kind_of(name, ctype=""):
    """'image', 'text' (dá para ler) ou None."""
    ext = os.path.splitext(name or "")[1].lower()
    ctype = (ctype or "").lower()
    if ctype.startswith("image/") or ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
                                             ".tif", ".tiff", ".heic"):
        return "image"
    if ext in TEXT_EXT or ext in (".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".rtf",
                                  ".htm", ".html", ".eml", ".doc", ".xls", ".ppt") \
            or ctype.startswith("text/") \
            or ctype in ("application/pdf", "message/rfc822"):
        return "text"
    return None


def _decode(data):
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", "replace")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _zip_xml(zf, member):
    info = zf.getinfo(member)
    if info.file_size > MAX_XML:
        raise Unreadable("O anexo é grande demais para ler aqui.")
    return ET.fromstring(zf.read(member))


def _open_zip(data):
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise Unreadable("O arquivo parece estar corrompido.")


def docx_text(data):
    zf = _open_zip(data)
    try:
        root = _zip_xml(zf, "word/document.xml")
    except KeyError:
        raise Unreadable("O arquivo parece estar corrompido.")
    lines = []

    def para(p):
        out = []
        for el in p.iter():
            name = _local(el.tag)
            if name == "t" and el.text:
                out.append(el.text)
            elif name == "tab":
                out.append("\t")
            elif name in ("br", "cr"):
                out.append("\n")
        return "".join(out)

    body = next((el for el in root if _local(el.tag) == "body"), root)
    for el in body:
        name = _local(el.tag)
        if name == "p":
            lines.append(para(el))
        elif name == "tbl":
            for row in el.iter():
                if _local(row.tag) == "tr":
                    cells = [" ".join(para(p) for p in cell.iter() if _local(p.tag) == "p").strip()
                             for cell in row if _local(cell.tag) == "tc"]
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref or "")
    n = 0
    for ch in (letters.group(0) if letters else ""):
        n = n * 26 + ord(ch) - 64
    return max(n - 1, 0)


def xlsx_text(data):
    zf = _open_zip(data)
    names = set(zf.namelist())
    shared = []
    if "xl/sharedStrings.xml" in names:
        for si in _zip_xml(zf, "xl/sharedStrings.xml"):
            shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
    sheets = []
    if "xl/workbook.xml" in names:
        for el in _zip_xml(zf, "xl/workbook.xml").iter():
            if _local(el.tag) == "sheet":
                sheets.append(el.get("name", ""))
    files = sorted((n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
                   key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    out, rows_done = [], 0
    for i, member in enumerate(files):
        title = sheets[i] if i < len(sheets) else i18n.tr("Planilha %d") % (i + 1)
        out.append("== %s ==" % title)
        for row in _zip_xml(zf, member).iter():
            if _local(row.tag) != "row":
                continue
            cells = {}
            for c in row:
                if _local(c.tag) != "c":
                    continue
                kind, value = c.get("t"), None
                for sub in c:
                    if _local(sub.tag) == "v":
                        value = sub.text
                    elif _local(sub.tag) == "is":
                        value = "".join(t.text or "" for t in sub.iter() if _local(t.tag) == "t")
                if kind == "s" and value is not None:
                    try:
                        value = shared[int(value)]
                    except (ValueError, IndexError):
                        pass
                elif kind == "b" and value is not None:
                    value = i18n.tr("VERDADEIRO") if value == "1" else i18n.tr("FALSO")
                if value not in (None, ""):
                    cells[_col_index(c.get("r"))] = value
            if cells:
                width = max(cells) + 1
                out.append(" | ".join(cells.get(j, "") for j in range(width)).rstrip(" |"))
                rows_done += 1
                if rows_done >= MAX_ROWS:
                    out.append(i18n.tr("(planilha cortada em %d linhas)") % MAX_ROWS)
                    return "\n".join(out)
        out.append("")
    return "\n".join(out)


def pptx_text(data):
    zf = _open_zip(data)
    slides = sorted((n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                    key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    out = []
    for i, member in enumerate(slides, 1):
        out.append("== %s ==" % (i18n.tr("Slide %d") % i))
        for p in _zip_xml(zf, member).iter():
            if _local(p.tag) == "p":
                line = "".join(t.text or "" for t in p.iter() if _local(t.tag) == "t").strip()
                if line:
                    out.append(line)
        out.append("")
    return "\n".join(out)


def odf_text(data):
    zf = _open_zip(data)
    try:
        root = _zip_xml(zf, "content.xml")
    except KeyError:
        raise Unreadable("O arquivo parece estar corrompido.")
    out = []

    def text_of(el):
        parts = [el.text or ""]
        for child in el:
            name = _local(child.tag)
            if name == "s":
                parts.append(" " * int(child.get("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}c", "1")))
            elif name == "tab":
                parts.append("\t")
            elif name == "line-break":
                parts.append("\n")
            else:
                parts.append(text_of(child))
            parts.append(child.tail or "")
        return "".join(parts)

    def walk(el):
        for child in el:
            name = _local(child.tag)
            if name in ("p", "h"):
                out.append(text_of(child))
            elif name == "table-row":
                cells = [" ".join(text_of(p) for p in cell.iter() if _local(p.tag) == "p")
                         for cell in child if _local(cell.tag) == "table-cell"]
                line = " | ".join(cells).rstrip(" |")
                if line:
                    out.append(line)
            elif name == "table":
                out.append("== %s ==" % child.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name", ""))
                walk(child)
            else:
                walk(child)

    walk(root)
    return "\n".join(out)


def rtf_text(data):
    text = _decode(data)
    text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("cp1252", "replace"), text)
    text = re.sub(r"\\u(-?\d+)\??", lambda m: chr(int(m.group(1)) % 65536), text)
    text = re.sub(r"\\(par|line)\b ?", "\n", text)
    text = re.sub(r"\\tab\b ?", "\t", text)
    text = re.sub(r"\{\\\*[^{}]*\}", "", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    return text.replace("{", "").replace("}", "").replace("\\\\", "\\")


def pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise Unreadable("Esta cópia do AudioMail não tem o leitor de PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise Unreadable("O PDF tem senha.")
        pages = []
        for i, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            pages.append("== %s ==\n%s" % (i18n.tr("Página %d") % i, text) if len(reader.pages) > 1 else text)
    except Unreadable:
        raise
    except Exception:
        raise Unreadable("Não foi possível ler este PDF.")
    joined = "\n\n".join(pages)
    if not re.sub(r"(?m)^== .* ==$|\s", "", joined):
        raise Unreadable("Este PDF não tem texto, só imagens (pode ser um documento escaneado).")
    return joined


def eml_text(data):
    import mail_core as mc
    full = mc.parse_full_message(data, "0")
    return mc.full_to_text(full)


def extract_text(name, ctype, data):
    """O texto do anexo, pronto para ler. Levanta Unreadable se não der."""
    ext = os.path.splitext(name or "")[1].lower()
    ctype = (ctype or "").lower()
    if ext == ".pdf" or ctype == "application/pdf":
        text = pdf_text(data)
    elif ext == ".docx":
        text = docx_text(data)
    elif ext == ".xlsx":
        text = xlsx_text(data)
    elif ext == ".pptx":
        text = pptx_text(data)
    elif ext in (".odt", ".ods", ".odp"):
        text = odf_text(data)
    elif ext == ".rtf":
        text = rtf_text(data)
    elif ext in (".htm", ".html") or ctype == "text/html":
        text, _ = mt.html_to_readable(_decode(data))
    elif ext == ".eml" or ctype == "message/rfc822":
        text = eml_text(data)
    elif ext in TEXT_EXT or ctype.startswith("text/"):
        text = _decode(data)
    elif ext in (".doc", ".xls", ".ppt"):
        raise Unreadable("Arquivos antigos do Office (.doc, .xls, .ppt) não dão para ler aqui. "
                         "Use Abrir anexo.")
    else:
        raise Unreadable("O AudioMail não sabe ler esse tipo de arquivo. Use Abrir anexo.")
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if not text:
        raise Unreadable("O anexo está vazio.")
    return text
