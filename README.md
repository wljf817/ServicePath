# ServicePath

ServicePath 是一个由 AI Agent 驱动的网站连通性诊断工具。输入公开的 HTTP(S) 地址后，它会按需检查本机网络、DNS、路由、TCP、TLS 与 HTTP，定位最早出现异常的网络层，并保存带证据和处理建议的报告。浏览器只提供界面，检查实际运行在 ServicePath 所在设备上。

## 功能

- 支持远程测试、本地测试，以及两端结果对比。
- 检查 A/AAAA 记录、`traceroute`、端口连接、证书、重定向和 HTTP 状态。
- Agent 只能调用受限的只读工具；目标、调用次数、响应大小和执行时间均有限制。
- 保存历史报告，并区分模型结论与服务端采集的证据。
- 拒绝私有、回环、链路本地和保留地址，并重新检查 DNS 结果与重定向目标。

结果分为可达、降级、不可达和不确定，并标注故障阶段与置信度。模型结论缺少证据支持时，系统会返回低置信度的不确定结果，同时保留已经采集的数据。

## 本地运行

需要 Python 3.10+ 和支持工具调用、结构化输出的模型 API；`traceroute` 只用于补充路由证据。仅修改前端时需要 Node.js。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中至少填写：

```dotenv
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5.6
```

```bash
python app.py
```

打开 `http://127.0.0.1:5050`。报告默认保存在 `instance/servicepath.db`。

## Docker 部署

先在 `.env` 中设置两个不同的强随机值：

```dotenv
SETTINGS_PASSWORD=replace_with_a_random_value
SERVICEPATH_API_TOKEN=replace_with_another_random_value
```

执行下面的命令两次，并将结果分别写入上述变量：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

然后启动：

```bash
docker compose up -d --build
docker compose ps
```

容器使用 Gunicorn、非 root 用户、只读根文件系统和健康检查。默认只发布到 `127.0.0.1:5050`。首次启动会把配置写入卷内的 `/data/.env`，之后以卷内设置为准；SQLite 报告位于 `/data/servicepath.db`，重建容器不会丢失。

健康检查地址为 `/healthz`；只有应用和数据库均可访问时才会返回正常状态。

```bash
docker compose logs -f servicepath
docker compose down
docker compose build --pull && docker compose up -d
```

`docker compose down -v` 会永久删除报告与设置。当前 SQLite 架构只支持单容器运行，不能横向扩容。

## 运行模式

- **Remote Test**：在远端实例检查，默认的 `remote_server` 角色使用此模式。
- **Local Test**：在当前设备检查；需要诊断本机网络路径时使用 `local_device`。
- **Compare Both**：依次执行远程和本地测试，再对比两端差异。

连接本地与远端实例时，两端应使用相同的 `SERVICEPATH_API_TOKEN`。

## 主要配置

| 变量 | 用途 |
| --- | --- |
| `OPENAI_API_KEY` | 模型服务密钥 |
| `OPENAI_MODEL` | 模型名称，默认 `gpt-5.6` |
| `OPENAI_BASE_URL` | 可选的兼容 API 地址 |
| `OPENAI_API_MODE` | `auto`、`responses` 或 `chat_completions` |
| `REMOTE_SERVICE_URL` | 远程 ServicePath 地址 |
| `SERVICEPATH_API_TOKEN` | 远程诊断接口令牌 |
| `SETTINGS_PASSWORD` | 设置页面写入密码 |

设置页面写入的密钥保存在权限为 `0600` 的 `.env` 中，现有密钥不会返回浏览器。诊断目标和选中的证据会发送给配置的模型服务商。

## 开发与测试

```bash
python -m unittest discover -s tests
npm ci
npm run dev
npm run build
```

前端开发地址为 `http://127.0.0.1:5173`；Vite 会把接口请求转发到 5050 端口。生产前端位于 `static/frontend/`，请通过 `npm run build` 更新，不要手动编辑。

自动化测试会模拟模型和公网边界，不需要真实 API 密钥或公共网站。

## 安全说明

ServicePath 会锁定目标，验证 DNS 结果和每次重定向，并拒绝私有、回环及保留地址，但它不是完整沙箱，仍存在 DNS rebinding 竞态。系统没有通用用户认证和内置限流；诊断会消耗模型额度，报告可能包含网络证据，目标与选中证据也会发送给配置的模型服务商。公网部署必须通过反向代理提供 HTTPS、身份认证、访问限制和至少五分钟的请求超时，并使用出站网络策略限制容器访问。
