import json

path = r"C:\Users\ahmed\.gemini\antigravity\brain\995885c1-8b96-4539-a5e8-e0a8cde39e38\.system_generated\logs\transcript.jsonl"
out_path = r"g:\sms\vodacash_monitor\mobile\scratch\step_800_805.txt"

with open(path, "r", encoding="utf-8") as f, open(out_path, "w", encoding="utf-8") as out:
    for line in f:
        data = json.loads(line)
        idx = data.get("step_index")
        if idx is not None and 800 <= idx <= 806:
            out.write(f"=== Step {idx} ({data.get('source')}) ===\n")
            out.write(data.get("content", "") + "\n\n")
