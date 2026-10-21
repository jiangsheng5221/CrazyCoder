#Requires -Version 5.1
<#
.SYNOPSIS
    把签名资产一键写入 GitHub Repository Secrets。

.DESCRIPTION
    手工做 base64 最容易出错（多一个换行就废）。
    这个脚本从本地文件直接编码、直接写入，写完还会回读校验。

    安全约定：
      - 证书 / 描述文件 / .p8 永远只存在本地 certs/ 目录（已被 .gitignore 挡住）
      - Secrets 写入后 GitHub 只存密文，网页和 API 都读不回原文
      - 脚本不会 echo 任何密钥内容

.EXAMPLE
    # 最小可用：只配正式打包需要的 5 个
    .\scripts\setup_secrets.ps1 `
        -Repo jiangsheng5221/CrazyCoder `
        -P12          certs\distribution.p12 `
        -P12Password  '你的p12密码' `
        -Profile      certs\CrazyCoder.mobileprovision `
        -TeamID       9U9FGR2HTF

.EXAMPLE
    # 再带上 TestFlight 自动上传需要的三个
    .\scripts\setup_secrets.ps1 -Repo owner/name `
        -P12 certs\distribution.p12 -P12Password '密码' `
        -Profile certs\CrazyCoder.mobileprovision -TeamID 9U9FGR2HTF `
        -AscKey certs\AuthKey_XXXXXXXXXX.p8 -AscKeyID XXXXXXXXXX -AscIssuerID 00000000-0000-0000-0000-000000000000
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Repo,

    [Parameter(Mandatory = $true)][string]$P12,
    [Parameter(Mandatory = $true)][string]$P12Password,

    [Parameter(Mandatory = $true)][string]$Profile,
    [Parameter(Mandatory = $true)][string]$TeamID,

    # 留空则自动生成随机值：这只是 CI 里临时钥匙串的密码，用完即销毁
    [string]$KeychainPassword = '',

    # 下面三个是可选的，只有要自动上传 TestFlight 才需要
    [string]$AscKey = '',
    [string]$AscKeyID = '',
    [string]$AscIssuerID = ''
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "  -> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "     OK  $msg" -ForegroundColor Green }

function Assert-Path($path, $what) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "找不到$what：$path"
    }
    $size = (Get-Item -LiteralPath $path).Length
    if ($size -eq 0) { throw "$what 是空文件：$path" }
    return $size
}

function Set-SecretFromFile($name, $path) {
    $bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $path))
    $b64 = [Convert]::ToBase64String($bytes)
    # gh 从 stdin 读；base64 单行，不含换行
    $b64 | gh secret set $name --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw "写入 $name 失败（gh 退出码 $LASTEXITCODE）" }
    Write-Ok "$name（$([math]::Round($b64.Length / 1024, 1)) KB base64）"
}

function Set-SecretText($name, $value) {
    gh secret set $name --repo $Repo --body $value
    if ($LASTEXITCODE -ne 0) { throw "写入 $name 失败（gh 退出码 $LASTEXITCODE）" }
    Write-Ok $name
}

Write-Host ""
Write-Host "=== 校验环境 ===" -ForegroundColor White

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'gh CLI 不在 PATH 里（winget install --id GitHub.cli）'
}
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'gh 未登录，先跑 gh auth login' }
Write-Ok "gh 已登录"

if ($TeamID -notmatch '^[A-Z0-9]{10}$') {
    throw "Team ID 应该正好 10 位大写字母/数字，当前是：$TeamID"
}
Write-Ok "Team ID 格式正确：$TeamID"

$p12Size = Assert-Path $P12 '证书文件'
$profileSize = Assert-Path $Profile '描述文件'
Write-Ok ".p12 $([math]::Round($p12Size / 1KB, 1)) KB"
Write-Ok ".mobileprovision $([math]::Round($profileSize / 1KB, 1)) KB"

if ($profileSize -gt 100KB) {
    Write-Host "     注意：描述文件通常 8-15 KB，这个偏大，确认没选错文件" -ForegroundColor Yellow
}

if ([string]::IsNullOrWhiteSpace($KeychainPassword)) {
    $KeychainPassword = -join ((48..57) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
}

Write-Host ""
Write-Host "=== 写入 Secrets 到 $Repo ===" -ForegroundColor White

Set-SecretText 'DEVELOPMENT_TEAM' $TeamID
Set-SecretFromFile 'CERTIFICATE_BASE64' $P12
Set-SecretText 'P12_PASSWORD' $P12Password
Set-SecretFromFile 'PROVISIONING_PROFILE' $Profile
Set-SecretText 'KEYCHAIN_PASSWORD' $KeychainPassword

$hasAsc = -not [string]::IsNullOrWhiteSpace($AscKey) -and
          -not [string]::IsNullOrWhiteSpace($AscKeyID) -and
          -not [string]::IsNullOrWhiteSpace($AscIssuerID)

if ($hasAsc) {
    $ascSize = Assert-Path $AscKey '.p8 文件'
    Write-Ok ".p8 $([math]::Round($ascSize, 1)) KB"
    # .p8 是文本，直接按文本存（workflow 里 printf 出来就是钥匙文件）
    $p8 = Get-Content -LiteralPath $AscKey -Raw
    gh secret set 'ASC_KEY_P8' --repo $Repo --body $p8
    if ($LASTEXITCODE -ne 0) { throw '写入 ASC_KEY_P8 失败' }
    Write-Ok 'ASC_KEY_P8'
    Set-SecretText 'ASC_KEY_ID' $AscKeyID
    Set-SecretText 'ASC_ISSUER_ID' $AscIssuerID
} else {
    Write-Host ""
    Write-Host "  跳过 TestFlight 三件套（没给 .p8）：正式包仍可构建，只是不会自动上传" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== 回读校验 ===" -ForegroundColor White
gh secret list --repo $Repo
if ($LASTEXITCODE -ne 0) { throw '回读 secret 列表失败' }

Write-Host ""
Write-Host "完成。下一步：" -ForegroundColor Green
Write-Host "  1) 触发编译检查：gh workflow run compile.yml -R $Repo"
Write-Host "  2) 正式发版：    git tag v1.0.0; git push origin v1.0.0"
Write-Host ""
