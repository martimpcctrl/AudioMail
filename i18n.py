"""Textos da interface do AudioMail."""

LANGUAGES = [("pt", "Português"), ("en", "English"), ("es", "Español")]

_TEXT = {
    "en": {
        "Conta": "Account", "Pasta": "Folder", "Buscar": "Search", "Mensagens": "Messages",
        "Estado": "Status", "De": "From", "Assunto": "Subject", "Data": "Date",
        "Nova mensagem\tCtrl+N": "New message\tCtrl+N", "Atualizar\tF5": "Refresh\tF5",
        "Buscar\tCtrl+F": "Search\tCtrl+F", "Ir para as pastas\tF6": "Go to folders\tF6",
        "Ir para as contas\tF7": "Go to accounts\tF7", "Adicionar conta": "Add account",
        "Remover conta atual": "Remove current account", "Esconder na bandeja\tCtrl+M": "Hide to tray\tCtrl+M",
        "Sair\tCtrl+Q": "Exit\tCtrl+Q", "&Arquivo": "&File", "Abrir": "Open",
        "Responder\tCtrl+R": "Reply\tCtrl+R", "Responder a todos\tCtrl+Shift+R": "Reply all\tCtrl+Shift+R",
        "Traduzir mensagem\tCtrl+T": "Translate message\tCtrl+T", "Apagar\tDel": "Delete\tDel",
        "Marcar como lida\tCtrl+Shift+L": "Mark as read\tCtrl+Shift+L",
        "Marcar como não lida\tCtrl+Shift+U": "Mark as unread\tCtrl+Shift+U",
        "Agrupar por conversa\tCtrl+G": "Group by conversation\tCtrl+G", "&Mensagem": "&Message",
        "Preferências\tCtrl+P": "Preferences\tCtrl+P", "Escolher som de notificação": "Choose notification sound",
        "Testar som": "Test sound", "&Configurações": "&Settings", "Abrir manual\tF1": "Open manual\tF1",
        "Verificar atualizações": "Check for updates", "Sobre o AudioMail": "About AudioMail", "A&juda": "&Help",
        "Configurações": "Settings", "Idioma da interface": "Interface language",
        "Escolha o idioma para usar no AudioMail.": "Choose the language to use in AudioMail.",
        "Salvar": "Save", "Cancelar": "Cancel", "Português": "Português",
        "Idioma salvo.": "Language saved.", "Nova mensagem": "New message", "Verificar agora": "Check now",
        "Sair": "Exit", "ÁudioMail": "AudioMail", "Idioma": "Language",
    },
    "es": {
        "Conta": "Cuenta", "Pasta": "Carpeta", "Buscar": "Buscar", "Mensagens": "Mensajes",
        "Estado": "Estado", "De": "De", "Assunto": "Asunto", "Data": "Fecha",
        "Nova mensagem\tCtrl+N": "Nuevo mensaje\tCtrl+N", "Atualizar\tF5": "Actualizar\tF5",
        "Buscar\tCtrl+F": "Buscar\tCtrl+F", "Ir para as pastas\tF6": "Ir a carpetas\tF6",
        "Ir para as contas\tF7": "Ir a cuentas\tF7", "Adicionar conta": "Añadir cuenta",
        "Remover conta atual": "Eliminar cuenta actual", "Esconder na bandeja\tCtrl+M": "Ocultar en la bandeja\tCtrl+M",
        "Sair\tCtrl+Q": "Salir\tCtrl+Q", "&Arquivo": "&Archivo", "Abrir": "Abrir",
        "Responder\tCtrl+R": "Responder\tCtrl+R", "Responder a todos\tCtrl+Shift+R": "Responder a todos\tCtrl+Shift+R",
        "Traduzir mensagem\tCtrl+T": "Traducir mensaje\tCtrl+T", "Apagar\tDel": "Eliminar\tDel",
        "Marcar como lida\tCtrl+Shift+L": "Marcar como leído\tCtrl+Shift+L",
        "Marcar como não lida\tCtrl+Shift+U": "Marcar como no leído\tCtrl+Shift+U",
        "Agrupar por conversa\tCtrl+G": "Agrupar por conversación\tCtrl+G", "&Mensagem": "&Mensaje",
        "Preferências\tCtrl+P": "Preferencias\tCtrl+P", "Escolher som de notificação": "Elegir sonido de notificación",
        "Testar som": "Probar sonido", "&Configurações": "&Configuración", "Abrir manual\tF1": "Abrir manual\tF1",
        "Verificar atualizações": "Buscar actualizaciones", "Sobre o AudioMail": "Acerca de AudioMail", "A&juda": "A&yuda",
        "Configurações": "Configuración", "Idioma da interface": "Idioma de la interfaz",
        "Escolha o idioma para usar no AudioMail.": "Elige el idioma que se usará en AudioMail.",
        "Salvar": "Guardar", "Cancelar": "Cancelar", "Português": "Portugués",
        "Idioma salvo.": "Idioma guardado.", "Nova mensagem": "Nuevo mensaje", "Verificar agora": "Comprobar ahora",
        "Sair": "Salir", "ÁudioMail": "AudioMail", "Idioma": "Idioma",
    },
}


_TEXT['en'].update({
'E-mail':'Email','Senha de app':'App password','Lembrar a senha neste computador':'Remember password on this computer','Criar senha de app (abre o site do Google)':"Create an app password (opens Google's website)",'Entrar':'Sign in','Verificar novas mensagens a cada':'Check for new messages every','30 segundos':'30 seconds','1 minuto':'1 minute','2 minutos':'2 minutes','5 minutos':'5 minutes','10 minutos':'10 minutes','Traduzir mensagens para':'Translate messages to','Traduzir sem perguntar (autoriza enviar o texto ao serviço de tradução do Google)':'Translate without asking (allows sending text to Google Translate)','Receber mensagens na hora (tempo real)':'Receive messages instantly (real time)','Mostrar notificação quando chegar mensagem nova':'Show a notification when new messages arrive','Tocar som quando chegar mensagem nova':'Play a sound when new messages arrive','Falar com o leitor de tela quando chegar mensagem nova':'Announce new messages with the screen reader','Ao fechar a janela, continuar rodando na bandeja':'Keep running in the system tray when the window closes','Ao minimizar, esconder na bandeja':'Hide in the system tray when minimized','Abrir já escondido na bandeja':'Start hidden in the system tray','Iniciar junto com o Windows':'Start with Windows','Verificar atualizações automaticamente':'Check for updates automatically','Som de notificação':'Notification sound','Assinatura':'Signature','Escolher som':'Choose sound','Usar som padrão':'Use default sound','Padrão':'Default','Idioma da interface':'Interface language','Idioma salvo. Reinicie o AudioMail para aplicar a alteração.':'Language saved. Restart AudioMail to apply the change.','Para':'To','Cópia':'Cc','Cópia oculta':'Bcc','Texto da mensagem':'Message body','Anexos':'Attachments','Adicionar anexo':'Add attachment','Remover anexo':'Remove attachment','Traduzir texto':'Translate text','Desfazer tradução':'Undo translation','Salvar rascunho':'Save draft','Fechar':'Close','Salvar anexo':'Save attachment','Salvar todos os anexos':'Save all attachments','Abrir anexo':'Open attachment','Salvar como rascunho antes de sair?':'Save as a draft before closing?','Sair da mensagem':'Close message','Escolher arquivos para anexar':'Choose files to attach','Escolha a pasta para salvar os anexos':'Choose a folder to save attachments','Traduzir o assunto e o texto para qual idioma?':'Which language should the subject and message be translated to?','Não há texto para traduzir.':'There is no text to translate.','Tradução desfeita.':'Translation undone.','Traduzindo. Aguarde.':'Translating. Please wait.','Enviando':'Sending','Enviar':'Send','Informe o destinatário.':'Enter a recipient.','Informe o e-mail completo, com o arroba.':'Enter the full email address, including @.','Informe a senha de app do Google.':'Enter your Google app password.','Aviso':'Warning','Confirmar':'Confirm','Tradução':'Translation','Novidades':'What is new','Depois':'Later','Atualizar agora':'Update now','Fechar o AudioMail':'Close AudioMail','Pular esta versão':'Skip this version','Não foi possível entrar':'Sign-in failed','Não foi possível verificar agora.':'Could not check now.','Configurações salvas.':'Settings saved.','Som de notificação alterado.':'Notification sound changed.','Conta removida.':'Account removed.','Mensagem enviada.':'Message sent.','Rascunho salvo.':'Draft saved.','Mensagem aberta':'Message opened','Marcada como lida.':'Marked as read.','Marcada como não lida.':'Marked as unread.','Não lida':'Unread','Não foi possível alterar o início com o Windows.':'Could not change the Windows startup setting.','Mostrar a tradução.':'Showing the translation.','Mostrando o original.':'Showing the original.','Ver tradução':'View translation','Ver original':'View original','Atualização disponível':'Update available','Atualização recomendada.':'Update recommended.','Atualização obrigatória':'Required update','Anexo salvo.':'Attachment saved.','Anexo removido.':'Attachment removed.','Verificando atualizações':'Checking for updates','Tempo real ativo':'Real-time sync active','Agrupando por conversa.':'Grouping by conversation.','Mostrando cada mensagem separada.':'Showing each message separately.','Abrindo mensagem':'Opening message','Abrindo rascunho':'Opening draft','Preparando resposta':'Preparing reply','Carregando mensagens':'Loading messages','Apagando':'Deleting','Atualizando':'Updating','Buscando':'Searching','Carregando':'Loading','Tempo real desligado, verificando de tempos em tempos':'Real-time sync is off; checking periodically',
})
_TEXT['es'].update({
'E-mail':'Correo electrónico','Senha de app':'Contraseña de aplicación','Lembrar a senha neste computador':'Recordar la contraseña en este equipo','Criar senha de app (abre o site do Google)':'Crear contraseña de aplicación (abre el sitio de Google)','Entrar':'Iniciar sesión','Verificar novas mensagens a cada':'Buscar mensajes nuevos cada','30 segundos':'30 segundos','1 minuto':'1 minuto','2 minutos':'2 minutos','5 minutos':'5 minutos','10 minutos':'10 minutos','Traduzir mensagens para':'Traducir mensajes al','Traduzir sem perguntar (autoriza enviar o texto ao serviço de tradução do Google)':'Traducir sin preguntar (permite enviar texto a Google Translate)','Receber mensagens na hora (tempo real)':'Recibir mensajes al instante (tiempo real)','Mostrar notificação quando chegar mensagem nova':'Mostrar una notificación al recibir mensajes nuevos','Tocar som quando chegar mensagem nova':'Reproducir un sonido al recibir mensajes nuevos','Falar com o leitor de tela quando chegar mensagem nova':'Anunciar mensajes nuevos con el lector de pantalla','Ao fechar a janela, continuar rodando na bandeja':'Seguir ejecutándose en la bandeja al cerrar la ventana','Ao minimizar, esconder na bandeja':'Ocultar en la bandeja al minimizar','Abrir já escondido na bandeja':'Iniciar oculto en la bandeja','Iniciar junto com o Windows':'Iniciar con Windows','Verificar atualizações automaticamente':'Buscar actualizaciones automáticamente','Som de notificação':'Sonido de notificación','Assinatura':'Firma','Escolher som':'Elegir sonido','Usar som padrão':'Usar sonido predeterminado','Padrão':'Predeterminado','Idioma da interface':'Idioma de la interfaz','Idioma salvo. Reinicie o AudioMail para aplicar a alteração.':'Idioma guardado. Reinicia AudioMail para aplicar el cambio.','Para':'Para','Cópia':'CC','Cópia oculta':'CCO','Texto da mensagem':'Texto del mensaje','Anexos':'Adjuntos','Adicionar anexo':'Añadir adjunto','Remover anexo':'Quitar adjunto','Traduzir texto':'Traducir texto','Desfazer tradução':'Deshacer traducción','Salvar rascunho':'Guardar borrador','Fechar':'Cerrar','Salvar anexo':'Guardar adjunto','Salvar todos os anexos':'Guardar todos los adjuntos','Abrir anexo':'Abrir adjunto','Salvar como rascunho antes de sair?':'¿Guardar como borrador antes de salir?','Sair da mensagem':'Cerrar mensaje','Escolher arquivos para anexar':'Elegir archivos para adjuntar','Escolha a pasta para salvar os anexos':'Elegir la carpeta para guardar los adjuntos','Traduzir o assunto e o texto para qual idioma?':'¿A qué idioma traducir el asunto y el texto?','Não há texto para traduzir.':'No hay texto para traducir.','Tradução desfeita.':'Traducción deshecha.','Traduzindo. Aguarde.':'Traduciendo. Espera.','Enviando':'Enviando','Enviar':'Enviar','Informe o destinatário.':'Indica el destinatario.','Informe o e-mail completo, com o arroba.':'Indica el correo electrónico completo, incluido @.','Informe a senha de app do Google.':'Indica la contraseña de aplicación de Google.','Aviso':'Aviso','Confirmar':'Confirmar','Tradução':'Traducción','Novidades':'Novedades','Depois':'Después','Atualizar agora':'Actualizar ahora','Fechar o AudioMail':'Cerrar AudioMail','Pular esta versão':'Omitir esta versión','Não foi possível entrar':'No se pudo iniciar sesión','Não foi possível verificar agora.':'No se pudo comprobar ahora.','Configurações salvas.':'Configuración guardada.','Som de notificação alterado.':'Sonido de notificación cambiado.','Conta removida.':'Cuenta eliminada.','Mensagem enviada.':'Mensaje enviado.','Rascunho salvo.':'Borrador guardado.','Mensagem aberta':'Mensaje abierto','Marcada como lida.':'Marcado como leído.','Marcada como não lida.':'Marcado como no leído.','Não lida':'No leído','Não foi possível alterar o início com o Windows.':'No se pudo cambiar el inicio con Windows.','Mostrar a tradução.':'Mostrando la traducción.','Mostrando o original.':'Mostrando el original.','Ver tradução':'Ver traducción','Ver original':'Ver original','Atualização disponível':'Actualización disponible','Atualização recomendada.':'Actualización recomendada.','Atualização obrigatória':'Actualización obligatoria','Anexo salvo.':'Adjunto guardado.','Anexo removido.':'Adjunto eliminado.','Verificando atualizações':'Buscando actualizaciones','Tempo real ativo':'Sincronización en tiempo real activa','Agrupando por conversa.':'Agrupando por conversación.','Mostrando cada mensagem separada.':'Mostrando cada mensaje por separado.','Abrindo mensagem':'Abriendo mensaje','Abrindo rascunho':'Abriendo borrador','Preparando resposta':'Preparando respuesta','Carregando mensagens':'Cargando mensajes','Apagando':'Eliminando','Atualizando':'Actualizando','Buscando':'Buscando','Carregando':'Cargando','Tempo real desligado, verificando de tempos em tempos':'Sincronización en tiempo real desactivada; comprobando periódicamente',
})

_TEXT['en'].update({
    'Privacidade e termos do AudioMail': 'AudioMail privacy and terms',
})
_TEXT['es'].update({
    'Privacidade e termos do AudioMail': 'Privacidad y términos de AudioMail',
})

_TEXT['en'].update({
    'Abrir chamado de suporte':'Open a support ticket',
    'Não inclua senhas. E-mails e anexos não são enviados.':'Do not include passwords. Emails and attachments are not sent.',
    'Assunto do chamado':'Ticket subject', 'Informe o assunto do chamado.':'Enter the ticket subject.',
    'Descreva o que precisa. Não inclua senhas. Nenhuma mensagem ou anexo de e-mail será enviado automaticamente.':'Describe what you need. Do not include passwords. No email messages or attachments are sent automatically.',
    'E-mail para resposta (opcional)':'Reply email (optional)', 'Assunto':'Subject',
    'Tipo do chamado':'Ticket type', 'Problema':'Problem', 'Dúvida':'Question', 'Sugestão':'Suggestion',
    'Descreva o problema ou pedido':'Describe the problem or request', 'Enviar chamado':'Submit ticket',
    'Preencha o assunto e a descrição do chamado.':'Enter a subject and ticket description.',
    'Chamado incompleto':'Incomplete ticket', 'Confira o endereço de e-mail para resposta.':'Check the reply email address.',
    'E-mail inválido':'Invalid email', 'Enviando chamado de suporte.':'Sending support ticket.',
    'Chamado enviado. Número de protocolo: %s':'Ticket sent. Reference number: %s',
    'Chamado enviado':'Ticket sent', 'Falha ao enviar chamado':'Could not submit ticket',
    'Meus chamados':'My tickets', 'Concluído':'Completed', 'Aberto':'Open',
    'Marcar como concluído':'Mark as completed', 'Falha ao concluir chamado':'Could not complete ticket',
    'Você ainda não abriu chamados neste computador.':'You have not opened any tickets on this computer yet.',
})
_TEXT['es'].update({
    'Abrir chamado de suporte':'Abrir una solicitud de soporte',
    'Não inclua senhas. E-mails e anexos não são enviados.':'No incluyas contraseñas. No se envían correos ni archivos adjuntos.',
    'Assunto do chamado':'Asunto de la solicitud', 'Informe o assunto do chamado.':'Escribe el asunto de la solicitud.',
    'Descreva o que precisa. Não inclua senhas. Nenhuma mensagem ou anexo de e-mail será enviado automaticamente.':'Describe lo que necesitas. No incluyas contraseñas. No se enviarán mensajes ni archivos adjuntos automáticamente.',
    'E-mail para resposta (opcional)':'Correo para responder (opcional)', 'Assunto':'Asunto',
    'Tipo do chamado':'Tipo de solicitud', 'Problema':'Problema', 'Dúvida':'Pregunta', 'Sugestão':'Sugerencia',
    'Descreva o problema ou pedido':'Describe el problema o la solicitud', 'Enviar chamado':'Enviar solicitud',
    'Preencha o assunto e a descrição do chamado.':'Escribe el asunto y la descripción.',
    'Chamado incompleto':'Solicitud incompleta', 'Confira o endereço de e-mail para resposta.':'Revisa el correo para responder.',
    'E-mail inválido':'Correo no válido', 'Enviando chamado de suporte.':'Enviando solicitud de soporte.',
    'Chamado enviado. Número de protocolo: %s':'Solicitud enviada. Número de referencia: %s',
    'Chamado enviado':'Solicitud enviada', 'Falha ao enviar chamado':'No se pudo enviar la solicitud',
    'Meus chamados':'Mis solicitudes', 'Concluído':'Concluida', 'Aberto':'Abierta',
    'Marcar como concluído':'Marcar como completada', 'Falha ao concluir chamado':'No se pudo completar la solicitud',
    'Você ainda não abriu chamados neste computador.':'Aún no has abierto solicitudes en este equipo.',
})


_TEXT['en'].update({
'Autorizar tradução':'Allow translation','Traduzir envia o texto para o serviço de tradução do Google. Só vai o texto que você mandar traduzir, e só quando você pedir. Autorizar agora e nas próximas vezes?':'Translate sends text to Google Translate. Only text you ask to translate is sent. Allow now and in the future?','Senha de app':'App password','Manual':'Manual','Atualização':'Update','Erro ao enviar':'Send error','Erro ao salvar o rascunho':'Draft save error','A mensagem está sem assunto. Enviar assim mesmo?':'The message has no subject. Send it anyway?','A mensagem foi enviada.':'Message sent.','Os anexos passam do limite do Gmail (cerca de 18 MB no total). Remova algum antes de enviar.':'Attachments exceed Gmail’s limit (about 18 MB total). Remove an attachment before sending.','Não consegui abrir o navegador. Abra este endereço você mesmo:\n\n%s':'Could not open the browser. Open this address yourself:\n\n%s','O texto já está em %s.':'The text is already in %s.','Texto traduzido para %s.':'Text translated to %s.','O texto já está em %s.':'The text is already in %s.','O AudioMail já está aberto. Procure o ícone na bandeja: aperte Windows mais B.':'AudioMail is already open. Find its tray icon: press Windows+B.','Conta %s\n\n%s':'Account %s\n\n%s','Remover a conta %s do AudioMail? As mensagens continuam no Gmail.':'Remove account %s from AudioMail? Messages will remain in Gmail.','Conversa com %d mensagens, assunto %s':'Conversation with %d messages, subject %s','Apagar a conversa com %d mensagens, assunto %s?':'Delete the conversation with %d messages, subject %s?','Apagar a mensagem de %s, assunto %s?':'Delete the message from %s, subject %s?','%d resultados para %s':'%d results for %s','%d mensagens, %d não lidas':'%d messages, %d unread','%d anexos salvos.':'%d attachments saved.','A atualização foi instalada, mas não consegui reiniciar sozinho. Feche e abra o AudioMail de novo.\n\n%s':'The update was installed, but AudioMail could not restart automatically. Close and reopen it.\n\n%s','Atualização instalada. O AudioMail vai reiniciar.':'Update installed. AudioMail will restart.','Atualização disponível, versão %s.':'Update available, version %s.','Atualização urgente do AudioMail, versão %s.':'Urgent AudioMail update, version %s.','Atualização do AudioMail disponível, versão %s.':'AudioMail update available, version %s.','A atualização não foi instalada.\n\n%s':'The update was not installed.\n\n%s','Não consegui abrir o manual: %s':'Could not open the manual: %s',
})
_TEXT['es'].update({
'Autorizar tradução':'Autorizar traducción','Traduzir envia o texto para o serviço de tradução do Google. Só vai o texto que você mandar traduzir, e só quando você pedir. Autorizar agora e nas próximas vezes?':'Traducir envía el texto a Google Translate. Solo se envía el texto que pidas traducir. ¿Permitirlo ahora y en el futuro?','Senha de app':'Contraseña de aplicación','Manual':'Manual','Atualização':'Actualización','Erro ao enviar':'Error al enviar','Erro ao salvar o rascunho':'Error al guardar el borrador','A mensagem está sem assunto. Enviar assim mesmo?':'El mensaje no tiene asunto. ¿Enviar de todos modos?','Os anexos passam do limite do Gmail (cerca de 18 MB no total). Remova algum antes de enviar.':'Los adjuntos superan el límite de Gmail (unos 18 MB en total). Quita alguno antes de enviar.','Não consegui abrir o navegador. Abra este endereço você mesmo:\n\n%s':'No se pudo abrir el navegador. Abre esta dirección manualmente:\n\n%s','O texto já está em %s.':'El texto ya está en %s.','Texto traduzido para %s.':'Texto traducido al %s.','O AudioMail já está aberto. Procure o ícone na bandeja: aperte Windows mais B.':'AudioMail ya está abierto. Busca el icono en la bandeja: pulsa Windows+B.','Conta %s\n\n%s':'Cuenta %s\n\n%s','Remover a conta %s do AudioMail? As mensagens continuam no Gmail.':'¿Eliminar la cuenta %s de AudioMail? Los mensajes seguirán en Gmail.','Conversa com %d mensagens, assunto %s':'Conversación con %d mensajes, asunto %s','Apagar a conversa com %d mensagens, assunto %s?':'¿Eliminar la conversación con %d mensajes, asunto %s?','Apagar a mensagem de %s, assunto %s?':'¿Eliminar el mensaje de %s, asunto %s?','%d resultados para %s':'%d resultados para %s','%d mensagens, %d não lidas':'%d mensajes, %d sin leer','%d anexos salvos.':'%d adjuntos guardados.','A atualização foi instalada, mas não consegui reiniciar sozinho. Feche e abra o AudioMail de novo.\n\n%s':'La actualización se instaló, pero no se pudo reiniciar automáticamente. Cierra y vuelve a abrir AudioMail.\n\n%s','Atualização instalada. O AudioMail vai reiniciar.':'Actualización instalada. AudioMail se reiniciará.','Atualização disponível, versão %s.':'Actualización disponible, versión %s.','Atualização urgente do AudioMail, versão %s.':'Actualización urgente de AudioMail, versión %s.','Atualização do AudioMail disponível, versão %s.':'Actualización de AudioMail disponible, versión %s.','A atualização não foi instalada.\n\n%s':'No se instaló la actualización.\n\n%s','Não consegui abrir o manual: %s':'No se pudo abrir el manual: %s',
})


_TEXT['en'].update({
'Erro':'Error','Arquivos de som WAV (*.wav)|*.wav':'WAV sound files (*.wav)|*.wav','Espanhol':'Spanish','Inglês':'English','Francês':'French','Alemão':'German','Italiano':'Italian','Holandês':'Dutch','Polonês':'Polish','Russo':'Russian','Ucraniano':'Ukrainian','Turco':'Turkish','Árabe':'Arabic','Hebraico':'Hebrew','Hindi':'Hindi','Japonês':'Japanese','Coreano':'Korean','Chinês simplificado':'Simplified Chinese','Chinês tradicional':'Traditional Chinese','Sueco':'Swedish','Grego':'Greek','Indonésio':'Indonesian','Vietnamita':'Vietnamese','Tailandês':'Thai','Erro':'Error','Arquivos de som WAV (*.wav)|*.wav':'WAV sound files (*.wav)|*.wav','Espanhol':'Español','Inglês':'Inglés','Francês':'Francés','Alemão':'Alemán','Italiano':'Italiano','Holandês':'Neerlandés','Polonês':'Polaco','Russo':'Ruso','Ucraniano':'Ucraniano','Turco':'Turco','Árabe':'Árabe','Hebraico':'Hebreo','Hindi':'Hindi','Japonês':'Japonés','Coreano':'Coreano','Chinês simplificado':'Chino simplificado','Chinês tradicional':'Chino tradicional','Sueco':'Sueco','Grego':'Griego','Indonésio':'Indonesio','Vietnamita':'Vietnamita','Tailandês':'Tailandés','Nova mensagem de %s':'New message from %s','%d novas mensagens':'%d new messages','De %s':'From %s',' e outros':' and others','Nova mensagem de %s':'Nuevo mensaje de %s','%d novas mensagens':'%d mensajes nuevos','De %s':'From %s',' e outros':' and others','Baixando a atualização. Aguarde.':'Downloading the update. Please wait.','Baixando atualização':'Downloading update','Para abrir de novo, aperte Windows mais B, escolha o ícone e aperte Enter.':'To open it again, press Windows+B, select the icon, and press Enter.','AudioMail versão %s\nSite: %s':'AudioMail version %s\nWebsite: %s','Nenhuma mensagem nova. %d não lidas.%s':'No new messages. %d unread.%s','AudioMail versão %s. Abra o programa para atualizar.':'AudioMail version %s. Open the app to update.','Atualização obrigatória do AudioMail, versão %s.':'Required AudioMail update, version %s.','Versão %s ignorada.':'Version %s skipped.','Tradução automática de %s para %s.':'Automatic translation from %s to %s.','%s\n\nNova versão: %s\nVersão instalada: %s\n\nNovidades:\n%s':'%s\n\nNew version: %s\nInstalled version: %s\n\nWhat is new:\n%s','ATUALIZAÇÃO OBRIGATÓRIA: o AudioMail não pode continuar sem atualizar.':'REQUIRED UPDATE: AudioMail cannot continue without updating.','Mostrando a tradução.':'Showing the translation.','A mensagem já está em %s.':'The message is already in %s.','Atualização urgente':'Urgent update','ATUALIZAÇÃO URGENTE: atualize o quanto antes.':'URGENT UPDATE: update as soon as possible.','(sem descrição)':'(no description)','Só novidades: você pode atualizar quando quiser.':'Optional update: you can update whenever you like.','Esse arquivo não é um WAV válido. Converta o som para WAV e tente de novo.':'This is not a valid WAV file. Convert the sound to WAV and try again.','Idioma salvo. Reinicie o AudioMail para aplicar a alteração.':'Language saved. Restart AudioMail to apply the change.','Abrir AudioMail':'Open AudioMail','Configurações':'Settings','Idioma':'Language','Traduzir mensagem':'Translate message','Marcar como lida':'Mark as read','Marcar como não lida':'Mark as unread','Ir para as pastas':'Go to folders','Ir para as contas':'Go to accounts','Esconder na bandeja':'Hide to tray','Remover conta atual':'Remove current account','Escolher som de notificação':'Choose notification sound','Atualizar':'Refresh','Buscar':'Search','A&juda':'&Help','&Arquivo':'&File','&Mensagem':'&Message','&Configurações':'&Settings','Agrupar por conversa':'Group by conversation','AudioMail continua na bandeja':'AudioMail remains in the system tray',
})
_TEXT['es'].update({
'Baixando a atualização. Aguarde.':'Descargando la actualización. Espera.','Baixando atualização':'Descargando actualización','Para abrir de novo, aperte Windows mais B, escolha o ícone e aperte Enter.':'Para volver a abrirlo, pulsa Windows+B, selecciona el icono y pulsa Enter.','AudioMail versão %s\nSite: %s':'AudioMail versión %s\nSitio web: %s','Nenhuma mensagem nova. %d não lidas.%s':'No hay mensajes nuevos. %d sin leer.%s','AudioMail versão %s. Abra o programa para atualizar.':'AudioMail versión %s. Abre el programa para actualizar.','Atualização obrigatória do AudioMail, versão %s.':'Actualización obligatoria de AudioMail, versión %s.','Versão %s ignorada.':'Versión %s omitida.','Tradução automática de %s para %s.':'Traducción automática del %s al %s.','%s\n\nNova versão: %s\nVersão instalada: %s\n\nNovidades:\n%s':'%s\n\nNueva versión: %s\nVersión instalada: %s\n\nNovedades:\n%s','ATUALIZAÇÃO OBRIGATÓRIA: o AudioMail não pode continuar sem atualizar.':'ACTUALIZACIÓN OBLIGATORIA: AudioMail no puede continuar sin actualizar.','Mostrando a tradução.':'Mostrando la traducción.','A mensagem já está em %s.':'El mensaje ya está en %s.','Atualização urgente':'Actualización urgente','ATUALIZAÇÃO URGENTE: atualize o quanto antes.':'ACTUALIZACIÓN URGENTE: actualiza cuanto antes.','(sem descrição)':'(sin descripción)','Só novidades: você pode atualizar quando quiser.':'Actualización opcional: puedes actualizar cuando quieras.','Esse arquivo não é um WAV válido. Converta o som para WAV e tente de novo.':'Este archivo WAV no es válido. Convierte el sonido a WAV e inténtalo de nuevo.','Idioma salvo. Reinicie o AudioMail para aplicar a alteração.':'Idioma guardado. Reinicia AudioMail para aplicar el cambio.','Abrir AudioMail':'Abrir AudioMail','Configurações':'Configuración','Idioma':'Idioma','Traduzir mensagem':'Traducir mensaje','Marcar como lida':'Marcar como leído','Marcar como não lida':'Marcar como no leído','Ir para as pastas':'Ir a carpetas','Ir para as contas':'Ir a cuentas','Esconder na bandeja':'Ocultar en la bandeja','Remover conta atual':'Eliminar cuenta actual','Escolher som de notificação':'Elegir sonido de notificación','Atualizar':'Actualizar','Buscar':'Buscar','A&juda':'A&yuda','&Arquivo':'&Archivo','&Mensagem':'&Mensaje','&Configurações':'&Configuración','Agrupar por conversa':'Agrupar por conversación','AudioMail continua na bandeja':'AudioMail sigue en la bandeja del sistema',
})


_TEXT['en'].update({'Nova mensagem de %s':'New message from %s','%d novas mensagens':'%d new messages','De %s':'From %s',' e outros':' and others'})
_TEXT['es'].update({'Nova mensagem de %s':'Nuevo mensaje de %s','%d novas mensagens':'%d mensajes nuevos','De %s':'De %s',' e outros':' y otros'})


_TEXT['en'].update({'Ferramentas':'Tools','&Ferramentas':'&Tools','Configurações\tCtrl+P':'Settings\tCtrl+P'})
_TEXT['es'].update({'Ferramentas':'Herramientas','&Ferramentas':'&Herramientas','Configurações\tCtrl+P':'Configuración\tCtrl+P'})
_TEXT['en'].update({'Idioma e tradução':'Language and translation','Avisos de mensagens novas':'New message alerts','Janela e inicialização':'Window and startup','Outras opções':'Other settings'})
_TEXT['es'].update({'Idioma e tradução':'Idioma y traducción','Avisos de mensagens novas':'Avisos de mensajes nuevos','Janela e inicialização':'Ventana e inicio','Outras opções':'Otras opciones'})
_TEXT['en'].update({
    'Resumo com IA':'AI summary', 'OpenAI':'OpenAI', 'Gemini':'Gemini',
    'Outro compatível com OpenAI':'Other OpenAI-compatible service', 'Provedor de IA':'AI provider',
    'Modelo de IA':'AI model', 'Endereço base do serviço compatível':'Compatible service base URL',
    'Chave de API':'API key', 'Apagar a chave salva deste provedor':'Delete this provider’s saved key',
    'Já existe uma chave salva para este provedor.':'A key is already saved for this provider.',
    'Nenhuma chave salva para este provedor.':'No key saved for this provider.',
    'O conteúdo do e-mail só é enviado ao provedor quando você pedir o resumo. O uso da API pode gerar cobrança.':'Email content is sent to the provider only when you ask for a summary. API usage may incur charges. The ChatGPT subscription does not automatically include API usage.',
    'O conteúdo só é enviado quando você pede o resumo. O uso da API pode ser cobrado à parte; a senha ou assinatura do ChatGPT não é uma chave de API.':'Content is sent only when you ask for a summary. API usage may be billed separately; your ChatGPT password or subscription is not an API key.',
    'Resumir com IA':'Summarize with AI', 'Gerando resumo com IA. Aguarde.':'Generating AI summary. Please wait.',
    'Resumo da mensagem':'Message summary', 'Lembretes e datas importantes':'Reminders and important dates',
    'Enviar mensagem para resumo com IA':'Send message for AI summary',
    'Configure primeiro sua chave de API em Configurações > Resumo com IA.':'First configure your API key in Settings > AI summary.',
    'Esta mensagem não tem texto para resumir.':'This message has no text to summarize.',
    'O texto desta mensagem ou conversa será enviado ao %s usando sua chave de API. O provedor pode cobrar pelo uso; a assinatura do ChatGPT não inclui automaticamente o uso da API. Autorizar agora e nas próximas vezes?':'The text of this message or conversation will be sent to %s using your API key. The provider may charge for usage; a ChatGPT subscription does not automatically include API usage. Allow now and in the future?',
    'Não consegui proteger a chave com a criptografia do Windows. A chave não foi salva.':'Could not protect the key with Windows encryption. The key was not saved.',
    'Informe uma chave de API em Configurações > Resumo com IA.':'Enter an API key in Settings > AI summary.',
    'Informe o modelo de IA em Configurações > Resumo com IA.':'Enter an AI model in Settings > AI summary.',
    'Informe o endereço base do serviço compatível com OpenAI.':'Enter the base URL for the OpenAI-compatible service.',
    'Por segurança, o endereço do serviço precisa usar HTTPS.':'For security, the service URL must use HTTPS.',
    'Selecione um provedor de IA válido.':'Select a valid AI provider.',
    'A API de IA não devolveu um resumo.':'The AI API did not return a summary.',
    'A API de IA respondeu com erro %s%s':'The AI API returned error %s%s',
    'Não foi possível conectar à API de IA: %s':'Could not connect to the AI API: %s',
    'A API de IA devolveu uma resposta que o AudioMail não reconheceu.':'The AI API returned a response AudioMail could not understand.',
    'Apagar lembrete selecionado':'Delete selected reminder',
})
_TEXT['es'].update({
    'Resumo com IA':'Resumen con IA', 'OpenAI':'OpenAI', 'Gemini':'Gemini',
    'Outro compatível com OpenAI':'Otro servicio compatible con OpenAI', 'Provedor de IA':'Proveedor de IA',
    'Modelo de IA':'Modelo de IA', 'Endereço base do serviço compatível':'URL base del servicio compatible',
    'Chave de API':'Clave de API', 'Apagar a chave salva deste provedor':'Eliminar la clave guardada de este proveedor',
    'Já existe uma chave salva para este provedor.':'Ya hay una clave guardada para este proveedor.',
    'Nenhuma chave salva para este provedor.':'No hay una clave guardada para este proveedor.',
    'O conteúdo do e-mail só é enviado ao provedor quando você pedir o resumo. O uso da API pode gerar cobrança.':'El contenido del correo solo se envía al proveedor cuando pides el resumen. El uso de la API puede tener un costo. La suscripción de ChatGPT no incluye automáticamente el uso de la API.',
    'O conteúdo só é enviado quando você pede o resumo. O uso da API pode ser cobrado à parte; a senha ou assinatura do ChatGPT não é uma chave de API.':'El contenido solo se envía cuando pides el resumen. El uso de la API puede cobrarse aparte; tu contraseña o suscripción de ChatGPT no es una clave de API.',
    'Resumir com IA':'Resumir con IA', 'Gerando resumo com IA. Aguarde.':'Generando resumen con IA. Espera.',
    'Resumo da mensagem':'Resumen del mensaje', 'Enviar mensagem para resumo com IA':'Enviar mensaje para resumir con IA',
    'Configure primeiro sua chave de API em Configurações > Resumo com IA.':'Primero configura tu clave de API en Configuración > Resumen con IA.',
    'Esta mensagem não tem texto para resumir.':'Este mensaje no tiene texto para resumir.',
    'O texto desta mensagem ou conversa será enviado ao %s usando sua chave de API. O provedor pode cobrar pelo uso; a assinatura do ChatGPT não inclui automaticamente o uso da API. Autorizar agora e nas próximas vezes?':'El texto de este mensaje o conversación se enviará a %s con tu clave de API. El proveedor puede cobrar por el uso; la suscripción de ChatGPT no incluye automáticamente el uso de la API. ¿Permitirlo ahora y en el futuro?',
    'Não consegui proteger a chave com a criptografia do Windows. A chave não foi salva.':'No se pudo proteger la clave con el cifrado de Windows. No se guardó.',
    'Informe uma chave de API em Configurações > Resumo com IA.':'Introduce una clave de API en Configuración > Resumen con IA.',
    'Informe o modelo de IA em Configurações > Resumo com IA.':'Introduce un modelo de IA en Configuración > Resumen con IA.',
    'Informe o endereço base do serviço compatível com OpenAI.':'Introduce la URL base del servicio compatible con OpenAI.',
    'Por segurança, o endereço do serviço precisa usar HTTPS.':'Por seguridad, la URL del servicio debe usar HTTPS.',
    'Selecione um provedor de IA válido.':'Selecciona un proveedor de IA válido.',
    'A API de IA não devolveu um resumo.':'La API de IA no devolvió un resumen.',
    'A API de IA respondeu com erro %s%s':'La API de IA respondió con el error %s%s',
    'Não foi possível conectar à API de IA: %s':'No se pudo conectar con la API de IA: %s',
    'A API de IA devolveu uma resposta que o AudioMail não reconheceu.':'La API de IA devolvió una respuesta que AudioMail no pudo entender.',
})
_TEXT['en'].update({
    'Agenda de lembretes':'Reminder schedule', 'Calendário de lembretes':'Reminder calendar',
    'Calendário':'Calendar', 'Apagar lembrete selecionado':'Delete selected reminder',
    'Lembretes e datas importantes':'Reminders and important dates',
    'Qual lembrete deseja apagar?':'Which reminder do you want to delete?',
    'Adicionar lembrete':'Add reminder', 'Data':'Date', 'Lembretes':'Reminders',
    'Janeiro':'January', 'Fevereiro':'February', 'Março':'March',
    'Abril':'April', 'Maio':'May', 'Junho':'June', 'Julho':'July', 'Agosto':'August',
    'Setembro':'September', 'Outubro':'October', 'Novembro':'November', 'Dezembro':'December',
    'Setas: escolher dia. Ctrl+esquerda/direita: mês. Ctrl+cima/baixo: ano.':'Arrows: choose day. Ctrl+Left/Right: month. Ctrl+Up/Down: year.',
    'Setas: percorrer lembretes. Ctrl+esquerda/direita: mês. Ctrl+cima/baixo: ano.':'Arrows: move through reminders. Ctrl+Left/Right: month. Ctrl+Up/Down: year.',
    'Feriado nacional':'National holiday', 'Buscando feriados nacionais pela internet...':'Loading national holidays from the internet...',
    'Feriados nacionais salvos localmente.':'National holidays saved locally.',
    'Feriados nacionais atualizados.':'National holidays updated.',
    'Sem conexão: usando feriados salvos.':'Offline: showing saved holidays.',
    'Não foi possível carregar os feriados.':'Could not load holidays.',
    'Ano Novo':'New Year’s Day', 'Dia do Trabalho':'Labor Day', 'Independência do Brasil':'Brazil Independence Day',
    'Nossa Senhora Aparecida':'Our Lady of Aparecida', 'Finados':'All Souls’ Day',
    'Proclamação da República':'Republic Day', 'Natal':'Christmas Day',
    'Dia da Consciência Negra':'Black Awareness Day', 'Sexta-feira Santa':'Good Friday',
    'Véspera de Ano Novo':'New Year’s Eve', 'Véspera de Natal':'Christmas Eve',
    'Aniversário de São Paulo':'São Paulo Anniversary',
    'Public':'Public holiday', 'Bank':'Bank holiday', 'School':'School holiday',
    'Authorities':'Authorities holiday', 'Optional':'Optional holiday', 'Observance':'Observance',
    'Apagar lembrete':'Delete reminder', 'Título':'Title', 'Data e hora':'Date and time',
    'Hora':'Hour', 'Minuto':'Minute', 'Escolha uma data e hora futuras.':'Choose a future date and time.',
    'Lembrete':'Reminder', 'Novo recurso: lembretes':'New feature: reminders',
    'O AudioMail agora tem uma agenda de lembretes local. Os lembretes ficam salvos neste computador; não há integração nem sincronização com o Google.':'AudioMail now has a local reminder schedule. Reminders are saved on this computer; there is no Google integration or synchronization.',
})
_TEXT['es'].update({
    'Agenda de lembretes':'Agenda de recordatorios', 'Calendário de lembretes':'Calendario de recordatorios',
    'Calendário':'Calendario', 'Apagar lembrete selecionado':'Eliminar recordatorio seleccionado',
    'Lembretes e datas importantes':'Recordatorios y fechas importantes',
    'Qual lembrete deseja apagar?':'¿Qué recordatorio quieres eliminar?',
    'Adicionar lembrete':'Añadir recordatorio', 'Data':'Fecha', 'Lembretes':'Recordatorios',
    'Janeiro':'Enero', 'Fevereiro':'Febrero', 'Março':'Marzo',
    'Abril':'Abril', 'Maio':'Mayo', 'Junho':'Junio', 'Julho':'Julio', 'Agosto':'Agosto',
    'Setembro':'Septiembre', 'Outubro':'Octubre', 'Novembro':'Noviembre', 'Dezembro':'Diciembre',
    'Setas: escolher dia. Ctrl+esquerda/direita: mês. Ctrl+cima/baixo: ano.':'Flechas: elegir día. Ctrl+izquierda/derecha: mes. Ctrl+arriba/abajo: año.',
    'Setas: percorrer lembretes. Ctrl+esquerda/direita: mês. Ctrl+cima/baixo: ano.':'Flechas: recorrer recordatorios. Ctrl+izquierda/derecha: mes. Ctrl+arriba/abajo: año.',
    'Feriado nacional':'Festivo nacional', 'Buscando feriados nacionais pela internet...':'Buscando festivos nacionales en internet...',
    'Feriados nacionais salvos localmente.':'Festivos nacionales guardados localmente.',
    'Feriados nacionais atualizados.':'Festivos nacionales actualizados.',
    'Sem conexão: usando feriados salvos.':'Sin conexión: se muestran los festivos guardados.',
    'Não foi possível carregar os feriados.':'No se pudieron cargar los festivos.',
    'Ano Novo':'Año Nuevo', 'Dia do Trabalho':'Día del Trabajo', 'Independência do Brasil':'Independencia de Brasil',
    'Nossa Senhora Aparecida':'Nuestra Señora Aparecida', 'Finados':'Día de los Difuntos',
    'Proclamação da República':'Proclamación de la República', 'Natal':'Navidad',
    'Dia da Consciência Negra':'Día de la Conciencia Negra', 'Sexta-feira Santa':'Viernes Santo',
    'Véspera de Ano Novo':'Nochevieja', 'Véspera de Natal':'Nochebuena',
    'Aniversário de São Paulo':'Aniversario de São Paulo',
    'Public':'Festivo', 'Bank':'Festivo bancario', 'School':'Festivo escolar',
    'Authorities':'Cierre administrativo', 'Optional':'Festivo opcional', 'Observance':'Conmemoración',
    'Apagar lembrete':'Eliminar recordatorio', 'Título':'Título', 'Data e hora':'Fecha y hora',
    'Hora':'Hora', 'Minuto':'Minuto', 'Escolha uma data e hora futuras.':'Elige una fecha y hora futuras.',
    'Lembrete':'Recordatorio', 'Novo recurso: lembretes':'Nueva función: recordatorios',
    'O AudioMail agora tem uma agenda de lembretes local. Os lembretes ficam salvos neste computador; não há integração nem sincronização com o Google.':'AudioMail ahora tiene una agenda local de recordatorios. Se guardan en este equipo; no hay integración ni sincronización con Google.',
})

_language = "pt"


def set_language(code):
    global _language
    _language = code if code in ("pt", "en", "es") else "pt"


def tr(text):
    if not isinstance(text, str):
        return text
    catalog = _TEXT.get(_language, {})
    if text in catalog:
        return catalog[text]
    # Translate runtime messages that were formatted before reaching the UI.
    import re
    for source, target in catalog.items():
        if "%" not in source:
            continue
        parts = re.split(r"(%[sd])", source)
        pattern = "^" + "".join(r"(\d+)" if part == "%d" else r"(.+?)" if part == "%s" else re.escape(part) for part in parts) + "$"
        match = re.match(pattern, text, re.S)
        if match:
            values = iter(match.groups())
            return re.sub(r"%[sd]", lambda _m: next(values), target)
    return text


def message_box(message, caption="", *args, **kwargs):
    import wx
    return wx.MessageBox(tr(message), tr(caption), *args, **kwargs)
