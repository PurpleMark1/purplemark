# PurpleMark 本地 API 参考

## 基本约定

- 根地址：`http://127.0.0.1:39520`，仅监听本机回环地址。
- API Key：在本地 API 安全设置启用后，发送 `Authorization: Bearer <api-key>`。
- 成功响应：`{"code":0,"msg":"success","data":{...}}`。必须同时检查 HTTP 状态和 `code`。
- 请求 JSON 使用 `Content-Type: application/json`。
- 常见错误：`40000` 参数错误，`40001` JSON 无效，`40100` 未提供 Key，`40101` Key 无效，`40400` 路径不存在，`40500` 方法不正确，`50000` 内部错误。

## 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/healthz` | 确认本地 API 服务可用，并返回 API 安全配置状态。 |

## 环境分组

| 方法 | 路径 | 参数或请求体 |
| --- | --- | --- |
| GET | `/api/v1/profile/group/list?page=1&page_size=20` | 分页查询环境分组。 |
| POST | `/api/v1/profile/group/create` | `{"group_name":"<name>","remark":"<optional>"}` |
| POST | `/api/v1/profile/group/delete` | `{"group_id":123}` |

环境分组主键为数字 `group_id`。创建环境时，使用该字段，不使用代理分组的 `group_no`。

## 浏览器环境

| 方法 | 路径 | 参数或请求体 |
| --- | --- | --- |
| GET | `/api/v1/profile/list` | 可选 `profile_id`、`profile_no`、`group_id`、`page`、`page_size`。 |
| POST | `/api/v1/profile/create` | 创建环境，见下例。 |
| GET | `/api/v1/profile/status` | 必填其一：`profile_id` 或 `profile_no`。 |
| POST | `/api/v1/profile/start` | 必填其一：`profile_id` 或 `profile_no`。 |
| POST | `/api/v1/profile/stop` | 必填其一：`profile_id` 或 `profile_no`。 |
| POST | `/api/v1/profile/delete` | 必填其一：`profile_id` 或 `profile_no`。活动环境会先停止。 |

创建无代理环境：

```json
{
  "basic_set": {
    "profile_name": "Automation profile",
    "group_id": 123,
    "open_fixed_webpage": "https://example.com",
    "proxy_setting": { "mode": "no_proxy" },
    "bind_account": []
  },
  "cookies": "",
  "ui_state": {},
  "fingerprint_set": {},
  "advanced_set": {}
}
```

`proxy_setting.mode` 仅可为 `no_proxy`、`custom_proxy` 或 `existing_proxy`。后两者都必须提供数字 `id`，该 ID 是现有代理的内部记录 ID；先从代理列表响应中读取它。启动成功后，响应包含 `ws.puppeteer`、`ws.selenium`、`debug_port`、`webdriver` 和 `webdriver_info`，应直接使用这些返回值。

## 代理分组与代理

| 方法 | 路径 | 参数或请求体 |
| --- | --- | --- |
| GET | `/api/v1/proxy/group/list?page=1&page_size=20` | 分页查询代理分组。 |
| POST | `/api/v1/proxy/group/create` | `{"group_name":"<name>","remark":"<optional>"}` |
| POST | `/api/v1/proxy/group/delete` | `{"group_no":123}` |
| GET | `/api/v1/proxy/list` | 可选 `proxy_no`、`group_no`、`page`、`page_size`。 |
| POST | `/api/v1/proxy/create` | 创建代理，见下例。 |
| POST | `/api/v1/proxy/update` | 必填 `proxy_no`，再提供至少一个可变字段。 |
| POST | `/api/v1/proxy/delete` | `{"proxy_no":123}` |

创建 SOCKS5 代理：

```json
{
  "proxy_name": "Example SOCKS5",
  "group_no": 123,
  "ip": "203.0.113.10",
  "port": "1080",
  "type": "SOCKS5",
  "username": "<optional>",
  "password": "<optional>"
}
```

代理类型仅可为 `SOCKS5`、`HTTP` 或 `HTTPS`。更新可改 `proxy_name`、`group_no`、`ip`、`port`、`type`、`username`、`password`；将 `group_no` 设为 `0` 可移出分组。代理 API 的外部标识为数字 `proxy_no`，代理分组的外部标识为数字 `group_no`。

## 安全与执行建议

1. 列表和状态查询可以直接执行；创建、更新、停止、删除必须有用户明确指示。
2. 不输出完整 Cookie、代理密码或 API Key；命令示例使用占位符。
3. API 只供当前机器调用。远程控制应通过受控自动化通道连接启动响应中的 WebSocket，而不是暴露本地 API 端口。
