---
name: claw-data-tear-down-agent
description: >
  Hướng dẫn xóa (teardown) agent đã deploy trên GreenNode AgentBase để dừng phát sinh chi phí.
  Trigger khi user muốn: xóa agent, dừng runtime, dọn dẹp sau demo, teardown agent không cần thiết.
  CHỈ xóa runtime và CR image — KHÔNG BAO GIỜ xóa AIP API keys (dùng chung của team).
  Tham chiếu kinh nghiệm thực tế từ demo gold-price agent (hackathon GreenNode 2026).
---

# Claw-Data: Teardown Agent trên GreenNode AgentBase

Quy trình dọn dẹp agent sau khi demo hoặc khi không còn cần thiết.

**Console quản lý:** https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime

---

## ⚠️ Quy tắc cứng — ĐỌC TRƯỚC KHI LÀM

| Được xóa | KHÔNG được xóa |
|----------|----------------|
| Runtime (dừng tính phí compute) | AIP API keys (`claw26-team250`, ...) |
| CR image trong registry | CR repository (pre-provisioned, không xóa được) |
| Non-DEFAULT custom endpoints (trước khi xóa runtime) | Keys platform: `openclaw-service`, `runtime-service` |

**Lý do giữ API keys:** Keys là tài nguyên dùng chung của cả team. Xóa key sẽ làm hỏng tất cả agents và thành viên khác đang dùng key đó.

---

## Bước 0 — Xác nhận credentials

```bash
bash .claude/skills/agentbase/scripts/check_credentials.sh iam
```

- **OK** → tiếp tục
- **MISSING** → xem hướng dẫn trong `claw-data-build-deploy-agent` (Part 1a)

---

## Bước 1 — Discover tài nguyên cần xóa

```bash
bash .claude/skills/agentbase/scripts/discovery.sh json
```

Tìm trong output:
- `runtimes[].id` và `runtimes[].name` — lấy `RUNTIME_ID` của agent cần xóa
- `crRepository` — lấy tên repo (mặc định: `111480-abp112076`)

Lấy danh sách endpoints của runtime:
```bash
bash .claude/skills/agentbase/scripts/runtime.sh endpoints list $RUNTIME_ID
```

Lấy danh sách CR images:
```bash
bash .claude/skills/agentbase/scripts/cr.sh images list --name <agent-name> --page 1 --size 100
```

---

## Bước 2 — Trình bày kế hoạch và xin xác nhận

Luôn show kế hoạch đầy đủ trước khi xóa bất cứ thứ gì:

```
Teardown Plan for "<agent-name>":
  1. Xóa runtime "<agent-name>" (ID: runtime-xxx...)  → dừng tính phí compute
  2. Xóa CR image "<repo>/<agent-name>" (N artifacts) → giải phóng storage quota

Giữ lại:
  - AIP key "claw26-team250" (dùng chung team — KHÔNG xóa)
  - CR repository "111480-abp112076" (pre-provisioned — không xóa được)

Chi phí sau teardown = 0 đồng.
Proceed? (yes/ok/confirm)
```

---

## Bước 3 — Xóa runtime

```bash
RUNTIME_ID="runtime-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Xóa runtime (DEFAULT endpoint tự xóa theo; auto-provisioned identity tự dọn)
bash .claude/skills/agentbase/scripts/runtime.sh delete $RUNTIME_ID

# Poll đến khi GONE (~10-30 giây)
for i in $(seq 1 10); do
  STATUS=$(bash .claude/skills/agentbase/scripts/runtime.sh get $RUNTIME_ID 2>&1 \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null \
    || echo "GONE")
  echo "[$i] $STATUS"
  [ "$STATUS" = "GONE" ] && echo "Runtime đã xóa." && break
  sleep 8
done
```

> **Lưu ý về endpoints:**
> - **DEFAULT endpoint** → tự xóa khi runtime bị xóa, KHÔNG cần xóa thủ công.
> - **Custom endpoints (non-DEFAULT)** → phải xóa trước khi xóa runtime, nếu không API sẽ báo lỗi 400.
>
> ```bash
> # Xóa custom endpoint (chỉ khi có endpoint không phải DEFAULT)
> bash .claude/skills/agentbase/scripts/runtime.sh endpoints delete $RUNTIME_ID $ENDPOINT_ID
> ```

---

## Bước 4 — Xóa CR image

```bash
REPO_NAME="111480-abp112076"
AGENT_NAME="<agent-name>"

# Xóa image (cascades xóa tất cả artifacts/tags bên trong)
bash .claude/skills/agentbase/scripts/cr.sh images delete --name "$REPO_NAME/$AGENT_NAME"

# Verify đã xóa (kết quả phải là totalItem: 0)
bash .claude/skills/agentbase/scripts/cr.sh images list --name "$AGENT_NAME"
```

> **Lưu ý:** Nếu lệnh `cr.sh images delete --name <agent-name>` báo lỗi 400, thử với full path: `--name "<repo>/<agent-name>"`.

---

## Bước 5 — Xác nhận chi phí sau teardown

| Tài nguyên | Trạng thái | Chi phí |
|-----------|-----------|---------|
| Runtime compute | Đã xóa | Không còn |
| CR image/artifacts | Đã xóa | Không còn |
| CR repository | Còn (rỗng, pre-provisioned) | Miễn phí |
| AIP key `claw26-team250` | Còn (giữ lại) | Miễn phí (chỉ tính khi gọi LLM) |
| Model Qwen 3.5 27B | N/A | FREE model |

**Tổng chi phí còn lại = 0 đồng.**

---

## Quick Cheatsheet (copy-paste)

```bash
# === TEARDOWN AGENT ===
RUNTIME_ID="runtime-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
AGENT_NAME="<agent-name>"
REPO="111480-abp112076"

# 1. Xóa runtime (DEFAULT endpoint + identity tự dọn theo)
bash .claude/skills/agentbase/scripts/runtime.sh delete $RUNTIME_ID

# 2. Poll đến GONE
for i in $(seq 1 10); do
  STATUS=$(bash .claude/skills/agentbase/scripts/runtime.sh get $RUNTIME_ID 2>&1 \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null \
    || echo "GONE")
  echo "[$i] $STATUS"; [ "$STATUS" = "GONE" ] && break; sleep 8
done

# 3. Xóa CR image
bash .claude/skills/agentbase/scripts/cr.sh images delete --name "$REPO/$AGENT_NAME"

# 4. Verify image gone
bash .claude/skills/agentbase/scripts/cr.sh images list --name "$AGENT_NAME"
# → totalItem: 0 là OK

# === XONG — chi phí = 0 ===
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| Runtime deletion 400 | Còn custom endpoint chưa xóa | Xóa non-DEFAULT endpoints trước: `runtime.sh endpoints delete $RUNTIME_ID $ENDPOINT_ID` |
| CR image delete 400/404 | Sai tên (thiếu repo prefix) | Dùng full path: `--name "111480-abp112076/<agent-name>"` |
| Runtime vẫn DELETING sau 5 phút | Platform chậm | Đợi thêm, poll lại. Không cần làm gì thêm. |
| 401 Unauthorized | IAM token hết hạn | `bash .claude/skills/agentbase/scripts/get_token.sh --force` rồi thử lại |
