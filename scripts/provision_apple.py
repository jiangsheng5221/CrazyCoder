#!/usr/bin/env python3
"""用 App Store Connect API 全自动创建签名资产（App ID + 分发证书 + 描述文件）。

解决的问题：
    Apple 开发者后台那套「建 App ID → 建证书 → 建描述文件」是纯手工点击，
    还经常点错（Bundle ID 不一致、证书漏选、描述文件类型选成 AdHoc）。
    这里用官方 API 一次做完，产物直接落到本地 certs/，接着就能跑 setup_secrets。

用法：
    python scripts/provision_apple.py \
        --key-id  ABCDE12345 \
        --issuer  00000000-0000-0000-0000-000000000000 \
        --p8      ~/.appstoreconnect/private_keys/AuthKey_ABCDE12345.p8 \
        --team    9U9FGR2HTF \
        --bundle-id com.crazycoder.app \
        --profile-name "CrazyCoder AppStore"

    # 先只验证凭据和账号现状，不创建任何东西：
    python scripts/provision_apple.py ... --dry-run

    # 不联网，只自检本地环节（JWT 签名、p12 打包）：
    python scripts/provision_apple.py --self-test

产出的文件（全部在 --out 目录，默认 certs/，已被 .gitignore 挡住）：
    distribution.key     分发证书私钥（务必自己留底，丢了只能重新申请证书）
    distribution.cer     分发证书
    distribution.p12     证书+私钥，导入 CI 用的那个
    CrazyCoder.mobileprovision   App Store 描述文件

前提：API 密钥的权限需要 Admin（或至少能管证书/描述文件的角色）。
      密钥在 App Store Connect → 用户和访问 → 集成 → App Store Connect API 生成。

注意：App Store Connect API 不能创建「App 记录」（那是后台手工的），
      但那一步只在 TestFlight/上架时需要，签名和出 ipa 不需要。
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

API = "https://api.appstoreconnect.apple.com"
WWDR_URLS = [
    "https://www.apple.com/certificateauthority/AppleWWDRCAG3.cer",
    "https://www.apple.com/certificateauthority/AppleWWDRCAG2.cer",
]


# ---------------------------------------------------------------- 基础设施


def find_openssl(explicit=None):
    """Windows 上 openssl 通常只藏在 Git 的 usr/bin 里，不在 PATH。"""
    candidates = []
    if explicit:
        candidates.append(explicit)
    found = shutil.which("openssl")
    if found:
        candidates.append(found)

    git = shutil.which("git")
    if git:
        # D:\Program Files\Git\cmd\git.exe → D:\Program Files\Git
        git_root = os.path.dirname(os.path.dirname(git))
        candidates.append(os.path.join(git_root, "usr", "bin", "openssl.exe"))
        candidates.append(os.path.join(git_root, "usr", "bin", "openssl"))

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise SystemExit("找不到 openssl。装 Git for Windows 或指定 --openssl 路径。")


def run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, **kwargs)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "ignore")[:500]
        raise SystemExit(f"命令失败：{' '.join(cmd[:3])} …\n{stderr}")
    return result.stdout


def b64url(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def make_token(key_id, issuer, p8_path, openssl):
    """ES256 JWT。Apple 要求签名是 r||s 原始格式，而 openssl 输出 DER，需要转换。"""
    header = b64url(json.dumps({"alg": "ES256", "kid": key_id, "typ": "JWT"}).encode())
    now = int(time.time())
    payload = b64url(json.dumps({
        "iss": issuer,
        "iat": now,
        "exp": now + 900,
        "aud": "appstoreconnect-v1",
    }).encode())
    signing_input = header + b"." + payload

    with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
        handle.write(signing_input)
        msg_path = handle.name
    try:
        der = run([openssl, "dgst", "-sha256", "-sign", p8_path, msg_path])
    finally:
        os.unlink(msg_path)

    index = 2
    if der[index] & 0x80:
        index += der[index] & 0x7F
    index += 1
    len_r = der[index]
    r = der[index + 1: index + 1 + len_r]
    index += 1 + len_r + 1
    len_s = der[index]
    s = der[index + 1: index + 1 + len_s]
    signature = r.lstrip(b"\x00").rjust(32, b"\x00") + s.lstrip(b"\x00").rjust(32, b"\x00")
    return (signing_input + b"." + b64url(signature)).decode()


def call(token, method, path, body=None):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + token)
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw)
        except Exception:
            return error.code, {"raw": raw[:400].decode("utf-8", "ignore")}


def explain(status, payload):
    """把 Apple 的错误码翻译成人话，省得对着 409 猜。"""
    detail = payload.get("errors", [{}])[0] if isinstance(payload, dict) else {}
    title = detail.get("title", "")
    message = detail.get("detail", "")
    hints = {
        401: "凭据无效：Key ID / Issuer ID / .p8 不匹配，或密钥已撤销",
        403: "权限不足：这个 API 密钥没有 Admin / 证书管理权限，去后台提高角色",
        409: "冲突：同名资源已存在，或分发证书数量已达上限（3 张）",
    }
    hint = hints.get(status, "")
    return f"HTTP {status} {title} {message}".strip() + (f"\n  提示：{hint}" if hint else "")


# ---------------------------------------------------------------- 各步骤


def ensure_bundle_id(token, bundle_id, app_name, dry_run):
    status, payload = call(token, "GET", f"/v1/bundleIds?filter[identifier]={bundle_id}&limit=5")
    if status != 200:
        raise SystemExit("查询 App ID 失败：" + explain(status, payload))

    for item in payload.get("data", []):
        if item["attributes"].get("identifier") == bundle_id:
            print(f"  ✓ App ID 已存在：{bundle_id} [{item['id']}]")
            return item["id"], False

    if dry_run:
        print(f"  · [dry-run] 将创建 App ID：{bundle_id}")
        return None, True

    print(f"  → 创建 App ID：{bundle_id}")
    status, payload = call(token, "POST", "/v1/bundleIds", {
        "data": {
            "type": "bundleIds",
            "attributes": {
                "identifier": bundle_id,
                "name": app_name,
                "platform": "IOS",
            },
        }
    })
    if status not in (200, 201):
        raise SystemExit("创建 App ID 失败：" + explain(status, payload))
    created = payload["data"]
    print(f"  ✓ 已创建 [{created['id']}]")
    return created["id"], True


def list_distribution_certs(token):
    status, payload = call(
        token, "GET",
        "/v1/certificates?filter[certificateType]=DISTRIBUTION&limit=200")
    if status != 200:
        raise SystemExit("查询证书失败：" + explain(status, payload))
    return payload.get("data", [])


def create_certificate(token, workdir, openssl, dry_run):
    key_path = os.path.join(workdir, "distribution.key")
    csr_path = os.path.join(workdir, "distribution.csr")

    print("  → 本地生成 P-256 私钥与 CSR")
    run([openssl, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key_path])
    run([openssl, "req", "-new", "-key", key_path,
         "-subj", "/CN=CrazyCoder Distribution/O=CrazyCoder/C=US",
         "-out", csr_path])

    if dry_run:
        print("  · [dry-run] 将用该 CSR 申请 Apple Distribution 证书")
        return None, key_path

    with open(csr_path, encoding="utf-8") as handle:
        csr = handle.read()

    status, payload = call(token, "POST", "/v1/certificates", {
        "data": {
            "type": "certificates",
            "attributes": {
                "csrContent": csr,
                "certificateType": "DISTRIBUTION",
            },
        }
    })
    if status not in (200, 201):
        raise SystemExit("申请证书失败：" + explain(status, payload))

    data = payload["data"]
    content = base64.b64decode(data["attributes"]["certificateContent"])
    print(f"  ✓ 已签发：{data['attributes'].get('name', '')} 到期 {data['attributes'].get('expirationDate', '?')}")
    return content, key_path


def write_chain_helpers(workdir, openssl):
    """把证书和 Apple 中间证书都转成 PEM，打包 p12 时要带中间证书才完整。"""
    wwdr_pem = None
    for url in WWDR_URLS:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                der = response.read()
            path = os.path.join(workdir, "wwdr.cer")
            with open(path, "wb") as handle:
                handle.write(der)
            pem = run([openssl, "x509", "-inform", "DER", "-in", path])
            wwdr_pem = os.path.join(workdir, "wwdr.pem")
            with open(wwdr_pem, "wb") as handle:
                handle.write(pem)
            print(f"  ✓ 已获取 Apple 中间证书（{os.path.basename(url)}）")
            return wwdr_pem
        except Exception as error:  # 网络不通就退化成只打包叶子证书
            print(f"  ! 下载中间证书失败（{error}），继续但不带中间证书")
    return wwdr_pem


def build_p12(workdir, cert_der, key_path, password, openssl, wwdr_pem):
    cert_der_path = os.path.join(workdir, "distribution.der")
    with open(cert_der_path, "wb") as handle:
        handle.write(cert_der)

    cert_pem_path = os.path.join(workdir, "distribution.cer.pem")
    with open(cert_pem_path, "wb") as handle:
        handle.write(run([openssl, "x509", "-inform", "DER", "-in", cert_der_path]))

    p12_path = os.path.join(workdir, "distribution.p12")
    command = [openssl, "pkcs12", "-export",
               "-inkey", key_path, "-in", cert_pem_path,
               "-out", p12_path, "-passout", f"pass:{password}",
               "-name", "Apple Distribution"]
    if wwdr_pem:
        command += ["-certfile", wwdr_pem]
    run(command)
    print(f"  ✓ 已打包 {p12_path}")
    return p12_path


def create_profile(token, bundle_record_id, cert_id, profile_name, workdir, dry_run):
    if dry_run:
        print(f"  · [dry-run] 将创建 App Store 描述文件：{profile_name}")
        return None

    status, payload = call(token, "POST", "/v1/profiles", {
        "data": {
            "type": "profiles",
            "attributes": {
                "name": profile_name,
                "profileType": "IOS_APP_STORE",
            },
            "relationships": {
                "bundleId": {"data": {"type": "bundleIds", "id": bundle_record_id}},
                "certificates": {"data": [{"type": "certificates", "id": cert_id}]},
            },
        }
    })
    if status not in (200, 201):
        raise SystemExit("创建描述文件失败：" + explain(status, payload))

    data = payload["data"]
    content = base64.b64decode(data["attributes"]["profileContent"])
    path = os.path.join(workdir, f"{profile_name.replace(' ', '_')}.mobileprovision")
    with open(path, "wb") as handle:
        handle.write(content)
    print(f"  ✓ 已创建描述文件：{profile_name} [{data['id']}]")
    return path


# ---------------------------------------------------------------- 自检


def self_test(openssl):
    """不联网，验证本地最容易写错的两块：JWT 签名、p12 打包。"""
    import ssl  # noqa: F401  仅在确认运行环境可用
    workdir = tempfile.mkdtemp(prefix="cc-selftest-")
    print(f"工作目录：{workdir}")

    print("[1/3] 生成测试用 EC 密钥")
    key = os.path.join(workdir, "test.key")
    run([openssl, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", key])
    public = os.path.join(workdir, "test.pub")
    run([openssl, "ec", "-in", key, "-pubout", "-out", public])

    print("[2/3] ES256 JWT 签名 + 验签")
    token = make_token("TESTKEY123", "00000000-0000-0000-0000-000000000000", key, openssl)
    parts = token.split(".")
    if len(parts) != 3:
        raise SystemExit("JWT 结构不对，应该有 3 段")
    signature = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
    if len(signature) != 64:
        raise SystemExit(f"ES256 签名应固定 64 字节，实际 {len(signature)}")

    # 转回 DER 交给 openssl 验签
    def to_der(raw):
        def encode_int(chunk):
            chunk = chunk.lstrip(b"\x00") or b"\x00"
            if chunk[0] & 0x80:
                chunk = b"\x00" + chunk
            return b"\x02" + bytes([len(chunk)]) + chunk

        body = encode_int(raw[:32]) + encode_int(raw[32:])
        return b"\x30" + bytes([len(body)]) + body

    der_path = os.path.join(workdir, "sig.der")
    with open(der_path, "wb") as handle:
        handle.write(to_der(signature))
    msg_path = os.path.join(workdir, "msg.txt")
    with open(msg_path, "wb") as handle:
        handle.write(f"{parts[0]}.{parts[1]}".encode())

    result = subprocess.run(
        [openssl, "dgst", "-sha256", "-verify", public, "-signature", der_path, msg_path],
        capture_output=True)
    if result.returncode != 0:
        raise SystemExit("JWT 验签失败：" + result.stderr.decode("utf-8", "ignore")[:300])
    print("  ✓ 签名格式正确且可通过验签（64 字节 r||s）")

    print("[3/3] 自签证书 + p12 打包")
    cert = os.path.join(workdir, "test.pem")
    run([openssl, "req", "-x509", "-new", "-key", key, "-days", "1",
         "-subj", "/CN=self-test", "-out", cert])
    der_cert = run([openssl, "x509", "-in", cert, "-outform", "DER"])
    p12 = build_p12(workdir, der_cert, key, "test123", openssl, None)
    check = subprocess.run(
        [openssl, "pkcs12", "-in", p12, "-passin", "pass:test123", "-nokeys", "-noout"],
        capture_output=True)
    if check.returncode != 0:
        raise SystemExit("p12 回读失败：" + check.stderr.decode("utf-8", "ignore")[:300])
    print("  ✓ p12 可正常回读")

    print("\n自检全部通过。本地环节没问题，网络环节需要真实 API 密钥。")
    shutil.rmtree(workdir, ignore_errors=True)
    return 0


# ---------------------------------------------------------------- 主流程


def main():
    parser = argparse.ArgumentParser(description="用 ASC API 自动创建 App ID / 证书 / 描述文件")
    parser.add_argument("--key-id", default=os.environ.get("ASC_API_KEY_ID"))
    parser.add_argument("--issuer", default=os.environ.get("ASC_ISSUER_ID"))
    parser.add_argument("--p8", default=None)
    parser.add_argument("--team", default=os.environ.get("DEVELOPMENT_TEAM"))
    parser.add_argument("--bundle-id", default="com.crazycoder.app")
    parser.add_argument("--app-name", default="CrazyCoder")
    parser.add_argument("--profile-name", default="CrazyCoder AppStore")
    parser.add_argument("--out", default="certs")
    parser.add_argument("--password", default=None, help="p12 密码，不给则自动生成")
    parser.add_argument("--openssl", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    openssl = find_openssl(args.openssl)
    print(f"openssl: {openssl}\n")

    if args.self_test:
        return self_test(openssl)

    if not (args.key_id and args.issuer):
        raise SystemExit(
            "缺少凭据：--key-id / --issuer（或环境变量 ASC_API_KEY_ID / ASC_ISSUER_ID）\n"
            "  在 App Store Connect → 用户和访问 → 集成 → App Store Connect API 生成密钥。")

    p8 = args.p8 or os.path.expanduser(
        f"~/.appstoreconnect/private_keys/AuthKey_{args.key_id}.p8")
    if not os.path.isfile(p8):
        raise SystemExit(f"找不到私钥文件：{p8}")

    os.makedirs(args.out, exist_ok=True)
    password = args.password or base64.urlsafe_b64encode(os.urandom(18)).decode().rstrip("=")
    token = make_token(args.key_id, args.issuer, p8, openssl)
    print(f"凭据：Key ID={args.key_id[:4]}…（已签发 JWT）\n")

    print("[1/4] App ID")
    bundle_record_id, _ = ensure_bundle_id(token, args.bundle_id, args.app_name, args.dry_run)

    print("\n[2/4] 分发证书")
    existing = list_distribution_certs(token)
    if existing:
        print(f"  账号里已有 {len(existing)} 张分发证书：")
        for cert in existing[:5]:
            attributes = cert["attributes"]
            print(f"    · {attributes.get('name', '')} 到期 {attributes.get('expirationDate', '?')[:10]}")
        print("  ! 注意：我们没有这些证书的私钥，所以仍然新建一张（Apple 上限 3 张）")
    cert_der, key_path = create_certificate(token, args.out, openssl, args.dry_run)

    cert_id = None
    if not args.dry_run:
        refreshed = list_distribution_certs(token)
        for cert in refreshed:
            if cert["attributes"].get("expirationDate", "") > (existing[0]["attributes"].get("expirationDate", "") if existing else ""):
                cert_id = cert["id"]
        if not cert_id and refreshed:
            cert_id = refreshed[0]["id"]

    print("\n[3/4] p12 打包")
    if args.dry_run:
        print("  · [dry-run] 跳过")
        p12_path = None
    else:
        wwdr_pem = write_chain_helpers(args.out, openssl)
        p12_path = build_p12(args.out, cert_der, key_path, password, openssl, wwdr_pem)

    print("\n[4/4] App Store 描述文件")
    profile_path = create_profile(
        token, bundle_record_id, cert_id, args.profile_name, args.out, args.dry_run)

    print("\n" + "=" * 56)
    if args.dry_run:
        print("dry-run 完成：凭据可用，未创建任何资源。去掉 --dry-run 正式执行。")
        return 0

    print("完成。下一步把这些写进仓库 Secrets：\n")
    print(f"  .\\scripts\\setup_secrets.ps1 `")
    print(f"      -Repo <owner>/<repo> `")
    print(f"      -P12         {p12_path} `")
    print(f"      -P12Password '{password}' `")
    print(f"      -Profile     {profile_path} `")
    print(f"      -TeamID      {args.team or '<你的TeamID>'}")
    print("\n提示：distribution.key 一定要自己留底，证书丢了可以重签，私钥丢了只能重新申请。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
