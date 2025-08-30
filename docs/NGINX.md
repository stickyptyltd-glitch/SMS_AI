# NGINX Reverse Proxy (TLS + Admin)

Use NGINX to terminate TLS and proxy to the API (`localhost:8081`). This example also locks down `/admin` by IP and requires the `X-Admin-Token` header.

## 1) Install NGINX + Certs
- Ubuntu: `sudo apt-get install nginx`
- TLS: Use certbot or your own certs. Example assumes `/etc/letsencrypt/live/your.domain/fullchain.pem` and `privkey.pem`.

## 2) Site Config
Create `/etc/nginx/sites-available/smsai.conf`:

```
server {
  listen 443 ssl http2;
  server_name your.domain;

  ssl_certificate     /etc/letsencrypt/live/your.domain/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/your.domain/privkey.pem;

  # Increase proxy buffers for larger JSON bodies
  client_max_body_size 4m;

  location / {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
  }

  # Lock down admin by IP (optional) and require token header
  location /admin {
    allow 203.0.113.0/24;   # replace with your office IP block
    deny all;               # deny others
    proxy_set_header X-Admin-Token $http_x_admin_token; # forward header
    proxy_pass http://127.0.0.1:8081/admin;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
  }

  # Health and metrics (optionally restrict metrics)
  location /metrics {
    allow 127.0.0.1;
    allow 10.0.0.0/8;  # adjust to your network
    deny all;
    proxy_pass http://127.0.0.1:8081/metrics;
  }
}

server {
  listen 80;
  server_name your.domain;
  return 301 https://$host$request_uri;
}
```

Enable the site:

```
sudo ln -s /etc/nginx/sites-available/smsai.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 3) Admin Token
- Set `ADMIN_TOKEN` in your API environment. For admin access:
  - Add the header `X-Admin-Token: <your-token>` when hitting `/admin`.
  - Optionally use IP allow lists (as above) for extra protection.

## 4) Notes
- Ensure your Compose service binds to localhost or firewall appropriately if exposing via NGINX.
- For Prometheus, adjust the `/metrics` allow list accordingly.
- If running behind another proxy/CDN, ensure headers are forwarded.
