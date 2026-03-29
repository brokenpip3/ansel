import tempfile
from pathlib import Path
from typing import List
from typing import Optional

from git import GitCommandError
from git import Repo

from ansel.config import RepositoryConfig
from ansel.exceptions import RepoError


def clone_or_pull(
    repo_cfg: RepositoryConfig, workdir: Path, default_branch: str
) -> Repo:
    repo_path = workdir / repo_cfg.name
    target_branch = repo_cfg.branch or default_branch

    try:
        if not repo_path.exists():
            repo = Repo.clone_from(repo_cfg.url, repo_path)
        else:
            repo = Repo(repo_path)
            repo.remotes.origin.fetch()

        if target_branch in repo.remotes.origin.refs:
            repo.git.checkout(target_branch)
            repo.git.reset("--hard", f"origin/{target_branch}")
        else:
            try:
                repo.git.rev_parse("--verify", "HEAD")
                repo.git.reset("--hard", "HEAD")
            except GitCommandError:
                pass

        repo.git.clean("-fd")
        return repo
    except GitCommandError as e:
        raise RepoError(f"Failed to clone or pull repository {repo_cfg.name}: {e}")


def create_branch(repo: Repo, branch_name: str):
    try:
        repo.git.checkout("-b", branch_name)
    except GitCommandError:
        try:
            repo.git.checkout(branch_name)
        except GitCommandError as e:
            raise RepoError(f"Failed to create or checkout branch {branch_name}: {e}")


def commit_and_push(
    repo: Repo,
    message: str,
    branch_name: str,
    files: List[str],
) -> bool:
    try:
        working_dir = Path(repo.working_tree_dir)

        for file_path in files:
            p = Path(file_path)
            if p.is_absolute():
                try:
                    p = p.relative_to(working_dir)
                except ValueError:
                    pass
            repo.git.add(str(p))

        status = repo.git.status("--porcelain")
        if not status:
            return False

        repo.index.commit(message, skip_hooks=True)
        repo.remotes.origin.push(branch_name, force=True)
        return True
    except GitCommandError as e:
        raise RepoError(f"Failed to commit or push: {e}")


def get_workdir(
    config_workdir: Optional[str] = None, flag_workdir: Optional[str] = None
) -> Path:
    if flag_workdir and isinstance(flag_workdir, (str, Path)):
        path = Path(flag_workdir).absolute()
    elif config_workdir and isinstance(config_workdir, (str, Path)):
        path = Path(config_workdir).absolute()
    else:
        return Path(tempfile.gettempdir()) / "ansel"

    path.mkdir(parents=True, exist_ok=True)
    return path
