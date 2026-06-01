# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
import time

def print_banner():
    cyan = "\033[36m"
    green = "\033[32m"
    yellow = "\033[33m"
    red = "\033[31m"
    reset = "\033[0m"
    
    # Activar colores ANSI en Windows
    os.system("") 
    
    print(f"{cyan}======================================================================={reset}")
    print(f"{cyan}      __  ___   ____   _    __  ____   _____                           {reset}")
    print(f"{cyan}     / / /   | / __ \\ / /  / / / __ \\ / ___/                           {reset}")
    print(f"{cyan} __  / / / /| |/ /_/ // /  / / /_/ / \\__ \\                            {reset}")
    print(f"{cyan}/ /_/ / / ___ // _, _// /__/ /  / _, _/ ___/ /                            {reset}")
    print(f"{cyan}\\____/ /_/  |_|/_/ |_|/____/_/  /_/ |_|/____/                             {reset}")
    print("                                                                       ")
    print(f"{green}                  SISTEMA DE INSTALACIÓN INTELIGENTE                   {reset}")
    print(f"{cyan}======================================================================={reset}")
    print()

def silent_install():
    """Run installation non-interactively (called from Inno Setup with --install)."""
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    
    # FASE 1: Limpieza
    print("[INFO] Limpiando archivos temporales...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            try: shutil.rmtree(folder)
            except Exception: pass
    for f in os.listdir("."):
        if f.endswith(".spec") or f in ["jarvis.log", "JARVIS_Beta_Installer.exe"]:
            try: os.remove(f)
            except Exception: pass
    
    # FASE 2: Entorno Virtual
    print("[INFO] Configurando entorno virtual...")
    if not os.path.exists(".venv"):
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("[OK] Entorno virtual creado.")
        except Exception as e:
            print(f"[ERROR] No se pudo crear .venv: {e}")
            sys.exit(1)
    
    # FASE 3: Dependencias
    print("[INFO] Instalando dependencias...")
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = "python"
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("[OK] Dependencias instaladas.")
    except Exception as e:
        print(f"[ERROR] Falló instalación de dependencias: {e}")
        sys.exit(1)
    
    # FASE 4: Configuración inicial
    print("[INFO] Configuración inicial...")
    config_dir = os.path.join(".", "config")
    api_keys_path = os.path.join(config_dir, "api_keys.json")
    api_keys_template = os.path.join(config_dir, "api_keys.example.json")
    rules_path = os.path.join(config_dir, "rules.json")
    
    os.makedirs(config_dir, exist_ok=True)
    
    if not os.path.exists(api_keys_path):
        if os.path.exists(api_keys_template):
            shutil.copy2(api_keys_template, api_keys_path)
        else:
            import json
            with open(api_keys_path, "w", encoding="utf-8") as f:
                json.dump({
                    "gemini_api_key": "",
                    "openrouter_api_key": "",
                    "jarvis_voice": "",
                    "jarvis_visual": "sphere",
                    "gpu_acceleration": False,
                    "window_opacity": 100,
                    "background_mode": "default",
                    "background_image": "",
                    "mic_device": "",
                    "speaker_device": "",
                    "music_platform": "ytmusic",
                    "spotify_client_id": "",
                    "spotify_client_secret": "",
                    "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
                    "nombre": "",
                    "timezone": "",
                    "ubicacion": "",
                    "telegram_token": "",
                    "telegram_enabled": False
                }, f, indent=4)
        print("[OK] api_keys.json creado.")
    
    if not os.path.exists(rules_path):
        import json
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump({"rules": []}, f, indent=4)
    
    print("")
    print("¡Instalación completada con éxito!")
    print("Ejecutá 'Iniciar JARVIS Beta.vbs' para iniciar JARVIS.")

def silent_uninstall():
    """Remove venv and caches (called from Inno Setup with --uninstall)."""
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    print("[INFO] Desinstalando JARVIS...")
    for p in [".venv", "__pycache__", "build"]:
        if os.path.exists(p):
            try:
                shutil.rmtree(p)
                print(f"[OK] '{p}' eliminado.")
            except Exception as e:
                print(f"[WARN] No se pudo eliminar '{p}': {e}")
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            try: shutil.rmtree(os.path.join(root, "__pycache__"))
            except Exception: pass
    print("[OK] Desinstalación completada.")

def main():
    # ── CLI flags para Inno Setup ──
    if "--install" in sys.argv:
        silent_install()
        return
    if "--uninstall" in sys.argv:
        silent_uninstall()
        return
    
    print_banner()
    print("Este asistente preparará a JARVIS para funcionar de forma óptima.")
    print()
    print(" [1] Comenzar instalación limpia (Recomendado)")
    print(" [2] Salir")
    print()
    
    try:
        opt = input("Selecciona una opción (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        opt = "2"
        
    if opt != "1":
        print("\nSaliendo del instalador...")
        time.sleep(1.5)
        sys.exit(0)
        
    # FASE 1: Verificación de requisitos
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 1/5] - Verificando requisitos del sistema...\033[0m")
    print()
    
    print(f"[OK] Python detectado: {sys.version.split()[0]}")
    
    print("\033[33m[INFO] Limpiando archivos temporales viejos y cachés...\033[0m")
    
    basura = ["build", "dist"]
    for folder in basura:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except Exception:
                pass
                
    archivos_basura = ["jarvis.log", "JARVIS_Beta_Installer.exe"]
    for f in os.listdir("."):
        if f.endswith(".spec") or f in archivos_basura:
            try:
                os.remove(f)
            except Exception:
                pass
                
    print("\033[32m[OK] Limpieza de residuos completada.\033[0m")
    time.sleep(1)
    
    # FASE 2: Entorno Virtual
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 2/5] - Configurando Entorno Virtual (.venv)...\033[0m")
    print()
    
    if not os.path.exists(".venv"):
        print("\033[33m[INFO] Creando un entorno virtual de Python limpio...\033[0m")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print("\033[32m[OK] Entorno virtual creado exitosamente.\033[0m")
        except Exception as e:
            print(f"\033[31m[ERROR] No se pudo crear el entorno virtual: {e}\033[0m")
            input("Presiona Enter para salir...")
            sys.exit(1)
    else:
        print("\033[32m[OK] Entorno virtual existente detectado.\033[0m")
        
    time.sleep(1)
    
    # FASE 3: Instalación de dependencias
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 3/5] - Instalando dependencias de JARVIS...\033[0m")
    print()
    print("Esto puede tomar unos minutos dependiendo de tu conexión a Internet.")
    print("Instalando requerimientos de forma segura...")
    print()
    
    venv_python = os.path.join(".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = "python"
        
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("\033[32m\n[OK] Todas las dependencias se instalaron correctamente.\033[0m")
    except Exception as e:
        print(f"\033[31m\n[ERROR] Ocurrió un error al instalar dependencias: {e}\033[0m")
        input("Presiona Enter para salir...")
        sys.exit(1)
        
    time.sleep(1)
    
    # FASE 4: Configuración inicial
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 4/5] - Configuración Inicial...\033[0m")
    print()
    
    config_dir = os.path.join(".", "config")
    api_keys_path = os.path.join(config_dir, "api_keys.json")
    api_keys_template = os.path.join(config_dir, "api_keys.example.json")
    rules_path = os.path.join(config_dir, "rules.json")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
        print("\033[32m[OK] Directorio config/ creado.\033[0m")
    
    if not os.path.exists(api_keys_path):
        if os.path.exists(api_keys_template):
            shutil.copy2(api_keys_template, api_keys_path)
            print("\033[32m[OK] Archivo api_keys.json creado desde plantilla.\033[0m")
            print("\033[33m[INFO] Al iniciar JARVIS se te pedirán tus API Keys de Gemini y OpenRouter.\033[0m")
        else:
            import json
            default_config = {
                "gemini_api_key": "",
                "openrouter_api_key": "",
                "jarvis_voice": "",
                "jarvis_visual": "sphere",
                "gpu_acceleration": False,
                "window_opacity": 100,
                "background_mode": "default",
                "background_image": "",
                "mic_device": "",
                "speaker_device": "",
                "music_platform": "ytmusic",
                "spotify_client_id": "",
                "spotify_client_secret": "",
                "spotify_redirect_uri": "http://127.0.0.1:8888/callback",
                "nombre": "",
                "timezone": "",
                "ubicacion": "",
                "telegram_token": "",
                "telegram_enabled": False
            }
            with open(api_keys_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            print("\033[32m[OK] Archivo api_keys.json creado.\033[0m")
            print("\033[33m[INFO] Al iniciar JARVIS se te pedirán tus API Keys de Gemini y OpenRouter.\033[0m")
    else:
        print("\033[32m[OK] Archivo api_keys.json existente detectado.\033[0m")
    
    if not os.path.exists(rules_path):
        import json
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump({"rules": []}, f, indent=4)
        print("\033[32m[OK] Archivo rules.json creado.\033[0m")
    else:
        print("\033[32m[OK] Archivo rules.json existente detectado.\033[0m")
    
    time.sleep(1)
    
    # FASE 5: Acceso directo
    os.system("cls")
    print_banner()
    print("\033[36m [FASE 5/5] - Creación de Accesos Directos...\033[0m")
    print()
    print("Creando acceso directo en tu Escritorio para un inicio rápido...")
    print()
    
    try:
        current_dir = os.getcwd()
        svg_path = os.path.join(current_dir, "assets", "jarvis_icono.svg")
        icon_path = os.path.join(current_dir, "assets", "jarvis_icono.ico")
        target_vbs = os.path.join(current_dir, "Iniciar JARVIS Beta.vbs")
        
        # Generar ICO desde SVG (necesario para el acceso directo en Windows)
        if os.path.exists(svg_path) and not os.path.exists(icon_path):
            try:
                ps_script = f"""
                Add-Type -AssemblyName System.Drawing
                $bmp = New-Object System.Drawing.Bitmap 256,256
                $g = [System.Drawing.Graphics]::FromImage($bmp)
                $g.SmoothingMode = 'HighQuality'
                $g.Clear([System.Drawing.Color]::Transparent)
                $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
                    (New-Object System.Drawing.Point 0,0),
                    (New-Object System.Drawing.Point 256,256),
                    [System.Drawing.Color]::FromArgb(30,41,59),
                    [System.Drawing.Color]::FromArgb(11,15,25)
                )
                $g.FillEllipse($brush, 10, 10, 236, 236)
                $pen = New-Object System.Drawing.Pen(
                    [System.Drawing.Color]::FromArgb(96,165,250), 6
                )
                $g.DrawEllipse($pen, 10, 10, 236, 236)
                $font = New-Object System.Drawing.Font('Segoe UI', 120, [System.Drawing.FontStyle]::Bold)
                $fmt = New-Object System.Drawing.StringFormat
                $fmt.Alignment = 'Center'
                $fmt.LineAlignment = 'Center'
                $g.DrawString('J', $font, [System.Drawing.Brushes]::DodgerBlue,
                    [System.Drawing.RectangleF]::new(0,20,256,256), $fmt)
                $g.Dispose()
                $ico = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
                $fs = [System.IO.FileStream]::new('{icon_path}', [System.IO.FileMode]::Create)
                $ico.Save($fs)
                $fs.Close()
                $bmp.Dispose()
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True, timeout=60
                )
            except Exception:
                pass
            
            if os.path.exists(icon_path):
                print("\033[32m[OK] Icono ICO generado desde SVG.\033[0m")
            else:
                print("\033[33m[ADVERTENCIA] SVG a ICO falló, se usará el SVG directo.\033[0m")
                icon_path = svg_path
        elif os.path.exists(icon_path):
            print("\033[32m[OK] Icono ICO existente detectado.\033[0m")
        else:
            print("\033[33m[ADVERTENCIA] No se encontró SVG, se usará icono por defecto.\033[0m")
            icon_path = ""
        
        # Crear acceso directo con PowerShell
        ps_cmd = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut(([System.Environment]::GetFolderPath('Desktop')+'\\JARVIS AI.lnk'));"
            f"$s.TargetPath='{target_vbs}';"
            f"$s.WorkingDirectory='{current_dir}';"
            f"$s.IconLocation='{icon_path}';"
            f"$s.Description='Lanzador de JARVIS AI (Admin)';"
            f"$s.Save()"
        )
        
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            lnk_path = os.path.join(desktop, "JARVIS AI.lnk")
            if os.path.exists(lnk_path):
                with open(lnk_path, "rb") as f:
                    data = bytearray(f.read())
                data[21] = data[21] | 0x20
                with open(lnk_path, "wb") as f:
                    f.write(data)
        except Exception:
            pass
        
        print("\033[32m[OK] Acceso directo 'JARVIS AI' creado en el Escritorio (con permisos de Admin).\033[0m")
    except Exception as e:
        print(f"\033[33m[ADVERTENCIA] No se pudo crear el acceso directo de forma automática: {e}\033[0m")
        
    time.sleep(1)
    
    # Pantalla Final
    os.system("cls")
    print_banner()
    print("\033[32m=======================================================================")
    print("     ¡INSTALACIÓN Y CONFIGURACIÓN COMPLETADA CON ÉXITO!")
    print("=======================================================================\033[0m")
    print()
    print("JARVIS está listo para servirte.")
    print("Al iniciar el sistema por primera vez se te solicitarán tus API Keys")
    print("para Gemini y OpenRouter automáticamente de forma visual.")
    print()
    print(" [1] Iniciar JARVIS ahora mismo")
    print(" [2] Salir")
    print()
    
    try:
        launch_opt = input("Selecciona una opción (1-2): ").strip()
    except (KeyboardInterrupt, EOFError):
        launch_opt = "2"
        
    if launch_opt == "1":
        print("Iniciando JARVIS...")
        try:
            os.startfile("Iniciar JARVIS Beta.vbs")
        except Exception:
            subprocess.Popen(["wscript.exe", "Iniciar JARVIS Beta.vbs"])
            
    print("\nGracias por usar el instalador de JARVIS AI.")
    time.sleep(2)

if __name__ == "__main__":
    main()
