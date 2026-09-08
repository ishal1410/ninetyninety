# Deploy runbook

Two ways to host the Streamlit app (`app.py`). Both need one secret, `GOOGLE_API_KEY`
(free key, no card: https://aistudio.google.com/apikey). The app reads it from the
environment or from a `.env` file next to `app.py` (`src/ninetyninety/config.py` calls
`load_dotenv()` and then reads `os.environ["GOOGLE_API_KEY"]`); nothing else is
required. `.streamlit/config.toml` (theme, `server.headless = true`) ships in the repo
and is picked up by both hosts.

| | Streamlit Community Cloud | Amazon EC2 |
|---|---|---|
| Cost | Free | t3.small, about $0.02 an hour, from the $100 credit |
| URL | `https://<name>.streamlit.app` | `http://<public-ip>` (no TLS) |
| Catch | Sleeps after a stretch with no visitors | Stop the instance when judging ends |
| Diagram | No AWS service to show | "Hosted on Amazon EC2" goes into box 1 |

Pick EC2 if the diagram matters (criterion 1 asks for AWS services); pick Community
Cloud if the goal is just a link that works. Either way, finish with the checklist at
the bottom.

## Option A: Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub. Authorize the Streamlit
   app for the `ishal1410` account (it needs read access to public repos).
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill the form:
   - Repository: `ishal1410/ninetyninety`
   - Branch: `master`
   - Main file path: `app.py`
   - App URL: pick a subdomain, for example `ninetyninety` (gives `https://ninetyninety.streamlit.app`)
4. Open **Advanced settings**:
   - Python version: **3.12** (the repo is developed and tested on 3.12; the dropdown
     default is older)
   - Secrets (TOML, one line):

     ```toml
     GOOGLE_API_KEY = "paste-the-key-here"
     ```

     Optional second line if one model id runs out of free quota during judging:

     ```toml
     GEMINI_MODEL_IDS = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash-lite"
     ```

   Top-level string secrets are exported as environment variables, which is exactly
   where `config.py` looks. No code change.
5. Click **Deploy**. The first build takes a few minutes (`requirements.txt` pulls
   `strands-agents[gemini]`, `streamlit`, `pypdf`). Watch the log in the right-hand panel.
6. Open the URL, leave "Use the synthetic demo ledger instead" ticked, and run it once
   to confirm a full run completes (a 54-row ledger takes a few minutes on the free
   tier). If it fails with the "set GOOGLE_API_KEY" message, the secret was saved under
   a different name; fix it under **Settings > Secrets** and the app restarts on its own.

**Sleep caveat.** Free apps hibernate after a period with no visitors (Streamlit has
tightened this threshold over time; assume hours, not days). A sleeping app shows a
"get this app back up" button and takes about a minute to wake, which a judge may not
wait for. Before the judging window (and again on the morning of 2026-09-14) open the
URL yourself, click the wake button if shown, and run the demo ledger so the container
is warm and the Gemini key is proven live.

To redeploy after a push: nothing, Community Cloud rebuilds on every push to `master`.
To change the Python version or secrets later: app menu (three dots) > **Settings**.

## Option B: Amazon EC2 (t3.small, Amazon Linux 2023)

The whole install is `scripts/ec2-user-data.sh`: cloud-init runs it once at first
boot as root. It installs `python3.12` and `git` with `dnf`, clones the repo to
`/opt/ninetyninety`, builds a venv from `requirements.txt`, writes `.env`, and
installs a systemd unit that runs

```
streamlit run app.py --server.port 80 --server.address 0.0.0.0 --server.headless true
```

as the non-root user `ninetyninety` with `AmbientCapabilities=CAP_NET_BIND_SERVICE`
(so it can bind port 80 without being root). The service user owns `/opt/ninetyninety`
because the app writes `data/f990ez.pdf` on first run.

### Launch

1. Open `scripts/ec2-user-data.sh` locally and replace `PASTE_YOUR_GEMINI_KEY_HERE`
   with the real key. Do not commit that edit (`.env` is gitignored; the script is not).
2. AWS Console > **EC2** > **Launch instance**:
   - Name: `ninetyninety`
   - AMI: **Amazon Linux 2023** (x86_64, the default quick-start image)
   - Instance type: **t3.small** (2 GB RAM; t3.micro swaps during the pip install)
   - Key pair: create or pick one if you want SSH; otherwise choose "Proceed without a
     key pair" and use **Connect > Session Manager** later
   - Network settings > Firewall: **Create security group**, tick **Allow HTTP traffic
     from the internet** (TCP 80, 0.0.0.0/0). Tick **Allow SSH** only from *My IP*.
   - Storage: the default 8 GB gp3 is enough
   - **Advanced details** > scroll to **User data**: paste the edited script
3. **Launch instance**. It is reachable about 4 to 6 minutes after the state shows
   *Running* (the pip install is most of that). Open `http://<Public IPv4 address>`.

### Check

```
sudo tail -f /var/log/cloud-init-output.log      # the install, line by line
sudo systemctl status ninetyninety               # active (running)
sudo journalctl -u ninetyninety -f               # Streamlit's own log
curl -sI http://localhost | head -1              # HTTP/1.1 200 OK
```

If the key was left as the placeholder, the app starts but every run fails with the
"set GOOGLE_API_KEY" message. Fix: `sudo nano /opt/ninetyninety/.env`, then
`sudo systemctl restart ninetyninety`.

### Update after a push

```
sudo -u ninetyninety git -C /opt/ninetyninety pull
sudo -u ninetyninety /opt/ninetyninety/.venv/bin/pip install -r /opt/ninetyninety/requirements.txt
sudo systemctl restart ninetyninety
```

### Keep the URL, keep the credit

- The public IP changes every time the instance is stopped and started. If the URL is
  already in `index.html` and the README, either never stop it before judging or attach
  an **Elastic IP** (free while attached to a running instance) and use that instead.
- HTTP only. Browsers show "Not secure" but the app works; TLS would need a domain and
  a reverse proxy, which the demo does not need.
- Stop (or terminate) the instance after results are announced. t3.small is roughly $15
  a month if left running.

## After deploy: checklist

Do these in order, then commit and push once.

1. `index.html` line 357: set the URL.

   ```js
   const STREAMLIT_URL = 'https://ninetyninety.streamlit.app';   // or http://<elastic-ip>
   ```

   The page rewrites both "Draft a return" buttons and the footer link from this one
   constant; nothing else in the HTML changes.
2. `python scripts/build_landing.py` re-injects the recorded run into `index.html` and
   `technical.html`. It leaves the constant alone; run it so the two pages are rebuilt
   from the same state you are about to push.
3. `README.md` line 65: replace "The Streamlit app is not hosted yet; run it locally
   with `streamlit run app.py`." with the live link, for example
   "Hosted app: **https://ninetyninety.streamlit.app** (also runs locally with
   `streamlit run app.py`)."
4. **Only if EC2 is the host:** in `scripts/diagram.py` add the bullet
   `"Hosted on Amazon EC2 (t3.small, Amazon Linux 2023)"` to the first `BOXES` entry
   ("User input / interface"), then `python scripts/diagram.py` to regenerate
   `docs/architecture.png` (needs Playwright's Chromium: `python -m playwright install
   chromium`). Run `python -m pytest tests/test_diagram.py` afterwards. Do not add the
   bullet for a Community Cloud deploy; the diagram must not claim an AWS service that
   is not in use.
5. `python -m pytest` (the landing-page tests check for stray dashes and the run
   numbers).
6. Commit and push:

   ```
   git add index.html technical.html README.md scripts/diagram.py docs/architecture.png
   git commit -m "docs: hosted app URL"
   git push
   ```

   GitHub Pages publishes the new `index.html` within a minute or two; open
   https://ishal1410.github.io/ninetyninety/ and click "Draft a return" to confirm it
   lands on the hosted app.
