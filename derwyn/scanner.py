from pathlib import Path
import hashlib
import zipfile as z
import sqlite3
import json

from derwyn.utils import config 

rom_dir = Path(config.load_paths()["roms_dir"])
systems = config.load_systems()
old_cache = config.load_cache()

archive_list = {
    ".zip"
}

valid_extensions = set()
for system, system_data in systems.items():
    for extension in system_data.get("extensions", []):
        valid_extensions.add(extension.lower())

def calculate_md5(file_object, chunk_size=1024 * 1024): #dosya büyüklüğüne göre chunk ayarlanacak
    md5 = hashlib.md5()
    while chunk := file_object.read(chunk_size):
        md5.update(chunk)
    return md5.hexdigest().upper()

def load_database():
    query = """
    SELECT
        roms.id AS rom_id,
        roms.md5,
        roms.name AS rom_name,

        games.id AS game_id,
        games.serial_id,
        games.display_name,
        games.full_name,
        games.users,
        games.release_year,
        games.release_month,
        games.platform_id,

        platforms.name AS platform,
        developers.name AS developer,
        publishers.name AS publisher,
        ratings.name AS rating,
        franchises.name AS franchise,
        regions.name AS region,
        genres.name AS genre,
        manufacturers.name AS manufacturer

    FROM roms

    JOIN games
        ON games.serial_id = roms.serial_id

    LEFT JOIN developers
        ON developers.id = games.developer_id

    LEFT JOIN publishers
        ON publishers.id = games.publisher_id

    LEFT JOIN ratings
        ON ratings.id = games.rating_id

    LEFT JOIN franchises
        ON franchises.id = games.franchise_id

    LEFT JOIN regions
        ON regions.id = games.region_id

    LEFT JOIN genres
        ON genres.id = games.genre_id

    LEFT JOIN platforms
        ON platforms.id = games.platform_id

    LEFT JOIN manufacturers
        ON manufacturers.id = platforms.manufacturer_id

    """

    with sqlite3.connect(config.db_path) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(query).fetchall()
        database = {row["md5"]: dict(row) for row in rows}
    return database

database = load_database()

def find_game_by_cache(file, file_name=None):
    path = str(file)
    size = file.stat().st_size
    for system_id, games in old_cache.items():
        for game in games:
            if game.get("path") == path and game.get("size") == size and (file_name is None or game.get("file_name") == file_name):
                return system_id, game

            if game.get("size") != size:
                continue

            if file_name is not None:
                if game.get("file_name") != file_name:
                    continue
            else:
                if Path(game.get("path")).name != file.name:
                    continue

            game["path"] = path
            return system_id, game
    return None, None

def add_games_to_cache(system_id, game):
    old_cache.setdefault(system_id, []).append(game.copy())

def find_game_by_md5(md5):
    return database.get(md5)

def find_system_by_platform_id(platform_id):
    for system_id, system in systems.items():
        if system["id"] == platform_id:
            return system_id, system
    return None, None

def scan_roms():
    games = {}
    for file in rom_dir.rglob("*"):
        if file.is_dir():
            continue

        size = file.stat().st_size

        if size > 1024 ** 3:
            continue

        suffix = file.suffix.lower()

        if suffix in archive_list: #gözden geçirilecek
            try:
                with z.ZipFile(file, "r") as zf:
                    for f_inzip in zf.infolist():
                        if f_inzip.is_dir():
                            continue
                        print("inzip:", f_inzip.filename)

                        system_id, cached_game = find_game_by_cache(file, f_inzip.filename)
                        if cached_game is not None:
                            print("cache bulundu: ", cached_game["display_name"])
                            games.setdefault(system_id,[]).append(cached_game.copy())
                            continue

                        with zf.open(f_inzip, "r") as rom:
                            md5 = calculate_md5(rom)

                        game = find_game_by_md5(md5)
                        if game is None:
                            print("bulunamadı: ", f_inzip.filename)
                            continue

                        system_id, system = find_system_by_platform_id(game["platform_id"])
                        if system is None:
                            print("sistem bulunamadı: ", game["platform_id"])
                            continue

                        game = game.copy()
                        game["path"] = str(file)
                        game["file_name"] = f_inzip.filename
                        game["size"] = int(size)

                        add_games_to_cache(system_id, game)
                        games.setdefault(system_id, []).append(game)
                        print("bulundu: ", game["display_name"])

            except Exception as e:
                print("geçersiz zip: ", file, e)
        
        elif suffix in valid_extensions:
            system_id, cached_game = find_game_by_cache(file)
            if cached_game is not None:
                print("cache bulundu: ", cached_game["display_name"])
                games.setdefault(system_id, []).append(cached_game.copy())
                continue
            try:

                with file.open("rb") as rom:
                    md5 = calculate_md5(rom)

            except:
                print("dosya okunamadı: ", file)
                continue

            game = find_game_by_md5(md5)
            if game is None:
                print("bulunamadı: ", file.name)
                continue

            system_id, system = find_system_by_platform_id(game["platform_id"])


            if system is None:
                print("sistem bulunamadı:", game["platform_id"])
                continue

            game = game.copy()
            game["path"] = str(file)
            game["size"] = int(size)

            add_games_to_cache(system_id, game)
            games.setdefault(system_id, []).append(game)

            print("bulundu:", game["display_name"])

    if not config.save_games(games):
        print("games.json yazılamadı")
    
    if not config.save_cache(old_cache):
        print("games_cache.json yazılamadı")

if __name__ == "__main__":
    scan_roms()