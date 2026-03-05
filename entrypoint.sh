#!/bin/sh
# Wait for MySQL to be ready, then run migrations and start the app
set -e

if [ -n "$DB_HOST" ]; then
  echo "Waiting for MySQL at $DB_HOST:${DB_PORT:-3306}..."
  while ! python -c "
import socket, os, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
try:
  s.connect((os.environ.get('DB_HOST','localhost'), int(os.environ.get('DB_PORT',3306))))
  s.close()
  sys.exit(0)
except Exception as e:
  sys.exit(1)
" 2>/dev/null; do
    sleep 2
  done
  echo "MySQL is up."
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear || true
exec gunicorn zeno_time.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 60
