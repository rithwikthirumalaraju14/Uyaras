---
description: Preserve transaction visibility and reliable checkout verification
applyTo: 'backend/uyaras/**/*.py,frontend/src/**/*.tsx,tests/uyaras-browser/**'
---

FastAPI database dependencies must use `Depends(database, scope="function")` so the transaction commits before success is sent. The default request scope can expose a new session cookie before that session is visible to the next request; keep the HTTP-response commit-visibility regression test.

Share one in-flight frontend session initialization promise between mount effects and API calls. Concurrent initializations can replace the cookie while a mutation still carries the other session's CSRF token.

Account and checkout both contain an address form. Browser tests must await the checkout URL and heading after clicking Continue checkout before filling those shared labels. Warm route modules before timing journeys against the development server.
