import os
import threading
from llama_cpp import Llama

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL_PATH = os.path.join(BASE_DIR, "models", "tinyllama-1.1b-chat.Q4_K_M.gguf")

_LLM = None
_LOCK = threading.Lock()


def _thread_count():
    cpu = os.cpu_count() or 2
    return max(1, min(4, cpu))


def get_llm():
    global _LLM
    if _LLM is None:
        with _LOCK:
            if _LLM is None:
                _LLM = Llama(
                    model_path=MODEL_PATH,
                    n_ctx=2048,
                    n_threads=_thread_count(),
                    n_batch=64,
                    n_gpu_layers=0,
                    seed=42,
                    verbose=False,
                )
    return _LLM


def one_line(text, max_words=None):
    words = text.split()
    if max_words is not None:
        words = words[:max_words]
    return " ".join(words)


def safe_generate(prompt, max_tokens=256):
    try:
        llm = get_llm()
        out = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=0.2,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=None,
        )
        text = out["choices"][0]["text"]
        return (text or "").strip()
    except Exception:
        return ""
