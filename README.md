# Xkiro OpenAI Images Adapter

- [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

A lightweight FastAPI adapter that exposes [Xkiro](https://xkiro.com/) image generation and editing through synchronous, OpenAI Images API-shaped endpoints. It creates an asynchronous Xkiro job, polls it with backoff, and returns either a CDN URL or Base64 image bytes.

## Features

- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `GET /v1/models?modality=image` (passes the upstream model catalog through unchanged)
- `GET /health` (no authentication required)
- Separate client and upstream API keys
- OpenAI-style error responses
- Single-container Docker deployment

## Quick start with Docker

The image is published on Docker Hub as `rainbreath/xkiro-openai-images-adapter:latest`.

```bash
docker run --rm -p 5080:5080 \
  -e API_KEY=replace-me \
  -e XKIRO_API_KEY=your-xkiro-key \
  rainbreath/xkiro-openai-images-adapter:latest
```

The service listens on port `5080` by default.

## Quick start with Docker Compose

Copy `.env.example` to `.env`, replace both required keys, then start the service:

```bash
cp .env.example .env
docker compose up -d
```

The default Compose configuration publishes the service port on the host. Stop it with:

```bash
docker compose down
```

## Use only within an existing Docker network

To make the adapter available only to other containers on the same Docker network (for example, `new-api`), use the internal Compose file. Ensure the target network exists first; do not create it again if `new-api` already uses it:

```bash
docker network inspect new-api >/dev/null 2>&1 || docker network create new-api
docker compose -f docker-compose.internal.yaml up -d
```

The internal configuration reads `DOCKER_NETWORK` from `.env`, defaulting to `new-api`. If the existing network has another name, set it instead:

```env
DOCKER_NETWORK=your-existing-network
```

Other containers on that network can use this base URL:

```text
http://xkiro-openai-images-adapter:5080
```

Configure `new-api` with that URL and use the adapter's `API_KEY` as the Bearer key. This configuration has no `ports` mapping, so the service is not directly reachable through a host port or from outside the Docker network.

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
├── docker-compose.yaml            # Published image with host port mapping
├── docker-compose.internal.yaml   # Existing Docker network without port mapping
├── .env.example                   # Safe configuration template
├── .dockerignore                  # Files excluded from the image build context
├── .gitignore                     # Local secrets and generated files excluded from Git
├── pyproject.toml                 # Dependencies, build metadata, and test configuration
├── README.md                      # Primary English documentation
├── README.zh-CN.md                # Simplified Chinese documentation
└── README.ja.md                   # Japanese documentation
```

`app/main.py` is the runtime entry point. The generation and editing routes share `xkiro_client.py`, `poller.py`, and `response_builder.py`; this keeps upstream communication, job lifecycle handling, and OpenAI response conversion in one place. The Compose files load secrets and runtime options from `.env`; `docker-compose.yaml` publishes a host port, while `docker-compose.internal.yaml` joins an existing Docker network without publishing a port. `Dockerfile` remains available for building a custom image.

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
