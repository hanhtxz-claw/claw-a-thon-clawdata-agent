import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

import catalog as cat
import llm as llm_module

app = FastAPI(title="DataHub Catalog Advisor")

# Load once at startup
_catalog_data = cat.load_catalog()
_playbook = (Path(__file__).parent / "prompts" / "agent_playbook.md").read_text(encoding="utf-8")

# Session memory: session_id → list of {role, content} dicts (max 20 = 10 pairs)
_MAX_HISTORY_PAIRS = 10
_sessions: dict = {}

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.get("/", response_class=HTMLResponse)
async def root():
    index = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


@app.post("/invocations")
async def invoke(payload: dict):
    message = str(payload.get("message", "")).strip()
    session_id = str(payload.get("session_id", "default"))
    if not message:
        return JSONResponse({"status": "error", "answer": "Vui lòng nhập câu hỏi / Please enter a question."})

    # Retrieve session history (prior turns, plain user messages + assistant answers)
    history = _sessions.get(session_id, [])

    candidates = cat.search(message, top_n=8)

    # Strip lineage fields before sending to LLM — prevents URN: N/A hallucinations
    _STRIP = {"lineage_downstream", "lineage_upstream"}
    safe_candidates = [{k: v for k, v in c.items() if k not in _STRIP} for c in candidates]

    candidate_block = json.dumps(safe_candidates, ensure_ascii=False, indent=2)
    user_prompt = f"""## Câu hỏi của user / User question:
{message}

## Các bảng ứng viên tìm được từ DataHub catalog / Candidate tables found in DataHub catalog:
{candidate_block}

Hãy phân tích nhu cầu và trả lời theo đúng playbook. CHỈ dùng URN từ danh sách candidates trên — không được bịa URN.
Analyze the need and respond following the playbook. ONLY use URNs from the candidate list above — never invent URNs.
"""

    answer = llm_module.chat(_playbook, user_prompt, candidates, history=history)

    # Save this turn to session history (store raw question for clean context)
    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": answer},
    ]
    # Keep only the last N pairs
    max_msgs = _MAX_HISTORY_PAIRS * 2
    _sessions[session_id] = history[-max_msgs:]

    recommended_urn = None
    for line in answer.splitlines():
        if "URN:" in line and "`" in line:
            start = line.find("`") + 1
            end = line.rfind("`")
            if start < end:
                recommended_urn = line[start:end]
                break

    return JSONResponse({
        "status": "ok",
        "answer": answer,
        "candidates": candidates,
        "recommended_urn": recommended_urn,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
