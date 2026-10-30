# Deploying the listener page

Target: `https://teesrakaan.aryangorde.com`, one small server paid from the AWS credits. Caddy serves HTTPS (browsers only allow the microphone on HTTPS) and passes everything, WebSockets included, to the app on port 8000.

## Steps (Aryan, in the AWS console)
1. **Region:** Mumbai (ap-south-1), close to the users.
2. **Launch an instance:** Ubuntu Server 24.04 LTS, **arm64**, type **t4g.small** (2 vCPU, 2 GB), 10 GB gp3. A key pair you keep on the laptop.
3. **Security group:** SSH (22) from *My IP* only; HTTP (80) and HTTPS (443) from anywhere.
4. **Elastic IP:** allocate one and associate it with the instance.
5. **DNS (Hostinger → aryangorde.com → DNS zone):** add an **A record**, name `teesrakaan`, value the Elastic IP, TTL 300. Leave `@` and `www` alone (the portfolio).
6. **On the server:** `scp deploy/setup-server.sh ubuntu@<ip>:` then `ssh ubuntu@<ip> bash setup-server.sh`.
7. **No API key on the server.** The public page plays the demo calls and the "Try an example" checks with Muse Spark's real replies, saved in `examples/spark-replies/`, so it needs no key and can't spend anything. Live listening and "check a call you recorded" say they're switched off there. Typed checks of other text use the keyword stand-in. Paid calls end on Nov 5, 00:00 IST in any case, before judging, so a key on the server would stop working mid-judging. The live features are shown in the video, run from the laptop.
8. **From the laptop, in `teesra-kaan/`:** `deploy/push.sh ubuntu@<ip>`. Open `https://teesrakaan.aryangorde.com` from a phone.

## Cost (from the credits)
- t4g.small: about $0.017 an hour, about $12 a month;
- the Elastic IP (public IPv4): about $3.60 a month;
- 10 GB gp3: under $1 a month.

So about $16 a month while it runs (Nov 1–16), well inside the credits. Set the AWS Budgets alert at $50.

## After judging (after Nov 16)
Stop the instance, release the Elastic IP, and remove the DNS record.
