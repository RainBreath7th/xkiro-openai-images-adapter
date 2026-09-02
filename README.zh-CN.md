# Xkiro OpenAI Images 适配器

[English](README.md) · [日本語](README.ja.md)

这是一个轻量的 FastAPI 适配服务，将 Xkiro 图片生成与编辑接口封装为同步的 OpenAI Images API 风格接口。服务内部创建 Xkiro 异步任务并按退避策略轮询，任务完成后返回 CDN URL 或 Base64 图片数据。

## 功能

- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `GET /v1/models?modality=image`（完整透传上游模型目录）
- `GET /health`（无需鉴权）
- 客户端 Key 与 Xkiro 上游 Key 分离
- OpenAI 风格错误响应
- 单容器 Docker 部署

## Docker 快速部署

镜像已发布至 Docker Hub：`rainbreath/xkiro-openai-images-adapter:latest`。

```bash
docker run --rm -p 5080:5080 \
  -e API_KEY=replace-me \
  -e XKIRO_API_KEY=your-xkiro-key \
  rainbreath/xkiro-openai-images-adapter:latest
```

服务默认监听 `5080` 端口。

## 使用 Docker Compose

将 `.env.example` 复制为 `.env`，替换两个必填 Key，然后启动服务：

```bash
cp .env.example .env
docker compose up -d
```

默认 Compose 配置会将服务端口发布到宿主机。停止服务：

```bash
docker compose down
```

## 仅供同一 Docker 网络内使用

如果适配器只供同一 Docker 网络中的其他容器（例如 `new-api`）使用，可以使用不发布宿主机端口的配置。先确保目标网络已经存在；如果 `new-api` 已经在该网络中，则无需重复创建：

```bash
docker network inspect new-api >/dev/null 2>&1 || docker network create new-api
docker compose -f docker-compose.internal.yaml up -d
```

内部配置从 `.env` 中读取 `DOCKER_NETWORK`，默认值为 `new-api`。若现有网络使用其他名称，请修改该变量：

```env
DOCKER_NETWORK=your-existing-network
```

同一网络中的其他容器可使用以下基础地址访问适配器：

```text
http://xkiro-openai-images-adapter:5080
```

例如，在 `new-api` 中将 OpenAI 兼容接口地址设置为上述地址，并将适配器的 `API_KEY` 作为 Bearer Key。该模式没有 `ports` 映射，因此宿主机和 Docker 网络外部无法直接通过端口访问服务。

## 配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `API_KEY` | 必填 | 客户端发送的 Bearer Key |
| `XKIRO_API_KEY` | 必填 | 服务访问 Xkiro 使用的 Bearer Key |
| `XKIRO_BASE_URL` | `https://api.xkiro.com` | Xkiro API 基础地址 |
| `PORT` | `5080` | HTTP 监听端口 |
| `UPSTREAM_TIMEOUT_SECONDS` | `300` | 单次请求创建、轮询和结果转换的最长时间 |
| `STRICT_PARAMETERS` | `false` | 是否拒绝而不是忽略不支持的参数 |
| `MAX_BODY_BYTES` | `10485760` | 请求体最大值（10 MiB） |
| `LOG_LEVEL` | `INFO` | 应用日志级别 |

## 项目目录结构

```text
xkiro-openai-images-adapter/
├── app/
│   ├── main.py                    # FastAPI 应用、路由、生命周期和请求体限制
│   ├── config.py                  # 从环境变量加载应用配置
│   ├── dependencies.py            # 客户端 Bearer 鉴权依赖
│   ├── exceptions.py              # OpenAI 风格错误模型与响应
│   └── services/
│       ├── xkiro_client.py        # Xkiro HTTP 客户端和上游错误处理
│       ├── poller.py              # 异步任务轮询与退避策略
│       ├── param_policy.py        # 支持字段透传和严格模式
│       ├── response_builder.py    # URL/Base64 图片响应转换
│       └── image_format.py        # JPEG/PNG/GIF/WebP 文件特征检测
├── tests/
│   ├── conftest.py                # 测试配置和共享 HTTP 客户端 fixture
│   ├── test_api.py                # 端点、鉴权、响应和 models 测试
│   └── test_image_format.py       # 图片特征检测测试
├── docker-compose.yaml            # 使用已发布镜像并发布宿主机端口
├── docker-compose.internal.yaml   # 仅加入现有 Docker 网络，不发布端口
├── .env.example                   # 安全的配置模板
├── .dockerignore                  # Docker 构建时排除的文件
├── .gitignore                     # Git 排除的本地密钥和生成文件
├── pyproject.toml                 # 依赖、构建信息和测试配置
├── README.md                      # 英文主文档
├── README.zh-CN.md                # 简体中文文档
└── README.ja.md                   # 日文文档
```

`app/main.py` 是运行入口。图片生成和编辑路由共享 `xkiro_client.py`、`poller.py` 与 `response_builder.py`，将上游通信、任务生命周期和 OpenAI 响应转换集中管理。两个 Compose 文件都从 `.env` 加载密钥和运行参数；`docker-compose.yaml` 发布宿主机端口，`docker-compose.internal.yaml` 加入现有 Docker 网络但不发布端口。`Dockerfile` 仍可用于构建自定义镜像。

## API 行为

适配器会保持 Xkiro 支持的字段和值不变，不会自动补充模型、改写 `n`、拆分请求或聚合多个任务。Xkiro 当前要求 `n=1`。

`response_format` 仅在本地处理，不会发送给上游：

- 默认值为 `url`，返回 Xkiro 合法的绝对 CDN URL。
- `b64_json` 会下载生成图片并将图片字节编码为 Base64。

生成和编辑接口会等待 Xkiro 任务完成。轮询从 2 秒后开始，间隔按 1.5 倍增长，最大为 10 秒。客户端断开连接时会取消进行中的请求。

编辑接口接收一个 multipart `image` 文件，支持 JPEG、PNG、GIF 和 WebP。Xkiro 文档没有定义多图或 `mask` 能力，因此适配器不会自行添加这些语义。默认忽略不支持的字段；设置 `STRICT_PARAMETERS=true` 后会返回 OpenAI 风格的 `400` 错误。

## 本地开发

```bash
python -m pip install -e ".[test]"
API_KEY=client-key XKIRO_API_KEY=upstream-key python -m uvicorn app.main:app --port 5080
python -m pytest -q
```

## 安全提示

`XKIRO_API_KEY` 只能保存在服务端，客户端只应获得 `API_KEY`。不要将任何 Key 提交到代码仓库。健康检查只表示适配器进程存活，不验证 Xkiro 连通性。
