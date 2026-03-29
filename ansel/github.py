import json
import subprocess
import urllib.error
import urllib.request
from typing import List


def fetch_repos(org_name: str, use_gh_cli: bool = False) -> List[str]:
    if not use_gh_cli:
        repos = []

        for kind in ["orgs", "users"]:
            page = 1
            found_kind = False
            while True:
                url = f"https://api.github.com/{kind}/{org_name}/repos?page={page}&per_page=100"
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "ansel-cli"}
                    )
                    with urllib.request.urlopen(req) as response:
                        data = json.loads(response.read().decode())
                        if not data and page == 1:
                            return []
                        if not data:
                            break

                        repos.extend([repo["full_name"] for repo in data])
                        page += 1
                        found_kind = True
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        # Try next kind (users)
                        break
                    raise e

            if found_kind:
                break

        return repos

    needs_logout = False
    auth_status = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if auth_status.returncode != 0:
        needs_logout = True
        subprocess.run(["gh", "auth", "login", "--web"], check=True)

    try:
        api_res = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                org_name,
                "--json",
                "nameWithOwner",
                "--limit",
                "10000",
            ],
            capture_output=True,
        )
        if api_res.returncode != 0:
            return []

        data = json.loads(api_res.stdout.decode())
        repos = [r["nameWithOwner"] for r in data]
        return repos
    finally:
        if needs_logout:
            subprocess.run(["gh", "auth", "logout", "--hostname", "github.com"])
