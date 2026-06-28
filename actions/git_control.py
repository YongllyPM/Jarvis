import subprocess
import os


def git_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status")
    repo_path = parameters.get("path", os.getcwd())
    message = parameters.get("message", "Actualización automática")
    branch = parameters.get("branch", "")
    remote = parameters.get("remote", "origin")
    file_path = parameters.get("file_path", "")

    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return f"'{repo_path}' no es un repositorio Git."

    try:
        if action == "status":
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            out = r.stdout.strip()
            return out if out else "Working tree limpio."

        elif action == "log":
            count = parameters.get("count", 10)
            r = subprocess.run(
                ["git", "log", f"--oneline", f"-{count}"],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return r.stdout.strip() or "No hay commits."

        elif action == "add":
            target = file_path if file_path else "."
            r = subprocess.run(
                ["git", "add", target],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return "Archivos agregados al stage." if not r.stderr else f"Error: {r.stderr.strip()}"

        elif action == "commit":
            r = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return r.stdout.strip() or r.stderr.strip()

        elif action == "push":
            args = ["git", "push", remote]
            if branch:
                args.append(branch)
            r = subprocess.run(args, capture_output=True, text=True, cwd=repo_path, timeout=60)
            return r.stdout.strip() or r.stderr.strip()

        elif action == "pull":
            args = ["git", "pull", remote]
            if branch:
                args.append(branch)
            r = subprocess.run(args, capture_output=True, text=True, cwd=repo_path, timeout=60)
            return r.stdout.strip() or r.stderr.strip()

        elif action in ("diff", "changes"):
            r = subprocess.run(
                ["git", "diff", "--stat"],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return r.stdout.strip() or "Sin cambios sin stage."

        elif action == "branch":
            r = subprocess.run(
                ["git", "branch", "-a"],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return r.stdout.strip()

        elif action == "checkout":
            target = branch or file_path
            if not target:
                return "Indica el branch o archivo para checkout."
            r = subprocess.run(
                ["git", "checkout", target],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return r.stdout.strip() or r.stderr.strip()

        elif action == "clone":
            url = parameters.get("url", "")
            dest = parameters.get("dest", "")
            if not url:
                return "Indica la URL del repositorio a clonar."
            args = ["git", "clone", url]
            if dest:
                args.append(dest)
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
            return r.stdout.strip() or r.stderr.strip()

        elif action == "init":
            r = subprocess.run(
                ["git", "init"],
                capture_output=True, text=True, cwd=repo_path, timeout=15
            )
            return f"Repositorio Git inicializado en {repo_path}."

        else:
            return f"Acción Git '{action}' no reconocida. Acciones: status, log, add, commit, push, pull, diff, branch, checkout, clone, init."

    except subprocess.TimeoutExpired:
        return "El comando Git tardó demasiado y fue cancelado."
    except FileNotFoundError:
        return "Git no está instalado o no está en el PATH."
    except Exception as e:
        return f"Error ejecutando Git: {e}"
