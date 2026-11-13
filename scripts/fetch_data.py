#!/usr/bin/env python3
"""Refresh data/contributions.json from the GitHub GraphQL API (run daily by the Action).

Env: GITHUB_TOKEN (required), GH_LOGIN (default ANC-DOMINATER), MAX_REPOS (default 6).
Featured repos = your pinned repos; falls back to most-starred public non-fork repos.
"""
import json
import os
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("GH_LOGIN", "ANC-DOMINATER")
MAX_REPOS = int(os.environ.get("MAX_REPOS", "6"))
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

REPO = """name description url stargazerCount forkCount isFork
  primaryLanguage { name color }"""
QUERY = """query($login:String!,$n:Int!){ user(login:$login){ login name
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
  pinnedItems(first:$n,types:REPOSITORY){ nodes{ ... on Repository{ %s } } }
  repositories(first:$n,ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,
    orderBy:{field:STARGAZERS,direction:DESC}){ nodes{ %s } } } }""" % (REPO, REPO)


def gql(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN, "n": MAX_REPOS}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if out.get("errors"):
        raise SystemExit(json.dumps(out["errors"], indent=2))
    return out["data"]["user"]


def repo(n):
    lang = n.get("primaryLanguage") or {}
    return {"name": n["name"], "description": n.get("description") or "", "url": n["url"],
            "stars": n["stargazerCount"], "forks": n["forkCount"],
            "language": lang.get("name"), "language_color": lang.get("color")}


def main():
    u = gql(os.environ["GITHUB_TOKEN"])
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [{"date": d["date"], "count": d["contributionCount"]}
            for w in cal["weeks"] for d in w["contributionDays"]]
    nodes = [n for n in u["pinnedItems"]["nodes"] if n] or u["repositories"]["nodes"]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"login": u["login"], "name": u["name"], "total": cal["totalContributions"],
                               "days": days, "repos": [repo(n) for n in nodes][:MAX_REPOS]}, indent=1) + "\n")
    print(f"wrote {OUT}: {len(days)} days, {len(nodes)} repos")


if __name__ == "__main__":
    main()
