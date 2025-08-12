# Codebase Structure

## Directory Layout
```
LLM-Planner/
├── app.py                 # Main application file
├── README.md             # Documentation
├── requirements.txt      # Python dependencies
├── .mcp.json            # MCP configuration
├── static/
│   ├── calendar.js      # JavaScript for calendar interactions
│   └── style.css        # Custom CSS styles
└── __pycache__/         # Python cache directory
```

## Key Files

### app.py (Main Application)
Contains all Python logic including:
- **Constants**: START_H, END_H, GRID_CELL_MIN, PX_PER_MIN for calendar configuration
- **Data structures**: events_init, users_init, groups_init for initial data
- **Calendar functions**: month_range, week_range_for_anchor, generate_month_view, generate_week_bars
- **LLM functions**: dummy_llm_api for event parsing, find_available_slots for time conflict detection
- **UI components**: Modal creation functions for event editing
- **Callbacks**: Dash callbacks for user interactions

### static/calendar.js
JavaScript functionality for:
- Drag and drop event manipulation
- Event resizing
- Keyboard shortcuts (Esc, Ctrl+Z/Y)
- Ghost elements during drag operations
- Tooltip display during interactions

### static/style.css  
Custom styling for:
- Drag states (.event-bar.dragging)
- Resize handles (.resize-handle)
- Tooltips (.drag-tooltip)
- Ghost elements (.ghost-bar)

## Code Organization Patterns
- Functions are organized by purpose (calendar generation, UI creation, data manipulation)
- Event handling through Dash callbacks with clear input/output specifications
- Japanese language support throughout UI and LLM processing
- Bootstrap grid system for responsive layouts