# Codex 完整 OAuth Token 导出到 Cockpit Tools 设计文档

## 1. 背景

当前项目在 GoPay/Stripe 支付成功后，已经会重新登录 OpenAI，并通过 Codex OAuth client 获取 `refresh_token`。

现状流程只保存了：

```text
refresh_token
```

存储位置：

```text
output/webui.db -> card_results.refresh_token
```

但 Cockpit Tools 的 Codex 账号导入功能要求至少具备：

```text
id_token + access_token
```

`refresh_token` 用于后续刷新，是长期可用性的关键字段，但单独一个 `refresh_token` 不足以被 Cockpit Tools 直接导入。

本功能目标是在支付成功后，获取并保存完整 Codex OAuth token response，生成 Cockpit Tools 可导入的 JSON。

---

## 2. 目标

### 2.1 功能目标

支付成功后自动完成以下流程：

```text
支付成功
→ 重新登录目标 OpenAI 账号
→ Codex OAuth 授权
→ 获取 id_token + access_token + refresh_token
→ 校验 token 属于本次支付账号
→ 保存完整 token 信息
→ WebUI 提供 Cockpit Tools JSON 导出
```

### 2.2 兼容目标

导出的 JSON 应能粘贴到 Cockpit Tools：

```text
Codex → 添加 Codex 账号 → Token / JSON
```

推荐导出格式：

```json
{
  "tokens": {
    "id_token": "...",
    "access_token": "...",
    "refresh_token": "..."
  },
  "last_refresh": "2026-05-06T00:00:00.000000Z"
}
```

### 2.3 非目标

本阶段不做：

- 自动调用 Cockpit Tools 导入接口；
- 自动启动 Cockpit Tools；
- API Key 账号导入；
- 第三方云端 token 同步；
- token 加密存储系统重构；
- 多账号批量导出 UI。

---

## 3. 当前事实与约束

### 3.1 当前项目已有能力

当前项目已经具备：

1. GoPay 支付流程；
2. WhatsApp OTP 自动/手动 relay；
3. Stripe poll 支付成功判断；
4. 支付成功后重新登录 OpenAI；
5. Codex OAuth authorize；
6. 捕获 `localhost:1455/auth/callback?code=...`；
7. POST `https://auth.openai.com/oauth/token`；
8. 保存 `refresh_token` 到 SQLite。

### 3.2 当前不足

当前 `/oauth/token` 响应中实际包含更多字段，但代码只取：

```text
refresh_token
```

需要改为保留完整 token response 中的：

```text
id_token
access_token
refresh_token
expires_in
scope
token_type
```

最小必需字段：

```text
id_token
access_token
refresh_token
```

---

## 4. Cockpit Tools 兼容性要求

Cockpit Tools 的 Codex 添加账号功能有四种路径：

| 路径 | 用途 | 本功能是否使用 |
|---|---|---|
| OAuth Authorization | Cockpit Tools 自己发起 OpenAI OAuth | 不直接使用，但要兼容其 token 格式 |
| Token / JSON | 导入 Codex token/auth.json | 使用 |
| API Key | OpenAI API Key 或兼容供应商 Key | 不使用 |
| 本地导入 | 从 `~/.codex/auth.json` 导入 | 可作为参考格式 |

Cockpit Tools Token / JSON 导入要求：

```text
id_token + access_token
```

`refresh_token` 可选但强烈建议提供。

支持的 JSON 格式包括：

### 4.1 顶层 token 格式

```json
{
  "id_token": "...",
  "access_token": "...",
  "refresh_token": "...",
  "account_id": "optional"
}
```

### 4.2 auth.json 格式

```json
{
  "tokens": {
    "id_token": "...",
    "access_token": "...",
    "refresh_token": "...",
    "account_id": "optional"
  },
  "last_refresh": "2026-05-06T00:00:00.000000Z"
}
```

本项目应导出 4.2 格式。

---

## 5. OAuth 参数要求

### 5.1 client_id

应继续使用 Codex OAuth client：

```text
app_EMoamEEZ73f0CkXaXp7hrann
```

这是当前项目和 Cockpit Tools 都使用的 Codex client。

### 5.2 redirect_uri

应继续使用：

```text
http://localhost:1455/auth/callback
```

当前项目通过浏览器 route 拦截该 callback，不依赖真实 HTTP server。

### 5.3 scope

当前项目 scope：

```text
openid email profile offline_access
```

Cockpit Tools scope：

```text
openid profile email offline_access api.connectors.read api.connectors.invoke
```

为最大兼容 Cockpit Tools，应调整为：

```text
openid profile email offline_access api.connectors.read api.connectors.invoke
```

原因：

- `offline_access`：确保返回 `refresh_token`；
- `openid/profile/email`：确保返回身份 token；
- `api.connectors.read/api.connectors.invoke`：对齐 Cockpit Tools/Codex 连接器权限。

---

## 6. 推荐数据流

```text
[GoPay/Stripe 支付成功]
        ↓
[验证 ChatGPT Plus 状态，可选但推荐]
        ↓
[读取本次账号 email/password/mail 配置]
        ↓
[重新登录 OpenAI]
        ↓
[打开 Codex OAuth authorize URL]
        ↓
[邮箱 OTP 验证]
        ↓
[Codex consent Continue]
        ↓
[捕获 callback code]
        ↓
[POST /oauth/token]
        ↓
[获得完整 token response]
        ↓
[校验 token email == chatgpt_email]
        ↓
[校验 refresh_token 可用，可选但推荐]
        ↓
[保存 token 到 SQLite]
        ↓
[WebUI 结果页提供复制/下载 Cockpit JSON]
```

---

## 7. 数据模型建议

### 7.1 推荐方案：新增表

推荐新增独立表，而不是继续扩展 `card_results`。

表名建议：

```text
codex_auth_tokens
```

字段建议：

```sql
CREATE TABLE IF NOT EXISTS codex_auth_tokens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_result_id INTEGER DEFAULT NULL,
  chatgpt_email TEXT NOT NULL COLLATE NOCASE,
  account_id TEXT DEFAULT '',
  id_token TEXT NOT NULL,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  scope TEXT DEFAULT '',
  token_type TEXT DEFAULT '',
  expires_at REAL DEFAULT 0,
  last_refresh TEXT DEFAULT '',
  auth_json TEXT NOT NULL,
  created_at REAL NOT NULL
);
```

### 7.2 为什么不只放 `card_results`

`card_results` 当前是支付结果表。完整 token 信息属于高敏感授权凭据，独立表更清晰：

- 更容易单独清理；
- 更容易做导出权限控制；
- 更容易后续加密；
- 避免支付结果列表默认带出敏感字段。

### 7.3 最小 MVP 方案

如果希望减少 schema 变更，也可以先在 `card_results` 增加：

```text
codex_auth_json
codex_token_scope
codex_token_expires_at
```

但长期不推荐。

---

## 8. Token 校验规则

### 8.1 必填校验

`/oauth/token` 返回后必须检查：

```text
id_token 非空
access_token 非空
refresh_token 非空
```

任何一个缺失，都不生成 Cockpit JSON。

### 8.2 账号一致性校验

必须解码 `id_token` 或 `access_token`，校验：

```text
token.email == chatgpt_email
```

如果 token 中 email 缺失，可退而检查：

```text
sub/account_id 存在
```

但推荐至少对 email 做强校验。

不一致时：

```text
拒绝保存
记录脱敏错误日志
支付结果仍保持成功
Codex token 导出标记失败
```

### 8.3 过期时间校验

如果 token response 有：

```text
expires_in
```

计算：

```text
expires_at = now + expires_in
```

导出时可显示：

```text
access_token 将于 xx 时间过期；refresh_token 用于后续刷新
```

### 8.4 refresh_token 可用性校验

推荐在保存前做一次可选验证：

```text
POST /oauth/token
  grant_type=refresh_token
  client_id=app_EMoamEEZ73f0CkXaXp7hrann
  refresh_token=<refresh_token>
```

如果刷新成功：

- 使用新返回的 access_token/id_token；
- 更新 refresh_token，如果服务端返回了新 refresh_token；
- 保存最终 token。

如果刷新失败：

- 标记 `refresh_validation_failed`；
- 不建议导出，除非用户手动确认。

MVP 可以先不做 refresh 验证，但文档实现时应预留。

---

## 9. WebUI 交互设计

### 9.1 支付结果页

在成功结果中增加区域：

```text
Codex 授权导出
状态：已生成 / 未生成 / 失败
按钮：复制 Cockpit JSON / 下载 auth.json
```

### 9.2 默认脱敏

列表中只显示：

```text
email
account_id 前后 4 位
access_token 是否存在
refresh_token 是否存在
scope
created_at
```

不要直接显示完整 token。

### 9.3 导出前确认

点击复制/下载前弹确认：

```text
该 JSON 包含 OpenAI/Codex 长期登录凭据。任何获得它的人都可能访问此账号。请只导入你信任的本地 Cockpit Tools。
```

确认后才复制或下载。

### 9.4 导出文件名

下载文件名建议：

```text
codex-auth-<masked-email-or-hash>-<yyyyMMdd-HHmmss>.json
```

不要直接使用完整 email 作为文件名，避免隐私泄露。

---

## 10. 日志与安全要求

### 10.1 禁止日志输出

禁止输出完整：

```text
id_token
access_token
refresh_token
auth_json
callback code
```

允许输出：

```text
id_token_len
access_token_len
refresh_token_len
scope
expires_in
email masked
```

### 10.2 数据库存储风险

SQLite 中保存的是明文 token。短期 MVP 可以接受，但必须：

- 不提交 `output/webui.db`；
- 不将数据库上传到云端；
- 不把 token 放入日志；
- WebUI 默认脱敏；
- 后续可考虑本机密钥加密。

### 10.3 文件导出风险

导出的 JSON 是高敏感文件。导出动作必须由用户主动触发。

不建议自动写入：

```text
output/logs
项目根目录
会被 git 扫到的目录
```

---

## 11. 错误处理

### 11.1 支付失败

```text
不触发 Codex token 获取
不生成导出 JSON
```

### 11.2 缺少登录条件

如果缺少：

```text
password
mail config
OTP provider
```

行为：

```text
支付结果成功
Codex token 状态 = skipped
日志说明缺少条件
```

### 11.3 OAuth 登录失败

行为：

```text
支付结果成功
Codex token 状态 = failed
保存失败原因，不保存 partial token
```

### 11.4 token 字段缺失

行为：

```text
不保存 auth_json
记录字段缺失
```

### 11.5 token email 不匹配

行为：

```text
拒绝保存
标记为 security_mismatch
提示人工检查
```

---

## 12. 实施步骤建议

### Phase 1：后端最小闭环

1. 修改 Codex OAuth token exchange 返回结构：
   - 从只返回 `refresh_token` 改为返回 token object；
   - 包含 `id_token/access_token/refresh_token/scope/expires_in/token_type`。
2. OAuth scope 对齐 Cockpit Tools。
3. 增加 token 解码工具：
   - 解码 JWT payload；
   - 提取 email/account_id/exp。
4. 增加账号一致性校验。
5. 新增 SQLite 表或字段保存 token JSON。
6. 日志只输出长度和状态。
7. 保持支付成功主流程不因 Codex token 失败而失败。

### Phase 2：WebUI 导出

1. 后端新增接口：
   - 查询 Codex token 记录列表；
   - 导出指定记录的 Cockpit JSON。
2. 前端结果页增加导出按钮。
3. 增加复制/下载功能。
4. 增加敏感信息确认弹窗。
5. 默认脱敏显示。

### Phase 3：可靠性增强

1. 增加 refresh_token 验证；
2. 增加 Plus 状态确认；
3. 增加 token 过期提示；
4. 增加失败状态枚举；
5. 增加清理/删除 token 功能。

---

## 13. 测试计划

### 13.1 单元测试

覆盖：

- OAuth token response 解析；
- 缺少 `id_token`；
- 缺少 `access_token`；
- 缺少 `refresh_token`；
- JWT email 提取；
- email 匹配成功；
- email 不匹配拒绝保存；
- Cockpit JSON 生成格式。

### 13.2 集成测试

覆盖：

- 支付成功 + token 获取成功；
- 支付成功 + token 获取失败不影响支付结果；
- SQLite 写入成功；
- WebUI 导出接口返回正确 JSON；
- 导出 JSON 可被 Cockpit Tools Token / JSON 格式识别。

### 13.3 安全测试

覆盖：

- `card.log` 不包含完整 token；
- WebUI 列表不明文展示 token；
- 导出接口需要登录；
- 不能通过普通结果接口拿完整 token；
- 文件名不泄露完整 email。

### 13.4 手动验收

1. 跑一次 GoPay 支付成功流程；
2. 确认日志显示：

```text
Codex token 获取成功 id_token_len=... access_token_len=... refresh_token_len=...
```

3. 在 WebUI 点击导出 Cockpit JSON；
4. 打开 Cockpit Tools：

```text
Codex → 添加 Codex 账号 → Token / JSON
```

5. 粘贴 JSON；
6. 确认账号导入成功；
7. 确认账号 email 与支付账号一致；
8. 确认 Codex 功能可用。

---

## 14. 验收标准

功能完成必须满足：

- 支付成功后能生成完整 Codex auth JSON；
- JSON 包含 `id_token/access_token/refresh_token`；
- OAuth scope 对齐 Cockpit Tools；
- token email 与支付账号一致；
- Cockpit Tools Token / JSON 可导入；
- token 不出现在日志；
- WebUI 默认不明文展示 token；
- Codex token 获取失败不影响支付成功结果落库。

---

## 15. 推荐最终方案

推荐实现路径：

```text
后端保存完整 token 到独立 SQLite 表
+ WebUI 提供主动导出 Cockpit auth.json
+ 日志/列表脱敏
+ email 一致性校验
+ scope 对齐 Cockpit Tools
```

不要使用 API Key 路径，因为本功能目标是 ChatGPT Plus 账号授权给 Codex，而不是 OpenAI API Key 调用。

---

## 16. 后续可选增强

- 使用系统密钥链或本地加密保护 SQLite 中的 token；
- 支持批量导出多个 Codex auth JSON；
- 支持 token refresh 状态检测；
- 支持删除/吊销本地保存的 Codex token；
- 在 WebUI 中显示 Cockpit Tools 导入说明；
- 增加一键复制 Cockpit Tools auth.json 格式与顶层 token 格式切换。
