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
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                assets_folder='static',
                suppress_callback_exceptions=True)

START_H = 8
END_H = 20
TOTAL_MIN = (END_H - START_H) * 60
PX_PER_MIN = 1
GRID_CELL_MIN = 15
HIST_MAX = 50  # Undo履歴の最大数

# 優先度の色設定 (Atlassianデザインシステム準拠)
PRIORITY_COLORS = {
    "最高":   {"bg": "#DE350B", "text": "white"},  # Red 600
    "高":     {"bg": "#FF8B00", "text": "white"},  # Orange 600  
    "中":     {"bg": "#FFAB00", "text": "black"},  # Yellow 600
    "低":     {"bg": "#6B778C", "text": "white"},  # Neutral 600
}

# スケジュールラベルの色設定 (Atlassianデザインシステム準拠)
SCHEDULE_LABELS = {
    "空き時間": {"bg": "#F4F5F7", "text": "#172B4D"},  # Neutral 100 / Dark Blue 900
    "仮予定":   {"bg": "#FFFAE6", "text": "#172B4D"},  # Yellow 100
    "予定あり": {"bg": "#E6FCFF", "text": "#172B4D"},  # Blue 100
    "外出中":   {"bg": "#E3FCEF", "text": "#172B4D"},  # Green 100
    "会議":     {"bg": "#DEEBFF", "text": "#172B4D"},  # Blue 200
    "研修":     {"bg": "#EAE6FF", "text": "#172B4D"},  # Purple 100
    "出張":     {"bg": "#FFEBE6", "text": "#172B4D"},  # Red 100
    "休み":     {"bg": "#E3FCEF", "text": "#172B4D"},  # Green 100
}

# --- 初期イベント：空（サンプル削除） ---
events_init = []  # ← 空にしました

# ユーザー管理用の初期データ
users_init = [
    {"id": "user_a", "name": "ユーザーA", "email": "usera@example.com"},
    {"id": "user_b", "name": "ユーザーB", "email": "userb@example.com"}
]

# グループ管理用の初期データ
groups_init = [
    {"id": "group_1", "name": "開発チーム", "user_ids": ["user_a", "user_b"]},
    {"id": "group_2", "name": "マーケティング", "user_ids": ["user_b"]}
]

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
    header_style = {
        "backgroundColor": "#F4F5F7",
        "color": "#172B4D", 
        "fontWeight": "600",
        "fontSize": "14px",
        "padding": "12px",
        "borderBottom": "2px solid #DFE1E6"
    }
    header = [html.Thead(html.Tr([html.Th(d, className="text-center", style=header_style) for d in
                                  ["日", "月", "火", "水", "木", "金", "土"]]))]
    weeks, curr = [], []
    today_d = datetime.now(TZ).date()

    for day in date_range:
        d_date = day.date()
        badges = []
        for ev in events_data:
            s = parse_iso(ev['start']).date()
            e = parse_iso(ev['end']).date()
            if s <= d_date <= e:
                priority = ev.get('priority', '中')
                schedule_label = ev.get('schedule_label', '予定あり')
                priority_color = PRIORITY_COLORS.get(priority, PRIORITY_COLORS['中'])
                badge_style = {
                    "backgroundColor": priority_color["bg"],
                    "color": priority_color["text"],
                    "fontSize": "11px",
                    "fontWeight": "500",
                    "borderRadius": "6px",
                    "border": "none"
                }
                badges.append(html.Span(ev['title'], className="d-block mb-1 text-truncate badge", style=badge_style))

        cell_cls = "p-3"
        cell_style = {
            "height": "130px", 
            "verticalAlign": "top",
            "backgroundColor": "#FAFBFC" if day.weekday() in [5, 6] else "#ffffff",
            "border": "1px solid #DFE1E6",
            "borderRadius": "0"  # テーブルセルなので角丸なし
        }
        if day.month != month: 
            cell_style["backgroundColor"] = "#F4F5F7"
            cell_style["color"] = "#6B778C"
        if d_date == today_d:  
            cell_style["border"] = "2px solid #0052CC"
            cell_style["backgroundColor"] = "#E6FCFF"

        curr.append(
            html.Td(
                html.Div(
                    [html.Div(f"{day.day}", className="fw-bold"),
                     html.Div(badges, className="mt-1")],
                    id={'type': 'date-cell', 'date': day.strftime('%Y-%m-%d')},
                    className="h-100", style={"cursor": "pointer"}
                ),
                className=cell_cls, style=cell_style
            )
        )
        if len(curr) == 7: weeks.append(html.Tr(curr)); curr = []
    body = [html.Tbody(weeks)]
    table_style = {
        "borderRadius": "8px",
        "overflow": "hidden",
        "boxShadow": "0 1px 3px rgba(9, 30, 66, 0.12), 0 1px 2px rgba(9, 30, 66, 0.24)",
        "border": "1px solid #DFE1E6"
    }
    return html.Div(
        dbc.Table(header + body, bordered=False, hover=False, className="table-fixed mb-0"),
        style=table_style
    )

def week_range_for_anchor(anchor: datetime):
    days_back = (anchor.weekday() + 1) % 7  # to Sun
    start = (anchor - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59)
    return start, end

def format_japanese_month_year(year, month):
    """日本語の年月フォーマット"""
    month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', 
                   '7月', '8月', '9月', '10月', '11月', '12月']
    return f"{year}年{month_names[month]}"

def format_japanese_date(d):
    """日本語の曜日付き日付フォーマット"""
    weekdays = ['日', '月', '火', '水', '木', '金', '土']
    return f"{weekdays[d.weekday()]}{d.strftime('%m/%d')}"

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
         dbc.Col(dbc.Row([dbc.Col(html.Div(format_japanese_date(d),
                                           id={'type':'week-header','day':d.strftime('%Y-%m-%d')},
                                           className="text-center fw-bold day-col-header" + (" text-secondary" if d.weekday() in [5, 6] else ""), 
                                           style={"cursor":"pointer"}))
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
                                 'priority': ev.get('priority','中'),
                                 'schedule_label': ev.get('schedule_label','予定あり'),
                                 's': vs, 'e': ve})

        items, lane_count = assign_lanes(proj)

        bg = {"backgroundImage":"repeating-linear-gradient(to bottom, #FAFBFC 0px, #FAFBFC 59px, #DFE1E6 60px)",
              "backgroundSize":"100% 60px"}

        bars = []
        for it in items:
            mins = (it['s'].hour - START_H)*60 + it['s'].minute
            dur  = int((it['e'] - it['s']).total_seconds()//60)
            top_px, height_px = mins*PX_PER_MIN, max(dur*PX_PER_MIN, 6)
            lane_w = 100 / lane_count
            left_pct = it['lane'] * lane_w
            width_calc = f"calc({lane_w:.6f}% - 6px)"
            priority_col = PRIORITY_COLORS.get(it['priority'], PRIORITY_COLORS['中'])
            schedule_col = SCHEDULE_LABELS.get(it['schedule_label'], SCHEDULE_LABELS['予定あり'])

            bars.append(
                html.Div(
                    html.Div(
                        [
                            html.Div(it['title'], className="text-truncate", style={"fontSize":"12px","fontWeight":"600"}),
                            html.Div([
                                html.Span(it['schedule_label'], className="badge me-1",
                                          style={"background":schedule_col["bg"],"color":schedule_col["text"],"fontSize":"9px",
                                                 "padding":"1px 4px","borderRadius":"4px"}),
                                html.Span(f"優先度:{it['priority']}", className="badge",
                                          style={"background":priority_col["bg"],"color":priority_col["text"],"fontSize":"9px",
                                                 "padding":"1px 4px","borderRadius":"4px"}),
                            ], style={"marginTop":"2px"}),
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
                               "background":schedule_col["bg"],"color":schedule_col["text"],"borderRadius":"8px",
                               "padding":"6px 8px 12px 8px","boxShadow":"0 2px 4px rgba(9, 30, 66, 0.08)",
                               "overflow":"hidden","cursor":"grab","userSelect":"none",
                               "borderLeft":f"4px solid {priority_col['bg']}", "border":"1px solid rgba(9, 30, 66, 0.04)"},
                        title=f"{it['s'].strftime('%H:%M')}–{it['e'].strftime('%H:%M')} {it['title']} ({it['schedule_label']}, 優先度:{it['priority']})"
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
                       "borderRadius":"8px","backgroundColor":"#f8f9fa" if d.weekday() in [5, 6] else "#ffffff",
                       "boxShadow":"0 1px 1px rgba(9, 30, 66, 0.04)"}
            )
        )

    grid = dbc.Row([dbc.Col(time_axis, width=1, style={"position":"relative"}),
                    dbc.Col(html.Div(day_columns, style={"display":"flex"}), width=11)])

    return html.Div([header, grid])

# --- LLM with commitment (簡易) ---
def find_available_slots(users, events_data, date_start, date_end, duration_minutes=60):
    """指定されたユーザー間の空き時間を検索"""
    available_slots = []
    
    # 各日をチェック
    current_date = date_start.replace(hour=START_H, minute=0, second=0, microsecond=0)
    end_date = date_end.replace(hour=END_H, minute=0, second=0, microsecond=0)
    
    while current_date.date() <= end_date.date():
        day_start = current_date.replace(hour=START_H, minute=0)
        day_end = current_date.replace(hour=END_H, minute=0)
        
        # その日のユーザーの予定を取得
        user_events = []
        for event in events_data:
            event_attendees = event.get('attendees', [])
            if any(user in event_attendees for user in users):
                event_start = parse_iso(event['start'])
                event_end = parse_iso(event['end'])
                if event_start.date() == current_date.date() or event_end.date() == current_date.date():
                    # その日の範囲内でクリップ
                    clipped_start = max(event_start, day_start)
                    clipped_end = min(event_end, day_end)
                    if clipped_start < clipped_end:
                        user_events.append((clipped_start, clipped_end))
        
        # 予定を時間順にソート
        user_events.sort(key=lambda x: x[0])
        
        # 空き時間を検索
        current_time = day_start
        for event_start, event_end in user_events:
            # 前の予定との間に十分な空きがあるかチェック
            if (event_start - current_time).total_seconds() >= duration_minutes * 60:
                available_slots.append({
                    'start': current_time,
                    'end': event_start,
                    'duration': int((event_start - current_time).total_seconds() // 60)
                })
            current_time = max(current_time, event_end)
        
        # 最後の予定から1日の終わりまでの空き時間
        if (day_end - current_time).total_seconds() >= duration_minutes * 60:
            available_slots.append({
                'start': current_time,
                'end': day_end,
                'duration': int((day_end - current_time).total_seconds() // 60)
            })
        
        current_date += timedelta(days=1)
    
    return available_slots

def dummy_llm_api(text):
    text_l = text.lower()
    now = datetime.now(TZ)
    title = "New Event"
    start_dt = now.replace(second=0, microsecond=0)
    duration = timedelta(hours=1)
    q = re.findall(r"['\"](.*?)['\"]", text_l)
    if q: title = q[0].strip().capitalize()
    if "tomorrow" in text_l or "明日" in text_l: start_dt = now + timedelta(days=1)
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_l)
    if m:
        h = int(m.group(1)); mi = int(m.group(2) or 0); ap = m.group(3)
        if ap == 'pm' and h < 12: h += 12
        if ap == 'am' and h == 12: h = 0
        start_dt = start_dt.replace(hour=h, minute=mi)
    # 英語と日本語の時間指定パターン
    dm = re.search(r'for\s+(\d+)\s*(hour|minute)s?', text_l)  # 英語
    if not dm:
        dm = re.search(r'(\d+)\s*(時間|分間?)', text_l)  # 日本語
    if dm:
        n = int(dm.group(1)); unit = dm.group(2)
        duration = timedelta(hours=n) if unit in ['hour', '時間'] else timedelta(minutes=n)
    priority = "中"
    if "最高" in text_l or "緊急" in text_l: priority = "最高"
    elif "高" in text_l and "最高" not in text_l: priority = "高"
    elif "低" in text_l: priority = "低"
    
    schedule_label = "予定あり"
    if "会議" in text_l: schedule_label = "会議"
    elif "研修" in text_l: schedule_label = "研修"
    elif "出張" in text_l: schedule_label = "出張"
    elif "休み" in text_l or "休暇" in text_l: schedule_label = "休み"
    elif "外出" in text_l: schedule_label = "外出中"
    elif "仮" in text_l or "未定" in text_l: schedule_label = "仮予定"
    start_dt = round_to_grid(start_dt, up=True); end_dt = round_to_grid(start_dt+duration, up=True)
    return {"title": title, "start": start_dt.strftime('%Y-%m-%dT%H:%M'),
            "end": end_dt.strftime('%Y-%m-%dT%H:%M'), "priority": priority, "schedule_label": schedule_label}

# --- Modal ---
def create_event_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("イベントの作成・編集")),
            dbc.ModalBody(
                [
                    dbc.Alert(id="modal-error", color="danger", is_open=False, className="mb-3"),
                    dbc.Form([
                        dbc.Label("タイトル", style={"fontWeight": "600", "color": "#172B4D", "marginBottom": "8px"}),
                        dbc.Input(type="text", id="event-title", placeholder="イベントタイトルを入力", 
                                 style={"borderRadius": "6px", "border": "2px solid #DFE1E6"}),
                        dbc.Row([
                            dbc.Col([dbc.Label("開始時刻", className="mt-3"),
                                     dbc.Input(type="datetime-local", id="event-start-date")], md=6),
                            dbc.Col([dbc.Label("終了時刻", className="mt-3"),
                                     dbc.Input(type="datetime-local", id="event-end-date")], md=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("優先度", className="mt-3"),
                                dcc.Dropdown(id="event-priority",
                                           options=[{"label":"最高","value":"最高"},{"label":"高","value":"高"},{"label":"中","value":"中"},{"label":"低","value":"低"}],
                                           value="中", clearable=False)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("スケジュールラベル", className="mt-3"),
                                dcc.Dropdown(id="event-schedule-label",
                                           options=[{"label":k,"value":k} for k in SCHEDULE_LABELS.keys()],
                                           value="予定あり", clearable=False)
                            ], md=4),
                            dbc.Col([
                                dbc.Label("公開設定", className="mt-3"),
                                dcc.Dropdown(id="event-visibility",
                                           options=[{"label":"公開","value":"public"},{"label":"非公開","value":"private"}],
                                           value="public", clearable=False)
                            ], md=4),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("場所", className="mt-3"),
                                dbc.Input(id="event-location", type="text", placeholder="場所を入力")
                            ], md=6),
                            dbc.Col([
                                dbc.Label("参加者", className="mt-3"),
                                dcc.Dropdown(id="event-attendees", multi=True, placeholder="参加者を選択")
                            ], md=6),
                        ]),
                        dbc.Label("ノート", className="mt-3"),
                        dbc.Textarea(id="event-notes", placeholder="ノートを入力", style={"height": "80px"}),
                        dbc.Row([
                            dbc.Col([
                                dbc.Checklist(
                                    id="allow-double-booking",
                                    options=[{"label": "ダブルブッキングを許可", "value": "allow"}],
                                    value=[]
                                )
                            ], className="mt-3")
                        ]),
                    ])
                ]
            ),
            dbc.ModalFooter([
                dbc.Button("削除", id="delete-event-button", color="danger", outline=True, disabled=True, className="me-auto"),
                dbc.Button("キャンセル", id="cancel-event-button", color="secondary"),
                dbc.Button("保存", id="save-event-button", color="primary"),
            ]),
        ], id="event-modal", is_open=False, size="lg", 
        style={"boxShadow": "0 8px 16px rgba(9, 30, 66, 0.25)", "border": "none"}
    )

def create_date_picker_modal():
    current_year = datetime.now(TZ).year
    years = [{"label": str(y), "value": y} for y in range(current_year - 5, current_year + 6)]
    months = [{"label": f"{i}月", "value": i} for i in range(1, 13)]
    
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("年月選択")),
            dbc.ModalBody(
                [
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("年", className="mb-2"),
                            dcc.Dropdown(id="year-select", options=years, value=current_year, clearable=False)
                        ], md=6),
                        dbc.Col([
                            dbc.Label("月", className="mb-2"), 
                            dcc.Dropdown(id="month-select", options=months, value=datetime.now(TZ).month, clearable=False)
                        ], md=6),
                    ])
                ]
            ),
            dbc.ModalFooter([
                dbc.Button("キャンセル", id="cancel-date-button", color="secondary"),
                dbc.Button("移動", id="jump-date-button", color="primary"),
            ]),
        ], id="date-picker-modal", is_open=False
    )

def create_user_management_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("ユーザー管理")),
            dbc.ModalBody(
                [
                    dbc.Tabs([
                        dbc.Tab(label="ユーザー一覧", tab_id="user-list-tab"),
                        dbc.Tab(label="新規追加", tab_id="user-add-tab"),
                        dbc.Tab(label="編集", tab_id="user-edit-tab"),
                    ], id="user-tabs", active_tab="user-list-tab"),
                    html.Div(id="user-tab-content", className="mt-3")
                ]
            ),
            dbc.ModalFooter([
                dbc.Button("閉じる", id="close-user-modal-button", color="secondary"),
            ]),
        ], id="user-management-modal", is_open=False, size="lg"
    )

def create_group_management_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("グループ管理")),
            dbc.ModalBody(
                [
                    dbc.Tabs([
                        dbc.Tab(label="グループ一覧", tab_id="group-list-tab"),
                        dbc.Tab(label="新規追加", tab_id="group-add-tab"),
                        dbc.Tab(label="編集", tab_id="group-edit-tab"),
                    ], id="group-tabs", active_tab="group-list-tab"),
                    html.Div(id="group-tab-content", className="mt-3")
                ]
            ),
            dbc.ModalFooter([
                dbc.Button("閉じる", id="close-group-modal-button", color="secondary"),
            ]),
        ], id="group-management-modal", is_open=False, size="lg"
    )

# --- Layout ---
today_local = datetime.now(TZ)
app.layout = dbc.Container(
    [
        dcc.Store(id='current-date-store', data={'year': today_local.year,
                                                 'month': today_local.month,
                                                 'anchor': today_local.strftime('%Y-%m-%d')}),
        dcc.Store(id='events-store', data=events_init),
        dcc.Store(id='users-store', data=users_init),
        dcc.Store(id='groups-store', data=groups_init),
        dcc.Store(id='current-group', data="all"),  # "all" または group_id
        dcc.Store(id='current-user', data="all"),   # "all" または user_id
        dcc.Store(id='history-store', data=[]),  # Undo stack（各要素が events のスナップショット）
        dcc.Store(id='future-store', data=[]),   # Redo stack
        dcc.Store(id='editing-id', data=""),
        html.Div(id='ui-intent', style={'display':'none'}),
        html.Div(id='edit-open-store', style={'display':'none'}),
        html.Div(id='drag-update-store', style={'display':'none'}),
        dcc.Store(id='editing-user-store', data=None),  # 編集中のユーザー情報
        dcc.Store(id='editing-group-store', data=None), # 編集中のグループ情報



        create_event_modal(),
        create_date_picker_modal(),
        create_user_management_modal(),
        create_group_management_modal(),

        # ヘッダーセクション - タイトル、今日ボタン、現在日付、ビュー切替
        dbc.Row([
            dbc.Col([
                html.H1("Jules' Calendar", 
                       className="mb-0", 
                       style={"color": "#172B4D", "fontWeight": "700", "fontSize": "28px"})
            ], width="auto"),
            dbc.Col([
                dbc.Button("Today", id="today-button", color="primary", size="sm", className="me-3"),
                html.Span(id="current-month-year", className="h4 mb-0 me-3 align-middle", 
                         style={"cursor":"pointer", "color": "#172B4D", "fontWeight": "600"})
            ], width="auto", className="d-flex align-items-center")
        ], justify="between", align="center", className="mb-4 pb-3", 
           style={"borderBottom": "1px solid #DFE1E6"}),

        # ナビゲーション・ビューコントロールセクション - ナビゲーション、表示切替
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("‹", id="prev-month-button", color="primary", outline=True, size="sm"),
                    dbc.Button("›", id="next-month-button", color="primary", outline=True, size="sm"),
                ])
            ], width="auto", className="me-3"),
            dbc.Col([
                dbc.RadioItems(
                    id="view-switch",
                    className="btn-group",
                    inputClassName="btn-check", 
                    labelClassName="btn btn-outline-primary btn-sm",
                    labelCheckedClassName="active",
                    options=[{'label':'月表示','value':'month'},{'label':'週表示','value':'week'}],
                    value='month'
                )
            ], width="auto")
        ], align="center", className="mb-3"),

        # フィルターと管理セクション
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.Label("グループ:", className="me-2", 
                                  style={"fontSize": "14px", "fontWeight": "500", "color": "#6B778C"}),
                        dcc.Dropdown(id="group-filter", value="all", clearable=False, 
                                   style={"minWidth": "120px", "fontSize": "14px"})
                    ], xs=12, sm=6, className="d-flex align-items-center mb-2 mb-sm-0"),
                    dbc.Col([
                        html.Label("ユーザー:", className="me-2",
                                  style={"fontSize": "14px", "fontWeight": "500", "color": "#6B778C"}),
                        dcc.Dropdown(id="user-filter", value="all", clearable=False,
                                   style={"minWidth": "120px", "fontSize": "14px"})
                    ], xs=12, sm=6, className="d-flex align-items-center")
                ])
            ], xs=12, md=True, className="mb-2 mb-md-0"),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("ユーザー管理", id="open-user-modal-button", color="info", 
                              outline=True, size="sm"),
                    dbc.Button("グループ管理", id="open-group-modal-button", color="info", 
                              outline=True, size="sm")
                ])
            ], xs=12, sm="auto", className="d-flex justify-content-center")
        ], align="center", className="mb-3"),

        # アクションバー - Undo/Redo（カレンダーコンテンツの直上）
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("Undo", id="undo-button", color="secondary", outline=True, 
                              disabled=True, size="sm"),
                    dbc.Button("Redo", id="redo-button", color="secondary", outline=True, 
                              disabled=True, size="sm")
                ])
            ], width="auto")
        ], justify="end", className="mb-2"),

        dbc.Row(dbc.Col(html.Div(id="calendar-output"), width=12)),

        dbc.Row([
            dbc.Col([
                html.Hr(className="my-4", style={"borderColor": "#DFE1E6"}),
                html.H6("AIを使ってイベントをクイック作成", 
                       className="mb-3", 
                       style={"color": "#6B778C", "fontWeight": "600"}),
                dbc.InputGroup([
                    dbc.Input(id="llm-input", 
                             placeholder="例: '\"デザインミーティング\" 明日の午後3時から45分間'",
                             style={"borderRadius": "6px 0 0 6px", "border": "2px solid #DFE1E6"}),
                    dbc.Button("Create", id="llm-submit", color="primary", 
                              style={"borderRadius": "0 6px 6px 0"})
                ], className="mb-2"),
                html.Small(id="llm-output", className="text-muted d-block", 
                          style={"fontSize": "12px", "color": "#6B778C"})
            ], width=12)
        ], className="mt-4 pt-3", style={"borderTop": "1px solid #DFE1E6"}),

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
        # 月表示の場合：月単位で移動
        if tid == 'prev-month-button': month -= 1
        elif tid == 'next-month-button': month += 1
        if month == 0: month, year = 12, year-1
        elif month == 13: month, year = 1, year+1
        new_anchor = datetime(year, month, 1, tzinfo=TZ)
        return {'year': year, 'month': month, 'anchor': new_anchor.strftime('%Y-%m-%d')}
    elif view_mode == 'week':
        # 週表示の場合：週単位で移動
        delta = -7 if tid == 'prev-month-button' else (7 if tid == 'next-month-button' else 0)
        new_anchor = anchor + timedelta(days=delta)
        return {'year': new_anchor.year, 'month': new_anchor.month, 'anchor': new_anchor.strftime('%Y-%m-%d')}
    
    raise dash.exceptions.PreventUpdate

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
        label = format_japanese_month_year(year, month)
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
    
    # ナビゲーションボタンによる自動的な切り替えを防ぐため、
    # 実際のユーザークリックかどうかを判定する
    # この関数は一時的に無効化して問題を調査
    # デバッグ用ログを削除
    
    # 一時的に週表示への自動切り替えを無効化
    raise dash.exceptions.PreventUpdate
    
    # 元のコード（コメントアウト）:
    # date_str = ctx.triggered_id['date']
    # d = datetime.strptime(date_str, '%Y-%m-%d')
    # return {'year': d.year, 'month': d.month, 'anchor': date_str}, 'week'

# view-switchによる直接切り替え
@app.callback(
    Output('current-date-store', 'data', allow_duplicate=True),
    Input('view-switch', 'value'),
    State('current-date-store', 'data'),
    prevent_initial_call=True
)
def handle_view_switch(view_mode, date_data):
    if not view_mode:
        raise dash.exceptions.PreventUpdate
    
    # 現在のアンカー日付を取得
    current_anchor = datetime.strptime(date_data.get('anchor'), '%Y-%m-%d').replace(tzinfo=TZ)
    
    if view_mode == 'week':
        # 月表示から週表示に切り替える際は、現在のアンカー日付を維持
        return {'year': current_anchor.year, 'month': current_anchor.month, 'anchor': current_anchor.strftime('%Y-%m-%d')}
    elif view_mode == 'month':
        # 週表示から月表示に切り替える際は、アンカー日付の月の1日を使用
        new_anchor = current_anchor.replace(day=1)
        return {'year': new_anchor.year, 'month': new_anchor.month, 'anchor': new_anchor.strftime('%Y-%m-%d')}
    
    raise dash.exceptions.PreventUpdate

# Esc / ヘッダ or Ctrl+Z/Y → UI Intent受け
@app.callback(
    Output('view-switch','value', allow_duplicate=True),
    Output('ui-intent','children', allow_duplicate=True),
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
    Output('event-priority','value', allow_duplicate=True),
    Output('event-schedule-label','value', allow_duplicate=True),
    Output('event-visibility','value', allow_duplicate=True),
    Output('event-location','value', allow_duplicate=True),
    Output('event-attendees','value', allow_duplicate=True),
    Output('event-notes','value', allow_duplicate=True),
    Output('allow-double-booking','value', allow_duplicate=True),
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
    return "", True, True, False, "", "", s.strftime('%Y-%m-%dT%H:%M'), e.strftime('%Y-%m-%dT%H:%M'), "中", "予定あり", "public", "", [], "", []

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
    Output('event-priority','value', allow_duplicate=True),
    Output('event-schedule-label','value', allow_duplicate=True),
    Output('event-visibility','value', allow_duplicate=True),
    Output('event-location','value', allow_duplicate=True),
    Output('event-attendees','value', allow_duplicate=True),
    Output('event-notes','value', allow_duplicate=True),
    Output('allow-double-booking','value', allow_duplicate=True),
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
            target.get('priority','中'),
            target.get('schedule_label','予定あり'),
            target.get('visibility','public'),
            target.get('location',''),
            target.get('attendees',[]),
            target.get('notes',''),
            ["allow"] if target.get('allow_double_booking', False) else [])

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
    State('event-priority','value'),
    State('event-schedule-label','value'),
    State('event-visibility','value'),
    State('event-location','value'),
    State('event-attendees','value'),
    State('event-notes','value'),
    State('allow-double-booking','value'),
    State('events-store','data'),
    State('history-store','data'),
    State('editing-id','data'),
    prevent_initial_call=True
)
def close_save_delete(cancel_c, save_c, delete_c, title, start_val, end_val, priority, schedule_label, visibility, location, attendees, notes, allow_double_booking, ev_data, hist, editing_id):
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
        
        # ダブルブッキング検証（許可されていない場合）
        if not ("allow" in (allow_double_booking or [])):
            all_attendees = (attendees or []) + (['user_a'] if not editing_id else [])
            conflicts = check_double_booking(s, e, all_attendees, ev_data, editing_id)
            if conflicts:
                conflict_msgs = []
                for conflict in conflicts:
                    event_title = conflict['event']['title']
                    common_users = conflict['common_attendees']
                    conflict_msgs.append(f"「{event_title}」と参加者が重複: {', '.join(common_users)}")
                return True, True, f"ダブルブッキングが検出されました:\n" + "\n".join(conflict_msgs), dash.no_update, dash.no_update, dash.no_update, editing_id
        
        # 履歴に現状態をPush、Redoはクリア
        new_hist = push_history(hist, copy.deepcopy(ev_data))
        new_fut = []

        new_list = copy.deepcopy(ev_data)
        if editing_id:
            for i, ev in enumerate(new_list):
                if ev['id'] == editing_id:
                    new_list[i] = {**ev, 'title': (title or "新しいイベント").strip(),
                                   'start': s.isoformat(), 'end': e.isoformat(),
                                   'priority': priority or "中",
                                   'schedule_label': schedule_label or "予定あり",
                                   'visibility': visibility or "public",
                                   'location': location or "",
                                   'attendees': attendees or [],
                                   'notes': notes or "",
                                   'allow_double_booking': "allow" in (allow_double_booking or [])}
                    break
        else:
            new_list.append({'id': str(uuid.uuid4()),
                             'title': (title or "新しいイベント").strip(),
                             'start': s.isoformat(), 'end': e.isoformat(),
                             'created_by': 'user_a',  # 登録者
                             'priority': priority or "中",
                             'schedule_label': schedule_label or "予定あり",
                             'visibility': visibility or "public",
                             'location': location or "",
                             'attendees': (attendees or []) + ['user_a'],  # 登録者も参加者に含める
                             'notes': notes or "",
                             'allow_double_booking': "allow" in (allow_double_booking or [])})
        return False, False, "", new_list, new_hist, new_fut, ""

    # Cancel
    return False, False, "", dash.no_update, dash.no_update, dash.no_update, editing_id

# ダブルブッキング検証関数
def check_double_booking(new_start, new_end, new_attendees, existing_events, exclude_id=None):
    """ダブルブッキングをチェックする関数"""
    conflicts = []
    for event in existing_events:
        if exclude_id and event['id'] == exclude_id:
            continue
        
        event_start = parse_iso(event['start'])
        event_end = parse_iso(event['end'])
        
        # 時間の重複チェック
        if not (new_end <= event_start or new_start >= event_end):
            # 参加者の重複チェック
            event_attendees = event.get('attendees', [])
            common_attendees = set(new_attendees) & set(event_attendees)
            if common_attendees:
                conflicts.append({
                    'event': event,
                    'common_attendees': list(common_attendees)
                })
    
    return conflicts

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
    Output('event-priority','value', allow_duplicate=True),
    Output('event-schedule-label','value', allow_duplicate=True),
    Output('event-visibility','value', allow_duplicate=True),
    Output('event-location','value', allow_duplicate=True),
    Output('event-attendees','value', allow_duplicate=True),
    Output('event-notes','value', allow_duplicate=True),
    Output('allow-double-booking','value', allow_duplicate=True),
    Output('llm-output','children'),
    Input('llm-submit','n_clicks'),
    State('llm-input','value'),
    prevent_initial_call=True
)
def llm_preset_modal(n_clicks, text):
    if not text: raise dash.exceptions.PreventUpdate
    parsed = dummy_llm_api(text)
    
    # 空き時間検索の場合
    if parsed.get('type') == 'available_slots':
        # 仮のイベントデータを取得（実際のコールバックでは events_data を State として取得）
        # ここでは簡略化してメッセージのみ返す
        msg = f"空き時間検索: {parsed['message']}\n期間: {parsed['start_date']} ～ {parsed['end_date']}\n対象: {', '.join([f'ユーザー{u[-1].upper()}' for u in parsed['users']])}"
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, msg
    
    # 通常のイベント作成
    msg = f"LLM解析結果 → タイトル: {parsed['title']}, 開始: {parsed['start']}, 終了: {parsed['end']}, 優先度: {parsed['priority']}, ラベル: {parsed['schedule_label']}"
    return "", True, True, False, "", parsed['title'], parsed['start'], parsed['end'], parsed['priority'], parsed['schedule_label'], "public", "", [], "", [], msg

# JSドラッグ更新（適用直前に履歴へ積む）
@app.callback(
    Output('events-store','data', allow_duplicate=True),
    Output('history-store','data', allow_duplicate=True),
    Output('future-store','data', allow_duplicate=True),
    Input('drag-update-store','children'),
    State('drag-update-store','children'),
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

# 年月選択モーダル開くコールバック
@app.callback(
    Output('date-picker-modal', 'is_open', allow_duplicate=True),
    Output('year-select', 'value', allow_duplicate=True),
    Output('month-select', 'value', allow_duplicate=True),
    Input('current-month-year', 'n_clicks'),
    State('current-date-store', 'data'),
    prevent_initial_call=True
)
def open_date_picker(n_clicks, date_data):
    if not n_clicks: raise dash.exceptions.PreventUpdate
    return True, date_data.get('year'), date_data.get('month')

# 年月選択・移動・キャンセル
@app.callback(
    Output('date-picker-modal', 'is_open', allow_duplicate=True),
    Output('current-date-store', 'data', allow_duplicate=True),
    Input('cancel-date-button', 'n_clicks'),
    Input('jump-date-button', 'n_clicks'),
    State('year-select', 'value'),
    State('month-select', 'value'),
    prevent_initial_call=True
)
def date_picker_actions(cancel_clicks, jump_clicks, selected_year, selected_month):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    
    if ctx.triggered_id == 'cancel-date-button':
        return False, dash.no_update
    elif ctx.triggered_id == 'jump-date-button':
        new_anchor = datetime(selected_year, selected_month, 1, tzinfo=TZ)
        return False, {'year': selected_year, 'month': selected_month, 'anchor': new_anchor.strftime('%Y-%m-%d')}
    
    raise dash.exceptions.PreventUpdate

# グループフィルタのオプション更新
@app.callback(
    Output('group-filter', 'options'),
    Input('groups-store', 'data')
)
def update_group_filter_options(groups_data):
    options = [{"label": "すべて", "value": "all"}]
    for group in groups_data:
        options.append({"label": group['name'], "value": group['id']})
    return options

# ユーザーフィルターのオプション更新
@app.callback(
    Output('user-filter', 'options'),
    Input('users-store', 'data')
)
def update_user_filter_options(users_data):
    options = [{"label": "すべて", "value": "all"}]
    for user in users_data:
        options.append({"label": user['name'], "value": user['id']})
    return options

# 現在のユーザー状態を管理
@app.callback(
    Output('current-user', 'data'),
    Input('user-filter', 'value'),
    prevent_initial_call=False
)
def update_current_user(selected_user):
    return selected_user or "all"

# 参加者選択のオプション更新
@app.callback(
    Output('event-attendees', 'options'),
    Input('users-store', 'data')
)
def update_attendee_options(users_data):
    return [{"label": user['name'], "value": user['id']} for user in users_data]

# ユーザー管理モーダル開閉
@app.callback(
    Output('user-management-modal', 'is_open'),
    Input('open-user-modal-button', 'n_clicks'),
    Input('close-user-modal-button', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_user_modal(open_clicks, close_clicks):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    return ctx.triggered_id == 'open-user-modal-button'

# グループ管理モーダル開閉
@app.callback(
    Output('group-management-modal', 'is_open'),
    Input('open-group-modal-button', 'n_clicks'),
    Input('close-group-modal-button', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_group_modal(open_clicks, close_clicks):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    return ctx.triggered_id == 'open-group-modal-button'

# ユーザー管理タブコンテンツ
@app.callback(
    Output('user-tab-content', 'children'),
    Input('user-tabs', 'active_tab'),
    Input('users-store', 'data'),
    Input('editing-user-store', 'data'),
    prevent_initial_call=False
)
def update_user_tab_content(active_tab, users_data, editing_user):
    if active_tab == "user-list-tab":
        if not users_data:
            return html.P("ユーザーがありません")
        
        user_rows = []
        for user in users_data:
            user_rows.append(
                html.Tr([
                    html.Td(user['name']),
                    html.Td(user['email']),
                    html.Td([
                        dbc.Button("編集", id={'type': 'edit-user', 'id': user['id']}, 
                                 size="sm", color="primary", className="me-2"),
                        dbc.Button("削除", id={'type': 'delete-user', 'id': user['id']}, 
                                 size="sm", color="danger")
                    ])
                ])
            )
        
        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("名前"), html.Th("メール"), html.Th("操作")
            ])),
            html.Tbody(user_rows)
        ], striped=True, bordered=True, hover=True)
    
    elif active_tab == "user-add-tab":
        # 新規追加タブ - 常に空のフォーム
        return html.Div([
            dbc.Form([
                dbc.Label("名前"),
                dbc.Input(id="user-name-input", type="text", placeholder="ユーザー名を入力"),
                dbc.Label("メール", className="mt-3"),
                dbc.Input(id="user-email-input", type="email", placeholder="メール@example.com"),
                dbc.Button("追加", id="save-user-button", color="primary", className="mt-3")
            ]),
            html.Div(id="user-save-result", className="mt-3")
        ])
    
    elif active_tab == "user-edit-tab":
        # 編集タブ - 編集中のユーザー情報があれば事前入力する
        if editing_user:
            name_value = editing_user.get('name', '')
            email_value = editing_user.get('email', '')
            
            return html.Div([
                dbc.Form([
                    dbc.Label("名前"),
                    dbc.Input(id="user-name-input", type="text", placeholder="ユーザー名を入力", value=name_value),
                    dbc.Label("メール", className="mt-3"),
                    dbc.Input(id="user-email-input", type="email", placeholder="メール@example.com", value=email_value),
                    dbc.Button("更新", id="save-user-button", color="primary", className="mt-3")
                ]),
                html.Div(id="user-save-result", className="mt-3")
            ])
        else:
            return html.P("編集するユーザーを選択してください", className="text-muted text-center p-4")
    
    return html.Div()

# グループ管理タブコンテンツ
@app.callback(
    Output('group-tab-content', 'children'),
    Input('group-tabs', 'active_tab'),
    Input('groups-store', 'data'),
    Input('users-store', 'data'),
    Input('editing-group-store', 'data'),
    prevent_initial_call=False
)
def update_group_tab_content(active_tab, groups_data, users_data, editing_group):
    if active_tab == "group-list-tab":
        if not groups_data:
            return html.P("グループがありません")
        
        group_rows = []
        for group in groups_data:
            user_names = [u['name'] for u in users_data if u['id'] in group['user_ids']]
            group_rows.append(
                html.Tr([
                    html.Td(group['name']),
                    html.Td(", ".join(user_names)),
                    html.Td([
                        dbc.Button("編集", id={'type': 'edit-group', 'id': group['id']}, 
                                 size="sm", color="primary", className="me-2"),
                        dbc.Button("削除", id={'type': 'delete-group', 'id': group['id']}, 
                                 size="sm", color="danger")
                    ])
                ])
            )
        
        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("グループ名"), html.Th("メンバー"), html.Th("操作")
            ])),
            html.Tbody(group_rows)
        ], striped=True, bordered=True, hover=True)
    
    elif active_tab == "group-add-tab":
        # 新規追加タブ - 常に空のフォーム
        user_options = [{"label": u['name'], "value": u['id']} for u in users_data]
        
        return html.Div([
            dbc.Form([
                dbc.Label("グループ名"),
                dbc.Input(id="group-name-input", type="text", placeholder="グループ名を入力"),
                dbc.Label("メンバー", className="mt-3"),
                dcc.Dropdown(id="group-members-input", options=user_options, multi=True,
                           placeholder="メンバーを選択"),
                dbc.Button("追加", id="save-group-button", color="primary", className="mt-3")
            ]),
            html.Div(id="group-save-result", className="mt-3")
        ])
    
    elif active_tab == "group-edit-tab":
        # 編集タブ - 編集中のグループ情報があれば事前入力する
        user_options = [{"label": u['name'], "value": u['id']} for u in users_data]
        
        if editing_group:
            name_value = editing_group.get('name', '')
            members_value = editing_group.get('user_ids', [])
            
            return html.Div([
                dbc.Form([
                    dbc.Label("グループ名"),
                    dbc.Input(id="group-name-input", type="text", placeholder="グループ名を入力", value=name_value),
                    dbc.Label("メンバー", className="mt-3"),
                    dcc.Dropdown(id="group-members-input", options=user_options, multi=True,
                               placeholder="メンバーを選択", value=members_value),
                    dbc.Button("更新", id="save-group-button", color="primary", className="mt-3")
                ]),
                html.Div(id="group-save-result", className="mt-3")
            ])
        else:
            return html.P("編集するグループを選択してください", className="text-muted text-center p-4")
    
    return html.Div()

# ユーザー保存
@app.callback(
    Output('users-store', 'data', allow_duplicate=True),
    Output('user-save-result', 'children', allow_duplicate=True),
    Output('editing-user-store', 'data', allow_duplicate=True),
    Input('save-user-button', 'n_clicks'),
    State('user-name-input', 'value'),
    State('user-email-input', 'value'),
    State('users-store', 'data'),
    State('editing-user-store', 'data'),
    prevent_initial_call=True
)
def save_user(n_clicks, name, email, users_data, editing_user):
    if not n_clicks or not name or not email:
        raise dash.exceptions.PreventUpdate
    
    updated_users = users_data.copy()
    
    if editing_user:  # 編集モード
        for i, user in enumerate(updated_users):
            if user['id'] == editing_user['id']:
                updated_users[i] = {**user, 'name': name, 'email': email}
                break
        message = "ユーザーを更新しました"
    else:  # 新規追加モード
        new_user = {
            'id': f"user_{len(users_data) + 1}",
            'name': name,
            'email': email
        }
        updated_users = users_data + [new_user]
        message = "ユーザーを追加しました"
    
    return updated_users, dbc.Alert(message, color="success", dismissable=True), None

# ユーザー削除
@app.callback(
    Output('users-store', 'data', allow_duplicate=True),
    Input({'type': 'delete-user', 'id': ALL}, 'n_clicks'),
    State('users-store', 'data'),
    prevent_initial_call=True
)
def delete_user(n_clicks, users_data):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        raise dash.exceptions.PreventUpdate
    
    user_id = ctx.triggered_id['id']
    updated_users = [u for u in users_data if u['id'] != user_id]
    return updated_users



# グループ保存
@app.callback(
    Output('groups-store', 'data', allow_duplicate=True),
    Output('group-save-result', 'children', allow_duplicate=True),
    Output('editing-group-store', 'data', allow_duplicate=True),
    Input('save-group-button', 'n_clicks'),
    State('group-name-input', 'value'),
    State('group-members-input', 'value'),
    State('groups-store', 'data'),
    State('editing-group-store', 'data'),
    prevent_initial_call=True
)
def save_group(n_clicks, name, member_ids, groups_data, editing_group):
    if not n_clicks or not name:
        raise dash.exceptions.PreventUpdate
    
    updated_groups = groups_data.copy()
    
    if editing_group:  # 編集モード
        for i, group in enumerate(updated_groups):
            if group['id'] == editing_group['id']:
                updated_groups[i] = {**group, 'name': name, 'user_ids': member_ids or []}
                break
        message = "グループを更新しました"
    else:  # 新規追加モード
        new_group = {
            'id': f"group_{len(groups_data) + 1}",
            'name': name,
            'user_ids': member_ids or []
        }
        updated_groups = groups_data + [new_group]
        message = "グループを追加しました"
    
    return updated_groups, dbc.Alert(message, color="success", dismissable=True), None

# グループ削除
@app.callback(
    Output('groups-store', 'data', allow_duplicate=True),
    Input({'type': 'delete-group', 'id': ALL}, 'n_clicks'),
    State('groups-store', 'data'),
    prevent_initial_call=True
)
def delete_group(n_clicks, groups_data):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        raise dash.exceptions.PreventUpdate
    
    group_id = ctx.triggered_id['id']
    updated_groups = [g for g in groups_data if g['id'] != group_id]
    return updated_groups

# 編集ボタンでタブ切り替え（ユーザー）
# 編集ボタンでタブ切り替え（ユーザー）
@app.callback(
    Output('user-tabs', 'active_tab'),
    Output('editing-user-store', 'data'),
    Input({'type': 'edit-user', 'id': ALL}, 'n_clicks'),
    State('users-store', 'data'),
    prevent_initial_call=True
)
def switch_to_user_edit_tab(n_clicks, users_data):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        raise dash.exceptions.PreventUpdate
    
    user_id = ctx.triggered_id['id']
    user = next((u for u in users_data if u['id'] == user_id), None)
    
    return "user-edit-tab", user

# 編集ボタンでタブ切り替え（グループ）
# 編集ボタンでタブ切り替え（グループ）
@app.callback(
    Output('group-tabs', 'active_tab'),
    Output('editing-group-store', 'data'),
    Input({'type': 'edit-group', 'id': ALL}, 'n_clicks'),
    State('groups-store', 'data'),
    prevent_initial_call=True
)
def switch_to_group_edit_tab(n_clicks, groups_data):
    ctx = dash.callback_context
    if not ctx.triggered or all(c is None for c in n_clicks):
        raise dash.exceptions.PreventUpdate
    
    group_id = ctx.triggered_id['id']
    group = next((g for g in groups_data if g['id'] == group_id), None)
    
    return "group-edit-tab", group

# タブ切り替え時の編集情報リセット（ユーザー）
@app.callback(
    Output('editing-user-store', 'data', allow_duplicate=True),
    Input('user-tabs', 'active_tab'),
    prevent_initial_call=True
)
def reset_user_editing_on_tab_change(active_tab):
    # 一覧タブに切り替わったら編集情報をクリア
    if active_tab == "user-list-tab":
        return None
    raise dash.exceptions.PreventUpdate

# タブ切り替え時の編集情報リセット（グループ）
@app.callback(
    Output('editing-group-store', 'data', allow_duplicate=True),
    Input('group-tabs', 'active_tab'),
    prevent_initial_call=True
)
def reset_group_editing_on_tab_change(active_tab):
    # 一覧タブに切り替わったら編集情報をクリア
    if active_tab == "group-list-tab":
        return None
    raise dash.exceptions.PreventUpdate



if __name__ == '__main__':
    app.run(debug=True)
