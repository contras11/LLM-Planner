import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid

# --- Data ---
# タイムゾーンを設定
TZ = pytz.timezone('Asia/Tokyo')

# サンプルの予定データ (インメモリ)
# 実際のアプリケーションではデータベースから読み込む
events = [
    {
        'id': str(uuid.uuid4()),
        'title': 'Team Standup',
        'start': TZ.localize(datetime(2025, 8, 11, 10, 0)),
        'end': TZ.localize(datetime(2025, 8, 11, 10, 15)),
        'user_id': 'user_a',
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'Design Review',
        'start': TZ.localize(datetime(2025, 8, 11, 14, 0)),
        'end': TZ.localize(datetime(2025, 8, 11, 15, 30)),
        'user_id': 'user_a',
    },
    {
        'id': str(uuid.uuid4()),
        'title': '1-on-1 with Manager',
        'start': TZ.localize(datetime(2025, 8, 13, 11, 0)),
        'end': TZ.localize(datetime(2025, 8, 13, 11, 30)),
        'user_id': 'user_b',
    },
    {
        'id': str(uuid.uuid4()),
        'title': '[User B] Project Kick-off',
        'start': TZ.localize(datetime(2025, 8, 13, 15, 0)),
        'end': TZ.localize(datetime(2025, 8, 13, 16, 0)),
        'user_id': 'user_b',
    },
    {
        'id': str(uuid.uuid4()),
        'title': 'All-hands Meeting',
        'start': TZ.localize(datetime(2025, 8, 15, 9, 0)),
        'end': TZ.localize(datetime(2025, 8, 15, 10, 0)),
        'user_id': 'all', # Or some other identifier for a group event
    },
]

# Atlassian Design Systemの色やスタイルに近づけるため、FLATLYテーマを使用
# https://bootswatch.com/flatly/
# Atlassian Colors: https://atlassian.design/foundations/color
# Blue: #0052CC, Light Blue: #DEEBFF, Grey: #F4F5F7
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

import re

# --- Helper Functions ---
def dummy_llm_api(text):
    """
    A dummy LLM function to parse natural language text into event details.
    This is a simplified mock for demonstration purposes.
    """
    text = text.lower()
    now = datetime.now(TZ)

    # Defaults
    title = "New Event"
    start_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    duration = timedelta(hours=1)

    # Very simple title parsing
    try:
        quoted = re.findall(r"['\"](.*?)['\"]", text)
        if quoted:
            title = quoted[0].capitalize()
        else:
            # Fallback for simple cases like "Meeting with team at 3pm"
            title_part = re.split(r'\s(at|on|tomorrow|today)\s', text, 1)[0]
            title = title_part.strip().capitalize() if title_part else "New Event"
    except Exception:
        pass

    # Simple date/time parsing
    if "tomorrow" in text:
        start_dt = (now + timedelta(days=1))
    elif "today" in text:
        start_dt = now

    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = time_match.group(3)
        if ampm == 'pm' and hour < 12:
            hour += 12
        if ampm == 'am' and hour == 12: # 12am is 00:00
            hour = 0
        start_dt = start_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

    duration_match = re.search(r'for (\d+)\s*(hour|minute)s?', text)
    if duration_match:
        num = int(duration_match.group(1))
        unit = duration_match.group(2)
        if unit == 'hour':
            duration = timedelta(hours=num)
        elif unit == 'minute':
            duration = timedelta(minutes=num)

    end_dt = start_dt + duration

    return {
        "title": title,
        "start": start_dt.strftime('%Y-%m-%dT%H:%M'),
        "end": end_dt.strftime('%Y-%m-%dT%H:%M')
    }

def generate_month_view(year, month):
    """ 指定された年月の月表示カレンダーを生成する """
    first_day_of_month = datetime(year, month, 1)
    last_day_of_month = first_day_of_month + pd.offsets.MonthEnd(1)
    start_date = first_day_of_month - timedelta(days=(first_day_of_month.weekday() + 1) % 7)
    end_date = last_day_of_month + timedelta(days=6 - last_day_of_month.weekday())
    date_range = pd.date_range(start_date, end_date, freq='D')

    header = [html.Thead(html.Tr([html.Th(day, className="text-center") for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]]))]

    weeks = []
    current_week = []
    for day in date_range:
        day_events = []
        for event in events:
            if event['start'].date() <= day.date() <= event['end'].date():
                day_events.append(
                    dbc.Badge(
                        event['title'],
                        color="primary" if event['user_id'] == 'user_a' else "secondary",
                        className="d-block mb-1 text-truncate"
                    )
                )

        cell_class = "p-2 border"
        if day.month != month:
            cell_class += " bg-light text-muted"
        if day.date() == datetime.now(TZ).date():
            cell_class += " border-primary"

        # Make the cell clickable by wrapping its content
        cell_content = html.Div(
            [
                html.Div(f"{day.day}", className="fw-bold"),
                html.Div(day_events, className="mt-1"),
            ],
            id={'type': 'date-cell', 'date': day.strftime('%Y-%m-%d')},
            className="h-100"
        )

        current_week.append(
            html.Td(
                cell_content,
                className=cell_class,
                style={"height": "120px", "vertical-align": "top"}
            )
        )
        if len(current_week) == 7:
            weeks.append(html.Tr(current_week))
            current_week = []

    body = [html.Tbody(weeks)]
    return dbc.Table(header + body, bordered=False, hover=False, className="table-fixed")


# --- Modal ---
def create_event_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Create New Event")),
            dbc.ModalBody(
                dbc.Form([
                    dbc.Label("Title"),
                    dbc.Input(type="text", id="event-title", placeholder="Enter event title"),
                    dbc.Label("Start Time", className="mt-3"),
                    dbc.Input(type="datetime-local", id="event-start-date"),
                    dbc.Label("End Time", className="mt-3"),
                    dbc.Input(type="datetime-local", id="event-end-date"),
                ])
            ),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="cancel-event-button", color="secondary"),
                dbc.Button("Save", id="save-event-button", color="primary"),
            ]),
        ],
        id="event-modal",
        is_open=False,
    )

# --- Layout ---
app.layout = dbc.Container(
    [
        dcc.Store(id='current-date-store', data={'year': 2025, 'month': 8}),
        create_event_modal(),
        # Header
        dbc.Row(
            dbc.Col(
                html.H1("Jules' Calendar", className="text-primary my-4"),
                width=12
            ),
            align="center",
        ),
        # ... (rest of the layout is the same as before)
        # Toolbar
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.ButtonGroup(
                            [
                                dbc.Button("Today", id="today-button", color="light"),
                                dbc.Button("<", id="prev-month-button", color="light"),
                                dbc.Button(">", id="next-month-button", color="light"),
                            ]
                        ),
                        html.Span("August 2025", id="current-month-year", className="mx-3 h4 align-middle"),
                    ],
                    width="auto"
                ),
                dbc.Col(
                    dbc.RadioItems(
                        id="view-switch",
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary",
                        labelCheckedClassName="active",
                        options=[
                            {'label': 'Month', 'value': 'month'},
                            {'label': 'Week', 'value': 'week', 'disabled': True},
                        ],
                        value='month',
                    ),
                    width="auto"
                ),
            ],
            justify="between",
            className="mb-4"
        ),

        # Calendar View
        dbc.Row(
            dbc.Col(
                html.Div(id="calendar-output"), # カレンダーがここに描画される
                width=12
            )
        ),

        # LLM Input Area (Footer)
        dbc.Row(
            dbc.Col(
                [
                    html.Hr(className="my-4"),
                    dbc.InputGroup(
                        [
                            dbc.Input(id="llm-input", placeholder="Create event with natural language... (e.g., 'Meeting with team tomorrow at 3pm for 1 hour')"),
                            dbc.Button("Create", id="llm-submit", color="primary"),
                        ]
                    ),
                    html.Div(id="llm-output"), # LLMからの応答を表示
                ],
                width=12
            ),
            className="mt-auto" # Push to the bottom
        )
    ],
    fluid=True,
    className="d-flex flex-column vh-100 p-4" # Use full viewport height
)


# --- Callbacks ---
@app.callback(
    Output('current-date-store', 'data', allow_duplicate=True),
    Input('prev-month-button', 'n_clicks'),
    Input('next-month-button', 'n_clicks'),
    Input('today-button', 'n_clicks'),
    State('current-date-store', 'data'),
    prevent_initial_call=True
)
def update_current_date(prev_clicks, next_clicks, today_clicks, data):
    triggered_id = dash.callback_context.triggered_id
    if not triggered_id:
        raise dash.exceptions.PreventUpdate

    year, month = data['year'], data['month']

    if triggered_id == 'today-button':
        today = datetime.now(TZ)
        return {'year': today.year, 'month': today.month}

    # Calculate month difference
    if triggered_id == 'prev-month-button':
        month -= 1
    elif triggered_id == 'next-month-button':
        month += 1

    # Handle year change
    if month == 0:
        month = 12
        year -= 1
    elif month == 13:
        month = 1
        year += 1

    return {'year': year, 'month': month}

@app.callback(
    [Output('calendar-output', 'children'),
     Output('current-month-year', 'children')],
    [Input('current-date-store', 'data')]
)
def update_calendar_view(date_data):
    year = date_data.get('year', 2025)
    month = date_data.get('month', 8)
    month_view = generate_month_view(year, month)
    month_year_str = datetime(year, month, 1).strftime('%B %Y')
    return month_view, month_year_str

@app.callback(
    Output('event-modal', 'is_open', allow_duplicate=True),
    Output('event-start-date', 'value'),
    Input({'type': 'date-cell', 'date': ALL}, 'n_clicks'),
    State('event-modal', 'is_open'),
    prevent_initial_call=True
)
def open_event_modal(n_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered_id
    date_str = triggered_id['date']
    default_start_time = f"{date_str}T09:00"

    return not is_open, default_start_time

@app.callback(
    Output('event-modal', 'is_open', allow_duplicate=True),
    Input('cancel-event-button', 'n_clicks'),
    Input('save-event-button', 'n_clicks'),
    prevent_initial_call=True,
)
def close_or_save_modal(cancel_clicks, save_clicks):
    # This callback handles both saving and canceling.
    # For now, it just closes the modal in both cases.
    # The actual saving logic will be added later.
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update

    # In the future, we'd check ctx.triggered_id == 'save-event-button'
    # and then read form values and save the data.

    return False

if __name__ == '__main__':
    app.run(debug=True)
