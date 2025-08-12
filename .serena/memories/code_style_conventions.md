# Code Style and Conventions

## Python Code Style
- **Function naming**: Snake_case (e.g., `parse_iso`, `round_to_grid`, `generate_month_view`)
- **Variable naming**: Snake_case for local variables, UPPER_CASE for constants
- **Constants**: Defined at module level (START_H, END_H, TOTAL_MIN, PX_PER_MIN, etc.)
- **Docstrings**: Minimal, mostly for complex functions like `find_available_slots`
- **Type hints**: Not consistently used throughout the codebase
- **Line length**: No strict enforcement observed

## JavaScript Code Style  
- **Function naming**: camelCase (e.g., `ensureTooltip`, `nearestGridMin`, `pickDayColByPoint`)
- **Variable naming**: camelCase for local variables
- **Constants**: UPPER_CASE (e.g., `GRID`, `TOTAL_PX`)
- **Event handling**: Direct DOM manipulation with vanilla JavaScript
- **Code organization**: Functions grouped by purpose within the main initialization function

## CSS Naming Convention
- **Class names**: Kebab-case (e.g., `.event-bar`, `.drag-tooltip`, `.ghost-bar`)
- **Modifier classes**: Using class combination (e.g., `.event-bar.dragging`)

## Language Considerations
- **Bilingual support**: Japanese and English mixed throughout
- **UI elements**: Primarily in Japanese (月表示, 週表示, etc.)
- **LLM processing**: Supports both Japanese and English natural language input
- **Variable names**: Mixed Japanese and English (e.g., `期間`, `対象` for some variables)

## Data Structure Patterns
- **Events**: Dictionaries with keys: id, title, start, end, priority, schedule_label, attendees
- **Dates**: ISO format strings for storage, datetime objects for processing
- **Time handling**: pytz for timezone awareness, custom rounding to grid intervals