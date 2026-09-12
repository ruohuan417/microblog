import os
import re
import time
import threading
import subprocess
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor

import requests

parser = argparse.ArgumentParser()
parser.add_argument('--server', choices=['flask', 'waitress'], default='waitress')
args = parser.parse_args()
SERVER_MODE = args.server

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
DB_PATH = os.path.join(ROOT, '_load_test.db').replace('\\', '/')
DB_URL = 'sqlite:///' + DB_PATH
SERVER_LOG = os.path.join(ROOT, '_load_test_server.log')
PORT = 5017
BASE = 'http://127.0.0.1:%d' % PORT
DURATION = 10.0
CSRF_RE = re.compile(r'csrf_token[^>]*value="([^"]*)"')

if SERVER_MODE == 'flask':
    READ_LEVELS = [1, 10, 30, 50]
    WRITE_LEVELS = [10, 50]
else:
    READ_LEVELS = [1, 10, 30, 50, 100, 200, 500]
    WRITE_LEVELS = [10, 50, 100]

os.environ['DATABASE_URL'] = DB_URL

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    db.create_all()
    u = User(username='loadtester', email='load@test.com')
    u.set_password('loadtest123')
    db.session.add(u)
    db.session.commit()
print('setup: temp db ready, user loadtester created')

server = subprocess.Popen(
    [VENV_PY, '-m', 'flask', 'run', '--port', str(PORT), '--no-debugger']
    if SERVER_MODE == 'flask' else
    [os.path.join(ROOT, '.venv', 'Scripts', 'waitress-serve.exe'),
     '--host=127.0.0.1', '--port=%d' % PORT, '--threads=16',
     '--connection-limit=2000', 'microblog:app'],
    cwd=ROOT, env=os.environ,
    stdout=open(SERVER_LOG, 'w'), stderr=subprocess.STDOUT)
print('server: pid %d, mode=%s, port %d, waiting for readiness...'
      % (server.pid, SERVER_MODE, PORT))

ready = False
for _ in range(60):
    if server.poll() is not None:
        print('SERVER DIED AT STARTUP')
        sys.exit(1)
    try:
        r = requests.get(BASE + '/auth/login', timeout=2)
        if r.status_code == 200:
            ready = True
            break
    except requests.RequestException:
        pass
    time.sleep(0.5)
if not ready:
    print('SERVER NOT READY IN 30s')
    server.terminate()
    sys.exit(1)
print('server: ready\n')


def build_session():
    s = requests.Session()
    for attempt in range(3):
        try:
            r = s.get(BASE + '/auth/login', timeout=20)
            token = CSRF_RE.search(r.text).group(1)
            s.post(BASE + '/auth/login', data={
                'username': 'loadtester', 'password': 'loadtest123',
                'csrf_token': token}, timeout=20)
            r = s.get(BASE + '/', timeout=20)
            break
        except requests.ConnectionError:
            if attempt == 2:
                raise
            time.sleep(5)
    m = CSRF_RE.search(r.text)
    csrf = m.group(1) if m else None
    return s, csrf


_POOL_CACHE = {}


def build_pool(n):
    if n in _POOL_CACHE:
        return _POOL_CACHE[n]
    with ThreadPoolExecutor(max_workers=min(n, 50)) as ex:
        pool = list(ex.map(lambda _: build_session(), range(n)))
    _POOL_CACHE[n] = pool
    return pool


def pct(sorted_lat, p):
    return sorted_lat[min(int(len(sorted_lat) * p), len(sorted_lat) - 1)]


def run_level(n, mode):
    sessions = build_pool(n)
    latencies = []
    errors = []
    lock = threading.Lock()
    stop_at = time.perf_counter() + DURATION

    def work(sess, csrf):
        while time.perf_counter() < stop_at:
            t0 = time.perf_counter()
            try:
                if mode == 'write':
                    r = sess.post(BASE + '/', data={
                        'body': 'load test post %d' % t0,
                        'csrf_token': csrf}, timeout=20)
                else:
                    r = sess.get(BASE + '/explore', timeout=20)
                code = r.status_code
            except Exception as e:
                code = 'EXC:' + type(e).__name__
            dt = time.perf_counter() - t0
            with lock:
                latencies.append(dt)
                if code != 200:
                    errors.append(code)

    threads = [threading.Thread(target=work, args=(s, c), daemon=True)
               for s, c in sessions]
    t_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t_start

    total = len(latencies)
    lat_sorted = sorted(latencies)
    avg = sum(latencies) / total if total else 0
    p50 = pct(lat_sorted, 0.50) if total else 0
    p95 = pct(lat_sorted, 0.95) if total else 0
    p99 = pct(lat_sorted, 0.99) if total else 0
    err_n = len(errors)
    err_codes = {}
    for c in errors:
        err_codes[str(c)[:40]] = err_codes.get(str(c)[:40], 0) + 1
    for s, _ in sessions:
        s.close()
    print('conc=%-4d | RPS=%-7.1f | avg=%-7.0fms | p50=%-7.0fms | '
          'p95=%-7.0fms | p99=%-7.0fms | err=%d/%d (%.1f%%) %s'
          % (n, total / wall, avg * 1000, p50 * 1000, p95 * 1000,
             p99 * 1000, err_n, total, err_n * 100.0 / max(total, 1),
             err_codes if err_codes else ''))


try:
    r = requests.get(BASE + '/auth/login', timeout=20)
    print('[baseline] anonymous GET /auth/login: %d, %.0fms'
          % (r.status_code, r.elapsed.total_seconds() * 1000))
    print()

    print('=== [%s] READ /explore (authenticated) ===' % SERVER_MODE)
    for n in READ_LEVELS:
        run_level(n, 'read')
        time.sleep(5)
    print()

    print('=== [%s] WRITE POST / new post (authenticated) ===' % SERVER_MODE)
    for n in WRITE_LEVELS:
        run_level(n, 'write')
        time.sleep(5)
    print()
finally:
    server.terminate()
    try:
        server.wait(timeout=10)
    except Exception:
        server.kill()
    time.sleep(1)
    try:
        os.remove(DB_PATH)
    except OSError:
        pass
print('ALL DONE (server log kept at %s)' % SERVER_LOG)