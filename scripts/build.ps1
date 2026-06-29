# Determine the project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Define paths
$envPath = "C:\Users\Admin\Documents\work\projects\VSCodeProjects\universal-video-muxer\.conda"
$ffmpegPath = "tools\ffmpeg.exe"
$ffprobePath = "tools\ffprobe.exe"
$iconIco = "assets\icon.ico"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Universal Video Muxer - PyInstaller Build Tool " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# Pre-flight checks
$missingFiles = @()
if (-not (Test-Path $ffmpegPath)) { $missingFiles += $ffmpegPath }
if (-not (Test-Path $ffprobePath)) { $missingFiles += $ffprobePath }

if ($missingFiles.Count -gt 0) {
    Write-Host "[ERROR] Missing required files:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Build the PyInstaller command
$iconArg = ""
if (Test-Path $iconIco) {
    $iconArg = "--icon=`"$iconIco`""
}

$cmdToRun = "conda activate `"$envPath`" && pyinstaller --noconfirm --onefile --windowed --name `"UniversalVideoMuxer`" $iconArg --add-binary `"$ffmpegPath;.`" --add-binary `"$ffprobePath;.`" --collect-all `"customtkinter`" gui.py"

Write-Host "Activating environment: $envPath" -ForegroundColor Green
Write-Host "Executing PyInstaller..." -ForegroundColor Green
Write-Host ""

# Execute via cmd.exe to ensure Conda hooks trigger correctly
cmd /c $cmdToRun

# Check the exit code of the build process
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Build Successful!" -ForegroundColor Green
    Write-Host "Your executable is located at: .\dist\UniversalVideoMuxer.exe" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "Build Failed! Check the errors above." -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
