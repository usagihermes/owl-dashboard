# 🦉 OWL Dashboard

A real-time server status dashboard built for the OWL (Hermes Agent) environment. Monitors system resources, services, cron jobs, and active tasks with a sleek dark-themed UI.

![Dashboard Preview](https://img.shields.io/badge/status-live-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Flask](https://img.shields.io/badge/flask-3.x-lightgrey)

## Features

- **System Stats** — CPU load, memory, swap, disk usage with live progress bars
- **Service Monitoring** — TCP port checks + HTTP health probes for registered services
- **Cron Job Tracking** — Displays scheduled Hermes cron jobs
- **Task Management** — Interactive task list with status toggling
- **Activity Log** — Recent events timeline
- **Notes** — Editable context/notes area with auto-save
- **Auto-refresh** — Updates every 5 seconds
- **Responsive** — Works on desktop and mobile

## Quick Start

```bash
# Install dependencies
pip install flask

# Run the server
python3 server.py
```

The dashboard will be available at `http://localhost:8888`

## Configuration

Edit the `SERVICES` list in `server.py` to add/remove monitored services:

```python
SERVICES = [
    {"name": "My App", "url": "http://127.0.0.1:3000", "port": 3000, "icon": "🚀"},
    {"name": "Database", "url": None, "port": 5432, "icon": "🐘"},
]
```

- `url` — If set, performs an HTTP health check. If `null`, just checks the TCP port.
- `port` — TCP port for connectivity check
- `icon` — Emoji icon for the service

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/api/status` | GET | Full status JSON (system, services, cron, tasks, activity) |
| `/api/task` | POST | Add/update/remove tasks |
| `/api/activity` | POST | Log an activity entry |

### Task API

```bash
# Add a task
curl -X POST http://localhost:8888/api/task \
  -H "Content-Type: application/json" \
  -d '{"action":"add","task":{"content":"Do something","status":"pending"}}'

# Update a task
curl -X POST http://localhost:8888/api/task \
  -H "Content-Type: application/json" \
  -d '{"action":"update","id":"123","updates":{"status":"completed"}}'

# Remove a task
curl -X POST http://localhost:8888/api/task \
  -H "Content-Type: application/json" \
  -d '{"action":"remove","id":"123"}'
```

## File Structure

```
owl-dashboard/
├── server.py          # Flask API server
├── static/
│   └── index.html     # Dashboard UI (single-file, no dependencies)
├── .gitignore
└── README.md
```

## License

MIT
