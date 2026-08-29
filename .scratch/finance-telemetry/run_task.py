#!/usr/bin/env python
"""run_task.py <task-id> <prompt-file> <out-file>

POST the prompt file to Model A (llama-server, OpenAI-compatible on :8080),
strip a leading/trailing markdown code fence, write <out-file>.
Raw JSON response is kept in raw/<task-id>.json for inspection.
"""
from __future__ import annotations
import json, sys, time, urllib.request, pathlib, re

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
HERE = pathlib.Path(__file__).resolve().parent


def strip_fence(text: str) -> str:
    t = text.strip()
    # ```lang\n ... \n```
    m = re.match(r"^```[a-zA-Z0-9_-]*\n(.*)\n```$", t, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"
    # tolerate a stray opening/closing fence
    t = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", t)
    t = re.sub(r"\n```$", "", t)
    return t.strip() + "\n"


def main() -> None:
    task_id, prompt_file, out_file = sys.argv[1], sys.argv[2], sys.argv[3]
    append = "--append" in sys.argv[4:]
    prompt = pathlib.Path(prompt_file).read_text(encoding="utf-8")

    body = json.dumps({
        "model": "model-a",
        "temperature": 0,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    t0 = time.time()
    req = urllib.request.Request(ENDPOINT, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    dt = time.time() - t0

    (HERE / "raw").mkdir(exist_ok=True)
    (HERE / "raw" / f"{task_id}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    content = data["choices"][0]["message"]["content"]
    code = strip_fence(content)
    out = pathlib.Path(out_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    if append:
        prev = out.read_text(encoding="utf-8") if out.exists() else ""
        out.write_text(prev.rstrip() + "\n\n" + code, encoding="utf-8")
    else:
        out.write_text(code, encoding="utf-8")

    usage = data.get("usage", {})
    print(f"[{task_id}] {dt:.1f}s  prompt={usage.get('prompt_tokens','?')} "
          f"completion={usage.get('completion_tokens','?')}  -> {out_file} ({len(code)} chars)")


if __name__ == "__main__":
    main()
