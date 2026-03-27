import json
import os


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def read_jsonl(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)

