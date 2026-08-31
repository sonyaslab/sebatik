$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot '.venv-sebatik\Scripts\python.exe'
Set-Location $ProjectRoot

# `.env` produksi memakai nama layanan Docker `db`. Saat backend dijalankan
# langsung dari Windows, nama itu tidak tersedia; PostgreSQL dijangkau lewat
# port host yang dipublikasikan oleh Docker Compose.
$EnvFile = Join-Path $ProjectRoot '.env'
if (Test-Path $EnvFile) {
    $DatabaseLine = Get-Content $EnvFile | Where-Object { $_ -match '^SEBATIK_DATABASE_URL=' } | Select-Object -Last 1
    if ($DatabaseLine) {
        $DatabaseUrl = $DatabaseLine.Substring('SEBATIK_DATABASE_URL='.Length)
        if ($DatabaseUrl -match '@db:5432(?=/|$)') {
            $PortLine = Get-Content $EnvFile | Where-Object { $_ -match '^POSTGRES_HOST_PORT=' } | Select-Object -Last 1
            $HostPort = if ($PortLine) { $PortLine.Substring('POSTGRES_HOST_PORT='.Length) } else { '5434' }
            $env:SEBATIK_DATABASE_URL = $DatabaseUrl -replace '@db:5432(?=/|$)', "@127.0.0.1:$HostPort"
            Write-Host "Mode lokal: PostgreSQL Docker di 127.0.0.1:$HostPort" -ForegroundColor Cyan

            $TcpClient = [System.Net.Sockets.TcpClient]::new()
            try {
                $Connection = $TcpClient.ConnectAsync('127.0.0.1', [int]$HostPort)
                if (-not $Connection.Wait(1500) -or -not $TcpClient.Connected) {
                    throw 'PostgreSQL lokal belum siap.'
                }
            } catch {
                throw "PostgreSQL belum tersedia di port $HostPort. Nyalakan Docker Desktop, lalu jalankan: docker compose up -d db"
            } finally {
                $TcpClient.Dispose()
            }
        }
    }
}

if (-not (Test-Path 'frontend\dist\index.html')) {
    throw 'Frontend belum dibangun. Jalankan pnpm install dan pnpm build di folder frontend.'
}
$FallbackPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$LocalPackages = Join-Path $ProjectRoot '.runtime-packages'
if (Test-Path $PythonExe) {
    & $PythonExe -c 'import fastapi, pydantic_settings, sqlalchemy, uvicorn' *> $null
}

if ((Test-Path $PythonExe) -and ($LASTEXITCODE -eq 0)) {
    & $PythonExe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
} elseif ((Test-Path $FallbackPython) -and (Test-Path $LocalPackages)) {
    & $FallbackPython scripts\run_local_server.py
} else {
    throw 'Runtime Python belum tersedia. Jalankan .\pasang-sebatik.ps1 terlebih dahulu.'
}
