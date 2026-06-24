import json
import os
import subprocess
import urllib.request

from repo import Repo

REPOS_URL = "https://raw.githubusercontent.com/TheTangentLine/learn/main/data/repos.json"
REPOS_DIR = os.path.join(os.path.dirname(__file__), "..", "repositories")


def fetch_repos() -> list[Repo]:
    with urllib.request.urlopen(REPOS_URL) as response:
        data = json.loads(response.read().decode())
    entries = data if isinstance(data, list) else data.get("repos", [])
    return [
        Repo(
            slug=entry["slug"],
            label=entry["label"],
            category=entry["category"],
            username=entry["username"],
        )
        for entry in entries
    ]


def clone_repos(repos: list[Repo]) -> None:
    os.makedirs(REPOS_DIR, exist_ok=True)
    for repo in repos:
        dest = os.path.join(REPOS_DIR, repo.slug)
        if os.path.exists(dest):
            print(f"  skip  {repo.slug} (already exists)")
            continue
        url = f"https://github.com/{repo.username}/{repo.slug}.git"
        print(f"  clone {url}")
        subprocess.run(["git", "clone", url, dest], check=True)


if __name__ == "__main__":
    print("Fetching repo list...")
    repos = fetch_repos()
    print(f"Found {len(repos)} repos. Cloning...")
    clone_repos(repos)
    print("Done.")
