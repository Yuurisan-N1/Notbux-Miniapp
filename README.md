<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=NotBux%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Check%20In%7CDaily%20Quests%7CAchievements%7CRewarded%20Ads%7CTasks%20and%20Referrals&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Full%20daily%20cycle%20automation%20for%20the%20NotBux%20Miniapp;Daily%20check%20in%20streak%20and%20quest%20board%20handled%20automatically;Achievements%20unlocked%20and%20claimed%20as%20soon%20as%20they%20qualify;Rewarded%20ad%20slots%20filled%20and%20verified%20against%20the%20server;Task%20list%20worked%20through%20with%20a%20confirmed%20balance%20per%20claim"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-NotBux%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>NotBux Bot</b> is a full automation bot for the NotBux Telegram Miniapp.<br/>
  It runs the complete daily cycle: sign in with referral binding, daily check in streak, quest board, achievements, the full task list, referral team summary and every rewarded ad slot, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Notbux-Miniapp.git
cd Notbux-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening NotBux on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Sign In and Referral Binding

Every account is signed in with its own stored credential, and the referral code configured for the project is sent along with the first read so a fresh account is bound to the team on its first cycle. The binding state is read back from the server and reported, never assumed.

### Daily Check In

The check in streak is claimed once per day. The reward is only reported after the coin balance on the server has actually moved, and the current streak day is read from the rewards board rather than tracked locally.

### Daily Quests

All three daily quests are inspected each cycle: reading the official channel, completing a task and inviting a friend. Quests that are already done on the server side are started and then claimed, and every claimed quest is confirmed against a fresh balance read.

### Achievements

The full achievement board is walked each cycle, covering task milestones, referral milestones and task creation milestones. Every achievement whose target is already reached is claimed automatically, and the ones that are not reached yet are left untouched for the next cycle.

### Tasks

Every task available to the account is worked through in order, covering channel tasks, group tasks and bot registration tasks. Each task is started and then verified, and the credited amount is taken from a balance difference read back from the server. Tasks that need a real channel join the account does not have, or that the server refuses for any other reason, are counted and summarised at the end of the phase instead of being retried in a loop.

### Rewarded Ads

Every rewarded ad provider on the board is worked through up to the daily slot limit. Each view is confirmed against the per provider counter on the server before anything is reported, so a view is only ever announced when the counter moved. Views that the ad network acknowledges without moving the counter are counted, and the phase stops after a few of those instead of spinning forever.

### Referral Team

The referral team summary is read each cycle and reported as the number of invited friends together with the total referral earnings for the project.

### Per Cycle Balance Report

At the end of every account the bot prints the net coin movement for that cycle, followed by a closing line with the final coin and TON balances read back from the server.

### Multi Account

All accounts in `data.txt` are processed sequentially within every cycle. Each account is separated by a blank line, and the cycle number is tracked and logged at the start of each round.

### Proxy Support

Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown

After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
NotBux-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
