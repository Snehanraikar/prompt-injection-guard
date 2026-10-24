# Running the Project in Google Colab: Step by Step

Everything runs in Google's cloud on a free GPU. Your computer only needs a web browser.

| Part | When | Time |
|---|---|---|
| A. One-time setup | once | about 10 min |
| B. Start the demo | before every presentation | about 10 min |
| C. Present | during the jury session | |
| D. Stop | afterwards | 1 min |
| E. Optional: retrain everything on the GPU | only if you want the full-test-set results | about 40 min |

---

## A. One-time setup

### A1. Put the project on GitHub
The project must be in a GitHub repository (private is recommended). Claude will push it for you once you provide:
- the repository URL, for example `https://github.com/<username>/prompt-injection-guard`
- the GitHub account's display name and e-mail (used as the commit author)

To create the repository:
1. Sign in at **https://github.com** with the account you want to use.
2. Click **+** (top right), then **New repository**.
3. Name it `prompt-injection-guard`, choose **Private**, and do **not** tick "Add a README".
4. Click **Create repository** and copy the URL shown.

### A2. Create a GitHub access token (needed because the repository is private)
1. On GitHub, click your **profile picture** (top right), then **Settings**.
2. In the left menu at the very bottom, click **Developer settings**, then **Personal access tokens**, then **Fine-grained tokens**.
3. Click **Generate new token** and fill in:
   - **Token name:** `colab-demo`
   - **Expiration:** 90 days (or until after your presentation)
   - **Repository access:** *Only select repositories*, then pick `prompt-injection-guard`
   - **Permissions → Repository permissions → Contents:** **Read-only**
4. Click **Generate token** and **copy it now** (it starts with `github_pat_…`). Save it in a password manager or a private note; GitHub shows it only once.

> Never paste the token into chats, slides or the notebook text. Only paste it into the Colab password prompt.

### A3. (Optional) Kaggle API key
The Kaggle datasets and models download without a key. A key is only useful if you also want Meta's gated *Prompt Guard* model when retraining (part E).
1. Sign in at **https://www.kaggle.com** and click your **profile picture**, then **Settings**.
2. Under **API**, click **Create New Token**. A file `kaggle.json` downloads; it contains your `username` and `key`.
3. Optional, for Prompt Guard: open https://www.kaggle.com/models/metaresearch/llama-3.1-prompt-guard and accept the licence.

---

## B. Start the demo (before every presentation)

### B1. Open Colab with a GPU
1. Go to **https://colab.research.google.com** and sign in with your Google account.
2. Click **New notebook**.
3. Click **Runtime → Change runtime type**, select **T4 GPU**, and click **Save**.
4. Click **Connect** (top right) and wait until it shows RAM/Disk bars.

### B2. Open the terminal
- Click the **Terminal** icon (`>_`) at the **bottom of the left sidebar**. A black terminal panel opens.
- No Terminal icon? Use **B2-alt** below instead.

### B3. Download the project
In the terminal, type (replace `<username>`):
```
git clone https://github.com/<username>/prompt-injection-guard.git proj
```
When asked:
- **Username:** your GitHub username
- **Password:** paste the **token** from A2. Right-click to paste; nothing is shown while you paste. Then press Enter.

### B4. Start everything
```
cd proj
bash cloud/start.sh
```
It asks:
- **Kaggle username:** press **Enter** to skip, or type it
- **Kaggle API key:** only asked if you typed a username

Then it runs six steps by itself. Watch for the `==== 1/6 … ====` to `==== 6/6 … ====` lines:

| Step | What happens | Time |
|---|---|---|
| 1/6 | installs Python packages, shows `GPU: Tesla T4` | about 2 min |
| 2/6 | downloads the tunnel tool for the public link | a few seconds |
| 3/6 | installs Ollama and downloads the LLM `qwen2.5:3b` (about 2 GB) | about 3 min |
| 4/6 | uses the trained models already in the repository | instant |
| 5/6 | downloads the two Kaggle detector models and warms up; prints `guard ready - test injection score: 1.0` | about 2 min |
| 6/6 | starts the app and prints the link | about 30 s |

At the end you see:
```
==================================================================
  DEMO IS LIVE:  https://something-random-words.trycloudflare.com
==================================================================
```

### B5. Open the demo
- Copy the `https://….trycloudflare.com` link into any browser: your laptop, the projector PC, even a phone.
- If it says *not found* or *502*, wait 20 seconds and refresh.
- Do the **warm-up run** and **rehearsal** from [JURY_DEMO_GUIDE.md](JURY_DEMO_GUIDE.md), section 0.

### B2-alt. No terminal? Use notebook cells instead
In your new notebook, create these 3 cells and run them one after another.

**Cell 1: credentials (typed into hidden fields):**
```python
import os, getpass
user = input("GitHub username: ")
token = getpass.getpass("GitHub token: ")
os.environ["REPO_URL"] = f"https://{user}:{token}@github.com/{user}/prompt-injection-guard.git"
os.environ["KAGGLE_USERNAME"] = input("Kaggle username (Enter to skip): ")
os.environ["KAGGLE_KEY"] = getpass.getpass("Kaggle key (Enter to skip): ") if os.environ["KAGGLE_USERNAME"] else ""
```
**Cell 2: download the project:**
```
!rm -rf /content/proj && git clone -q "$REPO_URL" /content/proj && ls /content/proj
```
**Cell 3: start everything** (prints the link at the end):
```
!cd /content/proj && bash cloud/start.sh
```
(The repository also contains `notebooks/colab_one_click.ipynb` with the same cells. Open it via **File → Open notebook → GitHub**, tick *Include private repos*, and pick the repository.)

---

## C. Present
Follow **[JURY_DEMO_GUIDE.md](JURY_DEMO_GUIDE.md)**: the four acts on *🎯 Live Attack Demo*, then *📡 Live Traffic Monitor*, then *📊 Results*.

Keep the Colab browser tab **open** during the whole presentation. Colab disconnects after about 90 min without activity and after at most 12 h.

---

## D. Stop
- In the terminal: `bash cloud/stop.sh`, **or**
- In Colab: **Runtime → Disconnect and delete runtime**. This frees the GPU, and the link stops working.

Nothing is saved in Colab. Next time, repeat part B (about 10 min).

---

## E. Optional: retrain everything on the GPU (full test set)
This is the same as B, but in B4 run:
```
bash cloud/start.sh --retrain
```
It downloads the Kaggle datasets, re-trains every model and scores the **full** test set (13,815 texts) with the Kaggle benchmark detectors, about 30–40 min on a T4. It then starts the demo with the new models.

The new numbers are in `proj/results/*.csv`. They only live in this Colab session. To keep them, download the folder (right-click it in the Colab **Files** panel and choose **Download**), or tell Claude the new numbers so the paper can be updated.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `GPU: none (CPU only)` in step 1/6 | You forgot B1.3. Choose **Runtime → Change runtime type → T4 GPU**, then start again from B3. |
| `Authentication failed` when cloning | Wrong username or token, or the token isn't allowed on this repository (A2.3). Create a new token. |
| "You cannot currently connect to a GPU" | The free GPU quota is used up for today. Try again later or with another Google account, or run `bash cloud/start.sh --no-llm` on CPU (the demo then uses ⚡ Fast replay). |
| Step 3/6 fails (Ollama) | Run `bash cloud/start.sh` again; downloads sometimes time out. Or use `--no-llm`. |
| No `DEMO IS LIVE` link | Run `grep trycloudflare logs/tunnel.log`. If it's empty, run `bash cloud/start.sh` again. |
| The link stopped working | Colab disconnected. Repeat part B; you'll get a new link. |
| App shows an error | Run `tail -50 logs/app.log` and send the output to Claude. |
