"""Gera o manual do AudioMail (MANUAL.html e MANUAL.txt) a partir do manual_fonte.txt."""
import html
import os
import re
import sys

SOURCE_NAME = "manual_fonte.txt"


def slug(text):
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "-", text).strip("-")


def _inline(text):
    out = html.escape(text, quote=False)
    out = re.sub(r"(https?://[^\s<)]+)", r'<a href="\1">\1</a>', out)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", out)


def to_html(source, version, language="pt"):
    source = source.replace("{{versao}}", version)
    parts, toc, title = [], [], "Manual do AudioMail"
    lines = source.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
        elif line.startswith("# "):
            title = line[2:]
            parts.append("<h1>%s</h1>" % _inline(title))
            parts.append("@@TOC@@")
            i += 1
        elif line.startswith("## "):
            name = line[3:]
            toc.append((slug(name), name))
            parts.append('<h2 id="%s">%s</h2>' % (slug(name), _inline(name)))
            i += 1
        elif line.startswith("### "):
            parts.append("<h3>%s</h3>" % _inline(line[4:]))
            i += 1
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li>%s</li>" % _inline(lines[i][2:].strip()))
                i += 1
            parts.append("<ul>%s</ul>" % "".join(items))
        elif re.match(r"\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append("<li>%s</li>" % _inline(re.sub(r"^\d+\. ", "", lines[i]).strip()))
                i += 1
            parts.append("<ol>%s</ol>" % "".join(items))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r"(#|- |\d+\. )", lines[i]):
                para.append(lines[i].strip())
                i += 1
            parts.append("<p>%s</p>" % _inline(" ".join(para)))
    toc_label = {"en": "Contents", "es": "Índice"}.get(language, "Índice")
    toc_items = "".join('<li><a href="#%s">%s</a></li>' % (slug(name), html.escape(name))
                        for _, name in toc)
    nav = '<nav aria-label="%s"><h2>%s</h2><ul>%s</ul></nav>' % (
        toc_label, toc_label, toc_items)
    body = "\n".join(parts).replace("@@TOC@@", nav)
    css = ("body{font-family:Arial,sans-serif;font-size:1.15rem;line-height:1.55;max-width:50rem;"
           "margin:0 auto;padding:1rem;color:#111;background:#fff}h1,h2{border-bottom:2px solid #0066cc}"
           "a{color:#0044aa}a:focus{outline:4px solid #ff9900}code{background:#eee;padding:0 .2rem}")
    html_language = {"pt": "pt-BR", "en": "en", "es": "es"}.get(language, "pt-BR")
    return ('<!DOCTYPE html><html lang="%s"><head><meta charset="utf-8"><title>%s</title>'
            '<style>%s</style></head><body><main>%s</main></body></html>\n'
            % (html_language, html.escape(title), css, body))


def to_text(source, version):
    source = source.replace("{{versao}}", version).replace("\r\n", "\n")
    out = []
    for line in source.split("\n"):
        if line.startswith("# "):
            out += [line[2:].upper(), "=" * len(line[2:]), ""]
        elif line.startswith("## "):
            out += ["", line[3:].upper(), "-" * len(line[3:])]
        elif line.startswith("### "):
            out += ["", line[4:]]
        else:
            out.append(line.replace("`", ""))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"


def write_manual(source, folder, version, language="pt"):
    """Grava MANUAL.html e MANUAL.txt na pasta. Devolve o caminho do HTML."""
    os.makedirs(folder, exist_ok=True)
    html_path = os.path.join(folder, "MANUAL.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(to_html(source, version, language))
    with open(os.path.join(folder, "MANUAL.txt"), "w", encoding="utf-8-sig") as f:
        f.write(to_text(source, version).replace("\n", "\r\n"))
    return html_path


def find_source(app_dir):
    """Acha o manual_fonte.txt (ao lado do programa, no pacote do executavel ou na pasta do app)."""
    candidates = [getattr(sys, "_MEIPASS", None), app_dir,
                  os.path.dirname(os.path.abspath(sys.executable))]
    for folder in candidates:
        if folder and os.path.isfile(os.path.join(folder, SOURCE_NAME)):
            return os.path.join(folder, SOURCE_NAME)
    raise FileNotFoundError("Não encontrei o " + SOURCE_NAME)



MANUAL_EN = """# AudioMail User Guide {{versao}}

## What is AudioMail?
AudioMail is an accessible Gmail app for reading and writing email with a keyboard and a screen reader such as NVDA. It can notify you when messages arrive, stay in the Windows system tray, and update itself.

## Getting started
- Open AudioMail.exe. No installation is required. Choose the interface language the first time you run it.
- Enter your email address and Google app password. An app password is different from your normal Gmail password; Google creates a 16-character password for this app.
- Select Create an app password in the sign-in window to open https://myaccount.google.com/apppasswords. Sign in, create a password for AudioMail, then copy and paste it into the App password field. Spaces are accepted.
- If the page is unavailable, enable 2-Step Verification at https://myaccount.google.com/security. School or work accounts may have this feature disabled by an administrator.
- Leave Remember password on this computer selected to sign in automatically next time.

## Main window
Tab moves through Account (when you have more than one), Folder, Search, and Messages. Folder contains Inbox, Drafts, Sent, Trash, and other Gmail folders. The list shows read status, sender, subject, and date. F6 moves to folders, F7 to accounts, and Ctrl+F to Search. The status bar shows message and unread counts.

## Read and reply
- Press Enter on a message to open it. Read its text with the arrow keys.
- Use Reply, Reply all, or Close. Escape also closes the message.
- For attachments, choose Open attachment, Save attachment, or Save all attachments.
- Ctrl+R replies and Ctrl+Shift+R replies to all from the message list.
- Delete moves a message to Gmail Trash after confirmation. Ctrl+Shift+L marks it read; Ctrl+Shift+U marks it unread.

## Write a message
- Ctrl+N opens a new message. The fields are To, Cc, Bcc, Subject, Message body, and Attachments.
- Use Add attachment and Remove attachment to manage files. Gmail allows about 18 MB of attachments per message.
- Separate multiple recipients with a comma or semicolon. Ctrl+Enter sends from any field.
- Ctrl+S saves a draft to Gmail Drafts. If you cancel a changed message, AudioMail asks whether to save it.
- Set your automatic signature in Settings. It is added to new messages and replies.

## Translate
- Press Ctrl+T on a message to open and translate it, or open it and select Translate.
- The translation appears in the reading field. The button switches between View original and View translation. Email headers are not translated; each message in a conversation is translated separately.
- AudioMail lets you know when a message is already in the target language.
- To write in another language, write your message, choose Translate text, and select a language. The subject and body are translated. Undo translation restores your text.
- Choose the target language for received messages in Settings.
- The first time you translate, AudioMail asks permission to send text to Google Translate. Change this permission in Settings. Only text you ask to translate is sent.
- Machine translation can be inaccurate. Review results before relying on them. Long messages take longer; temporary service limits may require waiting a few minutes.

## AI summaries
Open a message and choose Summarize with AI. The first time, AudioMail asks permission before sending text to the provider. In Settings > AI summary, choose OpenAI, Gemini, or another OpenAI-compatible service, then enter its model and your own API key. For another service, enter its base URL too. The key is protected with Windows encryption on this computer. API usage may be billed by the provider; a ChatGPT subscription does not automatically include API usage. The message text and headers are sent for the summary; attachments are not.

## Search and conversations
Press Ctrl+F, enter a search, and press Enter. Search checks sender, subject, and message text in the current folder and supports accented characters. Escape clears the search. Ctrl+G turns conversation grouping on or off; it is off by default. With grouping on, each row is a conversation. Press Enter to read it from oldest to newest.

## Multiple accounts
Choose File > Add account to connect another Gmail account. Use F7 to switch accounts. Each account can notify you about new messages. File > Remove current account removes it from AudioMail; messages remain in Gmail.

## Alerts, sound, and speech
AudioMail keeps a connection to Gmail so alerts usually arrive within seconds. In Settings, enable or disable Windows notifications, a sound, and screen-reader speech independently. Choose Settings > Preferences > Choose sound to select a WAV file. Convert MP3 files to WAV first. AudioMail reconnects if the connection drops.

## Windows system tray
Closing the window keeps AudioMail running in the tray. Press Windows+B, select the AudioMail icon, and press Enter to reopen it. The icon menu includes Open AudioMail, Check now, Settings, and Exit. Ctrl+M hides the window in the tray; Ctrl+Q exits.

## Reminder calendar
Choose Tools > Calendar. The table shows every day of the selected month, with reminders and national holidays on their dates. Use Ctrl+Left/Right to change the month and Ctrl+Up/Down to change the year. Use the single Add reminder button or select a day and choose Delete selected reminder. Holiday dates come from a public API without an API key and are cached locally for offline viewing. AudioMail shows a Windows notification and announces a reminder with the screen reader when it is due. Reminders are stored only on this computer. AudioMail must be running (it may stay in the tray) to notify you.

## Settings
Open Settings > Preferences or press Ctrl+P. Options are grouped into Language and translation, New message alerts, Window and startup, and Other settings. Choose the interface language (restart AudioMail to apply it), translation language and permission, check interval, real-time delivery, notifications, sound, screen-reader speech, tray behavior, Windows startup, automatic updates, notification sound, and signature.

## Updates
AudioMail checks at startup and every six hours. Choose Help > Check for updates to check now. Optional updates can be installed later or skipped. Recommended updates notify you but let you choose when to install. Urgent updates open a window immediately and cannot be skipped. Required updates must be installed to continue using the app. AudioMail checks the downloaded file and restarts after installation.

## Portable mode
The portable package stores data in the `dados` folder beside AudioMail.exe, not in the Windows profile. Copy the complete AudioMail-Portatil folder to move it to another computer. The interface language and account settings are stored with that portable copy.
"""

MANUAL_ES = """# Manual de usuario de AudioMail {{versao}}

## ¿Qué es AudioMail?
AudioMail es una aplicación accesible para leer y escribir correos de Gmail con el teclado y un lector de pantalla como NVDA. Avisa cuando llegan mensajes, permanece en la bandeja del sistema de Windows y se actualiza automáticamente.

## Primeros pasos
- Abre AudioMail.exe. No hace falta instalarlo. La primera vez, elige el idioma de la interfaz.
- Introduce tu correo electrónico y la contraseña de aplicación de Google. Esta contraseña no es la normal de Gmail; Google crea una de 16 caracteres para esta aplicación.
- En la ventana de acceso, pulsa Crear contraseña de aplicación para abrir https://myaccount.google.com/apppasswords. Inicia sesión, crea una contraseña para AudioMail y pégala en el campo correspondiente. Puedes incluir los espacios.
- Si la página no está disponible, activa la verificación en dos pasos en https://myaccount.google.com/security. El administrador puede bloquear esta opción en cuentas de centros educativos o empresas.
- Deja marcada la opción Recordar la contraseña en este equipo para iniciar sesión automáticamente la próxima vez.

## Ventana principal
Tab recorre Cuenta (si tienes más de una), Carpeta, Buscar y Mensajes. Carpeta contiene Recibidos, Borradores, Enviados, Papelera y las demás carpetas de Gmail. La lista muestra el estado de lectura, remitente, asunto y fecha. F6 va a las carpetas, F7 a las cuentas y Ctrl+F a Buscar. La barra de estado muestra el total y los mensajes sin leer.

## Leer y responder
- Pulsa Enter sobre un mensaje para abrirlo. Lee el texto con las flechas.
- Usa Responder, Responder a todos o Cerrar. Escape también cierra el mensaje.
- Para los adjuntos, elige Abrir adjunto, Guardar adjunto o Guardar todos los adjuntos.
- Ctrl+R responde y Ctrl+Shift+R responde a todos desde la lista.
- Delete mueve el mensaje a la Papelera de Gmail tras pedir confirmación. Ctrl+Shift+L lo marca como leído y Ctrl+Shift+U como no leído.

## Escribir un mensaje
- Ctrl+N abre un mensaje nuevo. Los campos son Para, CC, CCO, Asunto, Texto del mensaje y Adjuntos.
- Usa Añadir adjunto y Quitar adjunto para gestionar archivos. Gmail permite unos 18 MB de adjuntos por mensaje.
- Separa las direcciones con coma o punto y coma. Ctrl+Enter envía desde cualquier campo.
- Ctrl+S guarda un borrador en Gmail. Si cancelas un mensaje modificado, AudioMail pregunta si quieres guardarlo.
- Configura la firma automática en Configuración; se añade a mensajes nuevos y respuestas.

## Traducir
- Pulsa Ctrl+T sobre un mensaje para abrirlo y traducirlo, o ábrelo y selecciona Traducir.
- La traducción aparece en el campo de lectura. El botón alterna entre Ver original y Ver traducción. Los encabezados no se traducen; cada mensaje de una conversación se traduce por separado.
- AudioMail avisa si el mensaje ya está en el idioma de destino.
- Para escribir en otro idioma, redacta el mensaje, elige Traducir texto y selecciona el idioma. Se traducen el asunto y el texto. Deshacer traducción recupera el original.
- Elige en Configuración el idioma de destino para los mensajes recibidos.
- La primera vez, AudioMail pide permiso para enviar texto a Google Translate. Puedes cambiarlo en Configuración. Solo se envía el texto que solicites traducir.
- La traducción automática puede contener errores. Revisa el resultado. Los mensajes largos tardan más y los límites temporales del servicio pueden requerir esperar unos minutos.

## Resumir con IA
Abre un mensaje y elige Resumir con IA. La primera vez, AudioMail pide permiso antes de enviar el texto al proveedor. En Configuración > Resumen con IA, elige OpenAI, Gemini u otro servicio compatible con la API OpenAI e indica el modelo y tu propia clave de API. Para otro servicio, indica también la URL base. La clave se protege con el cifrado de Windows en este equipo. El proveedor puede cobrar por el uso de la API; la suscripción de ChatGPT no incluye automáticamente el uso de la API. Se envían el texto y los encabezados del mensaje; no se envían los adjuntos.

## Buscar y conversaciones
Pulsa Ctrl+F, escribe la búsqueda y pulsa Enter. Se busca en el remitente, el asunto y el texto de la carpeta actual; se admiten tildes. Escape borra la búsqueda. Ctrl+G activa o desactiva la agrupación por conversación, desactivada de forma predeterminada. Al activarla, cada fila representa una conversación. Pulsa Enter para leerla de más antigua a más reciente.

## Varias cuentas
Elige Archivo > Añadir cuenta para conectar otra cuenta de Gmail. Usa F7 para cambiar de cuenta. Todas pueden avisarte de mensajes nuevos. Archivo > Eliminar cuenta actual la quita de AudioMail; los mensajes siguen en Gmail.

## Avisos, sonido y voz
AudioMail mantiene una conexión con Gmail para que los avisos lleguen normalmente en pocos segundos. En Configuración puedes activar por separado las notificaciones de Windows, un sonido y el aviso del lector de pantalla. Ve a Configuración > Preferencias > Elegir sonido para seleccionar un archivo WAV. Convierte los MP3 a WAV antes. AudioMail se reconecta si pierde la conexión.

## Bandeja del sistema de Windows
Al cerrar la ventana, AudioMail sigue ejecutándose en la bandeja. Pulsa Windows+B, selecciona su icono y pulsa Enter para volver a abrirlo. El menú incluye Abrir AudioMail, Comprobar ahora, Configuración y Salir. Ctrl+M oculta la ventana; Ctrl+Q cierra la aplicación.

## Calendario de recordatorios
Elige Herramientas > Calendario. La tabla muestra todos los días del mes seleccionado, con recordatorios y festivos nacionales en sus fechas. Usa Ctrl+Izquierda/Derecha para cambiar el mes y Ctrl+Arriba/Abajo para cambiar el año. Usa el único botón Añadir recordatorio o selecciona un día y pulsa Eliminar recordatorio seleccionado. Las fechas festivas se obtienen de una API pública sin clave y se guardan localmente para consultarlas sin conexión. AudioMail muestra una notificación de Windows y anuncia el recordatorio con el lector de pantalla cuando llega la hora. Los recordatorios se guardan solo en este equipo. AudioMail debe estar abierto (puede quedarse en la bandeja) para avisarte.

## Configuración
Abre Configuración > Preferencias o pulsa Ctrl+P. Las opciones se agrupan en Idioma y traducción, Avisos de mensajes nuevos, Ventana e inicio y Otras opciones. Puedes elegir el idioma de la interfaz (reinicia AudioMail para aplicarlo), el idioma de traducción y su permiso, el intervalo de comprobación, recepción en tiempo real, notificaciones, sonido, voz del lector, comportamiento en la bandeja, inicio con Windows, actualizaciones automáticas, sonido y firma.

## Actualizaciones
AudioMail busca actualizaciones al abrirse y cada seis horas. Elige Ayuda > Buscar actualizaciones para comprobarlo ahora. Las opcionales se pueden instalar más tarde u omitir. Las recomendadas avisan, pero permiten elegir cuándo instalarlas. Las urgentes abren una ventana y no se pueden omitir. Las obligatorias deben instalarse para continuar usando la aplicación. AudioMail comprueba el archivo y se reinicia tras instalarlo.

## Modo portátil
El paquete portátil guarda los datos en la carpeta `dados`, junto a AudioMail.exe, y no en el perfil de Windows. Copia toda la carpeta AudioMail-Portatil para llevarlo a otro equipo. El idioma y la configuración de las cuentas se guardan en esa copia.
"""

def ensure_manual(folder, app_dir, version, language="pt"):
    if language == "en":
        return write_manual(MANUAL_EN, folder, version, "en")
    if language == "es":
        return write_manual(MANUAL_ES, folder, version, "es")
    with open(find_source(app_dir), encoding="utf-8") as f:
        return write_manual(f.read(), folder, version)
