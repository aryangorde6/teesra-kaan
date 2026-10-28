# Deploying the listener page

Target: `https://teesrakaan.aryangorde.com`, one small server paid from the AWS credits. Caddy serves HTTPS (browsers only allow the microphone on HTTPS) and passes everything, WebSockets included, to the app on port 8000.

## Steps (Aryan, in the AWS console)
1. **Region:** Mumbai (ap-south-1), close to the users.
2. **Launch an instance:** Ubuntu Server 24.04 LTS, **arm64**, type **t4g.small** (2 vCPU, 2 GB), 10 GB gp3. A key pair you keep on the laptop.
3. **Security group:** SSH (22) from *My IP* only; HTTP (80) and HTTPS (443) from anywhere.
4. **Elastic IP:** allocate one and associate it with the instance.
5. **DNS (Hostinger → aryangorde.com → DNS zone):** add an **A record**, name `teesrakaan`, value the Elastic IP, TTL 300. Leave `@` and `www` alone (the portfolio).
6. **On the server:** `scp deploy/setup-server.sh ubuntu@<ip>:` then `ssh ubuntu@<ip> bash setup-server.sh`.
7. **The server's `.env`** (typed on the server, never committed): `ssh ubuntu@<ip>`, then `nano /opt/teesrakaan/.env`:
   ```
   MODEL_API_KEY=<a separate key for the public page>
   TEESRAKAAN_ALLOW_PAID=1
   TEESRAKAAN_BUDGET_META_USD=25
   ```
   A separate key makes it easy to revoke after judging. The $25 stop is the public page's own; when it's reached, live listening switches itself off and the demo calls keep working.
8. **From the laptop, in `teesra-kaan/`:** `deploy/push.sh ubuntu@<ip>`. Open `https://teesrakaan.aryangorde.com` from a phone.

## Cost (from the credits)
- t4g.small: about $0.017 an hour, about $12 a month;
- the Elastic IP (public IPv4): about $3.60 a month;
- 10 GB gp3: under $1 a month.

So about $16 a month while it runs (Nov 1–16), well inside the credits. Set the AWS Budgets alert at $50.

## After judging (after Nov 16)
Stop the instance, release the Elastic IP, delete the page's API key on dev.meta.ai, and remove the DNS record.
