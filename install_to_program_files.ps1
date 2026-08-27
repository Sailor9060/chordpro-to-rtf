<#
    Moves ChordProToRTF.exe into "C:\Program Files\Franz Weber Software",
    fixes the Desktop shortcut, adds a matching shortcut inside that folder,
    and adds the folder to the system PATH.

    Must be run from an elevated (Administrator) PowerShell.
#>

$ErrorActionPreference = "Stop"

# --- Require elevation ---------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "This script must be run as Administrator. Right-click PowerShell -> 'Run as administrator', then run this script again." -ForegroundColor Red
    exit 1
}

$targetDir  = "C:\Program Files\Franz Weber Software"
$exeName    = "ChordProToRTF.exe"
$targetExe  = Join-Path $targetDir $exeName
$desktop    = [Environment]::GetFolderPath('Desktop')
$desktopLnk = Join-Path $desktop "ChordProToRTF.lnk"
$folderLnk  = Join-Path $targetDir "ChordProToRTF.lnk"

# Look for the exe next to this script first (the usual case when you've
# downloaded both files from the GitHub release into the same folder),
# then fall back to a couple of common locations.
$candidates = @(
    (Join-Path $PSScriptRoot $exeName),
    (Join-Path (Join-Path $HOME "Downloads") $exeName),
    "C:\Temp\ChordProToRTF\dist\$exeName"
)
$sourceExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

# --- 1. Create the folder -------------------------------------------------
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
Write-Host "Folder ready: $targetDir"

# --- 2. Move the exe --------------------------------------------------------
if ($sourceExe) {
    Move-Item -Path $sourceExe -Destination $targetExe -Force
    Write-Host "Moved exe to: $targetExe"
} elseif (Test-Path $targetExe) {
    Write-Host "Exe already at destination: $targetExe"
} else {
    throw "Could not find $exeName. Place it in the same folder as this script (or in your Downloads folder) and run again."
}

# --- 3. Fix the Desktop shortcut -------------------------------------------
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($desktopLnk)
$shortcut.TargetPath = $targetExe
$shortcut.WorkingDirectory = $targetDir
$shortcut.IconLocation = "$targetExe,0"
$shortcut.Description = "Drop a ChordPro file here to convert it to RTF (lyrics, labels, comments)"
$shortcut.Save()
Write-Host "Desktop shortcut updated: $desktopLnk"

# --- 4. Matching shortcut inside the Program Files folder -------------------
$shortcut2 = $WshShell.CreateShortcut($folderLnk)
$shortcut2.TargetPath = $targetExe
$shortcut2.WorkingDirectory = $targetDir
$shortcut2.IconLocation = "$targetExe,0"
$shortcut2.Description = "Drop a ChordPro file here to convert it to RTF (lyrics, labels, comments)"
$shortcut2.Save()
Write-Host "Shortcut created in Program Files folder: $folderLnk"

# --- 5. Add to system PATH ---------------------------------------------------
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$pathEntries = $machinePath -split ";" | Where-Object { $_ -ne "" }
if ($pathEntries -notcontains $targetDir) {
    $newPath = ($machinePath.TrimEnd(";") + ";" + $targetDir)
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    Write-Host "Added to system PATH: $targetDir"
} else {
    Write-Host "Already on system PATH: $targetDir"
}

Write-Host ""
Write-Host "Done. Open a NEW terminal window for the PATH change to take effect there." -ForegroundColor Green
Write-Host "You can then run the app from anywhere by typing: ChordProToRTF" -ForegroundColor Green
