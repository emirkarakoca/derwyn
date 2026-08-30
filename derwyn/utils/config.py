from pathlib import Path
from derwyn.utils.jsonutil import load_json, dump_json

root = Path(__file__).resolve().parents[2]
data = root / "data"
var = root / "var"

systems_path = data / "systems.json"
db_path = data / "libretrodb" / "libretrodb.sqlite"

paths_path = var / "paths.json"
games_path = var / "games.json"
cache_path = var / "cache" / "games_cache.json"

def load_paths():
    paths = load_json(paths_path)
    if "roms_dir" not in paths:
        raise SystemExit("paths.json eksik veya bozuk.")
    return paths

def load_systems():
    systems = load_json(systems_path)
    if not systems:
        raise SystemExit("systems.json bulunamadı.")
    return systems

def load_games():
    games = load_json(games_path)
    if not games:
        raise SystemExit("games.json bulunamadı veya boş.")
    return games

def load_cache():
    return load_json(cache_path)

def save_games(games):
    games_path.parent.mkdir(parents=True, exist_ok=True)
    return dump_json(games_path, games)

def save_cache(cache):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return dump_json(cache_path, cache)