<#
    Runs the connect-Google-and-WakaTime wizard from PowerShell.

    Why this file exists: in PowerShell, `bash` resolves to
    C:\Windows\System32\bash.exe - the WSL launcher, NOT Git Bash. On a box
    where WSL is not installed (or is broken, as here:
    Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG) that exits silently, so
    `bash connect_google_and_wakatime.sh` looks like nothing happened at all.

    This launcher finds the real Git Bash and runs the wizard with it.

        PS B:\inky_code> Main_Menu\Setup\connect_google_and_wakatime.ps1
#>

$ErrorActionPreference = 'Stop'

function Find-GitBash {
    # 1. The two standard install locations.
    $candidates = @(
        "$env:ProgramFiles\Git\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
        "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }

    # 2. Derive it from git.exe on PATH (…\Git\cmd\git.exe -> …\Git\bin\bash.exe).
    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($git) {
        $guess = Join-Path (Split-Path (Split-Path $git.Source) -Parent) 'bin\bash.exe'
        if (Test-Path $guess) { return $guess }
    }

    # 3. Any bash on PATH that is NOT the WSL shim.
    foreach ($b in (Get-Command bash -All -ErrorAction SilentlyContinue)) {
        if ($b.Source -and $b.Source -notmatch '\\System32\\|\\WindowsApps\\') { return $b.Source }
    }
    return $null
}

$bash = Find-GitBash
if (-not $bash) {
    Write-Host "Could not find Git Bash." -ForegroundColor Red
    Write-Host "Install Git for Windows (https://git-scm.com/download/win), then re-run."
    Write-Host "Note: plain 'bash' in PowerShell is the WSL launcher, which is not set up here."
    exit 1
}

$script = Join-Path $PSScriptRoot 'connect_google_and_wakatime.sh'
if (-not (Test-Path $script)) {
    Write-Host "Wizard script not found next to this launcher: $script" -ForegroundColor Red
    exit 1
}

Write-Host "Using $bash" -ForegroundColor DarkGray
& $bash $script @args
exit $LASTEXITCODE
