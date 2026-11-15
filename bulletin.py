"""Textos do boletim falado e das ações da notificação. Sem interface e sem rede."""
import datetime

import i18n

TOP_SENDERS = 3
ACTION_REPLY, ACTION_ARCHIVE, ACTION_READ = 1, 2, 3


def _plural(n, one, many):
    return i18n.tr(one) if n == 1 else i18n.tr(many) % n


def senders_summary(msgs, top=TOP_SENDERS):
    """'3 de Ana, 2 de Banco e mais 4 de outros remetentes'."""
    counts, order = {}, []
    for m in msgs:
        name = (m.get("from") or "").strip() or i18n.tr("remetente desconhecido")
        if name not in counts:
            counts[name] = 0
            order.append(name)
        counts[name] += 1
    ranked = sorted(order, key=lambda n: (-counts[n], order.index(n)))
    parts = [i18n.tr("%d de %s") % (counts[n], n) for n in ranked[:top]]
    rest = sum(counts[n] for n in ranked[top:])
    text = ", ".join(parts)
    if rest:
        text += i18n.tr(" e mais %d de outros remetentes") % rest
    return text


def account_part(unread_msgs, tabs=()):
    """O pedaço de uma conta: não lidas, de quem, e as abas do Gmail."""
    if not unread_msgs:
        text = i18n.tr("Nenhuma mensagem não lida.")
    else:
        text = "%s: %s." % (_plural(len(unread_msgs), "1 não lida", "%d não lidas"),
                            senders_summary(unread_msgs))
    tabs = [(name, n) for name, n in tabs if n]
    if tabs:
        text += " " + i18n.tr("Por aba: %s.") % ", ".join("%s %d" % (i18n.tr(name), n) for name, n in tabs)
    return text


def reminders_today(reminders, now=None):
    """[(hora, título)] dos lembretes de hoje, em ordem."""
    now = now or datetime.datetime.now()
    out = []
    for r in reminders or []:
        try:
            when = datetime.datetime.fromisoformat(r.get("when", ""))
        except (TypeError, ValueError):
            continue
        if when.date() == now.date():
            out.append((when, r.get("title", "")))
    out.sort()
    return [(w.strftime("%H:%M"), t) for w, t in out]


def scheduled_today(items, now=None):
    now = now or datetime.datetime.now()
    end = datetime.datetime.combine(now.date(), datetime.time(23, 59, 59)).timestamp()
    return sum(1 for i in items or [] if float(i.get("when", 0) or 0) <= end and not i.get("error"))


def build(parts, reminders=(), scheduled=0):
    """O boletim inteiro. ``parts``: [(conta ou "", texto da conta)]."""
    lines = []
    for email, text in parts:
        lines.append("%s: %s" % (email, text) if email else text)
    if reminders:
        lines.append(i18n.tr("Lembretes de hoje: %s.") % "; ".join("%s %s" % r for r in reminders))
    if scheduled:
        lines.append(_plural(scheduled, "1 mensagem agendada para hoje.", "%d mensagens agendadas para hoje."))
    return " ".join(lines)


def notification_actions(count):
    """Botões da notificação de mensagem nova: [(id, texto)]."""
    if count == 1:
        return [(ACTION_REPLY, "Responder"), (ACTION_ARCHIVE, "Arquivar"), (ACTION_READ, "Marcar como lida")]
    return [(ACTION_READ, "Marcar todas como lidas"), (ACTION_ARCHIVE, "Arquivar todas")]
