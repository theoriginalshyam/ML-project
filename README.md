# AlgoFlux

AlgoFlux is a full-stack ensemble trading review platform. It combines:

- a React client for the user experience
- a Node/Express backend for auth, user state, and API orchestration
- a Flask ML service that serves inference from pre-trained RL agents

The platform is inference-only. It does not train models inside the website. Instead, it loads trained ensemble artifacts, produces daily trading recommendations, and lets each user compare their own decisions against the model's untouched run.

## Local Setup

### Requirements

- Node.js
- Python
- MongoDB

### Backend Setup

In `Backend/.env`, make sure these values exist:

```env
NODE_ENV=development
PORT=5000
MONGODB_URL=...
JWT_SECRET=...
JWT_ACCESS_EXPIRATION_MINUTES=30
JWT_REFRESH_EXPIRATION_DAYS=30
JWT_RESET_PASSWORD_EXPIRATION_MINUTES=10
JWT_VERIFY_EMAIL_EXPIRATION_MINUTES=10
SERVER_SECRET=your-secret-key
ML_SERVICE_URL=http://127.0.0.1:6969
```

Install dependencies:

```powershell
cd Backend
npm install
```

### Client Setup

Install dependencies:

```powershell
cd Client
npm install
```

### ML Service Setup

Create a Python environment inside `ML_Models`, install the current `requirements.txt`, and place the trained artifacts under `ML_Models/output/`.

Then bootstrap the runtime state if needed:

```powershell
cd ML_Models
.\venv\Scripts\python.exe bootstrap_state.py
```

## How To Run Locally

Start the ML service first:

```powershell
cd ML_Models
.\venv\Scripts\python.exe app.py
```

Start the backend next:

```powershell
cd Backend
npm run dev
```

Start the client last:

```powershell
cd Client
npm start
```

Default local URLs:

- client: `http://localhost:3000`
- backend: `http://localhost:5000`
- ML service: `http://127.0.0.1:6969`

## What The Website Does Now

After login, the website behaves like a trading decision-support workspace.

### Dashboard

The dashboard shows the model's current operating context:

- active agent
- detected market regime
- VIX
- sentiment
- 10Y yield
- model portfolio value
- user portfolio status

It also tells the user whether today's recommendation set still needs review.

### Recommendations

This is the main action page.

The app pulls the current ensemble recommendation set from the ML service and shows one row per tracked stock with:

- ticker
- price
- signal (`BUY`, `SELL`, `HOLD`)
- conviction
- model suggested shares
- user editable shares
- estimated trade cost
- currently held shares

Users can:

- accept the model suggestion as-is
- override the number of shares for any stock
- skip the day entirely
- confirm the day once they are satisfied

Confirmed decisions are stored in MongoDB as that user's own portfolio history.

### My Portfolio

This page compares the user portfolio against the model portfolio.

It shows:

- user portfolio metrics
- model portfolio metrics
- a comparison line chart
- follow rate versus override rate
- the user's trade history

### History

This page explains how the ensemble behaved over time.

It shows:

- monthly regime selection log
- chosen agent for each month
- per-agent Sharpe snapshot
- macro context such as VIX and sentiment

### About / Learn / News

- `About` explains the current ensemble workflow and the user/model relationship.
- `Learn` is now a structured learning surface with curated study tracks, books, videos, and market references.
- `News` is a business-news page inside the same app shell.

## System Architecture

### Client

The React app lives in `Client/`.

Important routes:

- `/home`
- `/recommendations`
- `/portfolio`
- `/history`
- `/about`
- `/learn`
- `/news`

The client talks only to the Express backend.

### Backend

The Express app lives in `Backend/`.

Its responsibilities are:

- JWT auth
- protected routes
- user portfolio persistence in MongoDB
- proxying requests to the ML service
- enriching model recommendations with user cash and holdings

Important route groups:

- `/v1/auth`
- `/v1/users`
- `/v1/ensemble`
- `/v1/portfolio`

`/v1/ensemble/*` forwards model-related requests to Flask.

`/v1/portfolio/*` stores and evaluates what the user actually chose to do.

### ML Service

The Flask app lives in `ML_Models/`.

It exposes inference-only ensemble endpoints:

- `POST /ensemble/status`
- `POST /ensemble/recommendations`
- `POST /ensemble/portfolio`
- `POST /ensemble/simulate`
- `POST /ensemble/run-day`
- `POST /ensemble/bootstrap`

The service expects a shared `Token` header from the backend using `SERVER_SECRET`.

The `/model` route is disabled in this installation.

## Required ML Artifacts

The ML service expects an `ML_Models/output/` directory with at least:

- `agents/TQC.zip`
- `agents/CrossQ.zip`
- `agents/TD3.zip`
- `agents/RPPO.zip`
- `state.json`

Optional but supported:

- `gating_net.pt`
- `gating_dataset.json`
- `sentiment_cache.parquet`

The website does not generate the agent `.zip` files. Those come from your external training pipeline.

## State And Runtime Model

`state.json` is the ML runtime snapshot used by the website.

It stores things like:

- current trade date
- active agent
- regime
- macro context
- model cash
- model holdings
- model equity curve
- trade dates
- selection log
- last recommendation snapshot

`bootstrap_state.py` initializes that file from your trained artifacts and downloaded market data.

After bootstrap, `run-day` is the path that advances the saved ML state.

## Current Product Flow

1. A user logs in through the React client.
2. The dashboard asks the backend for current ensemble status and the user's simulated portfolio.
3. The backend calls the Flask service for model status and portfolio data.
4. On the recommendations page, the backend merges model suggestions with the user's stored holdings and remaining cash.
5. When the user confirms a day, their chosen trades are written to MongoDB.
6. The portfolio page simulates those stored user trades against market history and compares them with the model curve.
7. The history page explains how the ensemble selected agents through time.

## Group Members

| S.No. | Name                 | Enrollment no |
| ----: | -------------------- | ------------- |
| 1.    | Gitanjala Srivardhan | 23114028      |
| 2.    | Arjun Ganesh         | 23114009      |
| 3.    | Krishna Pahariya     | 23113089      |
| 4.    | Shyam Agarwal        | 23116089      |
