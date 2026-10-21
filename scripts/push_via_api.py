#!/usr/bin/env python3
"""git push 走不通时，改用 GitHub Contents API 提交文件。

什么情况下用：
    代理/网络只通 api.github.com、不通 github.com 时，git push 会报
    `CONNECT tunnel failed, response 502` 或 `Recv failure: Connection was reset`，
    但 `gh api` 通常还活着 —— 那就用这个通道提交。

用法：
    python scripts/push_via_api.py App/Main.swift -m "fix: ..."
    python scripts/push_via_api.py a.swift b.py -m "chore: 同步" --dry

注意：
    1. 每个文件单独生成一个 commit（Contents API 的天然行为）
    2. API 提交的 commit 与本地 git 历史会分叉，网络恢复后执行
       `git fetch origin && git reset --hard origin/main` 重新对齐
    3. 文件内容会把 CRLF 统一成 LF
    4. 大文件必须走 --input 传 JSON：`-f content=...` 会报 Argument list too long
    5. 仓库从当前目录的 git remote 自动推断，不用手填
"""
import argparse
import base64
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gh(args):
    return subprocess.run(["gh"] + args, capture_output=True, text=True)


def detect_repo():
    r = gh(["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    raise SystemExit("无法推断仓库，手动指定 --repo owner/name")


def remote_sha(repo, path, branch):
    r = gh(["api", f"repos/{repo}/contents/{path}?ref={branch}", "--jq", ".sha"])
    if r.returncode != 0:
        if "Not Found" in r.stderr or "404" in r.stderr:
            return ""      # 新文件，API 会走创建逻辑
        raise SystemExit(f"取 {path} 的 sha 失败：{r.stderr[:300]}")
    return r.stdout.strip()


def put_file(repo, path, content_b64, message, sha, branch):
    body = {"message": message, "content": content_b64, "branch": branch}
    if sha:
        body["sha"] = sha
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "gh_put_body.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    r = gh(["api", "-X", "PUT", f"repos/{repo}/contents/{path}",
            "--input", tmp, "--jq", ".commit.sha[0:7]"])
    if r.returncode != 0:
        raise SystemExit(f"提交 {path} 失败：{r.stderr[:400]}")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="相对仓库根目录的路径")
    ap.add_argument("-m", "--message", required=True, help="commit message")
    ap.add_argument("--repo", help="owner/name，默认从当前 git remote 推断")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry", action="store_true", help="只检查不提交")
    args = ap.parse_args()

    os.chdir(ROOT)
    repo = args.repo or detect_repo()
    print(f"仓库: {repo}  分支: {args.branch}\n")

    for path in args.files:
        if not os.path.isfile(path):
            raise SystemExit(f"文件不存在：{path}")
        raw = open(path, "rb").read().replace(b"\r\n", b"\n")
        b64 = base64.b64encode(raw).decode()
        sha = remote_sha(repo, path, args.branch)
        if args.dry:
            print(f"[dry] {path}  本地 {len(raw)} 字节  "
                  f"远端 {'已有 ' + sha[:7] if sha else '(新建)'}")
            continue
        new = put_file(repo, path, b64, args.message, sha, args.branch)
        print(f"\u2713 {path} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
