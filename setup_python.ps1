param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('InstallIfMissing', 'CheckUpdate')]
    [string]$Mode,
    [string]$CurrentVersion
)

$ErrorActionPreference = 'Stop'
$PythonDownloadsPage = 'https://www.python.org/downloads/windows/'

function Get-LatestPythonVersion {
    $page = Invoke-WebRequest -UseBasicParsing -Uri $PythonDownloadsPage
    $match = [regex]::Match(
        $page.Content,
        '(?is)Latest\s+Python\s+3\s+Release.*?Python\s+([0-9]+\.[0-9]+\.[0-9]+)'
    )

    if (-not $match.Success) {
        throw 'Could not determine the latest stable Python 3 release from python.org.'
    }

    return $match.Groups[1].Value
}

function Get-InstallerUrl([string]$Version) {
    if ([Environment]::Is64BitOperatingSystem) {
        $architecture = if ($env:PROCESSOR_ARCHITECTURE -match 'ARM64') { 'arm64' } else { 'amd64' }
        return "https://www.python.org/ftp/python/$Version/python-$Version-$architecture.exe"
    }

    return "https://www.python.org/ftp/python/$Version/python-$Version.exe"
}

function Install-Python([string]$Version) {
    $answer = Read-Host "  Download and install Python $Version from python.org now? [Y/N]"
    if ($answer -notmatch '^(?i:y|yes)$') {
        Write-Host '  Python installation cancelled.'
        return $false
    }

    $installer = Join-Path $env:TEMP "python-$Version-installer.exe"
    try {
        Write-Host '  Downloading the official Python installer...'
        Invoke-WebRequest -UseBasicParsing -Uri (Get-InstallerUrl $Version) -OutFile $installer

        $signature = Get-AuthenticodeSignature -FilePath $installer
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
            throw 'The downloaded installer does not have a valid Python Software Foundation signature.'
        }

        Write-Host '  Installing Python...'
        $process = Start-Process -FilePath $installer -ArgumentList @(
            '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1', 'Include_pip=1', 'Include_test=0'
        ) -Wait -PassThru

        if ($process.ExitCode -notin 0, 3010) {
            throw "The Python installer exited with code $($process.ExitCode)."
        }

        Write-Host "  Python $Version is ready."
        return $true
    }
    finally {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }
}

try {
    $latestVersion = Get-LatestPythonVersion

    if ($Mode -eq 'InstallIfMissing') {
        Write-Host "  Latest stable Python: $latestVersion"
        if (Install-Python $latestVersion) { exit 2 }
        exit 0
    }

    $installed = [version]$CurrentVersion
    $latest = [version]$latestVersion
    if ($installed -ge $latest) {
        Write-Host "  Python is up to date ($CurrentVersion)."
        exit 0
    }

    Write-Host "  Python update available: $CurrentVersion -> $latestVersion"
    if (Install-Python $latestVersion) { exit 2 }
    exit 0
}
catch {
    Write-Host "  WARNING: Python update check was skipped: $($_.Exception.Message)"
    exit 1
}
