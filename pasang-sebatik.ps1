$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# `.env` produksi memakai hostname internal Docker `db`. Perintah Alembic dan
# seed di bawah berjalan dari Windows, sehingga gunakan port host PostgreSQL.
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

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
$FallbackPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if ($PythonCommand) {
    & $PythonCommand.Source -c 'import sys; print(sys.executable)' *> $null
}
if ($PythonCommand -and ($LASTEXITCODE -eq 0)) {
    $BasePython = $PythonCommand.Source
} elseif (Test-Path $FallbackPython) {
    $BasePython = $FallbackPython
} else {
    throw 'Python 3.11 atau lebih baru belum tersedia. Pasang Python, lalu jalankan skrip ini kembali.'
}

$ExistingPython = Join-Path $ProjectRoot '.venv-sebatik\Scripts\python.exe'
$PaksaPasang = $false
if (Test-Path $ExistingPython) {
    & $ExistingPython -c 'import fastapi, pydantic_settings, sqlalchemy, uvicorn' *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Virtual environment lama rusak; membuatnya ulang...' -ForegroundColor Yellow
        # `--upgrade` memperbarui referensi absolut interpreter di pyvenv.cfg.
        # Paket biner kemudian wajib dipasang ulang untuk versi Python baru.
        & $BasePython -m venv --upgrade .venv-sebatik
        $PaksaPasang = $true
    }
} else {
    & $BasePython -m venv .venv-sebatik
}

$Python = Join-Path $ProjectRoot '.venv-sebatik\Scripts\python.exe'
if ($PaksaPasang) {
    & $Python -m pip install --force-reinstall -r requirements.txt
} else {
    & $Python -m pip install -r requirements.txt
}

Push-Location frontend
try {
    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        pnpm install
        pnpm build
    } elseif (Get-Command npm -ErrorAction SilentlyContinue) {
        npm install
        npm run build
    } else {
        throw 'Node.js/npm belum tersedia. Pasang Node.js versi 20 atau lebih baru, lalu jalankan skrip ini kembali.'
    }
} finally {
    Pop-Location
}

# Skema dikelola Alembic, bukan lagi dibuat saat aplikasi mengimpor modul.
& $Python -m alembic -c backend/alembic.ini upgrade head

# Akun awal dibuat eksplisit. Sandinya acak dan hanya ditampilkan sekali di sini.
& $Python -m backend.app.cli seed --tampilkan-sandi

# Master indikator dibundel sebagai fixture kanonis dan dimuat idempoten.
# Perintah ini aman dijalankan ulang karena melewati seed bila data sudah ada.
& $Python -m backend.app.cli seed-indikator

Write-Host ''
Write-Host 'Pemasangan selesai. Catat sandi di atas, lalu jalankan .\jalankan-sebatik.ps1' -ForegroundColor Green
