# Architecture

- **Web Server:** Flask (`app.py`), listening on port 5000.
- **API Handler:** `scheduler/api/handlers.py` parses Laravel payloads and formats JSON responses.
- **Data Models:** `scheduler/core/models.py` defines ClassData, Lesson, Period, and helper classes.
- **Engine:** `scheduler/core/engine.py` builds the OR-Tools CP-SAT model and solves it.
