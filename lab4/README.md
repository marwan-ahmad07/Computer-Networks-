# Run Commands

## Terminal 1 (Server)

```powershell
python -m lab4.http_server --host 127.0.0.1 --port 8080 --root .
```

## Terminal 2 (Client GET)

```powershell
python -m lab4.http_client GET /index.html --host 127.0.0.1 --port 8080
```

## Terminal 2 (Client POST)

```powershell
python -m lab4.http_client POST /note.txt --host 127.0.0.1 --port 8080 --body "hello world"
```
