Development TLS certificates directory

This folder is ignored by Git except for this README. Place self‑signed development certificates here to serve HTTPS locally.

Expected files (PEM format):
- dev.crt — certificate
- dev.key — private key

Quick generate (with OpenSSL, e.g., from Git for Windows):

PowerShell (run from the project root):

  # create folder if missing
  New-Item -ItemType Directory -Force -Path .\backend\certs | Out-Null
  # generate 825‑day cert for localhost and 127.0.0.1
  & openssl req -x509 -nodes -days 825 -newkey rsa:2048 `
    -keyout backend/certs/dev.key -out backend/certs/dev.crt `
    -subj "/CN=localhost" `
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

Use with:
- Django (runserver_plus):
    python backend\manage.py runserver_plus --cert-file backend\certs\dev.crt --key-file backend\certs\dev.key 0.0.0.0:8443
- Uvicorn:
    python -m uvicorn backend.core.asgi:application --host 0.0.0.0 --port 8443 --ssl-keyfile backend\certs\dev.key --ssl-certfile backend\certs\dev.crt

Note: Do not commit real keys. See .gitignore guidance below.

Troubleshooting on Windows (OpenSSL config not found):
- If you see an error like: "Can't open 'C:\\Program Files\\Common Files\\ssl/openssl.cnf'", your OpenSSL lacks a default config path.
- Easiest fix: run the helper script, which auto‑creates a minimal config and sets OPENSSL_CONF for you:
    PowerShell:
        scripts\make_dev_cert.ps1
- Alternatively, set OPENSSL_CONF to an existing openssl.cnf before running OpenSSL, e.g. for Git for Windows:
    $env:OPENSSL_CONF = "C:\\Program Files\\Git\\usr\\ssl\\openssl.cnf"
    & openssl req -x509 -nodes -days 825 -newkey rsa:2048 -keyout backend/certs/dev.key -out backend/certs/dev.crt -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"