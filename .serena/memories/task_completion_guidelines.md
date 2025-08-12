# Task Completion Guidelines

## What to Do When Tasks Are Completed

Since this project doesn't have formal testing, linting, or formatting configurations, the completion workflow is minimal:

### 1. Manual Testing
- Run `python app.py` to start the application
- Test functionality manually in browser at `http://127.0.0.1:8050/`
- Check both month and week views
- Test drag & drop, LLM functionality, undo/redo

### 2. Code Review (Optional)
- If development tools are installed, can run manually:
  ```bash
  # Code formatting (if black is installed)
  black app.py
  
  # Linting (if pylint is installed)  
  pylint app.py
  ```

### 3. No Automated Tests
- The project doesn't have test files or test runner configuration
- All testing is currently manual through the web interface

### 4. Version Control
- Use standard git workflow for committing changes
- No pre-commit hooks or automated checks configured

## Important Notes
- **No CI/CD pipeline**: Changes are tested manually
- **No type checking**: No mypy or similar tools configured  
- **No automated formatting**: Code style enforcement is manual
- **No test coverage**: No pytest configuration or test files

## Development Workflow
1. Make code changes
2. Run `python app.py` to test locally
3. Manually verify functionality works as expected
4. Commit changes with descriptive messages
5. Push to repository

The project emphasizes rapid prototyping and manual testing over formal development processes.