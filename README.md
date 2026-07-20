# GPU Index

Fetch GPU rental prices from [RunPod](https://www.runpod.io/) and [Vast.ai](https://vast.ai/), normalize them, and store time-series snapshots in a [Neon](https://neon.tech/) PostgreSQL database.

## Features

- **RunPod**: GraphQL `gpuTypes` query for secure, community, and spot pricing
- **Vast.ai**: REST marketplace search with per-GPU minimum on-demand and interruptible prices
- **Neon PostgreSQL**: GPU catalog + timestamped price snapshots with JSONB raw payloads
- **Scheduler**: Built-in interval fetching (default every 1 hour)

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure environment

Copy the example env file and add your keys:

```bash
cp .env.example .env
```

| Variable | Where to get it |
|----------|-----------------|
| `RUNPOD_API_KEY` | [RunPod console settings](https://www.runpod.io/console/user/settings) |
| `VAST_API_KEY` | [Vast.ai keys page](https://cloud.vast.ai/manage-keys/) |
| `DATABASE_URL` | [Neon console](https://console.neon.tech/) — connection string with `?sslmode=require` |

Optional settings:

```
FETCH_INTERVAL_HOURS=1
```

Example Neon connection string:

```
DATABASE_URL=postgresql://user:password@ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### 3. Initialize the database

```bash
python -m gpu_index init-db
```

This creates the `gpu_models` and `price_snapshots` tables in your Neon database.

## Usage

```bash
# One-shot fetch
python -m gpu_index fetch

# View latest prices
python -m gpu_index list --latest

# Start scheduled fetching (immediate fetch + repeat every N hours)
python -m gpu_index run
```

Or use the installed script:

```bash
gpu-index fetch
gpu-index list --latest
gpu-index run
```

## Web Dashboard

A React-based web dashboard is available to visualize GPU prices with charts and comparisons.

### Starting the Dashboard

1. Start the FastAPI backend server:
```bash
python -m gpu_index serve
```

2. In a separate terminal, start the React frontend:
```bash
cd index-fe
npm install
npm run dev
```

3. Open your browser to `http://localhost:5173`

### Dashboard Features

- **Dashboard View**: Shows all verified GPU models with mini price charts
- **Comparison View**: Side-by-side price comparison between RunPod and Vast.ai
- **Price History**: Click any GPU card to view historical price trends
- **Verified GPU Filter**: Automatically filters out unverified Vast.ai GPU models

### Verified GPU List

The dashboard focuses on these verified GPU models:
- NVIDIA: H100, A100, A6000, A5000, A4000, A40, RTX 4090/4080/4070, RTX 3090/3080/3070, RTX 6000, L40, L40S, V100
- AMD: MI300X, MI250X, MI210, MI200

## Database schema

**gpu_models** — GPU catalog per provider

| Column | Type | Description |
|--------|------|-------------|
| provider | TEXT | `runpod` or `vast` |
| gpu_id | TEXT | Provider GPU identifier |
| display_name | TEXT | Human-readable name |
| memory_gb | DOUBLE PRECISION | VRAM in GB |

**price_snapshots** — Time-series price records

| Column | Type | Description |
|--------|------|-------------|
| instance_type | TEXT | `secure`, `community`, `secure_spot`, `community_spot` (RunPod) or `ondemand`, `bid` (Vast.ai) |
| price_per_hour | DOUBLE PRECISION | USD per hour |
| stock_status | TEXT | RunPod availability or Vast.ai offer count |
| fetched_at | TIMESTAMPTZ | UTC timestamp |
| raw_json | JSONB | Full provider payload for debugging |

## Price normalization

| Provider | Instance types | Source |
|----------|---------------|--------|
| RunPod | secure, community, secure_spot, community_spot | Catalog list prices from `gpuTypes` |
| Vast.ai | ondemand, bid | Minimum `dph_total` per `gpu_name` across rentable offers |

## Error handling

Each provider is fetched independently — if one API fails, the other's data is still saved. Transient HTTP errors are retried once with a 30s timeout.
