# LLM-Planner Project Overview

## Project Purpose
Jules' Calendar is an interactive calendar application built with Dash and Python that provides intelligent schedule management with LLM integration. The application allows users to manage events with drag-and-drop functionality, switching between month and week views, and features natural language event creation through LLM assistance.

## Key Features
- Month and week view switching
- Drag & drop event manipulation (move and resize)
- Undo/Redo functionality with keyboard shortcuts (Ctrl/Cmd + Z/Y)
- LLM-powered event creation from natural language
- Available time slot detection between users
- Commitment levels (Primary, Secondary, Observer, Tentative)
- Japanese language support

## Tech Stack
- **Frontend**: Dash (Plotly Dash), Dash Bootstrap Components, Vanilla JavaScript
- **Backend**: Python 3.8+
- **Data Storage**: In-memory (no database)
- **UI Framework**: Bootstrap-based responsive design
- **Development Tools**: Git for version control

## Main Entrypoint
- `app.py` - Main application file containing the Dash server and all functionality
- Application runs on `http://127.0.0.1:8050/` by default

## Dependencies
- dash
- dash-bootstrap-components  
- pandas
- pytz
- gunicorn (for production)