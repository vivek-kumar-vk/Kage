"""Calls the local model running on this laptop through Ollama.

WHY THIS IS NOT A ROUTER MODEL AND NOT A TOOL
    do_one_task.py exists to pick between metered, hosted providers -
    it checks a free-tier allowance, checks Rule 5 for money data,
    writes a row to the call log that Claude Code's own token cost
    sits beside on the Models screen. None of that applies here: a
    local model costs nothing, has no quota, and never sends a byte
    off this machine. Routing it through do_one_task.py would be
    pretending it has constraints it does not have.

    It is not registered in Shared_By_All_Agents/Tools/ either.
    the_tool_registry.py's own definition of a tool is "deterministic
    ... never calls a model" - a function that calls an LLM is exactly
    the thing that definition excludes, on purpose, so a person
    reading an agent's TOOLS_I_MAY_USE list can trust that every name
    on it is instant and predictable.

    So this is its own small file, called directly by an agent's
    what_i_can_do.py, the same way it would call any other library
    function - just one that happens to think for a few seconds.

WHAT IT REFUSES TO DO
    Nothing about money or privacy - a fully local model raises none
    of Rule 5's concerns, which is the whole point of running one.
    What it does refuse is pretending Ollama is running when it is
    not: every function here returns has_data: False with a plain
    reason rather than letting a connection error look like a bug
    somewhere else.

RUN IT
    cd <repo root>
    python Shared_By_All_Agents\\call_the_local_model.py "say hello"
"""

from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_model_settings                                            # noqa: E402

OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
# Small on purpose - moondream is ~1.8B, chosen specifically so it does
# not compete with qwen3:8b for this laptop's 6GB VRAM. A bigger vision
# model reads images better but Ollama would have to swap it in and out
# of VRAM against the text model on every alternating step.
DEFAULT_VISION_MODEL = "moondream"
TIMEOUT_SECONDS = 300.0   # a local model on a laptop GPU is slow, not free


def is_ollama_running() -> bool:
    try:
        urllib.request.urlopen(OLLAMA_HOST, timeout=3)
        return True
    except Exception:                                                # noqa: BLE001
        return False


def _post(path: str, body: dict) -> tuple[dict | None, str | None]:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_HOST}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8")), None
    except urllib.error.URLError as e:
        return None, (
            f"Could not reach Ollama at {OLLAMA_HOST} ({e}). Is it running? "
            "It usually starts itself after install; on Windows, look for "
            "its icon in the system tray."
        )
    except TimeoutError:
        return None, f"No answer within {TIMEOUT_SECONDS:g}s - the model may still be loading."
    except Exception as e:                                           # noqa: BLE001
        return None, str(e)[:200]


def ask(prompt: str, *, model: str = DEFAULT_MODEL, temperature: float = 0.3,
       system: str = "") -> dict:
    """One turn, no memory of previous calls. Returns has_data, text,
    model, and seconds_taken - never raises for an ordinary failure."""
    if not local_model_settings.is_enabled():
        return {"has_data": False, "note": "the local model switch is off",
               "model": model, "seconds_taken": 0}
    started = time.time()
    body = {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        body["system"] = system

    data, error = _post("/api/generate", body)
    seconds = round(time.time() - started, 1)

    if error:
        return {"has_data": False, "note": error, "model": model, "seconds_taken": seconds}
    if not data or "response" not in data:
        return {"has_data": False, "note": "Ollama answered with no 'response' field.",
               "model": model, "seconds_taken": seconds}

    return {
        "has_data": True, "text": data["response"], "model": model,
        "seconds_taken": seconds,
        "tokens_in": data.get("prompt_eval_count", 0),
        "tokens_out": data.get("eval_count", 0),
    }


_FALLBACK_IMAGE_PROMPT = "What text, title, or numbers do you see in this image?"


def describe_an_image(image_path, *, prompt: str = "", model: str = DEFAULT_VISION_MODEL) -> dict:
    """What a vision model sees in one image, as plain text - which
    then goes through the exact same knowledge-base pipeline as
    anything else read from a web page or a document. The model never
    changes what "a source" means: the image's own file path becomes
    the source in the note.

    `prompt` defaults to a factual-description request; pass your own
    for a narrower ask (e.g. "read every number in this table").
    """
    if not local_model_settings.is_enabled():
        return {"has_data": False, "note": "the local model switch is off", "model": model}

    path = Path(image_path)
    if not path.exists():
        return {"has_data": False, "note": f"no such file: {path}", "model": model}

    started = time.time()
    # This exact wording, in this order - moondream's 2048-token context
    # leaves little room once the image itself is encoded, and swapping
    # these two sentences (or appending "Do not guess..." after the
    # description request instead of before it) reproducibly made the
    # model emit an immediate stop token and return empty text on
    # several real Dump/ covers, confirmed against the raw Ollama API,
    # not this wrapper.
    prompt = prompt or (
        "Do not guess at anything you cannot actually read. Describe "
        "exactly what is in this image - any text, numbers, tables, or "
        "diagrams, transcribed as accurately as you can."
    )
    image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    # A low temperature, not Ollama's default (~0.8) - this is a factual
    # transcription task, and the small 1B vision model would otherwise
    # occasionally sample an immediate stop token on the first step and
    # return has_data: True with empty text, especially on longer prompts.
    body = {"model": model, "prompt": prompt, "images": [image_b64], "stream": False,
           "options": {"temperature": 0.1}}

    data, error = _post("/api/generate", body)

    # Even with the wording above, a handful of real covers still made
    # this small model emit an immediate stop token and return an empty
    # "response" - confirmed on the raw Ollama API, not a bug in this
    # wrapper. One retry with a shorter, differently-worded prompt on
    # the SAME image reliably got a real answer every time this was
    # checked by hand, so it is worth one automatic attempt before
    # giving up on a real cover. Never retried a second time - if a
    # short, simple ask still gets nothing, the image likely has none.
    if data and data.get("response", "") == "" and prompt != _FALLBACK_IMAGE_PROMPT:
        body["prompt"] = _FALLBACK_IMAGE_PROMPT
        data, error = _post("/api/generate", body)

    seconds = round(time.time() - started, 1)

    if error:
        return {"has_data": False, "note": error, "model": model, "seconds_taken": seconds}
    if not data or "response" not in data:
        return {"has_data": False, "note": "Ollama answered with no 'response' field.",
               "model": model, "seconds_taken": seconds}

    return {"has_data": True, "text": data["response"], "model": model, "seconds_taken": seconds}


def embed(text: str, *, model: str = DEFAULT_EMBED_MODEL) -> dict:
    """A vector for one piece of text, for the knowledge base's search
    index. Returns has_data: False rather than a zero vector if Ollama
    is not reachable - a zero vector would look like a real answer to
    every cosine-similarity comparison that reads it later."""
    data, error = _post("/api/embeddings", {"model": model, "prompt": text})
    if error:
        return {"has_data": False, "note": error}
    if not data or "embedding" not in data:
        return {"has_data": False, "note": "Ollama answered with no 'embedding' field."}
    return {"has_data": True, "vector": data["embedding"], "model": model}


def which_models_are_pulled() -> list[str]:
    """What `ollama pull` has actually downloaded, so a caller can say
    "the model is not installed yet" instead of a confusing timeout."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except Exception:                                                # noqa: BLE001
        return []


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    prompt = " ".join(sys.argv[1:])

    if not is_ollama_running():
        print(f"Ollama is not answering at {OLLAMA_HOST}.")
        return

    pulled = which_models_are_pulled()
    print(f"models pulled: {', '.join(pulled) or '(none)'}")
    if DEFAULT_MODEL not in pulled and not any(p.startswith(DEFAULT_MODEL.split(':')[0]) for p in pulled):
        print(f"{DEFAULT_MODEL} is not pulled yet - run: ollama pull {DEFAULT_MODEL}")
        return

    result = ask(prompt)
    if result["has_data"]:
        print(f"\n[{result['seconds_taken']}s] {result['text']}")
    else:
        print(f"\ncould not get an answer: {result['note']}")


if __name__ == "__main__":
    main()
