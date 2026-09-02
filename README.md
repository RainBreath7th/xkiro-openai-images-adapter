# Xkiro OpenAI Images Adapter

- [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

A lightweight FastAPI adapter that exposes Xkiro image generation and editing through synchronous, OpenAI Images API-shaped endpoints. It creates an asynchronous Xkiro job, polls it with backoff, and returns either a CDN URL or Base64 image bytes.

## Features

- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `GET /v1/models?modality=image` (passes the upstream model catalog through unchanged)
- `GET /health` (no authentication required)
- Separate client and upstream API keys
- OpenAI-style error responses
- Single-container Docker deployment

## Quick start with Docker

```bash
docker build -t xkiro-openai-images-adapter .
docker run --rm -p 5080:5080 \
  -e API_KEY=replace-me \
  -e XKIRO_API_KEY=your-xkiro-key \
  xkiro-openai-images-adapter
```

The service listens on port `5080` by default.

## Quick start with Docker Compose

Copy `.env.example` to `.env`, replace both required keys, then start the service:

```bash
cp .env.example .env
docker compose up --build -d
```

The Compose file publishes the configured `PORT` (default `5080`) and includes a health check. Stop it with:

```bash
docker compose down
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `API_KEY` | required | Bearer key accepted from clients |
| `XKIRO_API_KEY` | required | Bearer key used for Xkiro requests |
| `XKIRO_BASE_URL` | `https://api.xkiro.com` | Xkiro API base URL |
| `PORT` | `5080` | HTTP listening port |
| `UPSTREAM_TIMEOUT_SECONDS` | `300` | Maximum time spent creating, polling, and converting one image request |
| `STRICT_PARAMETERS` | `false` | Reject unsupported parameters instead of ignoring them |
| `MAX_BODY_BYTES` | `10485760` | Maximum request body size (10 MiB) |
| `LOG_LEVEL` | `INFO` | Application log level |

## Project structure

```text
xkiro-openai-images-adapter/
├── app/
│   ├── main.py                    # FastAPI application, routes, lifecycle, and body limits
│   ├── config.py                  # Environment-backed application settings
│   ├── dependencies.py            # Client Bearer authentication dependency
│   ├── exceptions.py              # OpenAI-style error model and responses
│   └── services/
│       ├── xkiro_client.py        # Xkiro HTTP client and upstream error handling
│       ├── poller.py              # Asynchronous job polling with backoff
│       ├── param_policy.py        # Supported-field forwarding and strict mode
│       ├── response_builder.py    # URL/Base64 OpenAI image response conversion
│       └── image_format.py        # JPEG/PNG/GIF/WebP signature detection
├── tests/
│   ├── conftest.py                # Shared test settings and HTTP client fixture
│   ├── test_api.py                # Endpoint, authentication, response, and models tests
│   └── test_image_format.py       # Image signature detection tests
├── Dockerfile                     # Minimal non-root production image
├── docker-compose.yaml            # One-command local/container deployment
├── .env.example                   # Safe configuration template
├── .dockerignore                  # Files excluded from the image build context
├── .gitignore                     # Local secrets and generated files excluded from Git
├── pyproject.toml                 # Dependencies, build metadata, and test configuration
├── README.md                      # Primary English documentation
├── README.zh-CN.md                # Simplified Chinese documentation
└── README.ja.md                   # Japanese documentation
```

`app/main.py` is the runtime entry point. The generation and editing routes share `xkiro_client.py`, `poller.py`, and `response_builder.py`; this keeps upstream communication, job lifecycle handling, and OpenAI response conversion in one place. `docker-compose.yaml` loads secrets and runtime options from `.env`, while `Dockerfile` is suitable for a direct image build.

## API behavior

The adapter keeps Xkiro-supported fields and values unchanged. It does not invent a model, rewrite `n`, split a request into multiple jobs, or aggregate jobs. Xkiro currently requires `n=1`.

`response_format` is handled locally and is not sent upstream:

- Defaults to `url` and returns Xkiro's valid absolute CDN URL.
- `b64_json` downloads the generated image and encodes its bytes as Base64.

The generations and edits endpoints wait for the Xkiro job to finish. Polling starts after two seconds, grows by 1.5x, and is capped at ten seconds. A client disconnect cancels the in-flight request.

Edits accept one multipart `image` file. JPEG, PNG, GIF, and WebP are supported. Xkiro's documentation does not define multi-image or `mask` support, so the adapter does not add those semantics. Unsupported fields are ignored by default; set `STRICT_PARAMETERS=true` to receive an OpenAI-style `400` error.

## Local development

```bash
python -m pip install -e ".[test]"
API_KEY=client-key XKIRO_API_KEY=upstream-key python -m uvicorn app.main:app --port 5080
python -m pytest -q
```

On Windows PowerShell, set the variables with `$env:API_KEY = "client-key"` and `$env:XKIRO_API_KEY = "upstream-key"` before starting the server.

## Security notes

Keep `XKIRO_API_KEY` server-side and give clients only `API_KEY`. Do not commit either key. The health endpoint only indicates that the adapter process is alive; it does not verify Xkiro connectivity.
