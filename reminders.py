"""Agenda de lembretes guardada somente neste computador."""
import datetime
import threading

import wx
import wx.adv

import i18n
import holidays as holiday_api


class ReminderDialog(wx.Dialog):
    def __init__(self, parent, reminders):
        super().__init__(parent, title=i18n.tr("Calendário"), size=(620, 480))
        self.reminders = reminders
        self.selected_date = datetime.date.today()
        self.holidays = holiday_api.cached_holidays(self.selected_date.year)
        self._holiday_requests = set()
        self._destroyed = False
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        self.month_label = wx.StaticText(panel)
        layout.Add(self.month_label, 0, wx.ALIGN_CENTER | wx.ALL, 8)
        self.table = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.table.InsertColumn(0, i18n.tr("Data"), width=150)
        self.table.InsertColumn(1, i18n.tr("Lembretes e datas importantes"), width=400)
        self.table.SetName(i18n.tr("Calendário"))
        layout.Add(self.table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        hint = wx.StaticText(panel, label=i18n.tr(
            "Setas: percorrer lembretes. Ctrl+esquerda/direita: mês. Ctrl+cima/baixo: ano."))
        layout.Add(hint, 0, wx.EXPAND | wx.ALL, 8)
        self.holiday_status = wx.StaticText(panel, label="")
        layout.Add(self.holiday_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        add = wx.Button(panel, label=i18n.tr("Adicionar lembrete"))
        self.remove_button = wx.Button(panel, label=i18n.tr("Apagar lembrete selecionado"))
        row.Add(add, 0, wx.RIGHT, 8)
        row.Add(self.remove_button)
        layout.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        panel.SetSizer(layout)
        buttons = self.CreateStdDialogButtonSizer(wx.OK)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)
        add.Bind(wx.EVT_BUTTON, self.on_add)
        self.remove_button.Bind(wx.EVT_BUTTON, self.on_remove)
        self.table.Bind(wx.EVT_KEY_DOWN, self.on_table_key)
        self.table.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_row_selected)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        self.refresh()
        self.CentreOnParent()
        self.table.SetFocus()

    def on_destroy(self, evt):
        if evt.GetEventObject() is self:
            self._destroyed = True
        evt.Skip()

    def refresh(self):
        month_key = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro")
        month_name = i18n.tr(month_key[self.selected_date.month - 1])
        self.month_label.SetLabel("%s %s" % (month_name, self.selected_date.year))
        self.table.DeleteAllItems()
        events = {}
        for item in sorted(self.reminders, key=lambda reminder: reminder.get("when", "")):
            try:
                moment = datetime.datetime.fromisoformat(item["when"])
            except (KeyError, TypeError, ValueError):
                continue
            if moment.year == self.selected_date.year and moment.month == self.selected_date.month:
                events.setdefault(moment.date(), []).append("%s — %s" % (
                    moment.strftime("%H:%M"), item.get("title", "")))
        for holiday in self.holidays:
            try:
                day = datetime.date.fromisoformat(holiday["date"])
            except (KeyError, TypeError, ValueError):
                continue
            if day.year == self.selected_date.year and day.month == self.selected_date.month:
                name = self._holiday_name(holiday.get("name", "Feriado"))
                title = "%s: %s" % (i18n.tr("Feriado nacional"), name)
                events.setdefault(day, []).append(title)
        last_day = (self._next_month(self.selected_date.replace(day=1)) - datetime.timedelta(days=1)).day
        for day_number in range(1, last_day + 1):
            day = self.selected_date.replace(day=day_number)
            row = self.table.InsertItem(day_number - 1, day.strftime("%d/%m/%Y"))
            self.table.SetItem(row, 1, " | ".join(events.get(day, [])))
            self.table.SetItemData(row, day.toordinal())
            if day == self.selected_date:
                self.table.SetItemState(row, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        self._update_remove_button()
        self._load_holidays_for_year(self.selected_date.year)

    @staticmethod
    def _holiday_name(name):
        names = {
            "New Year's Day": "Ano Novo", "Tiradentes": "Tiradentes",
            "Labor Day": "Dia do Trabalho", "Independence Day": "Independência do Brasil",
            "Our Lady of Aparecida": "Nossa Senhora Aparecida", "All Souls' Day": "Finados",
            "Republic Proclamation Day": "Proclamação da República", "Christmas Day": "Natal",
            "Black Consciousness Day": "Dia da Consciência Negra", "Good Friday": "Sexta-feira Santa",
            "Carnival": "Carnaval", "Corpus Christi": "Corpus Christi",
            "New Year's Eve": "Véspera de Ano Novo", "Christmas Eve": "Véspera de Natal",
            "Founding of São Paulo": "Aniversário de São Paulo",
        }
        translated = names.get(name)
        return i18n.tr(translated) if translated else name

    def _load_holidays_for_year(self, year):
        if year in self._holiday_requests:
            return
        self._holiday_requests.add(year)
        cached = holiday_api.cached_holidays(year)
        if cached:
            self.holidays = cached
            self.holiday_status.SetLabel(i18n.tr("Feriados nacionais salvos localmente."))
        else:
            self.holidays = []
            self.holiday_status.SetLabel(i18n.tr("Buscando feriados nacionais pela internet..."))
        self.holiday_status.GetParent().Layout()
        threading.Thread(target=self._fetch_holidays, args=(year,), daemon=True).start()

    def _fetch_holidays(self, year):
        try:
            result = holiday_api.fetch_holidays(year)
            error = None
        except Exception as exc:
            result, error = None, exc
        wx.CallAfter(self._show_holidays, year, result, error)

    def _show_holidays(self, year, data, error):
        if self._destroyed:
            return
        if year == self.selected_date.year:
            if data is not None:
                self.holidays = data
                self.holiday_status.SetLabel(i18n.tr("Feriados nacionais atualizados."))
            else:
                cached = holiday_api.cached_holidays(year)
                self.holidays = cached
                self.holiday_status.SetLabel(i18n.tr(
                    "Sem conexão: usando feriados salvos." if cached else
                    "Não foi possível carregar os feriados."))
            self.refresh_without_holiday_fetch()
            self.holiday_status.GetParent().Layout()

    def refresh_without_holiday_fetch(self):
        # Rebuild the table using the new holiday data without starting another request.
        year = self.selected_date.year
        self._holiday_requests.add(year)
        self.refresh()

    def on_row_selected(self, evt):
        self.selected_date = datetime.date.fromordinal(self.table.GetItemData(evt.GetIndex()))
        self._update_remove_button()

    def _update_remove_button(self):
        has_reminders = False
        for item in self.reminders:
            try:
                has_reminders |= datetime.datetime.fromisoformat(item["when"]).date() == self.selected_date
            except (KeyError, TypeError, ValueError):
                continue
        self.remove_button.Enable(has_reminders)

    @staticmethod
    def _next_month(first):
        if first.month == 12:
            return first.replace(year=first.year + 1, month=1)
        return first.replace(month=first.month + 1)

    def on_table_key(self, evt):
        if evt.ControlDown() and evt.GetKeyCode() in (wx.WXK_LEFT, wx.WXK_RIGHT,
                                                       wx.WXK_UP, wx.WXK_DOWN):
            delta = -1 if evt.GetKeyCode() in (wx.WXK_LEFT, wx.WXK_UP) else 1
            month = self.selected_date.month
            year = self.selected_date.year
            if evt.GetKeyCode() in (wx.WXK_LEFT, wx.WXK_RIGHT):
                month += delta
                if month < 1:
                    month, year = 12, year - 1
                elif month > 12:
                    month, year = 1, year + 1
            else:
                year += delta
            first_next = self._next_month(datetime.date(year, month, 1))
            last_day = (first_next - datetime.timedelta(days=1)).day
            self.selected_date = datetime.date(year, month, min(self.selected_date.day, last_day))
            self.refresh()
            self.table.SetFocus()
            evt.Skip(False)
            return
        evt.Skip()

    def on_add(self, evt):
        selected_day = self.selected_date
        selected = self.table.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if selected != wx.NOT_FOUND:
            selected_day = datetime.date.fromordinal(self.table.GetItemData(selected))
        dlg = wx.Dialog(self, title=i18n.tr("Adicionar lembrete"))
        panel = wx.Panel(dlg)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(panel, label=i18n.tr("Título")), 0, wx.ALL, 8)
        title = wx.TextCtrl(panel)
        layout.Add(title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        layout.Add(wx.StaticText(panel, label=i18n.tr("Data e hora")), 0, wx.LEFT | wx.RIGHT, 8)
        date = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        date.SetValue(wx.DateTime.FromDMY(selected_day.day, selected_day.month - 1, selected_day.year))
        layout.Add(date, 0, wx.EXPAND | wx.ALL, 8)
        time_row = wx.BoxSizer(wx.HORIZONTAL)
        default_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
        hour = wx.SpinCtrl(panel, min=0, max=23, initial=default_time.hour)
        minute = wx.SpinCtrl(panel, min=0, max=59, initial=default_time.minute)
        time_row.Add(wx.StaticText(panel, label=i18n.tr("Hora")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        time_row.Add(hour, 0, wx.RIGHT, 12)
        time_row.Add(wx.StaticText(panel, label=i18n.tr("Minuto")), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        time_row.Add(minute)
        layout.Add(time_row, 0, wx.ALL, 8)
        panel.SetSizer(layout)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        outer.Add(dlg.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        dlg.SetSizerAndFit(outer)
        if dlg.ShowModal() == wx.ID_OK and title.GetValue().strip():
            selected = date.GetValue()
            moment = datetime.datetime(selected.GetYear(), selected.GetMonth() + 1,
                                       selected.GetDay(), hour.GetValue(), minute.GetValue())
            if moment > datetime.datetime.now():
                self.reminders.append({"title": title.GetValue().strip(), "when": moment.isoformat(timespec="minutes")})
                self.selected_date = moment.date().replace(day=1)
                self.refresh()
            else:
                wx.MessageBox(i18n.tr("Escolha uma data e hora futuras."), i18n.tr("Aviso"),
                              wx.OK | wx.ICON_WARNING, self)
        dlg.Destroy()

    def on_remove(self, evt):
        index = self.table.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index != wx.NOT_FOUND:
            day = datetime.date.fromordinal(self.table.GetItemData(index))
            candidates = []
            for original_index, item in enumerate(self.reminders):
                try:
                    moment = datetime.datetime.fromisoformat(item["when"])
                except (KeyError, TypeError, ValueError):
                    continue
                if moment.date() == day:
                    candidates.append((original_index, "%s — %s" % (
                        moment.strftime("%H:%M"), item.get("title", ""))))
            if len(candidates) == 1:
                del self.reminders[candidates[0][0]]
            elif candidates:
                dlg = wx.SingleChoiceDialog(self, i18n.tr("Qual lembrete deseja apagar?"),
                                            i18n.tr("Apagar lembrete selecionado"),
                                            [label for _, label in candidates])
                if dlg.ShowModal() == wx.ID_OK:
                    del self.reminders[candidates[dlg.GetSelection()][0]]
                dlg.Destroy()
            self.refresh()
