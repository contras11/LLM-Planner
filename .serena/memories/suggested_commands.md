# Suggested Commands for Development

## System Environment
- **Platform**: Windows
- **Python**: 3.8+
- **Git**: Available for version control

## Essential Development Commands

### Application Execution
```bash
# Run the development server
python app.py
```
The application will be available at `http://127.0.0.1:8050/`

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Optional Development Tools
```bash
# Install development dependencies (mentioned in README)
pip install black pylint pytest
```

### Production Deployment
```bash
# Run with gunicorn for production
gunicorn app:server
```

## Windows-Specific Commands
- **Directory listing**: `dir` (instead of `ls`)
- **Find files**: `where` command or PowerShell `Get-ChildItem`
- **Grep equivalent**: `findstr` or PowerShell `Select-String`
- **Process management**: `tasklist`, `taskkill`

## Git Workflow
```bash
# Standard git operations
git status
git add .
git commit -m "message"
git push origin main
```

## No Specific Testing/Linting Commands
- The project doesn't currently have configured test runners, linters, or formatters in the requirements
- Development tools like black, pylint, pytest are mentioned as optional in README but not required

## File Watching/Hot Reload
- Dash applications automatically reload on file changes during development
- No additional file watching commands needed