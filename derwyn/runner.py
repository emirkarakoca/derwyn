import subprocess

from derwyn.utils import config
#burası şimdilik test amaçlı

def main():
    games_data = config.load_games()
    paths_data = config.load_paths()
    systems_data = config.load_systems()

    choices = []
    for system_id, games in games_data.items():
        for game in games:
            choices.append((system_id, game))

    if not choices:
        print("games.json boş")
        return

    for index, (system_id, game) in enumerate(choices):
        display_name = game.get("display_name") or game.get("rom_name")
        platform_name = game.get("platform")
        print(f"[{index}] {display_name} ({platform_name})")

    try:
        index = int(input("\nindex seç:"))
        system_id, selected_game = choices[index]
    except Exception as e:
        print(f"Geçersin seçim: {e}")

    rom_path = selected_game.get("path")
    platform = selected_game.get("platform")
    display_name = selected_game.get("display_name") or selected_game.get("rom_name")

    print(f"\noyun: {selected_game.get('game_display_name')}")
    print(f"platform: {platform_name}")
    print(f"dosya Yolu: {rom_path}")

    selected_system = None
    for system_key, system_info in systems_data.items():
        if system_info.get("name").lower() == platform_name.lower():
            selected_system = system_info
            break

    if not selected_system:
        print(f"{platform} bulunamadı")
        return

    core_dir = paths_data.get("cores_dir", "")
    core_path = selected_system.get("core").replace("{core_dir}", core_dir)
    if not core_path:
        print("core bulunamadı")
    
    try:
        subprocess.Popen(["retroarch", "-f", "-L", core_path, rom_path])
    except Exception as e:
        print("Hata: ", e)

if __name__ == "__main__":
    main()