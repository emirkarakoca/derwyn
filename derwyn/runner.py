import json
import subprocess
from pathlib import Path

def main():
    games_json = Path("/home/emir/Projeler/qt-project/data/games.json")
    with open(games_json, "r") as file:
        games_data = json.load(file)

    paths_json = Path("/home/emir/Projeler/qt-project/data/paths.json")
    with open(paths_json, "r") as file:
        paths_data = json.load(file)

    systems_json = Path("/home/emir/Projeler/qt-project/data/systems.json")
    with open(systems_json, "r") as file:
        systems_data = json.load(file)

    for system, games in games_data.items():
        for game in games:
            display_name = game.get("display_name") or game.get("rom_name")
            platform = game.get("platform")
            print(f"[{index}] {display_name} ({platform})")


    choice = input("\nindex seç: ")
    index = int(choice)

    selected_game = games_data["gba"][index]
    rom_path = selected_game.get("path")
    platform_name = selected_game.get("platform")

    print(f"\noyun: {selected_game.get('game_display_name')}")
    print(f"platform: {platform_name}")
    print(f"dosya Yolu: {rom_path}")

    selected_system = None
    for sys_key, sys_info in systems_data.items():
        if sys_info.get("name").lower() == platform_name.lower():
            selected_system = sys_info
            break

    if not selected_system:
        return

    core_dir = paths_data.get("cores_dir", "")
    core_path = selected_system.get("core").replace("{core_dir}", core_dir)

    subprocess.Popen(["retroarch", "-L", core_path, rom_path])

if __name__ == "__main__":
    main()