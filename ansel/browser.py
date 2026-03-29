import re
import webbrowser
from typing import Optional


def build_pr_url(remote_url: str, branch: str) -> Optional[str]:
    gh_match = re.search(r"github\.com[:/](.+?/.+?)(\.git)?$", remote_url)
    if gh_match:
        repo_slug = gh_match.group(1)
        return f"https://github.com/{repo_slug}/compare/{branch}"

    if remote_url.startswith("https://"):
        match = re.search(r"https://(.*?)/(.+?)(\.git)?$", remote_url)
        if match:
            host, slug = match.group(1), match.group(2)
            return f"https://{host}/{slug}/compare/{branch}"

    if "@" in remote_url and ":" in remote_url:
        match = re.search(r"@(.+?):(?:(\d+)/)?(.+?)(\.git)?$", remote_url)
        if match:
            host, _, slug = match.group(1), match.group(2), match.group(3)
            return f"https://{host}/{slug}/compare/{branch}"

    return None


def open_pr(remote_url: str, branch: str):
    url = build_pr_url(remote_url, branch)
    if url:
        webbrowser.open(url)
    return url
