#!/usr/bin/env python3
"""OWL Dashboard - Status API Server"""
import subprocess, json, os, socket, time, threading
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder='/home/usagi/dashboard/static')

# --- Config ---
PORT = 8888
HOST = '0.0.0.0'
DASHBOARD_DIR = '/home/usagi/dashboard'

# --- Service registry ---
SERVICES = [
    {"name": "NetCheck", "url": "http://127.0.0.1:8080/index.html", "port": 8080, "icon": "🌐"},
    {"name": "Hermes Gateway", "url": None, "port": 9120, "icon": "🤖"},
    {"name": "Chrome DevTools", "url": None, "port": 9222, "icon": "🔍"},
    {"name": "GNOME Remote Desktop", "url": None, "port": 3389, "icon": "🖥️"},
    {"name": "CUPS Print", "url": None, "port": 631, "icon": "🖨️"},
]

# --- Helpers ---
def check_port(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        return result == 0
    except:
        return False

def check_http(url):
    try:
        import urllib.request
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req, timeout=3)
        return resp.status < 400
    except:
        return False

def get_system_stats():
    # Load
    with open('/proc/loadavg') as f:
        parts = f.read().split()
        load_1 = float(parts[0])
        load_5 = float(parts[1])
        load_15 = float(parts[2])
    
    # Memory
    mem = {}
    with open('/proc/meminfo') as f:
        for line in f:
            if ':' in line:
                k, v = line.split(':', 1)
                mem[k.strip()] = int(v.split()[0])
    
    mem_total = mem.get('MemTotal', 0)
    mem_available = mem.get('MemAvailable', 0)
    mem_used = mem_total - mem_available
    mem_pct = round(mem_used / mem_total * 100, 1) if mem_total else 0
    
    swap_total = mem.get('SwapTotal', 0)
    swap_free = mem.get('SwapFree', 0)
    swap_used = swap_total - swap_free
    swap_pct = round(swap_used / swap_total * 100, 1) if swap_total else 0
    
    # Disk
    disk_info = []
    try:
        df = subprocess.run(['df', '-h', '/', '/home'], capture_output=True, text=True, timeout=5)
        for line in df.stdout.strip().split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 6:
                disk_info.append({
                    'mount': parts[5],
                    'size': parts[1],
                    'used': parts[2],
                    'avail': parts[3],
                    'pct': int(parts[4].replace('%', ''))
                })
    except:
        pass
    
    # Uptime
    with open('/proc/uptime') as f:
        uptime_seconds = float(f.read().split()[0])
    
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    # CPU count for load normalization
    cpu_count = os.cpu_count() or 1
    load_normalized = round(load_1 / cpu_count * 100, 1)
    
    return {
        'load': {'1m': load_1, '5m': load_5, '15m': load_15, 'normalized_pct': load_normalized, 'cpu_count': cpu_count},
        'memory': {'total_kb': mem_total, 'used_kb': mem_used, 'available_kb': mem_available, 'pct': mem_pct},
        'swap': {'total_kb': swap_total, 'used_kb': swap_used, 'pct': swap_pct},
        'disk': disk_info,
        'uptime': {'days': days, 'hours': hours, 'minutes': minutes, 'seconds': int(uptime_seconds)},
        'hostname': socket.gethostname(),
    }

def get_cron_jobs():
    try:
        result = subprocess.run(
            ['python3', '-c', '''
import json, sys
sys.path.insert(0, "/home/usagi/.hermes/hermes-agent")
from hermes_cli.cron_store import CronStore
store = CronStore()
jobs = store.list_jobs()
for j in jobs:
    print(json.dumps(j))
'''],
            capture_output=True, text=True, timeout=10
        )
        jobs = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    jobs.append(json.loads(line))
                except:
                    pass
        return jobs
    except Exception as e:
        return []

def get_active_tasks():
    """Read current TODO state from dashboard state file"""
    state_file = os.path.join(DASHBOARD_DIR, 'state.json')
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                state = json.load(f)
            return state.get('tasks', [])
        except:
            pass
    return []

def get_recent_activity():
    """Read recent activity log"""
    log_file = os.path.join(DASHBOARD_DIR, 'activity.log')
    if os.path.exists(log_file):
        try:
            with open(log_file) as f:
                lines = f.readlines()
            return [line.strip() for line in lines[-20:]]
        except:
            pass
    return []

# --- API Endpoints ---
@app.route('/api/status')
def api_status():
    services = []
    for svc in SERVICES:
        if svc['url']:
            alive = check_http(svc['url'])
        else:
            alive = check_port(svc['port'])
        services.append({
            'name': svc['name'],
            'icon': svc['icon'],
            'port': svc['port'],
            'url': svc['url'],
            'status': 'online' if alive else 'offline',
        })
    
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'services': services,
        'system': get_system_stats(),
        'cron_jobs': get_cron_jobs(),
        'tasks': get_active_tasks(),
        'activity': get_recent_activity(),
    })

@app.route('/api/task', methods=['POST'])
def api_task():
    from flask import request
    data = request.get_json()
    state_file = os.path.join(DASHBOARD_DIR, 'state.json')
    state = {'tasks': [], 'notes': ''}
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                state = json.load(f)
        except:
            pass
    
    action = data.get('action')
    if action == 'add':
        task = data.get('task', {})
        task['id'] = str(int(time.time() * 1000))
        task['created'] = datetime.now(timezone.utc).isoformat()
        state['tasks'].append(task)
    elif action == 'update':
        task_id = data.get('id')
        for t in state['tasks']:
            if t.get('id') == task_id:
                t.update(data.get('updates', {}))
                break
    elif action == 'remove':
        task_id = data.get('id')
        state['tasks'] = [t for t in state['tasks'] if t.get('id') != task_id]
    elif action == 'set_notes':
        state['notes'] = data.get('notes', '')
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    return jsonify({'ok': True, 'tasks': state['tasks']})

@app.route('/api/activity', methods=['POST'])
def api_activity():
    from flask import request
    data = request.get_json()
    log_file = os.path.join(DASHBOARD_DIR, 'activity.log')
    entry = data.get('entry', '')
    if entry:
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} | {entry}\n")
    return jsonify({'ok': True})

@app.route('/')
def index():
    return send_from_directory('/home/usagi/dashboard/static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('/home/usagi/dashboard/static', path)

if __name__ == '__main__':
    os.makedirs('/home/usagi/dashboard/static', exist_ok=True)
    os.makedirs('/home/usagi/dashboard', exist_ok=True)
    print(f"OWL Dashboard running on http://0.0.0.0:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
