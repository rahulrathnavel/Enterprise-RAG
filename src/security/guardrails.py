from __future__ import annotations

import re
from dataclasses import dataclass

from openai import OpenAI

from src.config.settings import Settings
from src.security.pii import redact_pii


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    text: str
    reason: str | None = None


PROMPT_ATTACK_MARKERS = (
    "ignore previous instructions",
    "reveal the system prompt",
    "disable rbac",
    "bypass access control",
    "print api key",
    "show hidden prompt",
)


def input_guardrail(text: str, settings: Settings) -> GuardrailResult:
    """Reject clear prompt-injection and secret-exfiltration attempts."""

    lowered = text.lower()
    for marker in PROMPT_ATTACK_MARKERS:
        if marker in lowered:
            return GuardrailResult(False, "", f"Blocked prompt-injection marker: {marker}")
    return GuardrailResult(True, redact_pii(text))


def output_guardrail(text: str) -> str:
    """Redact PII from final model output before it is shown in the UI."""

    return redact_pii(text)


def optional_nvidia_safety_check(text: str, settings: Settings) -> GuardrailResult:
    """Use NVIDIA safety model when configured; fail closed only on clear refusal.

    The deterministic guardrails above are always active. The hosted safety model
    is additive because hackathon free endpoints can be rate-limited.
    """

    if settings.force_local_model_fallback or not settings.enable_remote_safety or not settings.nvidia_safety_api_key:
        return GuardrailResult(True, text)

    try:
        client = OpenAI(api_key=settings.nvidia_safety_api_key, base_url=settings.nvidia_base_url, timeout=20.0, max_retries=0)
        response = client.chat.completions.create(
            model=settings.nvidia_safety_model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify whether the user text is safe for an enterprise RAG assistant. Return SAFE or UNSAFE with a short reason.",
                },
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0,
            max_tokens=64,
            timeout=20,
        )
        verdict = response.choices[0].message.content or ""
        first_label = re.match(r"\s*(SAFE|UNSAFE)\b", verdict.strip(), flags=re.IGNORECASE)
        if first_label and first_label.group(1).upper() == "UNSAFE":
            return GuardrailResult(False, "", verdict)
    except Exception:
        if not settings.enable_local_model_fallback:
            return GuardrailResult(False, "", "Safety endpoint unavailable.")

    return GuardrailResult(True, text)
