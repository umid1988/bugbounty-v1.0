#!/usr/bin/env python3
"""
GitHub ga avtomatik repo yaratib, kodlarni push qiladi.
Ishlatish:
    python3 github_push.py --token YOUR_TOKEN --username YOUR_USERNAME
    python3 github_push.py --token YOUR_TOKEN --username YOUR_USERNAME --private
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

API = "https://api.github.com"
REPO_NAME = "bb-pro"
REPO_DESC = "Professional Bug Bounty Automation Pipeline — scope kontroli, zamonaviy toollar integratsiyasi"


def api_request(path, token, method="GET", body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept":        "application/vnd.github+json",
            "Content-Type":  "application/json",
            "User-Agent":    "bb-pro-uploader",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return json.loads(body) if body else {}, e.code


def check_token(token):
    data, status = api_request("/user", token)
    if status != 200:
        print(f"❌ Token noto'g'ri yoki ruxsat yo'q (HTTP {status})")
        sys.exit(1)
    return data["login"]


def create_or_get_repo(token, username, private):
    # Mavjudligini tekshirish
    data, status = api_request(f"/repos/{username}/{REPO_NAME}", token)
    if status == 200:
        print(f"ℹ️  Repo allaqachon mavjud: {data['html_url']}")
        return data["html_url"], data["clone_url"]

    # Yangi repo yaratish
    print(f"📁 Yangi repo yaratilmoqda: {REPO_NAME} ...")
    data, status = api_request("/user/repos", token, "POST", {
        "name":        REPO_NAME,
        "description": REPO_DESC,
        "private":     private,
        "auto_init":   False,
        "has_issues":  True,
        "has_wiki":    False,
    })
    if status not in (200, 201):
        print(f"❌ Repo yaratib bo'lmadi: {data.get('message', data)}")
        sys.exit(1)

    print(f"✓  Repo yaratildi: {data['html_url']}")
    return data["html_url"], data["clone_url"]


def run(cmd, cwd=None, check=True):
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"❌ Buyruq xatosi: {cmd}")
        print(result.stderr)
        sys.exit(1)
    return result


def push_to_github(token, username, clone_url, project_dir, branch="main"):
    # clone_url ga token qo'shish
    auth_url = clone_url.replace(
        "https://", f"https://{username}:{token}@"
    )

    print(f"\n🔧 Git sozlanmoqda ...")
    run(f"git init", cwd=project_dir)
    run(f"git config user.email 'bb-pro@local'", cwd=project_dir)
    run(f"git config user.name '{username}'", cwd=project_dir)
    run(f"git checkout -b {branch}", cwd=project_dir)

    print("📝 Fayllar qo'shilmoqda ...")
    run(f"git add .", cwd=project_dir)
    run(f'git commit -m "Initial commit: BB Pro v1.0"', cwd=project_dir)

    print("🚀 GitHub ga push qilinmoqda ...")
    run(f"git remote add origin {auth_url}", cwd=project_dir)
    run(f"git push -u origin {branch} --force", cwd=project_dir)

    print(f"✓  Push muvaffaqiyatli!")


def set_topics(token, username):
    topics = ["bug-bounty", "security", "python", "automation",
              "recon", "penetration-testing", "osint", "nuclei", "subfinder"]
    api_request(
        f"/repos/{username}/{REPO_NAME}/topics", token, "PUT",
        {"names": topics}
    )
    print(f"✓  Topics qo'shildi: {', '.join(topics)}")


def main():
    parser = argparse.ArgumentParser(description="BB Pro ni GitHub ga yuklash")
    parser.add_argument("--token",    required=True, help="GitHub Personal Access Token")
    parser.add_argument("--username", required=True, help="GitHub foydalanuvchi nomi")
    parser.add_argument("--private",  action="store_true", help="Repo private bo'lsin")
    parser.add_argument("--dir",      default=os.path.dirname(os.path.abspath(__file__)),
                        help="Loyiha papkasi (default: bu fayl joylashgan papka)")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  BB Pro → GitHub Uploader")
    print("="*55 + "\n")

    # Token tekshirish
    print("🔑 Token tekshirilmoqda ...")
    username = check_token(args.token)
    print(f"✓  Kirish muvaffaqiyatli: @{username}")

    # Repo yaratish
    visibility = "private" if args.private else "public"
    print(f"\n📦 Repo: {REPO_NAME} ({visibility})")
    html_url, clone_url = create_or_get_repo(args.token, username, args.private)

    # Push
    push_to_github(args.token, username, clone_url, args.dir)

    # Topics
    print("\n🏷️  Topics qo'shilmoqda ...")
    set_topics(args.token, username)

    # Natija
    print("\n" + "="*55)
    print("  ✅ MUVAFFAQIYATLI!")
    print("="*55)
    print(f"\n  🔗 Repo: {html_url}")
    print(f"  📋 Clone: git clone {html_url}.git\n")


if __name__ == "__main__":
    main()
