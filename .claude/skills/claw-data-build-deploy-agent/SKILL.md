---
name: claw-data-build-deploy-agent
description: >
  Hướng dẫn build, deploy và active endpoint cho bất kỳ AI agent nào lên GreenNode AgentBase
  (Clawdata team). Trigger khi user muốn: deploy agent, build và push image, tạo runtime, lấy
  endpoint public, redeploy agent mới. Dùng khi bắt đầu project agent mới hoặc update agent hiện có.
  Tham chiếu kinh nghiệm thực tế từ demo gold-price agent (hackathon GreenNode 2026).
  DO NOT use for: quản lý memory, identity, policy — dùng skill chuyên biệt cho các tác vụ đó.
---

# Claw-Data: Build & Deploy Agent lên GreenNode AgentBase

Quy trình đã được kiểm chứng thực tế khi build gold-price agent (hackathon GreenNode 06/2026).
Tất cả scripts dùng trong file này đều nằm tại `.claude/skills/agentbase/scripts/`.

**Console quản lý:** https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime

---

## Part 1 — Prerequisites (Làm 1 lần, dùng mãi)

### 1a. Kiểm tra IAM credentials
```bash
bash .claude/skills/agentbase/scripts/check_credentials.sh iam
```
- **OK** → tiếp tục
- **MISSING** → xem 3 cách setup bên dưới

**Nếu MISSING**, chọn 1 trong 3:

```bash
# Cách 1 — Import từ file JSON (có sẵn file credentials):
bash .claude/skills/agentbase/scripts/save_iam_credentials.sh --from-file /path/to/creds.json

# Cách 2 — Nhập thủ công (có Client ID + Secret từ portal IAM):
echo 'YOUR_CLIENT_SECRET' | bash .claude/skills/agentbase/scripts/save_iam_credentials.sh \
  --client-id "YOUR_CLIENT_ID" --secret-stdin

# Cách 3 — Tạo file trực tiếp (nhanh nhất cho demo):
cat > .greennode.json << 'EOF'
{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET","agent_identity":""}
EOF
```

Lấy Client ID + Secret tại: https://iam.console.vngcloud.vn/service-accounts

### 1b. Verify token và lấy CR repo info
```bash
# Verify token OK
TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh) && echo "Token OK"

# Lấy Container Registry repo (ghi nhớ registryUrl và name)
bash .claude/skills/agentbase/scripts/cr.sh repo get
# → {"name": "111480-abp112076", "registryUrl": "vcr.vngcloud.vn", ...}
# IMAGE_BASE = vcr.vngcloud.vn/111480-abp112076
```

---

## Part 2 — Scaffold Agent Project

### Contract cứng của AgentBase Runtime (BẮT BUỘC)
1. Container phải **listen port 8080**
2. **`GET /health`** phải trả HTTP 200 khi ready
→ Chỉ cần 2 điều này là runtime lên ACTIVE. Mọi thứ khác tùy ý.

### Template `main.py` (FastAPI — recommended, không cần SDK)

```python
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

load_dotenv()
app = FastAPI()

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})  # BẮT BUỘC

@app.post("/invocations")
async def invoke(payload: dict):
    message = payload.get("message", "")
    # === VIẾT LOGIC AGENT Ở ĐÂY ===
    answer = f"Echo: {message}"
    return JSONResponse({"status": "ok", "answer": answer})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # host="0.0.0.0" là bắt buộc
```

### Template `Dockerfile`

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Template `requirements.txt` (tối thiểu)
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-dotenv>=1.0.0
requests>=2.31.0
openai>=1.30.0   # chỉ khi cần gọi LLM
```

### Template `.dockerignore`
```
.venv/
venv/
__pycache__/
.env
.greennode.json
.agentbase/
.agentbase-state.json
.git/
.DS_Store
.claude/
```

### ⚠️ Env vars KHÔNG tự đặt trong `.env`
Runtime tự inject các biến này — đặt thủ công sẽ conflict:
- `GREENNODE_CLIENT_ID`, `GREENNODE_CLIENT_SECRET`
- `GREENNODE_AGENT_IDENTITY`, `GREENNODE_ENDPOINT_URL`

---

## Part 3 — Configure LLM (khi agent cần AI)

### 3a. Dùng API key có sẵn (team đã có key)
```bash
# List tất cả API keys
bash .claude/skills/agentbase/scripts/aip.sh api-keys list

# Load key vào .env (thay "claw26-team250" bằng tên key của team)
bash .claude/skills/agentbase/scripts/aip.sh api-keys get claw26-team250 --save-env

# Verify
bash .claude/skills/agentbase/scripts/check_credentials.sh llm
```

### 3b. Chọn model
```bash
# List models đang ENABLED
bash .claude/skills/agentbase/scripts/aip.sh models list --status ENABLED
# → Qwen 3.5 27B (FREE): path = qwen/qwen3-5-27b
# → Gemma 4 31B-IT:      path = google/gemma-4-31b-it
# → MiniMax M2.5:         path = minimax/minimax-m2.5
```

### 3c. Lưu env vars
```bash
bash .claude/skills/agentbase/scripts/save_env_var.sh \
  --key LLM_BASE_URL --value "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
bash .claude/skills/agentbase/scripts/save_env_var.sh \
  --key LLM_MODEL --value "qwen/qwen3-5-27b"
```

### 3d. Gọi LLM trong code (OpenAI-compatible)
```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url=os.environ.get("LLM_BASE_URL"),
)
resp = client.chat.completions.create(
    model=os.environ.get("LLM_MODEL"),
    messages=[{"role": "user", "content": "Hello!"}],
    extra_body={"enable_thinking": False},  # ⚠️ BẮT BUỘC với Qwen — không có dòng này content trả về rỗng
)
answer = resp.choices[0].message.content or ""
```

---

## Part 4 — Build, Push & Deploy

### 4a. Build Docker image
```bash
# BẮT BUỘC --platform linux/amd64 (AgentBase chạy amd64; Apple Silicon build arm64 sẽ fail)
docker build --platform linux/amd64 \
  -t vcr.vngcloud.vn/111480-abp112076/<agent-name>:latest .
```

### 4b. Login CR và push
```bash
bash .claude/skills/agentbase/scripts/cr.sh credentials docker-login
docker push vcr.vngcloud.vn/111480-abp112076/<agent-name>:latest
```

### 4c. Tạo runtime mới
```bash
# Check xem runtime tên này đã tồn tại chưa
bash .claude/skills/agentbase/scripts/runtime.sh list

# Tạo mới (PUBLIC mode — endpoint ra internet luôn)
bash .claude/skills/agentbase/scripts/runtime.sh create \
  --name "<agent-name>" \
  --image "vcr.vngcloud.vn/111480-abp112076/<agent-name>:latest" \
  --flavor "runtime-s2-general-2x4" \
  --env-file ".env" \
  --description "Mô tả ngắn" \
  --min-replicas 1 --max-replicas 1 \
  --cpu-scale 50 --mem-scale 50 \
  --from-cr

# Lưu RUNTIME_ID từ response: "id": "runtime-xxxxxxxx-..."
RUNTIME_ID="runtime-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**Flavors thực tế** (đã verify, không có `1x1-general`):
| Flavor ID | CPU | RAM |
|-----------|-----|-----|
| `runtime-s2-general-2x4` | 2 | 4 GB |
| `runtime-s2-general-4x8` | 4 | 8 GB |

### 4d. Update runtime đã có
```bash
bash .claude/skills/agentbase/scripts/runtime.sh update $RUNTIME_ID \
  --image "vcr.vngcloud.vn/111480-abp112076/<agent-name>:latest" \
  --flavor "runtime-s2-general-2x4" \
  --env-file ".env" \
  --from-cr \
  --min-replicas 1 --max-replicas 1 --cpu-scale 50 --mem-scale 50
```

### 4e. Đợi ACTIVE (~30 giây đến 3 phút)
```bash
RUNTIME_ID="runtime-xxxxxxxx-..."
for i in $(seq 1 20); do
  STATUS=$(bash .claude/skills/agentbase/scripts/runtime.sh get $RUNTIME_ID \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))")
  echo "[$i] $STATUS"
  [ "$STATUS" = "ACTIVE" ] && break || sleep 15
done
```

---

## Part 5 — Verify & Lấy Public Endpoint

```bash
# Lấy endpoint URL
bash .claude/skills/agentbase/scripts/runtime.sh endpoints list $RUNTIME_ID
# → url: "https://endpoint-xxxxxxxx.agentbase-runtime.aiplatform.vngcloud.vn"

ENDPOINT="https://endpoint-xxxxxxxx.agentbase-runtime.aiplatform.vngcloud.vn"

# Test health (phải 200)
curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT/health"

# Test agent
curl -s -X POST "$ENDPOINT/invocations" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'

# Mở chat UI (nếu agent có GET /)
open "$ENDPOINT"
```

**Endpoint URL là PUBLIC** — không cần auth header, gọi được từ browser/app/Postman bình thường.

---

## Quick Cheatsheet (copy-paste cho project mới)

```bash
# === 1. PREREQ (1 lần) ===
bash .claude/skills/agentbase/scripts/check_credentials.sh iam
bash .claude/skills/agentbase/scripts/cr.sh repo get
# → ghi lại: registryUrl=vcr.vngcloud.vn, repoName=111480-abp112076

# === 2. CONFIG LLM ===
bash .claude/skills/agentbase/scripts/aip.sh api-keys get claw26-team250 --save-env
bash .claude/skills/agentbase/scripts/save_env_var.sh --key LLM_BASE_URL \
  --value "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1"
bash .claude/skills/agentbase/scripts/save_env_var.sh --key LLM_MODEL \
  --value "qwen/qwen3-5-27b"

# === 3. BUILD & PUSH ===
AGENT=my-new-agent
docker build --platform linux/amd64 -t vcr.vngcloud.vn/111480-abp112076/$AGENT:latest .
bash .claude/skills/agentbase/scripts/cr.sh credentials docker-login
docker push vcr.vngcloud.vn/111480-abp112076/$AGENT:latest

# === 4. DEPLOY ===
bash .claude/skills/agentbase/scripts/runtime.sh create \
  --name "$AGENT" \
  --image "vcr.vngcloud.vn/111480-abp112076/$AGENT:latest" \
  --flavor "runtime-s2-general-2x4" \
  --env-file ".env" --from-cr \
  --min-replicas 1 --max-replicas 1 --cpu-scale 50 --mem-scale 50
# → copy RUNTIME_ID từ response

# === 5. VERIFY ===
RUNTIME_ID="runtime-xxx..."
bash .claude/skills/agentbase/scripts/runtime.sh endpoints list $RUNTIME_ID
# → copy ENDPOINT URL, test /health và /invocations
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `check_credentials.sh` → MISSING | `.greennode.json` chưa có hoặc sai | Dùng `save_iam_credentials.sh` hoặc tạo file thủ công |
| LLM trả về answer rỗng (Qwen) | Qwen 3.5 bật thinking mode mặc định | Thêm `extra_body={"enable_thinking": False}` vào `chat.completions.create()` |
| `docker build` sai arch / crash | Build arm64 trên Mac, runtime cần amd64 | Luôn dùng `--platform linux/amd64` |
| Flavor `1x1-general` not found | Flavor này không tồn tại trên tenant | Dùng `runtime-s2-general-2x4` (nhỏ nhất có) |
| Runtime status `ERROR` | Container crash khi start | Check `GET /health` trả 200 chưa; check `uvicorn host="0.0.0.0"` không phải `127.0.0.1` |
| `docker push` unauthorized | CR session hết hạn | Re-run `cr.sh credentials docker-login` rồi push lại |
| Runtime stuck `UPDATING` | Image mới chưa pull xong | Đợi thêm, poll `runtime.sh get $ID` mỗi 15s |
| Endpoint 502 sau ACTIVE | Container startup chậm | Đợi thêm 30s, test lại `/health` |
