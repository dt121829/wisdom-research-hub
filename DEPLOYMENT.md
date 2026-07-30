# Publishing this app — step-by-step guide

Written for someone who has never used GitHub. Allow about 30 minutes the first time.

## How the pieces fit together

```
Your PC  ──push──>  GitHub  ──reads──>  Streamlit Cloud  ──>  https://your-app.streamlit.app
(the code)          (online copy)       (runs it)             (what staff open)
```

**GitHub** is online storage for code. **Streamlit Community Cloud** is a free service that
reads code from GitHub and runs it as a live website. You need GitHub because Streamlit Cloud
can only deploy from there.

Everything on your PC is already prepared: the repository is initialised, the source files
are staged, and `.gitignore` is protecting your API key and virtual environment from being
uploaded.

---

## Part 0 · Pre-flight check (2 min)

Run these from the project folder before you push. They catch the things that actually
break a first deploy.

**1 · Confirm your secrets are not about to be uploaded.**

```
git status --short
```

`.streamlit/secrets.toml` must NOT appear. Only `secrets.toml.example` should ever be
listed. If the real one shows up, stop and check `.gitignore`.

**2 · Confirm the deploy files exist.** Streamlit Cloud reads three files from the repo
root, all of which are already here:

| File | What it does |
|---|---|
| `requirements.txt` | Python packages to install |
| `packages.txt` | System packages — installs `fonts-noto-cjk` so Traditional Chinese PDFs render |
| `.streamlit/config.toml` | Theme and server settings |

**3 · Stage everything, including the newer modules.**

```
git add -A
git status --short
```

You should see `services/pdf.py`, `services/documents.py`, `services/chartspec.py`,
`packages.txt` and `data/logo.svg` among the files to be added.

### A note on fonts

Traditional Chinese PDFs need a CJK font. Locally the app uses one from
`C:\Windows\Fonts`, but **those fonts are licensed for use on Windows and must not be
published in a GitHub repository** — `.gitignore` therefore excludes
`data/fonts/kaiu.ttf` and friends. The deployed app installs the open-licensed
**Noto CJK** family instead, via `packages.txt`, and `services/pdf.py` searches for it
automatically. You do not need to do anything; just don't force-add the Windows fonts.

If you would rather bundle a font than rely on `packages.txt`, download
**Noto Sans TC** (SIL Open Font License, free to redistribute) from
<https://fonts.google.com/noto/specimen/Noto+Sans+TC>, drop the `.ttf` into
`data/fonts/`, and commit it — the app picks up anything in that folder first.

---

## Part 1 · Create a GitHub account (5 min)

1. Go to **https://github.com/signup**
2. Enter your email, choose a password, and pick a username.
   The username becomes part of your web address, so keep it professional —
   e.g. `wisdomfo` or `diego-tsai`.
3. Verify your email address (GitHub sends a code).
4. When asked about a plan, choose **Free**.

Write your username down — you need it in Part 2.

---

## Part 2 · Upload the code to GitHub

### Step A — tell Git who you are (one time only)

Git stamps your name on every saved version. Replace the name with yours:

```
cd C:\Users\user\.claude\sessions\wisdom-research-app
git config user.name "Your Name"
git config user.email "you@example.com"
```

### Step B — save a snapshot ("commit")

A commit is a saved checkpoint of your code. Nothing leaves your PC yet.

```
git commit -m "Wisdom Research Hub - initial version"
git branch -M main
```

The second line renames your branch to `main`, which is what GitHub expects.

You should see something like `18 files changed`. If Git complains *"Author identity unknown"*,
Step A didn't run — go back and do it.

### Step C — create an empty repository on GitHub

1. Go to **https://github.com/new**
2. **Repository name:** `wisdom-research-hub`
3. **Description:** optional
4. **Visibility:** choose **Private**. This is internal research tooling — private means only
   people you invite can see the code. (Streamlit Cloud can still deploy it; it will ask your
   permission to read private repositories when you connect.)
5. **Important:** leave *Add a README file*, *Add .gitignore*, and *Choose a license*
   all **unticked**. You already have those files, and ticking them causes a conflict.
6. Click **Create repository**.

You'll land on a page showing setup commands. You only need the address at the top, which
looks like `https://github.com/YOUR-USERNAME/wisdom-research-hub.git`

### Step D — connect and upload ("push")

Replace `YOUR-USERNAME` with your actual GitHub username:

```
git remote add origin https://github.com/YOUR-USERNAME/wisdom-research-hub.git
git push -u origin main
```

**A browser window will pop up asking you to sign in to GitHub.** Sign in and click
**Authorize**. This happens once — Git remembers you afterwards.

When it finishes, refresh your GitHub repository page. You should see all your files listed.
Confirm that **`secrets.toml` is NOT there** — only `secrets.toml.example` should appear.

---

## Part 3 · Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io**
2. Click **Continue with GitHub** and authorise the connection.
   If you made the repository private, approve access to private repositories when prompted.
3. Click **Create app** (may be labelled **New app**), then choose the option for deploying
   an app you already have on GitHub.
4. Fill in the three fields:
   - **Repository:** `YOUR-USERNAME/wisdom-research-hub`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Optionally set a custom subdomain — this becomes your web address.
6. **Before clicking Deploy**, open **Advanced settings** and find the **Secrets** box.
   Paste in the following, with your own values:

   ```toml
   AZURE_OPENAI_ENDPOINT   = "https://your-resource.openai.azure.com/"
   AZURE_OPENAI_API_KEY    = "your-azure-key"
   AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
   APP_PASSWORD            = "a-strong-shared-password"
   ```

   - The three `AZURE_OPENAI_*` values turn on Copilot for everyone. Find them in the Azure
     portal under your Azure OpenAI resource → **Keys and Endpoint**, plus the name you gave
     your model deployment under **Model deployments**.
   - `APP_PASSWORD` is the password staff type to get in. **Set this before sharing the link** —
     without it, anyone who has the URL can open the app.
7. Click **Deploy**. The first build takes 2–5 minutes while it installs the libraries.

When it's done you'll have a URL like `https://wisdom-research-hub.streamlit.app`.

---

## Part 4 · Give staff access

Send them the URL and the password — ideally through separate channels (e.g. URL by email,
password by message). On first visit they'll see the sign-in screen, enter the password, and
land on the dashboard.

To change the password later: open your app on share.streamlit.io → **Settings** → **Secrets**,
edit `APP_PASSWORD`, and save. The app restarts automatically.

---

## Part 5 · Updating the app later

Whenever you change the code, run these three commands. Streamlit Cloud notices the change and
redeploys within a minute or two — no need to touch the website.

```
git add -A
git commit -m "Describe what you changed"
git push
```

---

## Part 5b · Connecting Copilot (Azure OpenAI)

### Step 1 — create the Azure OpenAI resource

1. Sign in at **https://portal.azure.com**
2. **Create a resource** → search **Azure OpenAI** → **Create**
3. On the **Basics** tab:
   - **Subscription:** yours
   - **Resource group:** *Create new* → `wisdom-research`
   - **Region:** pick one near you that carries the model you want (East US and Sweden
     Central have the widest selection)
   - **Name:** e.g. `wisdom-openai` — this becomes part of your endpoint URL
   - **Pricing tier:** Standard S0
4. On the **Network** tab leave **All networks** selected. If you restrict networks here,
   Streamlit Cloud won't be able to reach it.
5. **Review + submit** → **Create**, then **Go to resource** when it finishes.

There is no longer a waitlist or access application for Azure OpenAI.

### Step 2 — deploy a model

A resource is just an empty container. Nothing works until a model is deployed into it.

**First check which portal you're in.** At <https://ai.azure.com> there is a **New Foundry**
toggle, and the menus differ completely between the two. Check the toggle before hunting for
menu items:

| | New Foundry (toggle ON) | Foundry classic (toggle OFF) |
|---|---|---|
| Deploy a model | **Discover** (top-right) → **Models** → pick model → **Deploy** | **Deployments** → **+ Deploy model** |
| See what you've deployed | **Build** (top-right) → **Models** | **Deployments** or **Models + endpoints** |

> There is no menu item called "Deployments" in the new portal. Your existing deployments
> live under **Build → Models**. Note that **Discover → Models** is a different list — that's
> the *catalogue* of models available to deploy, not what you actually have running.

To deploy in the new portal: **Discover** → **Models** → choose your model (e.g. `gpt-4o` or
`gpt-5-mini`) → **Deploy** → **Default settings** is fine. Azure suggests a deployment name
such as `gpt-5-mini-1`; you can accept or change it. Wait until the status reads *Succeeded*.

### Step 3 — copy the three values (all from the same place)

**Take all three from the deployment itself**, not from a resource you created separately:

**Build** → **Models** → click your deployment. Its detail page shows the **endpoint** and
**key** for the resource that deployment actually lives in.

- Endpoint → `AZURE_OPENAI_ENDPOINT` (base URL only, no path)
- Key → `AZURE_OPENAI_API_KEY`
- The deployment's **Name** → `AZURE_OPENAI_DEPLOYMENT`

> **The mistake that costs the most time:** pairing an endpoint from one resource with a
> deployment name from another. The new Foundry portal often creates its *own* resource and
> project, so a separate Azure OpenAI resource you made earlier in the Azure portal may sit
> empty while your model runs somewhere else entirely. The symptom is a
> `DeploymentNotFound` error even though your key is valid. Reading the endpoint, key and
> name off the one deployment page avoids this completely.

The endpoint may look like `https://<name>.services.ai.azure.com/` rather than
`https://<name>.openai.azure.com/`. Both are fine — the app handles either.

### Step 4 — put them in the app

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

```toml
AZURE_OPENAI_ENDPOINT   = "https://wisdom-openai.openai.azure.com/"
AZURE_OPENAI_API_KEY    = "your-key-1-value"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
```

`secrets.toml` is git-ignored, so it never reaches GitHub.

### Step 5 — verify before launching the app

```
.venv\Scripts\python.exe check_azure.py
```

This makes one tiny API call and tells you in plain English what's wrong if anything is:
a wrong key, a wrong deployment name, or an unreachable endpoint each produce a different
message. A pass looks like `SUCCESS — the model replied: 'connection ok'`.

### Step 6 — the deployed site

For the live site, don't upload `secrets.toml`. Paste the same three lines into
share.streamlit.io → your app → **Settings** → **Secrets**, alongside `APP_PASSWORD`. The
app restarts automatically.

### Cost

Everyone using the app shares this Azure billing. AI results are cached against the current
article set, so a new call happens only when the news actually changes, not on every page
refresh. Set a budget alert under **Cost Management + Billing** in the Azure portal if you
want a hard ceiling.

## Part 6 · Keeping the app awake

**Streamlit Community Cloud puts an app to sleep after 12 hours with no traffic.** For a tool
used on weekdays that means it will usually be asleep first thing each morning, and after
every weekend.

### Waking it manually

- **Anyone with the link** can wake it: the sleeping page shows a button reading
  *"Yes, get this app back up!"*. Click it and wait 30–90 seconds. Viewers can do this
  themselves — it doesn't have to be you.
- **You, as owner:** open the app on share.streamlit.io and use **Manage app → Reboot**.

### Waking it automatically (recommended)

This repository includes `.github/workflows/keep-awake.yml`, which visits the app every
6 hours using a real headless browser and clicks the wake button if it finds the app asleep.

To switch it on, after you've deployed and have your app's address:

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Open the **Variables** tab → **New repository variable**
3. Name: `APP_URL` — Value: your full address, e.g. `https://wisdom-research-hub.streamlit.app`
4. Save. It runs on schedule from then on. To test immediately, go to the **Actions** tab,
   pick **Keep app awake**, and click **Run workflow**.

**Why a real browser?** Ordinary uptime pingers (UptimeRobot, cron-job.org) do *not* work
here. Streamlit counts real browser sessions, not page fetches — the ping gets an HTTP 200
back while the app stays fast asleep. That's why this uses Playwright rather than a simple
scheduled URL request.

Two things to know: GitHub disables scheduled workflows in a repository with no activity for
60 days (any commit re-enables them), and on a private repository each run consumes a couple
of minutes from your free monthly Actions allowance — roughly 120–240 minutes a month here,
well inside the 2,000 included.

### Avoiding the problem entirely

Sleeping is a Community Cloud (free tier) behaviour. Hosting the app yourself on Azure App
Service, Google Cloud Run, or Fly.io with a warm minimum instance removes it altogether, at
the cost of a monthly hosting bill and a little more setup.

## Troubleshooting

**"Author identity unknown"**
Step A didn't run. Set `git config user.name` and `git config user.email`, then commit again.

**"remote origin already exists"**
You ran the `git remote add` line twice. Fix it with:
`git remote set-url origin https://github.com/YOUR-USERNAME/wisdom-research-hub.git`

**"Repository not found" or "Authentication failed"**
Usually a typo in the username or repository name. Check the address matches your GitHub page
exactly. If the browser sign-in never appeared, run `git config --global credential.helper manager`
and push again.

**"Updates were rejected because the remote contains work that you do not have"**
You ticked one of the "Add a README / .gitignore / license" boxes when creating the repository.
Easiest fix: delete the repository on GitHub (Settings → scroll to the bottom → Delete this
repository) and redo Step C with all boxes unticked.

**Streamlit shows an error page after deploying**
Click **Manage app** in the bottom-right to see the logs. The most common cause is a missing
entry in `requirements.txt`.

**Market data shows ⚪ sample instead of 🟢 live**
Yahoo Finance sometimes rate-limits shared cloud servers. The app deliberately falls back to
sample figures rather than showing stale numbers as if they were real. If this happens often
in production, switch to a paid market-data provider in `services/live_data.py`.

**Chinese characters show as boxes in a downloaded PDF**
The CJK font did not install. Check that `packages.txt` exists in the repository root and
contains `fonts-noto-cjk`, then reboot the app from **Manage app → Reboot** so the system
packages are reinstalled. English reports are unaffected.

**The Reports Library is empty after a restart**
Expected on Community Cloud: generated reports are written to `data/reports/` on the
server's disk, and that disk is wiped whenever the app restarts or goes to sleep. Download
anything you need to keep as PDF or Word at the time you generate it. Durable storage means
either hosting the app yourself (Part 6, "Avoiding the problem entirely") or writing reports
to external storage such as Azure Blob or S3 from `services/report_store.py`.

**"Error installing requirements" during the build**
Open **Manage app** and read the log. This is usually a package that has no Linux wheel for
the Python version Streamlit picked. You can pin the interpreter by adding a `.python-version`
file containing e.g. `3.12` to the repository root.

**The app went to sleep**
See "Part 6 · Keeping the app awake" below.

---

## Security reminders

- Never put your API key directly in a code file — only in Streamlit's Secrets box, or in a
  local `.streamlit/secrets.toml` (which `.gitignore` already excludes from uploads).
- If you ever accidentally publish an Azure key, **rotate it immediately**: Azure portal →
  your Azure OpenAI resource → **Keys and Endpoint** → **Regenerate Key 1**, then paste the
  new value into Streamlit Secrets. Deleting the commit is not enough — anything pushed to
  GitHub should be treated as compromised even after removal.
- Set `APP_PASSWORD` before sharing the link. A Community Cloud URL is reachable by anyone
  who has it.
- Everyone using the app shares the firm's Azure billing. Monitor spend under **Cost
  Management + Billing** in the Azure portal and set a budget alert if you want a ceiling.
  The vision features (reading screenshots and PDF pages) cost noticeably more per call than
  text, so watch those if usage grows.
