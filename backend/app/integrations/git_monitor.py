"""
Monitor de Repositorios Git — Cerebro Operativo

Monitorea repositorios locales y genera reportes de actividad:
- Commits recientes
- Archivos modificados
- Branches activos
- Estado del working tree
"""
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


def scan_repo(repo_path: str) -> Optional[dict]:
    """Escanea un repositorio Git y retorna información resumida."""
    if not GIT_AVAILABLE:
        return {"error": "GitPython no está instalado"}

    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Ruta no encontrada: {repo_path}"}

    try:
        repo = git.Repo(path)
    except git.InvalidGitRepositoryError:
        return {"error": f"No es un repositorio Git: {repo_path}"}

    # Info básica
    active_branch = str(repo.active_branch) if not repo.head.is_detached else "DETACHED"
    branches = [str(b) for b in repo.branches]

    # Estado del working tree
    changed = [item.a_path for item in repo.index.diff(None)]
    staged = [item.a_path for item in repo.index.diff("HEAD")]
    untracked = repo.untracked_files

    # Commits recientes (últimos 10)
    recent_commits = []
    try:
        for commit in repo.iter_commits(max_count=10):
            recent_commits.append({
                "hash": commit.hexsha[:7],
                "message": commit.message.strip().split("\n")[0],
                "author": str(commit.author),
                "date": commit.committed_datetime.isoformat(),
                "files_changed": commit.stats.total.get("files", 0),
            })
    except Exception:
        pass

    # Estadísticas de actividad (última semana)
    week_ago = datetime.now() - timedelta(days=7)
    weekly_commits = 0
    try:
        for commit in repo.iter_commits():
            if commit.committed_datetime.replace(tzinfo=None) < week_ago:
                break
            weekly_commits += 1
    except Exception:
        pass

    # Remotes
    remotes = []
    for remote in repo.remotes:
        remotes.append({
            "name": remote.name,
            "url": remote.url,
        })

    return {
        "path": str(path.absolute()),
        "name": path.name,
        "active_branch": active_branch,
        "branches": branches,
        "status": {
            "clean": not (changed or staged or untracked),
            "modified": changed,
            "staged": staged,
            "untracked": untracked[:10],  # Limitar
        },
        "recent_commits": recent_commits,
        "weekly_commits": weekly_commits,
        "remotes": remotes,
        "is_dirty": repo.is_dirty(untracked_files=True),
    }


def scan_multiple_repos(paths: list) -> list:
    """Escanea múltiples repositorios."""
    results = []
    for path in paths:
        result = scan_repo(path)
        if result:
            results.append(result)
    return results


def get_commit_activity(repo_path: str, days: int = 30) -> dict:
    """Genera un mapa de actividad de commits por día."""
    if not GIT_AVAILABLE:
        return {"error": "GitPython no instalado"}

    try:
        repo = git.Repo(repo_path)
    except Exception:
        return {"error": f"No se pudo abrir: {repo_path}"}

    cutoff = datetime.now() - timedelta(days=days)
    activity = {}

    try:
        for commit in repo.iter_commits():
            commit_date = commit.committed_datetime.replace(tzinfo=None)
            if commit_date < cutoff:
                break
            date_key = commit_date.strftime("%Y-%m-%d")
            activity[date_key] = activity.get(date_key, 0) + 1
    except Exception:
        pass

    return {
        "repo": Path(repo_path).name,
        "days": days,
        "total_commits": sum(activity.values()),
        "activity": activity,
    }
