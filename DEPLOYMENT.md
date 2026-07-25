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

Everything on your PC is already prepared: the repository is initialised, all 18 source files
are staged, and `.gitignore` is protecting your API key and virtual environment from being
uploaded.

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
   ANTHROPIC_API_KEY = "sk-ant-your-real-key-here"
   APP_PASSWORD = "a-strong-shared-password"
   ```

   - `ANTHROPIC_API_KEY` turns on live Claude for everyone. Get one at
     **https://platform.claude.com** → Settings → API keys.
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

**The app is slow on first visit**
Free Streamlit apps sleep after a period of inactivity and take ~30 seconds to wake up.
Paid tiers stay awake.

---

## Security reminders

- Never put your API key directly in a code file — only in Streamlit's Secrets box, or in a
  local `.streamlit/secrets.toml` (which `.gitignore` already excludes from uploads).
- If you ever accidentally publish a key, revoke it immediately at platform.claude.com and
  generate a new one.
- Everyone using the app shares the firm's Anthropic billing. Monitor spend in the Anthropic
  console, and set a monthly limit there if you want a hard ceiling.
