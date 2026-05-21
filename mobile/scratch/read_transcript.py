import json
import sys

path = r"C:\Users\ahmed\.gemini\antigravity\brain\995885c1-8b96-4539-a5e8-e0a8cde39e38\.system_generated\logs\transcript.jsonl"
out_path = r"g:\sms\vodacash_monitor\mobile\scratch\read_transcript.txt"

with open(path, "r", encoding="utf-8") as f, open(out_path, "w", encoding="utf-8") as out:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            out.write(f"--- Step {data.get('step_index')} ({data.get('created_at')}) ---\n")
            out.write(data.get("content") + "\n\n")
