from pathlib import Path

from src.config.secrets import parse_apis_file


def test_parse_apiss_fallback_maps_model_keys(tmp_path: Path) -> None:
    (tmp_path / "apiss.txt").write_text(
        '''
from openai import OpenAI
client = OpenAI(base_url = "https://integrate.api.nvidia.com/v1", api_key = "nvapi-qwen")
completion = client.chat.completions.create(model="qwen/qwen3-coder-480b-a35b-instruct")
nv-embed-v1
api key:nvapi-embed
nv-embedcode-7b-v1
api key:nvapi-code
rerank-qa-mistral-4b
api key:nvapi-rerank
headers = {"Authorization": "Bearer nvapi-mistral"}
payload = {"model": "mistralai/mistral-large-3-675b-instruct-2512"}
nemotron-content-safety-reasoning-4b
api key:nvapi-safety
gliner-pii
api key:gliner-pii
''',
        encoding="utf-8",
    )
    parsed = parse_apis_file(tmp_path)
    assert parsed["NVIDIA_QWEN_API_KEY"] == "nvapi-qwen"
    assert parsed["NVIDIA_EMBED_API_KEY"] == "nvapi-embed"
    assert parsed["NVIDIA_EMBEDCODE_API_KEY"] == "nvapi-code"
    assert parsed["NVIDIA_RERANK_API_KEY"] == "nvapi-rerank"
    assert parsed["NVIDIA_MISTRAL_API_KEY"] == "nvapi-mistral"
    assert parsed["NVIDIA_SAFETY_API_KEY"] == "nvapi-safety"
