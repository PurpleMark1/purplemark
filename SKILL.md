---
name: purplemark-skill
description: 使用 PurpleMark 桌面端本地 API 管理浏览器环境、环境分组与代理；适用于查询、创建、启动、停止或删除本机 PurpleMark 对象，或获取自动化调试连接。
---

# PurpleMark Local API

通过 `scripts/local_api.py` 操作 PurpleMark 桌面端。调用必须可复现，且不得暴露 Local API Key。

## 前提条件

1. 必须与 PurpleMark 桌面端运行在同一台机器；Local API 仅监听回环地址。
2. 确认桌面端已启动，并登录到正确的账号或团队。
3. 认证接口从环境变量 `PURPLEMARK_API_KEY` 读取 Key。仅将其作为当前进程的临时环境变量使用，绝不在聊天、命令参数、文件或仓库中明文记录。
4. Local API 根地址默认是 `http://127.0.0.1:39520`；如需覆盖，使用 `PURPLEMARK_LOCAL_API_URL`，且只能指向回环地址。

## 工作流

1. 首次操作前运行健康检查：

   ```powershell
   python scripts/local_api.py health
   ```

2. 按任务读取 [references/local-api.md](references/local-api.md) 中对应的章节。较长的参考文档应按端点或标题搜索，而非全部加载：

   ```powershell
   rg -n "profile/start|^## 浏览器环境" references/local-api.md
   ```

3. 环境运行状态操作优先使用快捷命令；其他接口使用 `request` 子命令。
4. 同时检查 HTTP 状态、`code`、`msg` 和 `data`。非 2xx HTTP 状态或非零 `code` 均视为失败。
5. 对现有对象，先执行列表或状态查询，确认标识后再变更。环境可使用 `profile_id` 或 `profile_no`；环境分组使用 `group_id`；代理和代理分组分别使用 `proxy_no`、`group_no`。
6. 结果中不得回显 API Key、Authorization 头、完整 Cookie 或代理密码。

## 环境运行快捷命令

每次仅提供一个环境标识：`--profile-id` 或 `--profile-no`。

```powershell
# 启动环境
python scripts/local_api.py profile-start --profile-no 7

# 查询环境状态
python scripts/local_api.py profile-status --profile-id "<profile-id>"

# 停止环境
python scripts/local_api.py profile-stop --profile-no 7
```

启动成功后，直接使用响应中的 `data.ws.puppeteer` 作为 Puppeteer 的 `browserWSEndpoint`，使用 `data.ws.selenium` 作为 Selenium 的调试地址。也可读取返回的 `debug_port`、`webdriver` 或 `webdriver_info`；不得自行猜测或拼接连接地址。

## 通用请求

`request` 只允许访问 `/api/v1/` 下的路径，查询参数必须使用重复的 `--query` 传入。长请求体、含敏感字段的请求体，或 PowerShell 中容易产生转义歧义的 JSON，必须使用 UTF-8 JSON 文件；临时文件存放在 `/temp` 下，并在操作后清理。

```powershell
# 列出环境
python scripts/local_api.py request GET /api/v1/profile/list --query page=1 --query page_size=20

# 列出代理
python scripts/local_api.py request GET /api/v1/proxy/list --query page=1 --query page_size=20

# 从 JSON 文件创建环境
python scripts/local_api.py request POST /api/v1/profile/create --json-file /temp/profile-create.json
```

## 安全与错误处理

- 创建、更新、启动、停止和删除均须有用户明确授权。删除操作前确认确切的 ID 或编号，不得仅凭名称推断目标。
- 不要将 API Key 传给非回环地址，也不要通过 `--json`、`--query`、用户文件或输出传递或记录它。
- `401`：检查当前进程是否设置了 `PURPLEMARK_API_KEY`，但不要要求用户在聊天中粘贴 Key。
- `400`：核对请求字段和对象标识；`404`：核对路径、方法、目标 ID 与桌面端运行状态。
- 连接失败：请用户启动或重启 PurpleMark 桌面端。其他失败：概述操作和返回的错误码，不泄露敏感数据。
