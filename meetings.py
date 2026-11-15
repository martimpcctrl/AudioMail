"""Responder a convites de reunião pela janela principal (Aceitar, Talvez, Recusar)."""

import i18n
import invites
from common import save_config


def add_reminder(reminders, reminder):
    """Põe o lembrete no Calendário, sem repetir um igual. Devolve True se entrou."""
    if reminder is None:
        return False
    for r in reminders:
        if r.get("title") == reminder["title"] and r.get("when") == reminder["when"]:
            return False
    reminders.append(reminder)
    return True


class MeetingMixin:
    def invite_line(self, full):
        """A frase do convite para o começo da leitura, ou ''."""
        invite = full.get("invite")
        return invites.describe(invite) if invite else ""

    def can_answer_invite(self, acc, full):
        return bool(acc and acc.client) and invites.can_answer(full.get("invite"), acc.email)

    def answer_invite(self, acc, full, answer):
        invite, client = full["invite"], acc.client
        subject, body, ics = invites.build_reply(invite, acc.email, answer)

        def work():
            client.send_calendar_reply(invite["organizer"], subject, body, ics)

        def done(_):
            added = False
            if answer != "decline":
                added = add_reminder(self.cfg.setdefault("reminders", []), invites.reminder_for(invite))
                if added:
                    save_config(self.cfg)
            spoken = {"accept": "Convite aceito.", "tentative": "Resposta Talvez enviada.",
                      "decline": "Convite recusado."}[answer]
            if added:
                spoken = i18n.tr(spoken) + " " + i18n.tr("A reunião entrou no Calendário.")
            self.announce(spoken)
            self.SetStatusText(i18n.tr(spoken))

        self.run(work, done, "Enviando resposta ao convite")
