# KIMI API INFRASTRUCTURE AUDIT
## Extracted from HAR: www.kimi.com_Archive [26-08-14 10-50-25].har.txt

---

## 1. ACCOUNT STATUS

| Field | Value |
|-------|-------|
| Plan | Allegretto |
| Level | LEVEL_INTERMEDIATE |
| Price | $39.00/month |
| Status | SUBSCRIPTION_STATUS_ACTIVE |
| **Quota** | **OVERDRAWN** |
| Quota Notice | "Monthly quota used up" |
| Quota Reset | 2026-08-29T00:00:00Z |
| Payment Channel | PAYMENT_CHANNEL_GOOGLE_PLAY |
| Subscription End | 2026-08-29T00:00:00Z |
| Next Billing | 2026-08-28T01:34:31.255Z |

## 2. RATE LIMITS

| Limit | Reset Time |
|-------|------------|
| 5-hour code limit | 2026-08-15T09:34:30Z (~5 hours from now) |
| 7-day code limit | 2026-08-18T01:34:30Z (~3 days from now) |

## 3. UPGRADE PATH

Current: LEVEL_INTERMEDIATE (Allegretto, $39/mo)
**Required: LEVEL_ADVANCED** (next tier up)

The API explicitly returns:
```json
{
  "needUpgrade": true,
  "upgradeTo": "LEVEL_ADVANCED",
  "source": "membership_quota_notice"
}
```

## 4. AVAILABLE MODELS

| Key | Name | Scenario | Mode |
|-----|------|----------|------|
| k2d6 | Instant | SCENARIO_K2D5 | Standard |
| k3 | K3 | SCENARIO_OK_COMPUTER | TYPE_NORMAL |
| k3-agent-ultra | K3 Swarm | SCENARIO_OK_COMPUTER | TYPE_ULTRA |

K3 Swarm features: multi-worker, 3x multiplier, batch processing

## 5. PROJECTS

| Name | ID | Status |
|------|-----|--------|
| new | 19fd6126-0bc2-8dfe-8000-0e510dd7d34d | Active |
| huh | 19ff66f7-a8d2-8dd7-8000-... | Active |
| osint | 19fc93c7-17f2-8444-8000-... | Active |

## 6. CURRENT CHAT

- **Name**: Kernel Wait Token Review
- **ID**: 1a00117d-b102-84bd-8000-0951e0b50f12
- **Project**: new (19fd6126-0bc2-8dfe-8000-0e510dd7d34d)
- **Files**: 5 (27MB HAR + system logs)
- **Status**: STATUS_GENERATING

## 7. API ENDPOINTS DISCOVERED

```
POST /apiv2/kimi.gateway.chat.v1.ChatService/Chat
POST /apiv2/kimi.gateway.chat.v1.ChatService/GetChat
POST /apiv2/kimi.gateway.chat.v1.ChatService/ListMessages
POST /apiv2/kimi.gateway.config.v1.ConfigService/GetConfig
POST /apiv2/kimi.gateway.config.v1.ConfigService/GetAvailableModels
POST /apiv2/kimi.gateway.membership.v2.MembershipService/GetSubscription
POST /apiv2/kimi.gateway.membership.v2.MembershipService/ListSubscriptions
POST /apiv2/kimi.gateway.membership.v2.MembershipService/GetSubscriptionStats
POST /apiv2/kimi.gateway.project.v1.ProjectService/ListProjects
POST /apiv2/kimi.gateway.project.v1.ProjectService/ListProjectFiles
POST /apiv2/kimi.gateway.feed.v1.FeedService/ListFeeds
POST /apiv2/kimi.gateway.claw.v1.ClawService/ListBots
POST /apiv2/kimi.gateway.file.v1.FileService/GetFileParseProgress
POST /apiv2/kimi.gateway.file.v1.FileService/GetFile
POST /api/config
POST /update.json
GET  /favicon-dark.ico
```

## 8. AUTH MECHANISM

- **Type**: Bearer JWT
- **Issuer**: user-center
- **App ID**: kimi
- **Region**: overseas
- **Membership Level**: 10 (encoded in JWT)
- **Key Headers**:
  - `authorization: Bearer <JWT>`
  - `x-msh-session-id: 1731737410842547033`
  - `x-msh-device-id: 7652551588736807183`
  - `x-traffic-id: d87br2oh8njkr90jf520`
  - `x-msh-version: 2.0.0`
  - `connect-protocol-version: 1`

## 9. FILE STORAGE

- **CDN**: kimi-img.kimi.ai, kimicdn.com, moonshot.cn, kimi-file.msdev.cc
- **File Service**: apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F<checksum>
- **Upload**: /apiv2/kimi.gateway.file.v1.FileService/Upload
- **Max Size**: Not specified in HAR
- **Types**: FILE_TYPE_DOCUMENT, FILE_TYPE_IMAGE

## 10. KEY FINDINGS

1. **The 504 timeouts are NOT local** - they're from the upstream gateway at `kimi-api-sandbox.msh.team` because the account quota is exhausted
2. **LEVEL_ADVANCED is the real upgrade target** - not LEVEL_INTERMEDIATE (current)
3. **Quota resets Aug 29** - 14 days from now
4. **5h code limit resets in ~5 hours** - might allow some tool calls then
5. **The "K3 Swarm" mode** is the ultra/agent mode with 3x multiplier
6. **Project system** is real and active - 3 projects with multiple chats each
7. **File upload** uses checksum-based blob storage with signed URLs

---

Generated: 2026-08-15T04:52:00Z
