"""Genera los .zip de personajes y el index.json para subir a YongllyPM/Jarvis-characters."""
import json, zipfile, io, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CHARS_DIR = BASE / "assets" / "characters"
OUT_DIR = BASE / "_character_zips"

def main():
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True)

    index = {"characters": []}
    preview_png = None

    for cd in sorted(CHARS_DIR.iterdir()):
        if not cd.is_dir():
            continue
        zip_path = OUT_DIR / f"{cd.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in cd.iterdir():
                if f.is_file():
                    zf.write(f, arcname=f"{cd.name}/{f.name}")
                    if f.stem == "idle" and f.suffix == ".png":
                        preview_png = f"{cd.name}/{f.name}"

        index["characters"].append({
            "id": cd.name,
            "name": cd.name.title(),
            "description": f"Personaje {cd.name.title()}",
            "preview": preview_png or f"{cd.name}/idle.png",
            "type": "sprite",
            "download_url": f"https://github.com/YongllyPM/Jarvis-characters/raw/main/characters/{cd.name}.zip"
        })
        print(f"[OK] {cd.name}.zip")

    index_path = OUT_DIR / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] index.json generado con {len(index['characters'])} personajes")
    print(f"\nSubí todo el contenido de '{OUT_DIR}' a:")
    print("  https://github.com/YongllyPM/Jarvis-characters/tree/main")

if __name__ == "__main__":
    main()
