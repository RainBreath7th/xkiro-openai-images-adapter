# Xkiro OpenAI Images アダプター

[English](README.md) · [简体中文](README.zh-CN.md)

[Xkiro](https://xkiro.com/) の画像生成・編集 API を、同期的な OpenAI Images API 形式のエンドポイントとして利用できる軽量な FastAPI アダプターです。内部で Xkiro の非同期ジョブを作成し、バックオフ付きでポーリングした後、CDN URL または Base64 画像データを返します。

## 機能

- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `GET /v1/models?modality=image`（上流のモデルカタログを完全に透過）
- `GET /health`（認証不要）
- クライアント用キーと Xkiro 用キーを分離
- OpenAI 形式のエラーレスポンス
- 1 コンテナでの Docker デプロイ

## Docker でクイックスタート

イメージは Docker Hub の `rainbreath/xkiro-openai-images-adapter:latest` として公開されています。

```bash
docker run --rm -p 5080:5080 \
  -e API_KEY=replace-me \
  -e XKIRO_API_KEY=your-xkiro-key \
  rainbreath/xkiro-openai-images-adapter:latest
```

既定の待受ポートは `5080` です。

## Docker Compose でクイックスタート

`.env.example` を `.env` にコピーし、必須キーを設定してから起動します。

```bash
cp .env.example .env
docker compose up -d
```

既定の Compose 設定では、サービスのポートをホストに公開します。停止するには次を実行します。

```bash
docker compose down
```

## 既存の Docker ネットワーク内だけで使用する

アダプターを `new-api` など同じ Docker ネットワーク内のコンテナだけから利用する場合は、内部用 Compose ファイルを使います。まず対象ネットワークを作成してください。`new-api` がすでにそのネットワークを使用している場合は、再作成する必要はありません。

```bash
docker network inspect new-api >/dev/null 2>&1 || docker network create new-api
docker compose -f docker-compose.internal.yaml up -d
```

内部設定は `.env` の `DOCKER_NETWORK` を読み込み、既定値は `new-api` です。ネットワーク名が異なる場合は変更してください。

```env
DOCKER_NETWORK=your-existing-network
```

同じネットワーク上の他のコンテナからは、次のベース URL でアクセスできます。

```text
http://xkiro-openai-images-adapter:5080
```

`new-api` にはこの URL を設定し、アダプターの `API_KEY` を Bearer キーとして使用してください。内部設定には `ports` マッピングがないため、ホストポートや Docker ネットワーク外から直接アクセスすることはできません。

## 設定

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `API_KEY` | 必須 | クライアントから受け付ける Bearer キー |
| `XKIRO_API_KEY` | 必須 | Xkiro へのリクエストに使う Bearer キー |
| `XKIRO_BASE_URL` | `https://api.xkiro.com` | Xkiro API のベース URL |
| `PORT` | `5080` | HTTP 待受ポート |
| `UPSTREAM_TIMEOUT_SECONDS` | `300` | 1 リクエストの作成・ポーリング・変換に使える最大時間 |
| `STRICT_PARAMETERS` | `false` | 未対応パラメータを無視せず拒否するかどうか |
| `MAX_BODY_BYTES` | `10485760` | リクエスト本文の最大サイズ（10 MiB） |
| `LOG_LEVEL` | `INFO` | アプリケーションのログレベル |

## プロジェクト構成

```text
xkiro-openai-images-adapter/
├── app/
│   ├── main.py                    # FastAPI アプリ、ルート、ライフサイクル、本文サイズ制限
│   ├── config.py                  # 環境変数から読み込む設定
│   ├── dependencies.py            # クライアント Bearer 認証の依存関係
│   ├── exceptions.py              # OpenAI 形式のエラーとレスポンス
│   └── services/
│       ├── xkiro_client.py        # Xkiro HTTP クライアントと上流エラー処理
│       ├── poller.py              # 非同期ジョブのバックオフ付きポーリング
│       ├── param_policy.py        # 対応フィールドの転送と strict モード
│       ├── response_builder.py    # URL/Base64 画像レスポンスへの変換
│       └── image_format.py        # JPEG/PNG/GIF/WebP のシグネチャ検出
├── tests/
│   ├── conftest.py                # テスト設定と共有 HTTP クライアント fixture
│   ├── test_api.py                # エンドポイント、認証、レスポンス、models のテスト
│   └── test_image_format.py       # 画像シグネチャ検出テスト
├── Dockerfile                     # 非 root ユーザーで動く軽量な本番イメージ
├── docker-compose.yaml            # 公開済みイメージとホストポート公開
├── docker-compose.internal.yaml   # 既存 Docker ネットワークのみ（ポート非公開）
├── .env.example                   # 安全な設定テンプレート
├── .dockerignore                  # Docker ビルドコンテキストから除外するファイル
├── .gitignore                     # ローカルキーと生成ファイルの Git 除外設定
├── pyproject.toml                 # 依存関係、ビルド、テスト設定
├── README.md                      # 英語のメインドキュメント
├── README.zh-CN.md                # 簡体字中国語ドキュメント
└── README.ja.md                   # 日本語ドキュメントンス
```

`app/main.py` が実行エントリーポイントです。生成と編集のルートは `xkiro_client.py`、`poller.py`、`response_builder.py` を共有し、上流通信、ジョブのライフサイクル、OpenAI レスポンス変換を一か所で管理します。2 つの Compose ファイルは `.env` からキーと実行設定を読み込みます。`docker-compose.yaml` はホストポートを公開し、`docker-compose.internal.yaml` は既存の Docker ネットワークに参加するだけでポートを公開しません。`Dockerfile` はカスタムイメージのビルドに利用できます。

## API の動作

Xkiro が対応するフィールドと値は変更せずに転送します。モデルの補完、`n` の書き換え、リクエストの分割、複数ジョブの集約は行いません。Xkiro は現在 `n=1` を要求します。

`response_format` はローカルで処理し、上流には送信しません。

- 既定値は `url` で、Xkiro の有効な絶対 CDN URL を返します。
- `b64_json` では生成画像をダウンロードし、画像バイトを Base64 に変換します。

生成・編集エンドポイントは Xkiro のジョブが完了するまで待機します。ポーリングは 2 秒後に開始し、間隔を 1.5 倍に伸ばし、最大 10 秒とします。クライアントが切断すると、進行中のリクエストをキャンセルします。

編集では multipart の `image` ファイルを 1 つ以上受け付け、アップロード順のまま全ファイルを Xkiro に転送します。対応形式は JPEG、PNG、GIF、WebP です。未対応フィールドは既定では無視され、`STRICT_PARAMETERS=true` の場合は OpenAI 形式の `400` エラーになります。

## ローカル開発

```bash
python -m pip install -e ".[test]"
API_KEY=client-key XKIRO_API_KEY=upstream-key python -m uvicorn app.main:app --port 5080
python -m pytest -q
```

## セキュリティに関する注意

`XKIRO_API_KEY` はサーバー側だけに保管し、クライアントには `API_KEY` のみを渡してください。キーをリポジトリにコミットしないでください。ヘルスチェックはアダプターのプロセスが生きていることだけを示し、Xkiro への接続性は確認しません。
