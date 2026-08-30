from pathlib import Path
import json

def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print("Hata: ", e)
        return {}

def dump_json(path, data):
    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            return True
    except Exception as e:
        print("Hata: ", e)
        return False
