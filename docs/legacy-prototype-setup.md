# Clothing commerce

A shared local clothing store built from PRD v1: customer accounts, catalog, cart, server-priced checkout, inventory reservations, sandbox prepaid/COD orders and a staff workspace.

**This is a local MVP, not a production-ready store.** Real payments, carrier integrations, final policies and hosted deployment are outstanding. See [implementation status and limitations](docs/local-release.md).

## Run on Windows

Open PowerShell in this project folder:

```powershell
.\start.ps1
```

If script execution is blocked, use a process-only override:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

The launcher uses `uv` if installed, otherwise Python 3.12 through `py`. It prepares `.venv`, installs dependencies, seeds sample data once and starts the app. This machine's environment is already prepared.

Open **http://127.0.0.1:8000**. API docs: **http://127.0.0.1:8000/docs**. Stop with **Ctrl+C**; saved data remains in `commerce.sqlite3`.

If port 8000 is occupied, open the existing server or run `./start.ps1 -Port 8002`. If you configured `PUBLIC_ORIGIN`, keep its port aligned.

## Create an administrator

In a second PowerShell window, from this folder:

```powershell
.\.venv\Scripts\python.exe -m app.manage owner
```

Enter your email and choose a password of at least 12 characters. Password input is hidden. Sign in at `/account`, then open **Staff workspace** (`/admin`). No default password is included. Customers register directly through the Account page; the owner can assign staff roles to registered accounts.

## Try a complete order

1. Select a product, colour and size; add it to your bag.
2. Register or sign in. Your guest bag follows you into the account.
3. Save a fictional address with PIN **500001** (prepaid/COD) or **520001** (prepaid only).
4. Review the quote. Optional test coupon: **WELCOME10**.
5. Place the order. Prepaid orders have sandbox success/failure buttons. No real money is charged.
6. Sign in as owner to process, pack, dispatch with tracking and deliver. Record COD collection and remittance separately. Delivered items support return requests and staff inspection/refund records.

## Manual start

Python 3.12+ is recommended. Node is only needed for the original rehearsal and browser tests, not the new runtime.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.manage seed
python -m uvicorn app.commerce:app --host 127.0.0.1 --port 8000 --no-access-log
```

Run the expiry/notification worker separately when needed:

```sh
python -m app.manage worker
```

See [the local release guide](docs/local-release.md) for SMTP and recovery testing. [.env.example](.env.example) lists settings; Python does not automatically load that file.

## PostgreSQL through Docker

Start Docker Desktop. Create `.env` once with a long URL-safe `DB_PASSWORD` (hex characters work well). Preserve existing credentials. Stop the local Python server to free port 8000, then:

```sh
docker compose -f compose.commerce.yaml up --build -d
docker compose -f compose.commerce.yaml exec store python -m app.manage owner
```

Open port 8000. Docker uses a separate PostgreSQL dataset and includes a worker. Stop without removing data:

```sh
docker compose -f compose.commerce.yaml down
```

The original `compose.yaml` still runs the category-only foundation. Use **compose.commerce.yaml** for the shared store.

## Verify

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/test_rehearsal.cjs
```

Browser tests require the store running on port 8000 with sample data. They create fictional customers and orders in that installation:

```powershell
npm.cmd ci
npx.cmd playwright install chromium
npm.cmd run test:browser
```

Verified: 29 Python tests passed on SQLite (the PostgreSQL-only case is skipped there); all 30 tests passed against PostgreSQL 16; 13 original JavaScript rule tests and all three Playwright browser journeys passed. The Docker image built and served HTTP successfully; the Windows launcher and Compose configuration were also checked. Browser coverage includes mobile checkout, desktop filtering/gallery, and owner catalog/inventory/audit operations. This is not a full WCAG/load/cross-browser audit.

## Source map

- [app/commerce.py](app/commerce.py): shared-store API, permissions and workflows.
- [app/store.py](app/store.py): SQLAlchemy persistence, hashing and seed data.
- [app/manage.py](app/manage.py): owner setup and expiry/SMTP worker.
- [web/](web/): storefront and staff interface.
- [tests/test_commerce.py](tests/test_commerce.py): security and business-rule regressions.
- [docs/local-release.md](docs/local-release.md): PRD coverage, architecture differences and remaining work.
- [docs/clothing_ecommerce_prd_v1.pdf](docs/clothing_ecommerce_prd_v1.pdf): original requirements.

The original foundation (`app.main:app`) and isolated mock (`mock_store.main:app`) remain available; see [the original rehearsal guide](docs/mock-acceptance.md).
