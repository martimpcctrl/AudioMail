"""Politica de privacidade, termos de uso e aceite obrigatorio do AudioMail."""
import datetime

import wx

import i18n


# Altere este identificador sempre que o texto legal mudar. Usuarios existentes
# que ainda nao o aceitaram voltarao a ver a tela obrigatoria.
LEGAL_VERSION = "2026-11-17-1"
CONTACT_EMAIL = "martimpc318@gmail.com"

DOCUMENTS = {
    "pt": {
        "privacy": ("Política de privacidade", """POLÍTICA DE PRIVACIDADE DO AUDIOMAIL
Versão 5 — 17 de novembro de 2026

1. Quem responde e como falar
Martim Alves é o responsável pelo AudioMail. Para exercer direitos sobre dados ou fazer perguntas de privacidade, escreva para martimpc318@gmail.com. Também é possível abrir um chamado em Ajuda > Abrir chamado de suporte.

2. O que o AudioMail trata
• Dados da conta de e-mail que você informa (endereço e senha de aplicativo). A senha só é salva se você escolher lembrá-la e é protegida pelas funções de segurança do Windows neste usuário e computador. As configurações, preferências, lembretes, chaves de API de IA cifradas e protocolos dos chamados ficam no computador ou na pasta portátil, conforme a instalação.
• Mensagens, contatos, anexos e pastas são obtidos do provedor de e-mail para mostrar as funções solicitadas. O AudioMail não envia cópias dessas mensagens ao responsável pelo aplicativo.
• Para a lista abrir na hora e para ler sem internet, o AudioMail guarda neste computador, no arquivo mensagens.db da pasta de dados, a lista de pastas, a lista de mensagens de cada pasta e o texto das mensagens que você abre (os anexos só se você ligar essa opção). O arquivo é criptografado pela proteção do Windows deste usuário e computador e não é enviado a ninguém. Em Configurações > Mensagens guardadas no computador você desliga o recurso, escolhe por quantos dias guardar e apaga tudo; ao remover uma conta, o que estava guardado dela também é apagado. Os contatos e grupos que você cria ficam no arquivo contatos.json, também só neste computador.
• Se você ligar o bloqueio com PIN, o PIN não é guardado: fica só, nas configurações deste computador, um código derivado dele que não permite descobrir o PIN. Se ligar o Windows Hello, a verificação do rosto, da digital ou do PIN do Windows é feita pelo próprio Windows; o AudioMail só recebe a resposta "confirmado" ou "não confirmado" e nunca recebe nem guarda imagens do rosto ou digitais.
• Se você abrir um chamado, o aplicativo envia ao servidor de suporte o assunto, tipo, texto do chamado e versão do AudioMail. O chamado é armazenado no painel de suporte para atendimento. Não são enviados automaticamente e-mail da conta, mensagens ou anexos. O servidor e o provedor de hospedagem podem tratar dados técnicos da conexão, como endereço IP, para entregar e proteger o serviço.
• Se você pedir um resumo com IA, o conteúdo da mensagem ou conversa escolhido e as instruções do resumo são enviados ao provedor selecionado (OpenAI, Google Gemini ou endpoint compatível que você configurar), com a chave de API que você forneceu. O provedor trata os dados conforme seus próprios termos e políticas; não informe conteúdo que não queira compartilhar com esse provedor. A chave fica cifrada localmente. O recurso só envia conteúdo quando você pede e confirma autorização.
• Do mesmo jeito, se você pedir a descrição de uma imagem (anexo ou imagem dentro do e-mail), a imagem é enviada a esse provedor; e se usar Escrever com IA, o que você escreveu como ideia e a mensagem que está sendo respondida são enviados a ele. Cada recurso pede autorização na primeira vez. Os anexos lidos como texto (PDF, Word, Excel...) são lidos no seu computador e não são enviados a ninguém.
• Se você pedir tradução, o texto selecionado é enviado ao serviço Google Translate. A autorização é solicitada antes do primeiro envio e pode ser alterada nas configurações.
• O calendário pode consultar feriados nacionais na API pública Nager.Date. Os resultados são guardados em cache local; a consulta transmite o ano solicitado e dados técnicos da conexão ao serviço.
• A verificação de atualizações acessa o GitHub (github.com, serviço da GitHub, Inc., empresa da Microsoft), onde o AudioMail é publicado, para consultar versões e, quando você instala, baixar arquivos. Essa comunicação inclui os dados técnicos usuais de uma conexão web.

3. Finalidades e bases
Os dados locais são usados para executar as funções escolhidas e guardar suas preferências. O conteúdo enviado por você a tradutores, provedores de IA, provedor de e-mail ou suporte é tratado para realizar a função solicitada, com as permissões e instruções que você fornece. O aceite desta política e dos termos registra sua decisão de usar o aplicativo; ele não substitui as autorizações específicas para tradução e resumo com IA.

4. Compartilhamento, armazenamento e segurança
O AudioMail não possui uma conta central nem sincroniza suas configurações. Dados locais permanecem no seu computador até você removê-los ou desinstalar/apagar a pasta de dados. Os provedores de e-mail, tradução, IA, hospedagem e feriados recebem apenas os dados necessários à função que você aciona e podem tratá-los sob suas próprias políticas. Não controlamos os prazos de retenção desses terceiros. São usadas conexões HTTPS quando disponíveis e proteção do Windows para segredos salvos localmente; nenhum sistema pode prometer segurança absoluta.

5. Seus direitos
Nos termos da LGPD, você pode pedir confirmação e acesso, correção, informação sobre compartilhamentos, anonimização, bloqueio ou eliminação quando aplicável, portabilidade nos limites legais e revogação de consentimentos. Escreva para o contato acima. A resposta pode exigir confirmação razoável de identidade e observar as hipóteses legais de conservação. Para conteúdo de e-mail e chaves guardados localmente, você também pode removê-los nas configurações ou nos dados do aplicativo.

6. Crianças, mudanças e vigência
O AudioMail é uma ferramenta geral, não direcionada a crianças. Esta política pode ser atualizada; alterações relevantes serão apresentadas novamente para aceite antes de continuar usando o AudioMail. A versão aceita e a data ficam salvas localmente. Esta política deve ser lida junto dos Termos de uso.
"""),
        "terms": ("Termos de uso", """TERMOS DE USO DO AUDIOMAIL
Versão 1 — 5 de novembro de 2026

1. Sobre o aplicativo
O AudioMail é um cliente para acessar contas de e-mail compatíveis, organizar mensagens, criar lembretes locais, consultar feriados, traduzir textos, solicitar resumos com IA e abrir chamados de suporte. É fornecido por Martim Alves.

2. Aceite e uso responsável
Ao selecionar “Li e aceito”, você confirma que teve acesso a estes Termos e à Política de privacidade e aceita usá-los como regras do aplicativo. Use o AudioMail somente em contas e conteúdos que esteja autorizado a acessar. Você é responsável por proteger sua senha de aplicativo, suas chaves de API e os dados exibidos ou enviados. Não use o programa para violar leis, direitos de terceiros, regras do provedor de e-mail ou termos dos serviços externos.

3. Provedores externos e recursos opcionais
O acesso ao e-mail depende do seu provedor e das credenciais fornecidas. Tradução, resumo com IA, consulta de feriados e atualizações dependem de serviços externos, que podem ficar indisponíveis ou mudar suas condições. Você escolhe e configura a chave, o provedor e o modelo de IA; custos de API, limites e regras são definidos pelo respectivo provedor. Confira os dados antes de enviar e não compartilhe informações que não queira encaminhar a terceiros. Resumos, traduções, descrições de imagens e textos escritos pela IA podem conter erros e devem ser conferidos antes de decisões ou envios.

4. Chamados e conteúdo
Ao abrir um chamado, você autoriza o envio dos campos mostrados no formulário para atendimento. Não inclua senhas nem dados desnecessários. O responsável pode concluir um chamado após o atendimento. Chamados não são um canal de emergência e não há prazo garantido de resposta.

5. Disponibilidade e responsabilidade
O aplicativo é fornecido no estado em que se encontra. Podem ocorrer falhas, incompatibilidades, interrupções ou perda de dados; mantenha cópias de segurança importantes e confira destinatários e conteúdo antes de enviar mensagens. Na máxima extensão permitida pela legislação brasileira, não há garantia de disponibilidade contínua nem de que serviços de terceiros funcionem sem erros. Nada nestes Termos reduz direitos obrigatórios assegurados pelo Código de Defesa do Consumidor ou por outras normas aplicáveis.

6. Atualizações, encerramento e mudanças
Atualizações podem corrigir falhas, alterar funções ou substituir estes Termos e a Política de privacidade. Quando houver mudança que exija novo aceite, o AudioMail pedirá que você leia e aceite a nova versão. Você pode parar de usar o aplicativo e apagar os dados locais; a remoção de chamados já enviados deve ser solicitada pelo contato da Política de privacidade e pode observar obrigações legais de retenção.

7. Lei e contato
Aplicam-se as leis da República Federativa do Brasil, preservadas as regras obrigatórias de proteção ao consumidor e de proteção de dados. Dúvidas: martimpc318@gmail.com ou Ajuda > Abrir chamado de suporte.
"""),
    },
    "en": {
        "privacy": ("Privacy policy", """AUDIOMAIL PRIVACY POLICY
Version 5 — November 17, 2026

1. Who is responsible and how to contact us
Martim Alves is responsible for AudioMail. For privacy questions or requests about personal data, email martimpc318@gmail.com. You can also open a ticket at Help > Open support ticket.

2. Data AudioMail handles
• The email account details you enter (address and app password). The password is saved only if you choose to remember it and is protected using Windows security for this user and computer. Settings, preferences, local reminders, encrypted AI API keys and ticket references are stored on your computer or portable folder, depending on your setup.
• Messages, contacts, attachments and folders are obtained from your email provider to provide requested features. AudioMail does not send copies of those messages to the app maintainer.
• So the list opens instantly and you can read without internet, AudioMail saves on this computer, in the mensagens.db file in the data folder, the folder list, the message list of each folder and the text of the messages you open (attachments only if you turn that option on). The file is encrypted by Windows protection for this user and computer and is not sent to anyone. In Settings > Messages saved on this computer you can turn the feature off, choose how many days to keep and delete everything; removing an account also deletes what was saved for it. The contacts and groups you create are kept in the contatos.json file, also only on this computer.
• If you turn on the PIN lock, the PIN itself is not stored: only a code derived from it, which does not reveal the PIN, is kept in this computer's settings. If you turn on Windows Hello, Windows itself checks your face, fingerprint or Windows PIN; AudioMail only receives "confirmed" or "not confirmed" and never receives or stores face images or fingerprints.
• When you submit a support ticket, the app sends its subject, type, text and AudioMail version to the support server. Tickets are stored in the support panel. Your email account, messages and attachments are not sent automatically. The server and hosting provider may process technical connection data, such as IP address, to deliver and protect the service.
• When you request an AI summary, the selected message or conversation and summary instructions are sent to your chosen provider (OpenAI, Google Gemini or a compatible endpoint you configure), using your API key. The provider processes data under its own terms and policies. Do not submit content you do not wish to share with that provider. The key is encrypted locally. Content is sent only when you request a summary and authorize it.
• In the same way, if you ask for an image description (an attachment or an image inside an email), the image is sent to that provider; and if you use Write with AI, the idea you typed and the message you are replying to are sent to it. Each feature asks for permission the first time. Attachments read as text (PDF, Word, Excel...) are read on your computer and are not sent to anyone.
• When you request translation, the selected text is sent to Google Translate. Permission is requested before the first transmission and can be changed in settings.
• The calendar may query national holidays from the public Nager.Date API. Results are cached locally; the requested year and technical connection data are sent to that service.
• Update checks contact GitHub (github.com, a service of GitHub, Inc., a Microsoft company), where AudioMail is published, for version information and, when you install an update, download files. This web connection includes ordinary technical connection data.

3. Purposes and legal grounds
Local data is used to run requested features and save preferences. Data you send to translators, AI providers, your email provider or support is processed to carry out the function you request, based on your permissions and instructions. Accepting this policy and the terms records your choice to use the app; it does not replace the separate permissions for translation and AI summaries.

4. Sharing, storage and security
AudioMail has no central account and does not sync your settings. Local data stays on your computer until you remove it or delete the app data folder. Email, translation, AI, hosting and holiday providers receive only data needed for the feature you use and may process it under their own policies. We do not control third-party retention periods. HTTPS is used where available and Windows protection is used for locally stored secrets; no system can promise absolute security.

5. Your rights
Under Brazil’s LGPD, you may request confirmation and access, correction, information about sharing, anonymization, blocking or deletion where applicable, portability within legal limits, and withdrawal of consent. Contact us above. A reasonable identity check may be needed, and legal retention duties may apply. You can also remove locally stored email credentials and API keys in the app settings or data folder.

6. Children, changes and effective date
AudioMail is a general-purpose tool and is not directed to children. This policy may change; material changes will be shown again for acceptance before you continue using AudioMail. The accepted version and date are stored locally. Read this policy with the Terms of Use.
"""),
        "terms": ("Terms of use", """AUDIOMAIL TERMS OF USE
Version 1 — November 5, 2026

1. About the app
AudioMail is an email client for compatible accounts. It can organize messages, create local reminders, look up holidays, translate text, request AI summaries and submit support tickets. It is provided by Martim Alves.

2. Acceptance and responsible use
By selecting “I have read and accept”, you confirm that these Terms and the Privacy Policy were made available to you and agree to use the app under these rules. Use AudioMail only with accounts and content you are authorized to access. You are responsible for protecting your app password, API keys and data you view or send. Do not use the app to violate laws, third-party rights, your email provider’s rules or external service terms.

3. External providers and optional features
Email access depends on your provider and credentials. Translation, AI summaries, holiday lookup and updates depend on external services that may be unavailable or change their terms. You choose and configure the AI key, provider and model; API fees, limits and rules are set by that provider. Review data before sending it, and do not share information you do not want to send to third parties. Summaries, translations, image descriptions and AI-written text can be wrong and should be checked before decisions or sending messages.

4. Support tickets and content
Submitting a ticket authorizes sending the fields shown in the form for support. Do not include passwords or unnecessary data. The maintainer may mark a ticket complete after handling it. Tickets are not an emergency channel and no response time is guaranteed.

5. Availability and responsibility
The app is provided as available. Failures, incompatibilities, interruptions or data loss may occur; keep backups of important information and check recipients and content before sending messages. To the fullest extent allowed by Brazilian law, continuous availability and error-free third-party services are not guaranteed. Nothing in these Terms limits mandatory rights under Brazil’s Consumer Defense Code or other applicable law.

6. Updates, ending use and changes
Updates may fix issues, change features or replace these Terms and the Privacy Policy. If a change requires renewed acceptance, AudioMail will ask you to read and accept the new version. You may stop using the app and delete local data; deletion of submitted tickets can be requested using the privacy contact and may be subject to legal retention duties.

7. Law and contact
The laws of the Federative Republic of Brazil apply, while mandatory consumer and data-protection rules remain in force. Questions: martimpc318@gmail.com or Help > Open support ticket.
"""),
    },
    "es": {
        "privacy": ("Política de privacidad", """POLÍTICA DE PRIVACIDAD DE AUDIOMAIL
Versión 5 — 17 de noviembre de 2026

1. Responsable y contacto
Martim Alves es responsable de AudioMail. Para consultas de privacidad o solicitudes sobre datos personales, escribe a martimpc318@gmail.com. También puedes abrir una solicitud en Ayuda > Abrir solicitud de soporte.

2. Datos tratados por AudioMail
• Los datos de la cuenta de correo que ingresas (dirección y contraseña de aplicación). La contraseña solo se guarda si eliges recordarla y queda protegida por las funciones de seguridad de Windows para este usuario y equipo. La configuración, preferencias, recordatorios locales, claves API de IA cifradas y referencias de solicitudes se guardan en el equipo o carpeta portátil.
• Los mensajes, contactos, archivos adjuntos y carpetas se obtienen del proveedor de correo para ofrecer las funciones solicitadas. AudioMail no envía copias de esos mensajes al responsable de la aplicación.
• Para que la lista se abra al instante y para leer sin internet, AudioMail guarda en este equipo, en el archivo mensagens.db de la carpeta de datos, la lista de carpetas, la lista de mensajes de cada carpeta y el texto de los mensajes que abre (los adjuntos solo si activa esa opción). El archivo está cifrado por la protección de Windows de este usuario y equipo y no se envía a nadie. En Configuración > Mensajes guardados en el equipo puede desactivar la función, elegir cuántos días guardar y eliminarlo todo; al quitar una cuenta, también se elimina lo que estaba guardado de ella. Los contactos y grupos que crea se guardan en el archivo contatos.json, también solo en este equipo.
• Si activa el bloqueo con PIN, el PIN no se guarda: solo se conserva, en la configuración de este equipo, un código derivado que no permite descubrir el PIN. Si activa Windows Hello, la verificación del rostro, la huella o el PIN de Windows la hace el propio Windows; AudioMail solo recibe "confirmado" o "no confirmado" y nunca recibe ni guarda imágenes del rostro ni huellas.
• Al enviar una solicitud de soporte, la aplicación envía su asunto, tipo, texto y versión de AudioMail al servidor de soporte. Las solicitudes se guardan en el panel de soporte. La cuenta de correo, los mensajes y los archivos adjuntos no se envían automáticamente. El servidor y el proveedor de alojamiento pueden tratar datos técnicos de conexión, como la dirección IP, para prestar y proteger el servicio.
• Al pedir un resumen con IA, el mensaje o conversación seleccionados y las instrucciones se envían al proveedor elegido (OpenAI, Google Gemini o un endpoint compatible que configures), usando tu clave API. El proveedor trata los datos según sus propios términos y políticas. No envíes contenido que no quieras compartir con ese proveedor. La clave se cifra localmente. El contenido solo se envía cuando pides el resumen y lo autorizas.
• Del mismo modo, si pides la descripción de una imagen (un adjunto o una imagen dentro del correo), la imagen se envía a ese proveedor; y si usas Escribir con IA, la idea que escribiste y el mensaje que respondes se envían a él. Cada función pide autorización la primera vez. Los adjuntos leídos como texto (PDF, Word, Excel...) se leen en tu equipo y no se envían a nadie.
• Al pedir una traducción, el texto seleccionado se envía a Google Translate. Se solicita permiso antes del primer envío y puedes cambiarlo en la configuración.
• El calendario puede consultar los feriados nacionales en la API pública Nager.Date. Los resultados se guardan localmente; se envían el año solicitado y datos técnicos de conexión.
• La búsqueda de actualizaciones contacta GitHub (github.com, un servicio de GitHub, Inc., empresa de Microsoft), donde se publica AudioMail, para consultar versiones y, cuando instalas una actualización, descargar archivos. Esta conexión incluye datos técnicos habituales de una conexión web.

3. Finalidades y bases legales
Los datos locales se usan para ejecutar las funciones solicitadas y guardar preferencias. Los datos que envías a traductores, proveedores de IA, correo o soporte se tratan para realizar la función solicitada, según tus permisos e instrucciones. Aceptar esta política y los términos registra tu decisión de usar la aplicación; no sustituye los permisos específicos para traducción y resumen con IA.

4. Compartición, almacenamiento y seguridad
AudioMail no tiene una cuenta central ni sincroniza tu configuración. Los datos locales permanecen en tu equipo hasta que los elimines o borres la carpeta de datos. Los proveedores de correo, traducción, IA, alojamiento y feriados reciben solo los datos necesarios para la función que utilizas y pueden tratarlos según sus propias políticas. No controlamos los plazos de conservación de terceros. Se usa HTTPS cuando está disponible y protección de Windows para secretos guardados localmente; ningún sistema puede garantizar seguridad absoluta.

5. Tus derechos
Conforme a la LGPD brasileña, puedes solicitar confirmación y acceso, corrección, información sobre compartición, anonimización, bloqueo o eliminación cuando corresponda, portabilidad dentro de los límites legales y revocación del consentimiento. Contacta el canal indicado arriba. Puede ser necesaria una verificación razonable de identidad y pueden aplicarse obligaciones legales de conservación. También puedes eliminar credenciales y claves guardadas localmente desde la configuración o la carpeta de datos.

6. Niños, cambios y vigencia
AudioMail es una herramienta general, no dirigida a niños. La política puede cambiar; los cambios relevantes se presentarán de nuevo para aceptación antes de seguir usando AudioMail. La versión aceptada y la fecha se guardan localmente. Lee esta política junto con los Términos de uso.
"""),
        "terms": ("Términos de uso", """TÉRMINOS DE USO DE AUDIOMAIL
Versión 1 — 5 de noviembre de 2026

1. Sobre la aplicación
AudioMail es un cliente para acceder a cuentas de correo compatibles, organizar mensajes, crear recordatorios locales, consultar feriados, traducir textos, solicitar resúmenes con IA y abrir solicitudes de soporte. Lo proporciona Martim Alves.

2. Aceptación y uso responsable
Al seleccionar “He leído y acepto”, confirmas que tuviste acceso a estos Términos y a la Política de privacidad y aceptas usar la aplicación según estas reglas. Usa AudioMail solo con cuentas y contenido a los que estés autorizado a acceder. Eres responsable de proteger tu contraseña de aplicación, claves API y los datos que consultes o envíes. No uses la aplicación para infringir leyes, derechos de terceros, reglas de tu proveedor de correo o términos de servicios externos.

3. Proveedores externos y funciones opcionales
El acceso al correo depende de tu proveedor y credenciales. La traducción, resúmenes con IA, consulta de feriados y actualizaciones dependen de servicios externos que pueden no estar disponibles o cambiar sus condiciones. Tú eliges y configuras la clave API, el proveedor y el modelo de IA; el proveedor define tarifas, límites y reglas de la API. Revisa los datos antes de enviarlos y no compartas información que no quieras enviar a terceros. Los resúmenes, traducciones, descripciones de imágenes y textos escritos por la IA pueden contener errores y deben revisarse antes de tomar decisiones o enviar mensajes.

4. Solicitudes de soporte y contenido
Al enviar una solicitud, autorizas el envío de los campos mostrados en el formulario para recibir soporte. No incluyas contraseñas ni datos innecesarios. El responsable puede marcar una solicitud como concluida después de atenderla. No es un canal de emergencia y no se garantiza un plazo de respuesta.

5. Disponibilidad y responsabilidad
La aplicación se proporciona en su estado actual. Puede haber fallos, incompatibilidades, interrupciones o pérdida de datos; conserva copias de seguridad importantes y revisa destinatarios y contenido antes de enviar mensajes. En la máxima medida permitida por la legislación brasileña, no se garantiza disponibilidad continua ni servicios de terceros sin errores. Nada en estos Términos reduce los derechos obligatorios previstos por el Código de Defensa del Consumidor de Brasil u otras normas aplicables.

6. Actualizaciones, fin de uso y cambios
Las actualizaciones pueden corregir errores, cambiar funciones o sustituir estos Términos y la Política de privacidad. Si un cambio requiere nuevo consentimiento, AudioMail te pedirá leer y aceptar la nueva versión. Puedes dejar de usar la aplicación y borrar los datos locales; la eliminación de solicitudes ya enviadas puede pedirse por el contacto de privacidad y puede estar sujeta a obligaciones legales de conservación.

7. Ley y contacto
Se aplican las leyes de la República Federativa de Brasil, sin afectar las normas obligatorias de protección al consumidor y de datos. Consultas: martimpc318@gmail.com o Ayuda > Abrir solicitud de soporte.
"""),
    },
}


class LegalDialog(wx.Dialog):
    """Exibe os documentos e registra o aceite explícito, se solicitado."""

    def __init__(self, parent, language, require_acceptance=False):
        self.language = language if language in DOCUMENTS else "pt"
        self.require_acceptance = require_acceptance
        super().__init__(parent, title=i18n.tr("Privacidade e termos do AudioMail"),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        outer = wx.BoxSizer(wx.VERTICAL)
        book = wx.Notebook(self)
        self.viewed = set()
        docs = DOCUMENTS[self.language]
        self._text_controls = []
        for key in ("privacy", "terms"):
            tab = wx.Panel(book)
            layout = wx.BoxSizer(wx.VERTICAL)
            label, body = docs[key]
            text = wx.TextCtrl(tab, value=body.strip(), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
            text.SetName(label)
            layout.Add(text, 1, wx.EXPAND | wx.ALL, 8)
            tab.SetSizer(layout)
            book.AddPage(tab, label)
            self._text_controls.append(text)
        outer.Add(book, 1, wx.EXPAND | wx.ALL, 8)
        self.accept_checkbox = wx.CheckBox(self, label={
            "pt": "Li e aceito a Política de privacidade e os Termos de uso",
            "en": "I have read and accept the Privacy Policy and Terms of Use",
            "es": "He leído y acepto la Política de privacidad y los Términos de uso",
        }[self.language])
        self.accept_checkbox.SetName(self.accept_checkbox.GetLabel())
        self.accept_checkbox.Show(require_acceptance)
        outer.Add(self.accept_checkbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.continue_button = wx.Button(self, wx.ID_OK, {
            "pt": "Aceitar e continuar", "en": "Accept and continue", "es": "Aceptar y continuar",
        }[self.language])
        self.continue_button.SetName(self.continue_button.GetLabel())
        self.close_button = wx.Button(self, wx.ID_CANCEL, {
            "pt": "Não aceito / Sair", "en": "Decline / Exit", "es": "No acepto / Salir",
        }[self.language])
        self.close_button.SetName(self.close_button.GetLabel())
        row.Add(self.continue_button, 0, wx.RIGHT, 8)
        row.Add(self.close_button, 0)
        outer.Add(row, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(outer)
        self.SetSize((760, 620))
        self.SetMinSize((520, 420))
        self.Centre()
        if require_acceptance:
            self.continue_button.Enable(False)
            self.accept_checkbox.Bind(wx.EVT_CHECKBOX, self._update_accept)
        else:
            self.continue_button.SetLabel({"pt": "Fechar", "en": "Close", "es": "Cerrar"}[self.language])
            self.close_button.Hide()
        self.Bind(wx.EVT_BUTTON, self._on_continue, self.continue_button)

    def _update_accept(self, _event):
        self.continue_button.Enable(self.accept_checkbox.GetValue())

    def _on_continue(self, _event):
        if self.require_acceptance and not self.accept_checkbox.GetValue():
            return
        self.EndModal(wx.ID_OK)


def require_acceptance(config):
    acceptance = config.get("legal_acceptance")
    if not isinstance(acceptance, dict):
        return True
    return acceptance.get("version") != LEGAL_VERSION


def show_acceptance(config):
    dialog = LegalDialog(None, config.get("ui_language", "pt"), require_acceptance=True)
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return False
    finally:
        dialog.Destroy()
    config["legal_acceptance"] = {
        "version": LEGAL_VERSION,
        "accepted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    return True
