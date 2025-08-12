import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL
import pandas as pd
from datetime import datetime, timedelta
import pytz
import uuid
import re
import copy
import json

# --- Config ---
TZ = pytz.timezone('Asia/Tokyo')
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.FLATLY],
                assets_folder='static')

START_H = 8
END_H = 20
TOTAL_MIN = (END_H - START_H) * 60
PX_PER_MIN = 1
GRID_CELL_MIN = 15
HIST_MAX = 50  # Undo履歴の最大数

COMMIT_COLORS = {
    "Primary":   {"bg": "#0052CC", "text": "white"},
    "Secondary": {"bg": "#36B37E", "text": "white"},
    "Observer":  {"bg": "#FFAB00", "text": "black"},
    "Tentative": {"bg": "#7A869A", "text": "white"},
}

# --- 初期イベント：空（サンプル削除） ---
events_init = []  # ← 空にしました

# --- Helpers ---
def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(TZ)

def round_to_grid(dt: datetime, up=False) -> datetime:
    rem = dt.minute % GRID_CELL_MIN
    dt2 = dt + timedelta(minutes=(GRID_CELL_MIN - rem) % GRID_CELL_MIN) if up else dt - timedelta(minutes=rem)
    return dt2.replace(second=0, microsecond=0)

def month_range(year, month):
    first_day = datetime(year, month, 1)
    last_day = first_day + pd.offsets.MonthEnd(1)
    days_back = (first_day.weekday() + 1) % 7     # Sun start
    start_date = first_day - timedelta(days=days_back)
    days_fwd = (5 - last_day.weekday()) % 7       # Sat end
    end_date = last_day + timedelta(days=days_fwd)
    return start_date, end_date

def generate_month_view(year, month, events_data):
    start_date, end_date = month_range(year, month)
    date_range = pd.date_range(start_date, end_date, freq='D')
    header = [html.Thead(html.Tr([html.Th(d, className="text-center") for d in
                                  ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]]))]
    weeks, curr = [], []
    today_d = datetime.now(TZ).date()

    for day in date_range:
        d_date = day.date()
        badges = []
        for ev in events_data:
            s = parse_iso(ev['start']).date()
            e = parse_iso(ev['end']).date()
            if s <= d_date <= e:
                cm = ev.get('commitment', 'Primary')
                color = "primary" if cm == "Primary" else ("success" if cm == "Secondary"
                            else ("warning" if cm == "Observer" else "secondary"))
                badges.append(dbc.Badge(ev['title'], color=color, className="d-block mb-1 text-truncate"))

        cell_cls = "p-2 border"
        if day.month != month: cell_cls += " bg-light text-muted"
        if d_date == today_d:  cell_cls += " border-primary"

        curr.append(
            html.Td(
                html.Div(
                    [html.Div(f"{day.day}", className="fw-bold"),
                     html.Div(badges, className="mt-1")],
                    id={'type': 'date-cell', 'date': day.strftime('%Y-%m-%d')},
                    className="h-100", style={"cursor": "pointer"}
                ),
                className=cell_cls, style={"height": "120px", "vertical-align": "top"}
            )
        )
        if len(curr) == 7: weeks.append(html.Tr(curr)); curr = []
    body = [html.Tbody(weeks)]
    return dbc.Table(header + body, bordered=False, hover=False, className="table-fixed")

def week_range_for_anchor(anchor: datetime):
    days_back = (anchor.weekday() + 1) % 7  # to Sun
    start = (anchor - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59)
    return start, end

def assign_lanes(day_items):
    items = sorted(day_items, key=lambda x: x['s'])
    lanes = []
    for it in items:
        for i, end in enumerate(lanes):
            if it['s'] >= end:
                it['lane'] = i
                lanes[i] = it['e']; break
        else:
            it['lane'] = len(lanes); lanes.append(it['e'])
    return items, max(1, len(lanes))

def generate_week_bars(anchor_dt: datetime, events_data):
    week_start, _ = week_range_for_anchor(anchor_dt)
    days = [week_start + timedelta(days=i) for i in range(7)]

    header = dbc.Row(
        [dbc.Col("", width=1),
         dbc.Col(dbc.Row([dbc.Col(html.Div(d.strftime("%a %m/%d"),
                                           id={'type':'week-header','day':d.strftime('%Y-%m-%d')},
                                           className="text-center fw-bold day-col-header", style={"cursor":"pointer"}))
                          for d in days]), width=11)],
        className="mb-2"
    )

    time_labels = [html.Div(f"{h:02d}:00",
                    style={"position":"absolute","top":f"{(h-START_H)*60*PX_PER_MIN}px",
                           "right":0,"transform":"translateY(-50%)","fontSize":"12px"})
                   for h in range(START_H, END_H+1)]
    time_axis = html.Div(time_labels, style={"position":"relative","height":f"{TOTAL_MIN*PX_PER_MIN}px"})

    # 当日の可視投影→レーン割り当て→バー生成
    day_columns = []
    for idx, d in enumerate(days):
        proj = []
        for ev in events_data:
            s, e = parse_iso(ev['start']), parse_iso(ev['end'])
            if s.date() <= d.date() <= e.date():
                vs = max(s, d.replace(hour=START_H, minute=0, second=0, microsecond=0))
                ve = min(e, d.replace(hour=END_H, minute=0, second=0, microsecond=0))
                if vs < ve:
                    vs = round_to_grid(vs, up=False)
                    ve = round_to_grid(ve, up=True)
                    proj.append({'id': ev['id'], 'title': ev['title'],
                                 'commitment': ev.get('commitment','Primary'), 's': vs, 'e': ve})

        items, lane_count = assign_lanes(proj)

        bg = {"backgroundImage":"repeating-linear-gradient(to bottom, #F4F5F7 0px, #F4F5F7 59px, #DFE1E6 60px)",
              "backgroundSize":"100% 60px"}

        bars = []
        for it in items:
            mins = (it['s'].hour - START_H)*60 + it['s'].minute
            dur  = int((it['e'] - it['s']).total_seconds()//60)
            top_px, height_px = mins*PX_PER_MIN, max(dur*PX_PER_MIN, 6)
            lane_w = 100 / lane_count
            left_pct = it['lane'] * lane_w
            width_calc = f"calc({lane_w:.6f}% - 6px)"
            col = COMMIT_COLORS.get(it['commitment'], COMMIT_COLORS['Primary'])

            bars.append(
                html.Div(
                    html.Div(
                        [
                            html.Div(it['title'], className="text-truncate", style={"fontSize":"12px","fontWeight":"600"}),
                            html.Span(it['commitment'] , className="badge",
                                      style={"background":col["text"],"color":col["bg"],"fontSize":"10px",
                                             "marginTop":"2px","padding":"2px 6px","borderRadius":"8px"}),
                            html.Div("", className="resize-handle")
                        ],
                        className="event-bar",
                        **{
                            "data-id": it['id'],
                            "data-day": d.strftime('%Y-%m-%d'),
                            "data-day-index": str(idx),
                            "data-start": it['s'].isoformat(),
                            "data-end": it['e'].isoformat(),
                        },
                        style={"position":"absolute","left":f"{left_pct:.6f}%","width":width_calc,
                               "top":f"{top_px}px","height":f"{height_px}px",
                               "background":col["bg"],"color":col["text"],"borderRadius":"6px",
                               "padding":"4px 6px 10px 6px","boxShadow":"0 1px 2px rgba(0,0,0,0.1)",
                               "overflow":"hidden","cursor":"grab","userSelect":"none"},
                        title=f"{it['s'].strftime('%H:%M')}–{it['e'].strftime('%H:%M')} {it['title']} ({it['commitment']})"
                    ),
                    style={"position":"absolute","inset":"0"}
                )
            )

        plus_btn = html.Div("＋", id={'type':'date-cell','date':d.strftime('%Y-%m-%d')},
                            style={"position":"absolute","bottom":"6px","right":"6px","cursor":"pointer","opacity":0.4,"zIndex":1})

        day_columns.append(
            html.Div(
                [html.Div(style={"position":"relative","height":f"{TOTAL_MIN*PX_PER_MIN}px", **bg},
                          children=bars+[plus_btn])],
                className="day-col",
                **{"data-day": d.strftime('%Y-%m-%d'), "data-index": str(idx)},
                style={"flex":1,"margin":"0 4px","position":"relative","border":"1px solid #DFE1E6",
                       "borderRadius":"6px","backgroundColor":"white"}
            )
        )

    grid = dbc.Row([dbc.Col(time_axis, width=1, style={"position":"relative"}),
                    dbc.Col(html.Div(day_columns, style={"display":"flex"}), width=11)])

    return html.Div([header, grid])

# --- LLM with commitment (簡易) ---
def dummy_llm_api(text):
    text_l = text.lower()
    now = datetime.now(TZ)
    title = "New Event"
    start_dt = now.replace(second=0, microsecond=0)
    duration = timedelta(hours=1)
    q = re.findall(r"['\"](.*?)['\"]", text_l)
    if q: title = q[0].strip().capitalize()
    if "tomorrow" in text_l: start_dt = now + timedelta(days=1)
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_l)
    if m:
        h = int(m.group(1)); mi = int(m.group(2) or 0); ap = m.group(3)
        if ap == 'pm' and h < 12: h += 12
        if ap == 'am' and h == 12: h = 0
        start_dt = start_dt.replace(hour=h, minute=mi)
    dm = re.search(r'for\s+(\d+)\s*(hour|minute)s?', text_l)
    if dm:
        n = int(dm.group(1)); unit = dm.group(2)
        duration = timedelta(hours=n) if unit=='hour' else timedelta(minutes=n)
    cm = "Primary"
    if "secondary" in text_l: cm = "Secondary"
    elif "observer" in text_l or "listen-only" in text_l: cm = "Observer"
    elif "tentative" in text_l or "maybe" in text_l: cm = "Tentative"
    start_dt = round_to_grid(start_dt, up=True); end_dt = round_to_grid(start_dt+duration, up=True)
    return {"title": title, "start": start_dt.strftime('%Y-%m-%dT%H:%M'),
            "end": end_dt.strftime('%Y-%m-%dT%H:%M'), "commitment": cm}

# --- Modal ---
def create_event_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Create / Edit Event")),
            dbc.ModalBody(
                [
                    dbc.Alert(id="modal-error", color="danger", is_open=False, className="mb-3"),
                    dbc.Form([
                        dbc.Label("Title"),
                        dbc.Input(type="text", id="event-title", placeholder="Enter event title"),
                        dbc.Row([
                            dbc.Col([dbc.Label("Start Time", className="mt-3"),
                                     dbc.Input(type="datetime-local", id="event-start-date")], md=6),
                            dbc.Col([dbc.Label("End Time", className="mt-3"),
                                     dbc.Input(type="datetime-local", id="event-end-date")], md=6),
                        ]),
                        dbc.Label("Commitment", className="mt-3"),
                        dcc.Dropdown(id="event-commitment",
                                     options=[{"label":c,"value":c} for c in ["Primary","Secondary","Observer","Tentative"]],
                                     value="Primary", clearable=False),
                    ])
                ]
            ),
            dbc.ModalFooter([
                dbc.Button("Delete", id="delete-event-button", color="danger", outline=True, disabled=True, className="me-auto"),
                dbc.Button("Cancel", id="cancel-event-button", color="secondary"),
                dbc.Button("Save", id="save-event-button", color="primary"),
            ]),
        ], id="event-modal", is_open=False
    )

# --- Layout ---
today_local = datetime.now(TZ)
app.layout = dbc.Container(
    [
        dcc.Store(id='current-date-store', data={'year': today_local.year,
                                                 'month': today_local.month,
                                                 'anchor': today_local.strftime('%Y-%m-%d')}),
        dcc.Store(id='events-store', data=events_init),
        dcc.Store(id='history-store', data=[]),  # Undo stack（各要素が events のスナップショット）
        dcc.Store(id='future-store', data=[]),   # Redo stack
        dcc.Store(id='editing-id', data=""),
        dcc.Store(id='ui-intent', data=""),
        dcc.Store(id='edit-open-store', data=""),
        html.Div(id='drag-update-store', style={'display':'none'}),

        create_event_modal(),

        dbc.Row(dbc.Col(html.H1("Jules' Calendar", className="text-primary my-4"), width=12), align="center"),

        # Toolbar（Undo/Redoボタンを追加）
        dbc.Row(
            [
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Today", id="today-button", color="light"),
                        dbc.Button("<", id="prev-month-button", color="light"),
                        dbc.Button(">", id="next-month-button", color="light"),
                        dbc.Button("Undo", id="undo-button", color="secondary", outline=True, disabled=True, className="ms-2"),
                        dbc.Button("Redo", id="redo-button", color="secondary", outline=True, disabled=True),
                    ]),
                    html.Span(id="current-month-year", className="mx-3 h4 align-middle", style={"cursor":"pointer"}),
                ], width="auto"),
                dbc.Col(
                    dbc.RadioItems(
                        id="view-switch",
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary",
                        labelCheckedClassName="active",
                        options=[{'label':'Month','value':'month'},{'label':'Week','value':'week'}],
                        value='week'  # ← デフォルトで週ビュー
                    ), width="auto"
                ),
            ], justify="between", className="mb-3"
        ),

        dbc.Row(dbc.Col(html.Div(id="calendar-output"), width=12)),

        dbc.Row(
            dbc.Col([
                html.Hr(className="my-4"),
                dbc.InputGroup([
                    dbc.Input(id="llm-input", placeholder="e.g., '\"Design sync\" tomorrow 3pm for 45 minutes, secondary'"),
                    dbc.Button("Create", id="llm-submit", color="primary"),
                ]),
                html.Small(id="llm-output", className="text-muted"),
            ], width=12), className="mt-auto"
        ),

# JavaScriptの初期化
        html.Script(f"""
        // カレンダー初期化
        if (typeof initializeCalendar === 'function') {{
            initializeCalendar({PX_PER_MIN}, {START_H}, {GRID_CELL_MIN}, {END_H});
        }}
        """)
    ],
    fluid=True, className="d-flex flex-column vh-100 p-4"
)

# --- Callbacks ---

# ナビゲーション
@app.callback(
    Output('current-date-store', 'data', allow_duplicate=True),
    Input('prev-month-button','n_clicks'),
    Input('next-month-button','n_clicks'),
    Input('today-button','n_clicks'),
    State('view-switch','value'),
    State('current-date-store','data'),
    prevent_initial_call=True
)
def update_current_date(prev_c, next_c, today_c, view_mode, data):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    tid = ctx.triggered_id

    year, month = data.get('year'), data.get('month')
    anchor = datetime.strptime(data.get('anchor'),'%Y-%m-%d').replace(tzinfo=TZ)

    if tid == 'today-button':
        now = datetime.now(TZ)
        return {'year': now.year, 'month': now.month, 'anchor': now.strftime('%Y-%m-%d')}

    if view_mode == 'month':
        if tid == 'prev-month-button': month -= 1
        elif tid == 'next-month-button': month += 1
        if month == 0: month, year = 12, year-1
        elif month == 13: month, year = 1, year+1
        new_anchor = datetime(year, month, 1, tzinfo=TZ)
        return {'year': year, 'month': month, 'anchor': new_anchor.strftime('%Y-%m-%d')}
    else:
        delta = -7 if tid == 'prev-month-button' else (7 if tid == 'next-month-button' else 0)
        new_anchor = anchor + timedelta(days=delta)
        return {'year': new_anchor.year, 'month': new_anchor.month, 'anchor': new_anchor.strftime('%Y-%m-%d')}

# 月/週ビュー描画
@app.callback(
    [Output('calendar-output','children'),
     Output('current-month-year','children'),
     Output('undo-button','disabled'),
     Output('redo-button','disabled')],
    [Input('current-date-store','data'),
     Input('view-switch','value'),
     Input('events-store','data'),
     Input('history-store','data'),
     Input('future-store','data')]
)
def update_calendar_view(date_data, view_mode, events_data, hist, fut):
    year, month = date_data.get('year'), date_data.get('month')
    anchor = datetime.strptime(date_data.get('anchor'),'%Y-%m-%d').replace(tzinfo=TZ)
    if view_mode == 'month':
        comp = generate_month_view(year, month, events_data)
        label = datetime(year, month, 1).strftime('%B %Y')
    else:
        comp = generate_week_bars(anchor, events_data)
        s, e = week_range_for_anchor(anchor)
        label = f"{s.strftime('%Y-%m-%d')} – {e.strftime('%Y-%m-%d')}"
    undo_disabled = not hist
    redo_disabled = not fut
    return comp, label, undo_disabled, redo_disabled

# 月ビュー → 週へジャンプ（セルクリック）
@app.callback(
    Output('current-date-store','data', allow_duplicate=True),
    Output('view-switch','value', allow_duplicate=True),
    Input({'type':'date-cell','date': ALL}, 'n_clicks'),
    State('view-switch','value'),
    prevent_initial_call=True
)
def jump_to_week(n_clicks, view_mode):
    ctx = dash.callback_context
    if not ctx.triggered or view_mode != 'month': raise dash.exceptions.PreventUpdate
    date_str = ctx.triggered_id['date']
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return {'year': d.year, 'month': d.month, 'anchor': date_str}, 'week'

# Esc / ヘッダ or Ctrl+Z/Y → UI Intent受け
@app.callback(
    Output('view-switch','value', allow_duplicate=True),
    Output('ui-intent','data', allow_duplicate=True),
    Input('ui-intent','children'),
    State('current-date-store','data'),
    State('view-switch','value'),
    prevent_initial_call=True
)
def handle_ui_intent(intent, date_data, view_mode):
    if not intent: raise dash.exceptions.PreventUpdate
    if intent == 'to-month':
        return 'month', ''
    # undo/redoはここではviewは変えない→第二のコールバックで履歴更新
    if intent in ('undo','redo'):
        return dash.no_update, ''  # 消費して空に戻す
    raise dash.exceptions.PreventUpdate

# ---- Undo/Redo 実装 ----
def push_history(hist_list, snapshot):
    hist_list = hist_list or []
    hist_list = hist_list + [snapshot]
    if len(hist_list) > HIST_MAX:
        hist_list = hist_list[-HIST_MAX:]
    return hist_list

# Undo/Redo ボタン or ショートカット
@app.callback(
    Output('events-store','data', allow_duplicate=True),
    Output('history-store','data', allow_duplicate=True),
    Output('future-store','data', allow_duplicate=True),
    Input('undo-button','n_clicks'),
    Input('redo-button','n_clicks'),
    Input('ui-intent','children'),  # 'undo' / 'redo' が入る
    State('events-store','data'),
    State('history-store','data'),
    State('future-store','data'),
    prevent_initial_call=True
)
def do_undo_redo(undo_clicks, redo_clicks, intent, events, hist, fut):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    tid = ctx.triggered_id
    op = None
    if tid == 'undo-button' or intent == 'undo':
        op = 'undo'
    elif tid == 'redo-button' or intent == 'redo':
        op = 'redo'
    else:
        raise dash.exceptions.PreventUpdate

    hist = hist or []
    fut = fut or []
    events = events or []

    if op == 'undo':
        if not hist: raise dash.exceptions.PreventUpdate
        # 現在をfutureへ、history最後を現在に
        prev = hist[-1]
        new_hist = hist[:-1]
        new_fut = [copy.deepcopy(events)] + fut
        return copy.deepcopy(prev), new_hist, new_fut
    else:  # redo
        if not fut: raise dash.exceptions.PreventUpdate
        next_state = fut[0]
        new_fut = fut[1:]
        new_hist = push_history(hist, copy.deepcopy(events))
        return copy.deepcopy(next_state), new_hist, new_fut

# 週ビューセルクリック → 新規（履歴はまだ積まない：保存時に積む）
@app.callback(
    Output('editing-id','data', allow_duplicate=True),
    Output('delete-event-button','disabled', allow_duplicate=True),
    Output('event-modal','is_open', allow_duplicate=True),
    Output('modal-error','is_open', allow_duplicate=True),
    Output('modal-error','children', allow_duplicate=True),
    Output('event-title','value', allow_duplicate=True),
    Output('event-start-date','value', allow_duplicate=True),
    Output('event-end-date','value', allow_duplicate=True),
    Output('event-commitment','value', allow_duplicate=True),
    Input({'type':'date-cell','date': ALL}, 'n_clicks'),
    State('view-switch','value'),
    prevent_initial_call=True
)
def open_modal_from_week(n_clicks, view_mode):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks): raise dash.exceptions.PreventUpdate
    if view_mode != 'week': raise dash.exceptions.PreventUpdate
    date_str = ctx.triggered_id['date']
    now = datetime.now(TZ)
    s = TZ.localize(datetime.strptime(date_str, '%Y-%m-%d')).replace(hour=now.hour, minute=now.minute, second=0, microsecond=0)
    s = round_to_grid(s, up=True); e = round_to_grid(s + timedelta(hours=1), up=True)
    return "", True, True, False, "", "", s.strftime('%Y-%m-%dT%H:%M'), e.strftime('%Y-%m-%dT%H:%M'), "Primary"

# JS→編集オープン
@app.callback(
    Output('editing-id','data', allow_duplicate=True),
    Output('delete-event-button','disabled', allow_duplicate=True),
    Output('event-modal','is_open', allow_duplicate=True),
    Output('modal-error','is_open', allow_duplicate=True),
    Output('modal-error','children', allow_duplicate=True),
    Output('event-title','value', allow_duplicate=True),
    Output('event-start-date','value', allow_duplicate=True),
    Output('event-end-date','value', allow_duplicate=True),
    Output('event-commitment','value', allow_duplicate=True),
    Input('edit-open-store','children'),
    State('events-store','data'),
    prevent_initial_call=True
)
def open_modal_for_edit(edit_id, ev_data):
    if not edit_id: raise dash.exceptions.PreventUpdate
    target = next((e for e in ev_data if e['id'] == edit_id), None)
    if not target: raise dash.exceptions.PreventUpdate
    return (edit_id, False, True, False, "",
            target.get('title',''),
            parse_iso(target['start']).strftime('%Y-%m-%dT%H:%M'),
            parse_iso(target['end']).strftime('%Y-%m-%dT%H:%M'),
            target.get('commitment','Primary'))

# Save / Cancel / Delete（履歴に積むのは Save / Delete の直前状態）
@app.callback(
    Output('event-modal','is_open', allow_duplicate=True),
    Output('modal-error','is_open', allow_duplicate=True),
    Output('modal-error','children', allow_duplicate=True),
    Output('events-store','data', allow_duplicate=True),
    Output('history-store','data', allow_duplicate=True),
    Output('future-store','data', allow_duplicate=True),
    Output('editing-id','data', allow_duplicate=True),
    Input('cancel-event-button','n_clicks'),
    Input('save-event-button','n_clicks'),
    Input('delete-event-button','n_clicks'),
    State('event-title','value'),
    State('event-start-date','value'),
    State('event-end-date','value'),
    State('event-commitment','value'),
    State('events-store','data'),
    State('history-store','data'),
    State('editing-id','data'),
    prevent_initial_call=True
)
def close_save_delete(cancel_c, save_c, delete_c, title, start_val, end_val, commitment, ev_data, hist, editing_id):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    tid = ctx.triggered_id
    ev_data = ev_data or []
    hist = hist or []

    # Delete
    if tid == 'delete-event-button':
        if not editing_id: return False, False, "", dash.no_update, dash.no_update, dash.no_update, ""
        # 履歴に現状態をPush、Redoはクリア
        new_hist = push_history(hist, copy.deepcopy(ev_data))
        new_fut = []
        new_list = [e for e in ev_data if e['id'] != editing_id]
        return False, False, "", new_list, new_hist, new_fut, ""

    # Save
    if tid == 'save-event-button':
        if not start_val or not end_val:
            return True, True, "Start/End は必須です。", dash.no_update, dash.no_update, dash.no_update, editing_id
        try:
            s = TZ.localize(datetime.strptime(start_val, '%Y-%m-%dT%H:%M'))
            e = TZ.localize(datetime.strptime(end_val,   '%Y-%m-%dT%H:%M'))
        except Exception:
            return True, True, "日付の形式が不正です。", dash.no_update, dash.no_update, dash.no_update, editing_id
        if e < s:
            return True, True, "終了は開始以上である必要があります。", dash.no_update, dash.no_update, dash.no_update, editing_id
        if (e - s) > timedelta(hours=24):
            return True, True, "最長24時間までです。", dash.no_update, dash.no_update, dash.no_update, editing_id
        s = round_to_grid(s, up=False); e = round_to_grid(e, up=True)

        # 履歴に現状態をPush、Redoはクリア
        new_hist = push_history(hist, copy.deepcopy(ev_data))
        new_fut = []

        new_list = copy.deepcopy(ev_data)
        if editing_id:
            for i, ev in enumerate(new_list):
                if ev['id'] == editing_id:
                    new_list[i] = {**ev, 'title': (title or "New Event").strip(),
                                   'start': s.isoformat(), 'end': e.isoformat(),
                                   'commitment': commitment or "Primary"}
                    break
        else:
            new_list.append({'id': str(uuid.uuid4()),
                             'title': (title or "New Event").strip(),
                             'start': s.isoformat(), 'end': e.isoformat(),
                             'user_id': 'user_a', 'commitment': commitment or "Primary"})
        return False, False, "", new_list, new_hist, new_fut, ""

    # Cancel
    return False, False, "", dash.no_update, dash.no_update, dash.no_update, editing_id

# LLM → 新規作成プリセット（履歴は保存時に積む）
@app.callback(
    Output('editing-id','data', allow_duplicate=True),
    Output('delete-event-button','disabled', allow_duplicate=True),
    Output('event-modal','is_open', allow_duplicate=True),
    Output('modal-error','is_open', allow_duplicate=True),
    Output('modal-error','children', allow_duplicate=True),
    Output('event-title','value', allow_duplicate=True),
    Output('event-start-date','value', allow_duplicate=True),
    Output('event-end-date','value', allow_duplicate=True),
    Output('event-commitment','value', allow_duplicate=True),
    Output('llm-output','children'),
    Input('llm-submit','n_clicks'),
    State('llm-input','value'),
    prevent_initial_call=True
)
def llm_preset_modal(n_clicks, text):
    if not text: raise dash.exceptions.PreventUpdate
    parsed = dummy_llm_api(text)
    msg = f"LLM parsed → Title: {parsed['title']}, Start: {parsed['start']}, End: {parsed['end']}, Commitment: {parsed['commitment']}"
    return "", True, True, False, "", parsed['title'], parsed['start'], parsed['end'], parsed['commitment'], msg

# JSドラッグ更新（適用直前に履歴へ積む）
@app.callback(
    Output('events-store','data', allow_duplicate=True),
    Output('history-store','data', allow_duplicate=True),
    Output('future-store','data', allow_duplicate=True),
    Input('drag-update-store','input'),
    State('drag-update-store','textContent'),
    State('events-store','data'),
    State('history-store','data'),
    prevent_initial_call=True
)
def apply_drag_update(_evt, raw, ev_data, hist):
    if not raw: raise dash.exceptions.PreventUpdate
    try:
        payload = json.loads(raw)
    except Exception:
        raise dash.exceptions.PreventUpdate
    eid, start_s, end_s = payload.get("id"), payload.get("start"), payload.get("end")
    if not (eid and start_s and end_s): raise dash.exceptions.PreventUpdate

    s = TZ.localize(datetime.strptime(start_s, '%Y-%m-%dT%H:%M'))
    e = TZ.localize(datetime.strptime(end_s,   '%Y-%m-%dT%H:%M'))
    if e < s: raise dash.exceptions.PreventUpdate
    if (e - s) > timedelta(hours=24): e = s + timedelta(hours=24)
    s = round_to_grid(s, up=False); e = round_to_grid(e, up=True)

    # 履歴に現状態をPush、Redoはクリア
    new_hist = push_history(hist or [], copy.deepcopy(ev_data or []))
    new_fut = []

    new_list = []
    for ev in (ev_data or []):
        if ev['id'] == eid:
            upd = ev.copy(); upd['start'] = s.isoformat(); upd['end'] = e.isoformat()
            new_list.append(upd)
        else:
            new_list.append(ev)
    return new_list, new_hist, new_fut

if __name__ == '__main__':
    app.run(debug=True)
