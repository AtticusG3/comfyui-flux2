"""One-off miner for continual-learning; delete after use."""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\Kev\.cursor\projects\c-Cursor-IDE-comfyui-flux2\agent-transcripts")
TO_PROCESS = [
    ROOT / "0e2d27db-4415-4195-b6d2-f687908c27f6" / "0e2d27db-4415-4195-b6d2-f687908c27f6.jsonl",
    ROOT / "46fbb028-0867-4bbd-9f61-66e2c789bbde" / "46fbb028-0867-4bbd-9f61-66e2c789bbde.jsonl",
    ROOT / "4822bcb8-7735-449b-a323-9c27bb87d3f3" / "4822bcb8-7735-449b-a323-9c27bb87d3f3.jsonl",
    ROOT / "8eebd40f-442b-479f-827c-f9c881c284b8" / "8eebd40f-442b-479f-827c-f9c881c284b8.jsonl",
    ROOT / "8f09abf7-bc97-4219-9f82-cbf742b97f1d" / "8f09abf7-bc97-4219-9f82-cbf742b97f1d.jsonl",
    ROOT / "8f5d9da3-f3d4-4265-a608-8fd445532011" / "8f5d9da3-f3d4-4265-a608-8fd445532011.jsonl",
]
KEYWORDS = (
    "prefer", "always", "never", "do not", "don't", "keep", "bundled",
    "workflow", "reseed", "saveimage", "klein", "layerutility", "must",
    "should not", "avoid", "default",
)


def extract_text(msg):
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            parts = []
            for p in c:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
            return "\n".join(parts)
    return ""


def main():
    for fp in TO_PROCESS:
        print("=" * 80)
        print(fp.parent.name)
        print("=" * 80)
        for line in fp.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = o.get("role") or o.get("type")
            if role not in ("user", "assistant"):
                continue
            text = extract_text(o.get("message") or o.get("content") or o)
            if not text or len(text) < 20:
                continue
            low = text.lower()
            if role == "user" or any(k in low for k in KEYWORDS):
                preview = text[:2000].replace("\n", " ")
                if len(text) > 2000:
                    preview += "..."
                print(f"[{role}] {preview[:1000]}")
                print("---")


if __name__ == "__main__":
    main()
