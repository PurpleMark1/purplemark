---
name: purplemark-local-api
description: 使用 PurpleMark 本地 API 管理浏览器环境、环境分组、代理和代理分组，并启动、停止或查询环境状态。适用于用户要求自动化操作本机 PurpleMark 应用、获取浏览器调试连接或维护本机代理配置时。
---

# PurpleMark Local API

通过 `http://127.0.0.1:39520` 调用正在运行的 PurpleMark 桌面应用。此 API 只监听本机回环地址；先确认应用已启动并完成登录。

## 操作流程

1. 先运行健康检查：

   ```powershell
   python scripts/local_api.py /api/v1/healthz
   ```

2. 如果返回 `401`，要求用户在应用的本地 API 设置中提供 API Key，并通过环境变量传入，避免将密钥写入命令历史、文件或回复：

   ```powershell
   $env:PURPLEMARK_API_KEY = '<api-key>'
   ```

3. 对现有对象先执行列表或状态查询，确认目标 ID 后再变更。环境优先使用 `profile_id`；代理使用 `proxy_no`；环境分组使用 `group_id`；代理分组使用 `group_no`。

4. 仅在用户明确授权时创建、更新、停止或删除。删除环境前，确认其 ID；运行中的环境由删除接口自动停止。

5. 启动环境后，从响应的 `ws.puppeteer`、`ws.selenium` 或 `debug_port` 取得自动化连接信息。不要猜测或自行拼接调试端口。

## 调用方式

使用随附脚本发送 JSON 请求。它默认读取以下环境变量：

- `PURPLEMARK_LOCAL_API_URL`：API 根地址，默认 `http://127.0.0.1:39520`
- `PURPLEMARK_API_KEY`：可选的本地 API Key

GET 示例：

```powershell
python scripts/local_api.py "/api/v1/profile/list?page=1&page_size=20"
```

POST 示例：

```powershell
python scripts/local_api.py /api/v1/profile/start --method POST --data '{"profile_id":"<profile-id>"}'
```

对于复杂请求，将 JSON 放入临时文件并用 `--data-file` 传入；不要把账号、Cookie、代理密码或 API Key 提交到仓库。

## 常用任务

- 环境和环境分组：读取 [references/local-api.md](references/local-api.md) 的“环境”部分。
- 代理和代理分组：读取 [references/local-api.md](references/local-api.md) 的“代理”部分。
- 参数、返回结构、错误码和完整示例：读取 [references/local-api.md](references/local-api.md)。

## 结果处理

将 HTTP 成功和业务成功分开判断：响应中的 `code: 0` 才表示操作成功。遇到 `401` 时处理 API Key；遇到 `400` 时核对字段与对象标识；遇到 `404` 时核对路径、方法和本机应用是否已启动。脚本会保留服务返回的 JSON 并在失败时以非零状态退出。
