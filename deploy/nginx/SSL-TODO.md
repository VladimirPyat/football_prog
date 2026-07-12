# TLS for Football Predictions (planned)

HTTP configs: `football-single-host.http.conf`, `football-two-hosts.http.conf`.

When ready for HTTPS:

1. Point DNS A-records to the server.
2. Install certbot: `sudo apt install certbot python3-certbot-nginx`
3. Run certbot against the active site, e.g.:
   ```bash
   sudo certbot --nginx -d app.example.com -d api.example.com
   ```
4. Update `.env`:
   ```env
   PUBLIC_FRONTEND_URL=https://app.example.com
   PUBLIC_API_URL=https://api.example.com
   ```
5. Rebuild frontend: `docker compose build frontend && docker compose up -d frontend`
6. Restart API: `docker compose up -d api`

Certbot will add `listen 443 ssl` blocks and optional HTTP→HTTPS redirect.

For **single-host** mode use one `-d your.domain.com`.
