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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# グリッド設定（8:00–20:00、15分粒度）
START_H = 8
END_H = 20
TOTAL_MIN = (END_H - START_H) * 60
PX_PER_MIN = 1
GRID_CELL_MIN = 15

# コミットメント色
COMMIT_COLORS = {
    "Primary":   {"bg": "#0052CC", "text": "white"},
    "Secondary": {"bg": "#36B37E", "text": "white"},
    "Observer":  {"bg": "#FFAB00", "text": "black"},
    "Tentative": {"bg": "#7A869A", "text": "white"},
}

# --- Sample events ---
def dt_aware(y, m, d, H, M): return TZ.localize(datetime(y, m, d, H, M))
events_init = [
    {'id': str(uuid.uuid4()), 'title': 'Team Standup',
     'start': dt_aware(2025, 8, 11, 10, 0).isoformat(),
     'end':   dt_aware(2025, 8, 11, 10, 15).isoformat(),
     'user_id': 'user_a', 'commitment': 'Primary'},
    {'id': str(uuid.uuid4()), 'title': 'Design Review',
     'start': dt_aware(2025, 8, 11, 14, 0).isoformat(),
     'end':   dt_aware(2025, 8, 11, 15, 30).isoformat(),
     'user_id': 'user_a', 'commitment': 'Primary'},
    {'id': str(uuid.uuid4()), 'title': '1-on-1 with Manager',
     'start': dt_aware(2025, 8, 13, 11, 0).isoformat(),
     'end':   dt_aware(2025, 8, 13, 11, 30).isoformat(),
     'user_id': 'user_b', 'commitment': 'Secondary'},
    {'id': str(uuid.uuid4()), 'title': '[User B] Project Kick-off',
     'start': dt_aware(2025, 8, 13, 15, 0).isoformat(),
     'end':   dt_aware(2025, 8, 13, 16, 0).isoformat(),
     'user_id': 'user_b', 'commitment': 'Primary'},
    # 日跨りの例（許可）：金 19:30 → 土 08:30
    {'id': str(uuid.uuid4()), 'title': 'Overnight Maintenance',
     'start': dt_aware(2025, 8, 15, 19, 30).isoformat(),
     'end':   dt_aware(2025, 8, 16, 8, 30).isoformat(),
     'user_id': 'all', 'commitment': 'Observer'},
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
    # 貪欲レーン割当
    items = sorted(day_items, key=lambda x: x['s'])
    lanes = []
    for it in items:
        for i, end in enumerate(lanes):
            if it['s'] >= end:
                it['lane'] = i
                lanes[i] = it['e']
                break
        else:
            it['lane'] = len(lanes)
            lanes.append(it['e'])
    return items, max(1, len(lanes))

def generate_week_bars(anchor_dt: datetime, events_data):
    week_start, _ = week_range_for_anchor(anchor_dt)
    days = [week_start + timedelta(days=i) for i in range(7)]

    header = dbc.Row(
        [dbc.Col("", width=1),
         dbc.Col(dbc.Row([dbc.Col(html.Div(d.strftime("%a %m/%d"),
                                           className="text-center fw-bold day-col-header"))
                          for d in days]), width=11)],
        className="mb-2"
    )

    # 左：時間ラベル
    time_labels = [html.Div(f"{h:02d}:00",
                    style={"position":"absolute","top":f"{(h-START_H)*60*PX_PER_MIN}px",
                           "right":0,"transform":"translateY(-50%)","fontSize":"12px"})
                   for h in range(START_H, END_H+1)]
    time_axis = html.Div(time_labels, style={"position":"relative","height":f"{TOTAL_MIN*PX_PER_MIN}px"})

    day_columns = []
    for idx, d in enumerate(days):
        # 当日の可視投影
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

        # 背景
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

    css = html.Style("""
    .event-bar.dragging { opacity: 0.85; cursor: grabbing; }
    .event-bar .resize-handle { position:absolute; left:0; right:0; bottom:0; height:6px;
                                cursor: ns-resize; background: rgba(255,255,255,0.35); }
    .drag-tooltip { position: fixed; pointer-events:none; background: #172B4D; color:white;
                    padding:4px 8px; border-radius:6px; font-size:12px; z-index:9999; opacity:0.92; }
    """)

    return html.Div([header, grid, css])

# --- LLM（commitment 推定も返す） ---
def dummy_llm_api(text):
    text_l = text.lower()
    now = datetime.now(TZ)
    title = "New Event"
    start_dt = now.replace(second=0, microsecond=0)
    duration = timedelta(hours=1)
    # タイトル（引用）
    q = re.findall(r"['\"](.*?)['\"]", text_l)
    if q: title = q[0].strip().capitalize()
    # today/tomorrow
    if "tomorrow" in text_l: start_dt = now + timedelta(days=1)
    # 時刻
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_l)
    if m:
        h = int(m.group(1)); mi = int(m.group(2) or 0); ap = m.group(3)
        if ap == 'pm' and h < 12: h += 12
        if ap == 'am' and h == 12: h = 0
        start_dt = start_dt.replace(hour=h, minute=mi)
    # duration
    dm = re.search(r'for\s+(\d+)\s*(hour|minute)s?', text_l)
    if dm:
        n = int(dm.group(1)); unit = dm.group(2)
        duration = timedelta(hours=n) if unit=='hour' else timedelta(minutes=n)
    # commitment 推定
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
            dbc.ModalFooter([dbc.Button("Cancel", id="cancel-event-button", color="secondary"),
                             dbc.Button("Save", id="save-event-button", color="primary")]),
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
        html.Div(id='drag-update-store', style={'display':'none'}),  # JS→Python 受け皿（childrenにJSON）

        create_event_modal(),

        dbc.Row(dbc.Col(html.H1("Jules' Calendar", className="text-primary my-4"), width=12), align="center"),

        dbc.Row(
            [
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Today", id="today-button", color="light"),
                        dbc.Button("<", id="prev-month-button", color="light"),
                        dbc.Button(">", id="next-month-button", color="light"),
                    ]),
                    html.Span(id="current-month-year", className="mx-3 h4 align-middle"),
                ], width="auto"),
                dbc.Col(
                    dbc.RadioItems(
                        id="view-switch",
                        className="btn-group",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-primary",
                        labelCheckedClassName="active",
                        options=[{'label':'Month','value':'month'},{'label':'Week','value':'week'}],
                        value='week'
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

        # クライアントJS：ドラッグ＆ツールチップ＆横移動＆store更新
        html.Script(f"""
(function(){{
  const PX_PER_MIN = {PX_PER_MIN};
  const START_H = {START_H};
  const GRID = {GRID_CELL_MIN};
  const TOTAL_PX = {(END_H-START_H)*60*PX_PER_MIN};

  let tooltip;
  function ensureTooltip(){{
    if(!tooltip){{
      tooltip = document.createElement('div');
      tooltip.className = 'drag-tooltip';
      tooltip.style.display = 'none';
      document.body.appendChild(tooltip);
    }}
    return tooltip;
  }}
  function showTip(x,y,text){{
    const t = ensureTooltip();
    t.textContent = text;
    t.style.left = (x+12)+'px';
    t.style.top = (y+12)+'px';
    t.style.display = 'block';
  }}
  function hideTip(){{
    if(tooltip) tooltip.style.display = 'none';
  }}
  function nearestGridMin(mins){ return Math.round(mins/GRID)*GRID; }
  function clamp(v,lo,hi){ return Math.max(lo, Math.min(hi,v)); }
  function pxToMin(px){ return px / PX_PER_MIN; }
  function minToPx(m){ return m * PX_PER_MIN; }

  function toLocalISO(d){{
    const pad=(n)=> String(n).padStart(2,'0');
    return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+"T"+pad(d.getHours())+":"+pad(d.getMinutes());
  }}

  function pickDayByPoint(clientX, clientY){{
    const cols = Array.from(document.querySelectorAll('.day-col'));
    for(const col of cols){{
      const r = col.getBoundingClientRect();
      if(clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom){{
        return {{day: col.dataset.day, index: parseInt(col.dataset.index)}}
      }}
    }}
    return null;
  }}

  function setup(){
    const root = document.getElementById('calendar-output');
    if(!root) return;
    const bars = root.querySelectorAll('.event-bar');
    bars.forEach(bar=>{
      bar.onmousedown = null;
      const handle = bar.querySelector('.resize-handle');
      if(handle) handle.onmousedown = null;

      let dragging=false, resizing=false;
      let startY=0, startX=0, origTop=0, origHeight=0, origDay=bar.dataset.day, origDayIdx=parseInt(bar.dataset.dayIndex);

      // 移動ドラッグ
      bar.onmousedown = (ev)=>{
        if(ev.target.classList.contains('resize-handle')) return;
        ev.preventDefault();
        dragging=true; bar.classList.add('dragging');
        startY=ev.clientY; startX=ev.clientX;
        origTop = parseFloat(getComputedStyle(bar).top);
        document.onmousemove=(mv)=>{
          if(!dragging) return;
          const dy = mv.clientY - startY;
          let newTop = origTop + dy;
          const maxTop = TOTAL_PX - parseFloat(getComputedStyle(bar).height);
          newTop = clamp(newTop, 0, maxTop);
          bar.style.top = newTop + 'px';

          // ツールチップ：現在の候補時間＆日
          const topMin = nearestGridMin(pxToMin(newTop));
          const dayPick = pickDayByPoint(mv.clientX, mv.clientY) || {{day: origDay, index: origDayIdx}};
          const s = new Date(dayPick.day+'T00:00:00'); s.setHours(START_H,0,0,0); s.setMinutes(s.getMinutes()+topMin);
          const durMin = nearestGridMin(pxToMin(parseFloat(getComputedStyle(bar).height)));
          const e = new Date(s.getTime() + durMin*60000);
          showTip(mv.clientX, mv.clientY, dayPick.day+'  '+s.toTimeString().slice(0,5)+'–'+e.toTimeString().slice(0,5));
        };
        document.onmouseup=(up)=>{
          if(!dragging) return;
          dragging=false; bar.classList.remove('dragging');
          document.onmousemove=null; document.onmouseup=null; hideTip();

          const newTopPx = parseFloat(getComputedStyle(bar).top);
          let mins = nearestGridMin(pxToMin(newTopPx));
          const dayPick = pickDayByPoint(up.clientX, up.clientY) || {{day: origDay, index: origDayIdx}};

          const s = new Date(dayPick.day+'T00:00:00'); s.setHours(START_H,0,0,0); s.setMinutes(s.getMinutes()+mins);
          const heightPx = parseFloat(getComputedStyle(bar).height);
          let durMins = nearestGridMin(pxToMin(heightPx)); if(durMins<GRID) durMins=GRID;
          const e = new Date(s.getTime()+durMins*60000);

          // 送信
          const payload = {{id: bar.dataset.id, start: toLocalISO(s), end: toLocalISO(e)}};
          const sink = document.getElementById('drag-update-store');
          if(sink) {{ sink.textContent = JSON.stringify(payload); sink.dispatchEvent(new Event('input')); }}
        };
      };

      // リサイズ（下辺）
      if(handle){
        handle.onmousedown = (ev)=>{
          ev.preventDefault();
          resizing=true; bar.classList.add('dragging');
          startY=ev.clientY; origHeight = parseFloat(getComputedStyle(bar).height);
          document.onmousemove=(mv)=>{
            if(!resizing) return;
            const dy = mv.clientY - startY;
            let newH = origHeight + dy;
            const maxH = TOTAL_PX - parseFloat(getComputedStyle(bar).top);
            newH = clamp(newH, GRID, maxH);
            bar.style.height = newH + 'px';

            // ツールチップ
            const topPx = parseFloat(getComputedStyle(bar).top);
            const topMin = nearestGridMin(pxToMin(topPx));
            const dayPick = pickDayByPoint(mv.clientX, mv.clientY) || {{day: bar.dataset.day, index: parseInt(bar.dataset.dayIndex)}};
            const s = new Date(dayPick.day+'T00:00:00'); s.setHours(START_H,0,0,0); s.setMinutes(s.getMinutes()+topMin);
            const durMin = nearestGridMin(pxToMin(newH));
            const e = new Date(s.getTime()+durMin*60000);
            showTip(mv.clientX, mv.clientY, dayPick.day+'  '+s.toTimeString().slice(0,5)+'–'+e.toTimeString().slice(0,5));
          };
          document.onmouseup=(up)=>{
            if(!resizing) return;
            resizing=false; bar.classList.remove('dragging');
            document.onmousemove=null; document.onmouseup=null; hideTip();

            const topPx = parseFloat(getComputedStyle(bar).top);
            const heightPx = parseFloat(getComputedStyle(bar).height);
            let mins = nearestGridMin(pxToMin(topPx));
            let durMins = nearestGridMin(pxToMin(heightPx)); if(durMins<GRID) durMins=GRID;

            const dayPick = pickDayByPoint(up.clientX, up.clientY) || {{day: bar.dataset.day, index: parseInt(bar.dataset.dayIndex)}};
            const s = new Date(dayPick.day+'T00:00:00'); s.setHours(START_H,0,0,0); s.setMinutes(s.getMinutes()+mins);
            const e = new Date(s.getTime()+durMins*60000);

            const payload = {{id: bar.dataset.id, start: toLocalISO(s), end: toLocalISO(e)}};
            const sink = document.getElementById('drag-update-store');
            if(sink) {{ sink.textContent = JSON.stringify(payload); sink.dispatchEvent(new Event('input')); }}
          };
        };
      }
    });
  }

  // DOM更新のたびにセットアップ
  const obs = new MutationObserver(()=>setup());
  obs.observe(document.documentElement, {{childList:true, subtree:true}});
  setup();
}})();
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
     Output('current-month-year','children')],
    [Input('current-date-store','data'),
     Input('view-switch','value'),
     Input('events-store','data')]
)
def update_calendar_view(date_data, view_mode, events_data):
    year, month = date_data.get('year'), date_data.get('month')
    anchor = datetime.strptime(date_data.get('anchor'),'%Y-%m-%d').replace(tzinfo=TZ)
    if view_mode == 'month':
        comp = generate_month_view(year, month, events_data)
        label = datetime(year, month, 1).strftime('%B %Y')
        return comp, label
    else:
        comp = generate_week_bars(anchor, events_data)
        s, e = week_range_for_anchor(anchor)
        label = f"{s.strftime('%Y-%m-%d')} – {e.strftime('%Y-%m-%d')}"
        return comp, label

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

# 週ビューでの日付セルクリック → モーダル（現在時刻起点）
@app.callback(
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
    return True, False, "", "", s.strftime('%Y-%m-%dT%H:%M'), e.strftime('%Y-%m-%dT%H:%M'), "Primary"

# Save/Cancel（最大24h、日跨り許可）
@app.callback(
    Output('event-modal','is_open', allow_duplicate=True),
    Output('modal-error','is_open', allow_duplicate=True),
    Output('modal-error','children', allow_duplicate=True),
    Output('events-store','data', allow_duplicate=True),
    Input('cancel-event-button','n_clicks'),
    Input('save-event-button','n_clicks'),
    State('event-title','value'),
    State('event-start-date','value'),
    State('event-end-date','value'),
    State('event-commitment','value'),
    State('events-store','data'),
    prevent_initial_call=True
)
def close_or_save_modal(cancel_c, save_c, title, start_val, end_val, commitment, ev_data):
    ctx = dash.callback_context
    if not ctx.triggered: raise dash.exceptions.PreventUpdate
    if ctx.triggered_id == 'save-event-button':
        if not start_val or not end_val:
            return True, True, "Start/End は必須です。", dash.no_update
        try:
            s = TZ.localize(datetime.strptime(start_val, '%Y-%m-%dT%H:%M'))
            e = TZ.localize(datetime.strptime(end_val,   '%Y-%m-%dT%H:%M'))
        except Exception:
            return True, True, "日付の形式が不正です。", dash.no_update
        if e < s:
            return True, True, "終了は開始以上である必要があります。", dash.no_update
        # 最大24時間まで（日跨り許可）
        if (e - s) > timedelta(hours=24):
            return True, True, "最長24時間までです。", dash.no_update
        s = round_to_grid(s, up=False); e = round_to_grid(e, up=True)
        new_event = {'id': str(uuid.uuid4()), 'title': (title or "New Event").strip(),
                     'start': s.isoformat(), 'end': e.isoformat(),
                     'user_id': 'user_a', 'commitment': commitment or "Primary"}
        new_list = copy.deepcopy(ev_data) if isinstance(ev_data, list) else []
        new_list.append(new_event)
        return False, False, "", new_list
    else:
        return False, False, "", dash.no_update

# LLM → モーダル（commitment もプリセット）
@app.callback(
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
    return True, False, "", parsed['title'], parsed['start'], parsed['end'], parsed['commitment'], msg

# JSからのドラッグ更新（JSON文字列を children 経由で受ける）
@app.callback(
    Output('events-store','data', allow_duplicate=True),
    Input('drag-update-store','children'),
    State('events-store','data'),
    prevent_initial_call=True
)
def apply_drag_update(raw, ev_data):
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

    new_list = []
    for ev in ev_data:
        if ev['id'] == eid:
            upd = ev.copy(); upd['start'] = s.isoformat(); upd['end'] = e.isoformat()
            new_list.append(upd)
        else:
            new_list.append(ev)
    return new_list

if __name__ == '__main__':
    app.run(debug=True)
