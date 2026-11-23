# Uyaras clothing commerce

Uyaras now uses **Next.js + TypeScript + Tailwind/shadcn**, **FastAPI**, and **normalized PostgreSQL**. Product uploads have an R2 adapter. The previous plain HTML/JSON-store prototype is retained as historical code.

This is a **V1 development preview**. Payment simulation and manual shipping are available; production purchases remain blocked. The sample catalog starts with zero stock. No hosting, gateway, courier or R2 accounts were created.

## Run on Windows

Start Docker Desktop. Install Node.js 24 and Python 3.12 or uv, then run from this folder:

```powershell
.\start.ps1
```

Open **http://localhost:3000**. The script prepares the database, migrations and sample catalog and starts the frontend, backend and background worker. Press Ctrl+C to stop the application.

For simulated stock and test checkout:

```powershell
.\start.ps1 -DemoStock
```

This adds development-only stock; it does not enable production sales. Test PINs: **500001** and **520001**. Sample products, prices, customers, addresses and orders are disposable test data.

## Create staff access

```powershell
.\start.ps1 -SetupOnly
.\manage.ps1 owner -Email you@example.com
```

Enter a password when prompted. Sign in at /account, then open /admin. There is no default owner password. Customers register through the storefront.

## Verify

```powershell
.\manage.ps1 test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

Full browser and operations instructions are in the guide below. The legacy application has its own [historical setup guide](docs/legacy-prototype-setup.md) and [legacy launcher](start-legacy.ps1).

## Handover

- [V1 completion report](docs/uyaras-v1-report.md)
- [PRD acceptance tests and launch gates](docs/uyaras-v1-acceptance.md)
- [Payment and shipping provider proposal](docs/provider-comparison.md)
- [Setup, testing, backups and operations](docs/uyaras-operations.md)
- [Architecture and state transitions](docs/uyaras-architecture.md)
- [India and AP market research](docs/market-research.md)
- [Original PRD](docs/clothing_ecommerce_prd_v1.pdf)

FastAPI interactive API documentation: **http://127.0.0.1:8001/docs** while the backend is running.
