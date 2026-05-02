# WhatsApp / GoPay OTP – Android Notification Forwarder

[← 回到 README](../README.md)

WhatsApp 在 2024-10 上线了 OTP Code Confidentiality，服务端不再把业务 OTP
明文路由到 linked devices。因此 Puppeteer / Baileys / whatsapp-web.js **全部失效**。

替代方案：在 **Android 手机** 上安装通知转发 App，把收到的 OTP 自动 POST 到
webui 的 `/api/whatsapp/external-otp` 端点。

---

## 1. 推荐 App

| App | 链接 | 特点 |
|---|---|---|
| NotificationForwarder | [GitHub](https://github.com/ItsAzni/NotificationForwarder) | 轻量、支持正则过滤 |
| NotificationWebhookApp | [GitHub](https://github.com/BigShoots/NotificationWebhookApp) | 支持自定义 body 模板 |

## 2. 安装与权限

1. 下载 APK 安装（或从 F-Droid / GitHub Releases）
2. 进入 **设置 → 通知监听权限**，给 App 开启 Notification Listener
3. 打开 App，确认可以看到实时通知流

## 3. 过滤规则

只转发 GoPay / GoJek 的 OTP 通知，减少噪音：

- **发件人过滤**：包名含 `com.gojek` 或通知标题含 `GoPay` / `GoJek` / `Midtrans`
- **内容过滤**：body 匹配 `\d{6}`（6 位数字）

## 4. Webhook 配置

| 字段 | 值 |
|---|---|
| URL | `https://你的-webui-地址/api/whatsapp/external-otp` |
| Method | POST |
| Header | `Authorization: Bearer <token>` |
| Body | `{"otp": "<提取的6位数字>", "source": "android-forwarder"}` |

### 获取 Token

访问 webui 的 **设置** 页面，或调用：

```bash
curl http://127.0.0.1:8765/api/whatsapp/token
```

### Body 模板（NotificationWebhookApp）

```json
{"otp": "{{regex \\d{6}}}", "source": "android-notification-forwarder"}
```

## 5. 测试

```bash
# 发一条测试 OTP
curl -X POST http://127.0.0.1:8765/api/whatsapp/external-otp \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"otp": "123456", "source": "test"}'

# 期望: {"status": "no_pending_request"} （没有 pipeline 在等 OTP 时）
# 或者: {"status": "consumed"} （pipeline 正在等 OTP 时）
```

## 6. 排错

| 现象 | 原因 | 解决 |
|---|---|---|
| 401 Unauthorized | Token 不对 | 检查 Bearer token 是否匹配 |
| 422 otp field is empty | 正则没匹配到 | 检查 App 的正则配置 |
| `no_pending_request` | pipeline 没在等 OTP | 正常，说明时序不对或没有 GoPay 流程在跑 |
| 手机收不到通知 | 系统限制 | 检查 Notification Listener 权限、电池优化白名单 |
| 防火墙拦截 | webui 不在公网 | 配 nginx 反代 + HTTPS，或用 Tailscale/frp 内网穿透 |
