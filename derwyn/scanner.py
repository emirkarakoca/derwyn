from pathlib import Path
import hashlib
import sqlite3
import zipfile
import rarfile
import py7zr
import tarfile

from derwyn.utils import config 

default_rom_dir = Path(config.load_paths()["roms_dir"])
systems = config.load_systems()
old_cache = config.load_cache()

valid_extensions = set()
for system, system_data in systems.items():
    for extension in system_data.get("extensions", []):
        valid_extensions.add(extension.lower())

def get_archive_kind(filename):
    name = filename.lower()
    if name.endswith(".tar"):
        return "tar"
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar"
    elif name.endswith(".tar.bz2") or name.endswith(".tbz2"):
        return "tar"
    elif name.endswith(".tar.xz") or name.endswith(".txz"):
        return "tar"        
    elif name.endswith(".zip"):
        return "zip"
    elif name.endswith(".rar"):
        return "rar"
    elif name.endswith(".7z"):
        return "7z"
    else:    
        return None


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

class RomScanner:
    def __init__(self, old_cache, database, rom_dir=default_rom_dir):
        self.old_cache = old_cache
        self.database = database
        self.rom_dir = rom_dir
        self.games = {}

    def find_game_by_cache(self, file, file_name=None):
        path = str(file)
        size = file.stat().st_size
        for system_id, games in self.old_cache.items():
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

    def add_games_to_cache(self, system_id, game):
        self.old_cache.setdefault(system_id, []).append(game.copy())

    def find_game_by_md5(self, md5):
        return self.database.get(md5)

    def find_system_by_platform_id(self, platform_id):
        for system_id, system in systems.items():
            if system["id"] == platform_id:
                return system_id, system
        return None, None

    def register_game(self, file, member_name, size, md5):
        game = self.find_game_by_md5(md5)
        if game is None:
            print("bulunamadı: ", member_name)
            return
 
        system_id, system = self.find_system_by_platform_id(game["platform_id"])
        if system is None:
            print("sistem bulunamadı: ", game["platform_id"])
            return
 
        game = game.copy()
        game["path"] = str(file)
        game["file_name"] = member_name
        game["size"] = int(size)  # şimdilik dursun
 
        self.add_games_to_cache(system_id, game)
        self.games.setdefault(system_id, []).append(game)
        print("bulundu: ", game["display_name"])

    def scan_archive(self, file, kind, size):
        try:
            if kind == "zip":
                self.scan_zip_or_rar(file, size, zipfile.ZipFile, zipfile.BadZipFile)
            elif kind == "rar":
                self.scan_zip_or_rar(file, size, rarfile.RarFile, rarfile.BadRarFile)
            elif kind == "tar":
                self.scan_tar(file, size)
            elif kind == "7z":
                self.scan_7z(file, size)
        
        except (OSError, RuntimeError, NotImplementedError) as e:
            print("Arşiv okunamadı: ", file, e)

    def scan_zip_or_rar(self, file, size, archive_cls, bad_file_exc):
        with archive_cls(file, "r") as archive:
            for info in archive.infolist():
                is_dir = info.is_dir() if hasattr(info, "is_dir") else info.isdir()
                if is_dir:
                    continue
 
                if info.compress_size and info.file_size / info.compress_size > 1000:
                    continue
 
                member_suffix = Path(info.filename).suffix.lower()
                if member_suffix not in valid_extensions:
                    continue
 
                system_id, cached_game = self.find_game_by_cache(file, info.filename)
                if cached_game is not None:
                    print("cache bulundu: ", cached_game["display_name"])
                    self.games.setdefault(system_id, []).append(cached_game.copy())
                    continue
 
                try:
                    with archive.open(info, "r") as rom:
                        md5 = calculate_md5(rom)
                except (bad_file_exc, OSError, RuntimeError, NotImplementedError) as e:
                    print("arşiv içindeki dosya okunamadı: ", info.filename, e)
                    continue
 
                self.register_game(file, info.filename, size, md5)

    def scan_7z(self, file, size):
        with py7zr.SevenZipFile(file, "r") as archive:
            targets = []
            for info in archive.list():
                if info.is_directory:
                    continue
 
                member_suffix = Path(info.filename).suffix.lower()
                if member_suffix not in valid_extensions:
                    continue
 
                system_id, cached_game = self.find_game_by_cache(file, info.filename)
                if cached_game is not None:
                    print("cache bulundu: ", cached_game["display_name"])
                    self.games.setdefault(system_id, []).append(cached_game.copy())
                    continue
 
                targets.append(info.filename)
 
            if not targets:
                return
 
            extracted = archive.read(targets=targets)
            for member_name, stream in extracted.items():
                md5 = calculate_md5(stream)
                self.register_game(file, member_name, size, md5)

    def scan_tar(self, file, size):
        with tarfile.open(file, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
 
                member_suffix = Path(member.name).suffix.lower()
                if member_suffix not in valid_extensions:
                    continue
 
                system_id, cached_game = self.find_game_by_cache(file, member.name)
                if cached_game is not None:
                    print("cache bulundu: ", cached_game["display_name"])
                    self.games.setdefault(system_id, []).append(cached_game.copy())
                    continue
 
                extracted = tf.extractfile(member)
                if extracted is None:
                    print("tar içindeki dosya okunamadı: ", member.name)
                    continue
 
                md5 = calculate_md5(extracted)
                self.register_game(file, member.name, size, md5)
 

 
    def scan_rom(self, file, size):
        system_id, cached_game = self.find_game_by_cache(file)
        if cached_game is not None:
            print("cache bulundu: ", cached_game["display_name"])
            self.games.setdefault(system_id, []).append(cached_game.copy())
            return
 
        try:
            with file.open("rb") as rom:
                md5 = calculate_md5(rom)
        
        except OSError as e:
            print("dosya okunamadı: ", file, e)
            return
 
        self.register_game(file, file.name, size, md5)


    def scan(self):
        for file in self.rom_dir.rglob("*"):
            if file.is_dir():
                continue
 
            size = file.stat().st_size
 
            if size > 1024 ** 3:
                continue
 
            kind = get_archive_kind(file.name)
            if kind is not None:
                self.scan_archive(file, kind, size)
            
            elif file.suffix.lower() in valid_extensions:
                self.scan_rom(file, size)
 
        if not config.save_games(self.games):
            print("games.json yazılamadı")
 
        if not config.save_cache(self.old_cache):
            print("games_cache.json yazılamadı")


if __name__ == "__main__":
    scanner = RomScanner(old_cache, database)
    scanner.scan()


# edge hash hesaplama eklenecek
# duplicate rom
# şimdilik 1gb boyutundan küçük dosyaları tarıyor daha sonra çaresine bakıcam
