param(
    [switch]$Jalankan
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Database ini sengaja terpisah dari .env dan database deployment.
$DatabasePath = Join-Path $ProjectRoot 'data\processed\sebatik-uji-operator.db'
$DatabaseUrlPath = $DatabasePath.Replace('\', '/')
$env:SEBATIK_ENVIRONMENT = 'development'
$env:SEBATIK_DATABASE_URL = "sqlite:///$DatabaseUrlPath"
$env:SEBATIK_SECRET_KEY = 'sebatik-uji-lokal-2026-kunci-rahasia-aman'
$PasswordUji = 'Sebatik-Uji-Lokal-2026!'

Write-Host "Database uji: $DatabasePath" -ForegroundColor Cyan
Write-Host 'Database produksi tidak akan disentuh.' -ForegroundColor Cyan

$Python = Join-Path $ProjectRoot '.venv-sebatik\Scripts\python.exe'
$FallbackPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$LocalPackages = Join-Path $ProjectRoot '.runtime-packages'
$RuntimeSiap = $false
if (Test-Path $Python) {
    # Windows PowerShell mengubah stderr program native menjadi ErrorRecord.
    # Turunkan preferensi hanya selama probe agar runtime rusak dapat diperbaiki,
    # bukan menghentikan skrip sebelum blok pemasangan dijalankan.
    $PreferensiSemula = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    & $Python -c 'import fastapi, openpyxl, sqlalchemy, uvicorn' 2>$null
    $KodeProbe = $LASTEXITCODE
    $ErrorActionPreference = $PreferensiSemula
    $RuntimeSiap = $KodeProbe -eq 0
}
if ((-not $RuntimeSiap) -and (Test-Path $FallbackPython) -and (Test-Path $LocalPackages)) {
    $PythonPathSemula = $env:PYTHONPATH
    $env:PYTHONPATH = $LocalPackages
    $PreferensiSemula = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    & $FallbackPython -c 'import fastapi, openpyxl, sqlalchemy, uvicorn, alembic, pydantic_core; assert callable(getattr(uvicorn, "run", None))' 2>$null
    $KodeProbe = $LASTEXITCODE
    $ErrorActionPreference = $PreferensiSemula
    if ($KodeProbe -eq 0) {
        $Python = $FallbackPython
        $RuntimeSiap = $true
        Write-Host 'Menggunakan runtime cadangan lokal.' -ForegroundColor Cyan
    } else {
        $env:PYTHONPATH = $PythonPathSemula
    }
}
if (-not $RuntimeSiap) {
    Write-Host 'Runtime belum siap; menjalankan pemasangan lokal...' -ForegroundColor Yellow
    & (Join-Path $ProjectRoot 'pasang-sebatik.ps1') -LewatiSeed
    $Python = Join-Path $ProjectRoot '.venv-sebatik\Scripts\python.exe'
}

& $Python -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migrasi database uji gagal.' }
& $Python -m backend.app.cli seed-indikator
if ($LASTEXITCODE -ne 0) { throw 'Seed indikator uji gagal.' }
& $Python -m backend.app.cli seed-uji --password $PasswordUji
if ($LASTEXITCODE -ne 0) { throw 'Seed akun uji gagal.' }
& $Python -m backend.app.cli periksa
if ($LASTEXITCODE -ne 0) { throw 'Pemeriksaan database uji gagal.' }

Write-Host ''
Write-Host 'Lingkungan uji siap.' -ForegroundColor Green
Write-Host "Password seluruh akun uji: $PasswordUji" -ForegroundColor Green
Write-Host 'Admin       : admin'
Write-Host 'Verifikator : verifikator.65.1'
Write-Host 'Operator    : operator.<kode-wilayah>.1 atau .2'
Write-Host ''

if ($Jalankan) {
    & (Join-Path $ProjectRoot 'jalankan-sebatik.ps1')
} else {
    Write-Host 'Jalankan aplikasi pada terminal yang sama dengan:' -ForegroundColor Yellow
    Write-Host '  .\siapkan-uji-unggahan-operator.ps1 -Jalankan'
}
