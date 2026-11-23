"""Boot built images with a disposable PostgreSQL volume/network; never touches the local store."""
import json
import secrets
import subprocess
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
prefix = "uyaras-check-" + secrets.token_hex(4)
env_file = root / "tmp" / (prefix + ".env")
env_file.parent.mkdir(exist_ok=True)
password = secrets.token_hex(24)
env_file.write_text(f"POSTGRES_PASSWORD={password}\nPOSTGRES_USER=uyaras\nPOSTGRES_DB=uyaras\nUYARAS_DATABASE_URL=postgresql+psycopg://uyaras:{password}@db:5432/uyaras\nAPP_ENV=development\nPUBLIC_ORIGIN=http://localhost:3003\n")
containers = []


def docker(*args):
    result = subprocess.run(["docker", *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return result.stdout.strip()


try:
    docker("network", "create", prefix)
    db = prefix + "-db"; containers.append(db)
    docker("run", "-d", "--name", db, "--network", prefix, "--network-alias", "db", "--env-file", str(env_file), "postgres:16-alpine")
    for _ in range(60):
        ready = subprocess.run(["docker", "exec", db, "pg_isready", "-U", "uyaras"], capture_output=True)
        if ready.returncode == 0: break
        time.sleep(1)
    else: raise RuntimeError("Test PostgreSQL did not become ready")
    for command in [["alembic", "-c", "backend/alembic.ini", "upgrade", "head"], ["uyaras.manage", "seed"]]:
        docker("run", "--rm", "--network", prefix, "--env-file", str(env_file), "uyaras-api:local", "python", "-m", *command)
    api = prefix + "-api"; containers.append(api)
    docker("run", "-d", "--name", api, "--network", prefix, "--network-alias", "api", "--env-file", str(env_file), "uyaras-api:local")
    frontend = prefix + "-web"; containers.append(frontend)
    docker("run", "-d", "--name", frontend, "--network", prefix, "-p", "127.0.0.1:3003:3000",
           "-e", "BACKEND_URL=http://api:8001", "-e", "PUBLIC_ORIGIN=http://localhost:3003", "uyaras-frontend:local")
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://localhost:3003", timeout=5) as response:
                assert "Uyaras" in response.read().decode()
            break
        except Exception: time.sleep(1)
    else: raise RuntimeError("Container storefront did not become ready")
    with urllib.request.urlopen("http://localhost:3003/api/v1/products") as response:
        catalog = json.load(response)
    assert catalog["total"] == 4
    assert all(v["available"] == 0 for p in catalog["items"] for v in p["variants"])
    docker("exec", api, "python", "-m", "uyaras.manage", "worker-once")
    # Cookie/session creation and a mutation through the production frontend proxy.
    import http.cookiejar
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    session = json.load(opener.open("http://localhost:3003/api/v1/session"))
    payload = json.dumps({"sku": catalog["items"][0]["variants"][0]["sku"], "quantity": 1}).encode()
    request = urllib.request.Request("http://localhost:3003/api/v1/cart/items", data=payload,
        headers={"Content-Type":"application/json", "X-CSRF-Token":session["csrf"], "Origin":"http://localhost:3003"})
    assert json.load(opener.open(request))["lines"]
    print("Container smoke passed: migrations, seed, frontend, API proxy, session/CSRF, cart and worker; stock remains zero.")
finally:
    for container in reversed(containers):
        subprocess.run(["docker", "rm", "-f", "-v", container], capture_output=True)
    subprocess.run(["docker", "network", "rm", prefix], capture_output=True)
    env_file.unlink(missing_ok=True)
