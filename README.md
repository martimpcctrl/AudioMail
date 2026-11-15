# AudioMail

Cliente de Gmail para Windows feito para quem usa leitor de tela (NVDA, JAWS, Narrador). A interface usa controles nativos do Windows (wxPython), e o programa fala os avisos pelo leitor de tela.

## O que ele faz

- Lê, escreve, responde e organiza e-mails do Gmail (também Google Workspace), com várias contas.
- Avisa na hora quando chega mensagem nova e fica na bandeja do sistema.
- Busca, conversas, pastas, rascunhos e atalhos de teclado para tudo.
- Tradução de mensagens e do texto que você escreve.
- Resumo de mensagens com IA (OpenAI, Google Gemini ou compatível), com a sua própria chave de API.
- Lembretes, calendário com feriados e chamados de suporte direto pelo programa.
- Atualização automática conferida por SHA-256.

## Baixar

A versão mais recente está em [Releases](https://github.com/martimpcctrl/AudioMail/releases). Baixe o `AudioMail-Portatil-X.Y.Z.zip`, extraia e abra o `AudioMail.exe`.

Para entrar, use o seu e-mail do Gmail e uma **senha de app** (crie em <https://myaccount.google.com/apppasswords>, com a verificação em duas etapas ativada). A senha fica criptografada pelo Windows, só neste computador.

## Rodar pelo código

```
pip install -r requirements.txt
python audiomail.py
```

O `accessible-output2` é o que faz o programa falar pelo leitor de tela. Sem ele, o AudioMail funciona, só sem a fala.

Para compilar o executável portátil, rode `compilar.bat`. O manual completo está no programa (Ajuda, Abrir manual, F1) e no [LEIA-ME.txt](LEIA-ME.txt).

## Privacidade

O AudioMail não tem conta própria nem servidor que guarde os seus e-mails. A política de privacidade e os termos de uso aparecem no programa, na primeira vez que ele abre.

## Contato

Abra um chamado em Ajuda, Abrir chamado de suporte, ou uma [issue](https://github.com/martimpcctrl/AudioMail/issues) aqui no GitHub.
