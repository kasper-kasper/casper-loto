# Casper Loto Web Admin Panel

Separate React/TypeScript administrator client for Milestone 6. It uses a
signed HttpOnly session cookie, an in-memory CSRF token and the backend
`/api/v1/admin` use cases. No CAS amount is changed directly by this client.

```powershell
npm install
npm run dev
```

Vite serves <http://127.0.0.1:5174> and proxies `/api` to the local backend.
Configure credentials first with:

```powershell
.venv\Scripts\python.exe -m scripts.configure_admin
```
