$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Push-Location -LiteralPath $projectRoot

try {
    python -m PyInstaller --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is not installed. Run: python -m pip install -r requirements-build.txt"
    }

    python -m PyInstaller --noconfirm --clean .\CameraTool.spec
    if ($LASTEXITCODE -ne 0) {
        throw "EXE build failed. PyInstaller exit code: $LASTEXITCODE"
    }

    $exePath = Join-Path $projectRoot "dist\CameraTool.exe"
    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "Build finished but the expected file was not found: $exePath"
    }

    Write-Host "Build succeeded: $exePath"
}
finally {
    Pop-Location
}
