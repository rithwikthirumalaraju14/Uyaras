# Uyaras setup and operations

## Windows development

Install/start Docker Desktop, Node.js 24 and Python 3.12 or uv. From the repository root:

```powershell
.\start.ps1
```

The launcher installs Python dependencies, creates an ignored local secret file if missing, starts PostgreSQL on `127.0.0.1:5434`, applies Alembic migrations, seeds the sample catalog, and starts FastAPI, the worker and Next.js. Open `http://localhost:3000`. Use localhost consistently for session/origin checks. Ctrl+C stops the application processes; the database volume remains available.

For test checkout with simulated stock:

```powershell
.\start.ps1 -DemoStock
```

This does not represent actual stock. The seed is idempotent and does not overwrite catalog edits. Real stock remains unconfirmed and production ordering stays blocked. Sample PINs are `500001` and `520001`; they are unverified test destinations. Sample promotions and prices are editable in the staff studio.

To prepare dependencies/database without launching servers:

```powershell
.\start.ps1 -SetupOnly
.\manage.ps1 owner -Email you@example.com
```

Owner creation prompts for a password of at least twelve characters and refuses to silently upgrade an existing customer account. There is no default administrator password. Sign in at `/account`, then open `/admin`. Existing staff can be assigned Catalog, Operations, Support, Analyst or Owner roles from the studio. Use fictional customer data during preview development.

The old launcher is preserved as [start-legacy.ps1](../start-legacy.ps1) for the historical prototype. Do not use it to run the new Uyaras application.

## Manual startup

Each PowerShell terminal must load the environment:

```powershell
. .\scripts\load-env.ps1
```

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn uyaras.main:create_app --factory --host 127.0.0.1 --port 8001
```

Worker:

```powershell
.\manage.ps1 worker
```

Frontend:

```powershell
npm.cmd --prefix frontend run dev
```

If port 8001/3000 is already in use, stop the previous instance first. Keep Docker Desktop running. The backend deliberately requires PostgreSQL and has no silent SQLite fallback.

## Production build and local container preview

```powershell
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run start
```

Backend and worker must also be running. To use containers instead, first finish local setup/seeding, stop local application servers and run:

```powershell
docker compose --env-file .env.uyaras -f compose.full.yaml up --build -d
```

This is still a **local preview**, not public deployment. The API/frontend/worker images use non-root runtime users. PostgreSQL data persists in `uyaras_pg`; do not use `down -v` unless you intend to erase it. Hosting accounts, domains, provider accounts and paid infrastructure were not created.

## R2 and notifications

Copy the needed variable names from [.env.uyaras.example](../.env.uyaras.example) into the ignored local environment file. Configure `R2_ACCOUNT_ID`, access key, secret key, bucket and public URL. Permit your frontend origin in bucket CORS for PUT/GET/HEAD and Content-Type. Use a restricted bucket token. Restart/rebuild the frontend after changing the public image hostname. The staff Products screen provides upload and image descriptions. Sample files continue to work without R2.

SMTP requires host, port, from address, username and password. The worker uses STARTTLS. Without SMTP, notifications remain queued and are not reported as delivered. For local recovery testing, first request a recovery link on the account page, then run:

```powershell
.\manage.ps1 recovery-link -Email customer@example.test
```

This command is disabled in production. Treat the printed one-time link as a secret.

## Backups and recovery

```powershell
.\scripts\backup.ps1
.\scripts\restore-check.ps1 -Backup .\backups\uyaras-YYYYMMDD-HHMMSS.dump
```

The restore check creates a separate timestamped database and verifies schema/catalog/order counts; it never overwrites the live database. Backups contain customer information. Before launch, encrypt off-site copies, restrict access, schedule backups, define retention and test restoration regularly. A reasonable initial operational target is daily backups with an RPO of 24 hours and an RTO of 4 hours; these are targets, not measured service guarantees. Managed PostgreSQL PITR should improve that target when available.

Before a release, record the current migration revision and take a backup. Prefer a forward fix or a reviewed database restore over an unreviewed destructive downgrade. Keep the prior application image for rollback; verify schema compatibility before switching versions. Do not restore into the live database without an explicit recovery decision.

## Verification commands

```powershell
.\manage.ps1 test
. .\scripts\load-env.ps1
npm.cmd ci
npx.cmd playwright install chromium firefox webkit
.\.venv\Scripts\python.exe -u scripts\browser-test.py
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Integration and browser tests use separate PostgreSQL schemas. Browser tests launch their own backend on 8005 and frontend on 3002. They remove their isolated test schema afterward. Do not run two browser suites at the same time on those ports. Browser failure screenshots and traces are saved under the ignored test-results folder.

## V1 completion controls

See the [acceptance matrix](uyaras-v1-acceptance.md) for named tests, budgets and release gates, and the [provider comparison](provider-comparison.md) before selecting integrations. The [OpenAPI snapshot](uyaras-openapi.json) documents the API; interactive docs are at the backend `/docs` endpoint.

Customers request cancellation with a reason. Confirmed/processing/packed orders enter Cancellation Requested and cannot progress through fulfillment until staff resolve the request. Approval releases reserved stock; captured prepaid funds require refund resolution. Rejection requires a reason and restores the previous state. Unpaid orders can cancel immediately.

Notification jobs carry a channel, template and subject. The SMTP worker processes email only, retries with backoff and marks a job failed after eight attempts. Inspect failed jobs in the staff studio and diagnose SMTP before a controlled retry; queued email is not delivered email. Other channels need an adapter and separate acceptance.

For an isolated container rehearsal:

```powershell
docker build -f Dockerfile.uyaras -t uyaras-api:local .
docker build -f frontend/Dockerfile -t uyaras-frontend:local .
.\.venv\Scripts\python.exe scripts/container-smoke.py
```

The rehearsal removes its own containers/network and does not modify the store database. Port 3003 must be free. GitHub Actions includes the same checks; remote status remains unknown until the project is pushed to the owner's selected repository.

## Launch operations still required

Use ₹1,500–₹3,000/month as a planning budget for a small initial launch, not a purchased or verified hosting quote. Plan for a frontend host, conventional Python backend/worker host, managed PostgreSQL, and Cloudflare DNS/CDN/R2. Gateway fees, courier charges, tax, domain, email, backup storage and higher availability can add costs. Provider choice and current pricing need confirmation before deployment.

Production monitoring should cover API errors/latency, database storage, failed notification jobs, overdue reservations, late payment captures, stock discrepancies and COD/remittance mismatches. Establish alerts to a real monitored contact. Suggested frontend budgets are p75 LCP ≤2.5 s, INP ≤200 ms and CLS ≤0.1 on target devices; local browser checks are not a field-performance certification.

Define a real privacy retention/deletion process and policy before collecting customer data. Account deletion must respect financial-record obligations; do not simply cascade-delete paid order history. Carry out staff acceptance, keyboard/screen-reader checks, broader browser testing and actual provider sandbox acceptance before launch.
