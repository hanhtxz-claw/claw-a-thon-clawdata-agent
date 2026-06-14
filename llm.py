import os
from openai import OpenAI

# Model cascade: Gemma (fast) → MiniMax (deeper thinking) → Qwen (last resort)
# enable_thinking=False is ONLY required for Qwen — do NOT pass for Gemma/MiniMax
_MODEL_CASCADE = [
    {"model": "google/gemma-4-31b-it", "extra_body": {}},
    {"model": "minimax/minimax-m2.5",  "extra_body": {}},
    {"model": "qwen/qwen3-5-27b",      "extra_body": {"enable_thinking": False}},
]


def _build_fallback(candidates: list, query: str) -> str:
    if not candidates:
        return (
            "Mình chưa tìm thấy bảng nào khớp với yêu cầu của bạn. "
            "Thử mô tả rõ hơn hoặc dùng từ khóa khác nhé!\n\n"
            "I couldn't find a matching table. Try describing your need with different keywords!"
        )

    warehouse = [c for c in candidates if c.get("layer") == "data_warehouse"]
    lake = [c for c in candidates if c.get("layer") == "data_lake"]
    primary = warehouse[0] if warehouse else candidates[0]

    lines = [
        "## Gợi ý bảng / Recommended Table\n",
        f"**{primary['name']}**",
        f"URN: `{primary['urn']}`",
        f"Platform: {primary.get('platform', 'N/A')} | Layer: {primary.get('layer', 'N/A')}",
        f"\n{primary.get('best_for', '')}",
    ]
    if lake and primary.get("layer") != "data_lake":
        alt = lake[0]
        lines += [
            f"\n---\n## Bảng thay thế / Alternative\n**{alt['name']}**",
            f"URN: `{alt['urn']}`",
            "→ Dùng khi cần deep-dive log raw / Use for raw log investigation",
        ]
    lines.append("\nNhu cầu của bạn có thay đổi không? Hãy mô tả thêm nhé!")
    return "\n".join(lines)


def chat(system: str, user: str, candidates: list = None, history: list = None) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str} — prior turns in this session.
    These are injected between the system prompt and the current user message so the LLM
    has conversation context (e.g. can follow up on a previous off-topic question).
    """
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1")

    if not api_key:
        return _build_fallback(candidates or [], user)

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user})

    for spec in _MODEL_CASCADE:
        try:
            kwargs = dict(model=spec["model"], temperature=0.2, messages=messages)
            if spec["extra_body"]:
                kwargs["extra_body"] = spec["extra_body"]

            resp = client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return content
            # empty content → try next model
        except Exception:
            pass  # any error → try next model

    return _build_fallback(candidates or [], user)
