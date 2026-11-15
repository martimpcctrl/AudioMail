"""Imprimir uma mensagem pela janela normal de impressão do Windows."""
import html

import i18n


def message_html(title, text):
    """A mensagem como página simples: o assunto em destaque e o texto linha por linha."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    body = "<br>\n".join(html.escape(line).replace("  ", "&nbsp; ") for line in lines)
    return ('<html><head><meta charset="utf-8"></head><body>'
            '<font face="Segoe UI"><h3>%s</h3><p>%s</p></font></body></html>'
            % (html.escape(title or ""), body))


def print_message(parent, title, text):
    """Abre a janela de impressão. Devolve True se a pessoa mandou imprimir."""
    import wx.html
    printer = wx.html.HtmlEasyPrinting(i18n.tr("Imprimir"), parent)
    printer.SetFooter(i18n.tr("Página @PAGENUM@ de @PAGESCNT@"))
    return bool(printer.PrintText(message_html(title, text)))
