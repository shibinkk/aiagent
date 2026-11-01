# 🤖 AI Job Search Agent

An autonomous AI-powered agent that searches for jobs across multiple platforms, scores them against your resume, generates tailored cover letters, auto-applies, and sends you daily summaries.

## ✨ Features

| Feature | Details |
|---------|---------|
| 🔍 **Multi-Platform Scraping** | LinkedIn, Indeed, Glassdoor, Naukri, Internshala |
| 🧠 **AI Scoring** | Ollama (local LLM) scores each job 0-100 against your resume |
| ✉️ **Cover Letters** | Auto-generates tailored cover letters per job |
| 🤖 **Auto Apply** | LinkedIn Easy Apply automation via Selenium |
| 📊 **Dashboard** | Web UI at `localhost:5000` with charts & analytics |
| 📬 **Notifications** | Telegram alerts + daily email digest |
| ✋ **Approval Queue** | Review jobs before applying (safety mode) |
| 🗄️ **Tracking** | SQLite DB tracks every job & application status |

---

## 🚀 Quick Start

### 1. Run Setup
```batch
setup.bat
```

### 2. Add Your Resume
```
resume\resume.pdf   ← Drop your CV here
```

### 3. Configure
Edit `.env` with your credentials:
```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
EMAIL_SENDER=...
EMAIL_PASSWORD=...
LINKEDIN_EMAIL=...
LINKEDIN_PASSWORD=...
```

Edit `config.yaml` to set your target roles and preferences.

### 4. Install Ollama (Free Local AI)
1. Download: https://ollama.com
2. Run: `ollama pull llama3`

### 5. Start the Agent
```batch
start_agent.bat
```

Open dashboard: **http://localhost:5000**

---

## 📁 Project Structure

```
Job_Search_Agent/
├── main.py                 # 🧠 Main orchestrator + scheduler
├── config.yaml             # ⚙️  Your preferences
├── .env                    # 🔐 Credentials (never commit this)
├── setup.bat               # 🛠️  One-click setup
├── start_agent.bat         # ▶️  Start agent
├── resume/
│   └── resume.pdf          # 📄 Your CV
├── scraper/                # Web scraping modules
├── filter/                 # Job filtering logic
├── ai_engine/              # Ollama AI scoring & generation
├── applicator/             # Auto-apply automation
├── tracker/                # SQLite database layer
├── notifier/               # Telegram + Email notifications
├── dashboard/              # Flask web dashboard
└── logs/                   # Log files
```

---

## ⚙️ Configuration Guide

### config.yaml — Key Settings

```yaml
job_search:
  roles: ["Software Engineer", "Product Manager"]
  relevance_threshold: 65    # Min AI score to consider applying

apply:
  auto_apply: false          # true = fully automatic
  require_approval: true     # true = you review before applying
  max_applications_per_day: 15

ai:
  model: "llama3"            # or mistral, gemma, etc.
```

### Getting a Telegram Bot
1. Message @BotFather on Telegram
2. Send `/newbot` → follow prompts → get token
3. Message @userinfobot to get your Chat ID

### Getting a Gmail App Password
1. Enable 2FA on your Google account
2. Go to: Google Account → Security → App Passwords
3. Create one for "Mail" → use that as `EMAIL_PASSWORD`

---

## 🔐 Safety Notes

> ⚠️ Auto-applying on LinkedIn/Indeed may violate their ToS. Start with `require_approval: true` and `auto_apply: false` to review each job first.

> ✅ Ollama runs 100% locally — your resume never leaves your machine.

> 💡 Set `max_applications_per_day: 15` to stay under rate limits.

---

## 📊 Dashboard Pages

| Page | URL | Description |
|------|-----|-------------|
| Overview | `/` | Stats, charts, recent jobs |
| All Jobs | `/jobs` | Browse & filter all discovered jobs |
| Approvals | `/approvals` | Review + approve/reject before applying |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `Ollama not available` | Run `ollama serve` in a terminal |
| No jobs found | Check your role keywords in config.yaml |
| Email not sending | Use Gmail App Password, not your real password |
| Telegram not working | Verify BOT_TOKEN and CHAT_ID in .env |
| LinkedIn apply fails | LinkedIn may require manual CAPTCHA; use approval mode |
