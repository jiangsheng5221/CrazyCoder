#!/usr/bin/env python3
"""构建前本地预检 —— 把能静态发现的问题挡在最便宜的一步。

为什么值得有这个东西：
    macOS runner 一次构建 6-12 分钟，失败了要等十几分钟才知道。
    公开仓库虽然不要钱，但时间成本一样在。能本地查出来的，就别上 CI 查。

用法：
    python scripts/precheck.py

检查项：
    [1] workflow YAML 合法 + 关键防护存在
    [2] project.yml 合法 + Bundle ID 一致性
    [3] Info.plist 合规（出口合规、版本占位、权限说明）
    [4] 工作区是否干净（构建应该基于已提交的代码）
    [5] 证书/描述文件有效期（如果本地存了的话）

零第三方依赖（CI 里需要 pyyaml，本地建议也装：pip install pyyaml）
"""
import os
import re
import sys
from datetime import datetime

FAILS = []


def prepare_console():
    """Windows 控制台默认 GBK，打印 ✓/✗ 会 UnicodeEncodeError 直接崩。
    这里把输出流切到 UTF-8 并对无法编码的字符降级，保证任何平台都能跑完。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def ok(msg):
    print(f"  \u2713 {msg}")


def bad(msg):
    print(f"  \u2717 {msg}")
    FAILS.append(msg)


def warn(msg):
    print(f"  ! {msg}")


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        print("  需要 pyyaml：pip install pyyaml")
        return None
    try:
        return yaml.safe_load(open(path, encoding="utf-8"))
    except Exception as e:
        bad(f"{path} YAML 解析失败: {e}")
        return None


def check_workflow():
    print("\n[1] workflow YAML + 关键防护")
    path = ".github/workflows/build.yml"
    if not os.path.isfile(path):
        bad(f"找不到 {path}")
        return None
    wf_text = open(path, encoding="utf-8").read()
    data = load_yaml(path)
    if data is None:
        return None
    ok(f"{path} 合法（{len(data.get('jobs', {}))} 个 job）")

    guards = [
        ("timeout-minutes:", "没有超时保护，卡住会跑满默认 6 小时"),
        ("concurrency:", "没有并发取消，重复触发会同时跑多份"),
        ("cancel-in-progress: true", "并发不取消，白白多烧一份"),
        ("refs/tags/v", "tag 触发规则缺失"),
    ]
    for token, why in guards:
        if token in wf_text:
            ok(f"防护存在: {token}")
        else:
            bad(f"缺少「{token}」—— {why}")

    # tag 触发必须强制定为正式包，否则 AdHoc 包上传 TestFlight 必被拒
    if 'BT="2"' in wf_text:
        ok("标签触发强制正式包")
    else:
        bad("标签触发未强制 build_type=2，AdHoc 包会被 TestFlight 拒收")

    # xcodegen 不能写死解压路径
    if "find /tmp/xcg" in wf_text and "brew install xcodegen" in wf_text:
        ok("xcodegen 用 find 定位且有 brew 兜底")
    else:
        bad("xcodegen 获取写死路径或缺 brew 兜底 —— 解压层级一变就构建失败")
    return data


def check_project(wf_data):
    print("\n[2] project.yml")
    path = "project.yml"
    if not os.path.isfile(path):
        bad("找不到 project.yml")
        return
    data = load_yaml(path)
    if not data:
        return
    name = data.get("name")
    targets = data.get("targets") or {}
    if not name or not targets:
        bad("project.yml 缺少 name 或 targets")
        return
    ok(f"合法（name={name}，targets={list(targets.keys())}）")

    tgt = targets.get(name) or list(targets.values())[0]
    bundle_id = (tgt.get("settings", {}).get("base", {})
                 or {}).get("PRODUCT_BUNDLE_IDENTIFIER", "")
    if not bundle_id:
        bad("target 里没有 PRODUCT_BUNDLE_IDENTIFIER")

    # workflow 里的 BUNDLE_ID 必须和 project.yml 一致，否则导出时签名失败
    wf = open(".github/workflows/build.yml", encoding="utf-8").read()
    m = re.search(r"BUNDLE_ID:\s*(\S+)", wf)
    if m:
        wf_bid = m.group(1).strip()
        if wf_bid == bundle_id:
            ok(f"workflow 与 project.yml 的 Bundle ID 一致: {bundle_id}")
        else:
            bad(f"Bundle ID 不一致：workflow={wf_bid}  project.yml={bundle_id}")
    else:
        warn("workflow 里没找到 BUNDLE_ID 变量")

    # workflow 里的 APP_NAME 必须和 project.yml 的 name 一致（scheme 名字靠它）
    m = re.search(r"APP_NAME:\s*(\S+)", wf)
    if m:
        if m.group(1).strip() == name:
            ok(f"workflow 与 project.yml 的项目名一致: {name}")
        else:
            bad(f"项目名不一致：workflow={m.group(1).strip()}  project.yml={name}")


def value_of(text, key):
    """同时支持 <string>x</string> 与 <true/> 两种写法"""
    m = re.search(rf"<key>{re.escape(key)}</key>\s*<string>([^<]*)</string>", text)
    if m:
        return m.group(1)
    m = re.search(rf"<key>{re.escape(key)}</key>\s*<(true|false)\s*/>", text)
    return m.group(1) if m else None


def check_infoplist():
    print("\n[3] Info.plist 合规")
    path = None
    for root, _, files in os.walk("."):
        if "Info.plist" in files and ".git" not in root:
            path = os.path.join(root, "Info.plist")
            break
    if not path:
        bad("找不到 Info.plist")
        return
    text = open(path, encoding="utf-8").read()

    enc = value_of(text, "ITSAppUsesNonExemptEncryption")
    if enc == "false":
        ok("ITSAppUsesNonExemptEncryption=false（免每次人工填出口合规）")
    else:
        bad("缺少 ITSAppUsesNonExemptEncryption=false —— 每次上传都要人工点合规问答")

    vs = value_of(text, "CFBundleShortVersionString")
    if vs == "$(MARKETING_VERSION)":
        ok("版本号用 $(MARKETING_VERSION) 占位")
    elif vs:
        warn(f"版本号被写死为 {vs}，建议改成 $(MARKETING_VERSION) 让 CI 统一管理")

    bs = value_of(text, "CFBundleVersion")
    if bs == "$(CURRENT_PROJECT_VERSION)":
        ok("构建号用 $(CURRENT_PROJECT_VERSION) 占位")

    for key, why in [("NSCameraUsageDescription", "相机"),
                     ("NSPhotoLibraryUsageDescription", "相册"),
                     ("NSLocationWhenInUseUsageDescription", "定位")]:
        if f"<key>{key}</key>" in text:
            ok(f"{key} 已声明（{why}）")


def check_git():
    print("\n[4] 工作区状态")
    r = os.popen("git status --porcelain").read().strip()
    if r:
        n = len([x for x in r.splitlines() if x.strip()])
        bad(f"有 {n} 个未提交改动（构建前先 commit）")
        for line in r.splitlines()[:5]:
            print(f"      {line}")
    else:
        ok("工作区干净")


def check_cert():
    print("\n[5] 签名资产有效期")
    cands = []
    for root, _, files in os.walk("."):
        if ".git" in root:
            continue
        for f in files:
            if f.endswith(".cer") or f.endswith(".mobileprovision"):
                cands.append(os.path.join(root, f))
    if not cands:
        warn("本地没有 .cer / .mobileprovision，跳过（证书在 Secrets 里也正常）")
        return
    for p in cands[:4]:
        r = os.popen(f'openssl x509 -inform DER -in "{p}" -noout -enddate 2>/dev/null').read().strip()
        if not r:
            continue
        try:
            dt = datetime.strptime(r.split("=", 1)[1].strip(), "%b %d %H:%M:%S %Y %Z")
            days = (dt - datetime.now()).days
            if days < 0:
                bad(f"{os.path.basename(p)} 已过期")
            elif days < 30:
                warn(f"{os.path.basename(p)} 还有 {days} 天到期，该续了")
            else:
                ok(f"{os.path.basename(p)} 剩余 {days} 天")
        except Exception:
            pass


def main():
    prepare_console()
    print("=" * 50)
    print("  构建前本地预检")
    print("=" * 50)
    wf = check_workflow()
    if wf:
        check_project(wf)
    check_infoplist()
    check_git()
    check_cert()

    print("\n" + "=" * 50)
    if FAILS:
        print(f"  {len(FAILS)} 项未过，先修本地再上 CI")
        for f in FAILS:
            print(f"    - {f}")
        print("=" * 50)
        return 1
    print("  全部通过")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
