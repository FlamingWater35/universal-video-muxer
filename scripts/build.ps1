# Define the Conda environment path
$envPath = "C:\Users\Admin\Documents\Mux-Sub\.conda"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host " Universal Video Muxer - PyInstaller Build Tool " -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Pre-flight check: Ensure binaries are present to be embedded
if (-not (Test-Path "ffmpeg.exe") -or -not (Test-Path "ffprobe.exe")) {
    Write-Host "[WARNING] ffmpeg.exe or ffprobe.exe not found in the current directory!" -ForegroundColor Yellow
    Write-Host "Please ensure they are in the same folder as this script before building." -ForegroundColor Yellow
    Write-Host ""
}

# Construct the command string
$cmdToRun = "conda activate `"$envPath`" && pyinstaller --noconfirm --onefile --windowed --name `"UniversalVideoMuxer`" --add-binary `"ffmpeg.exe;.`" --add-binary `"ffprobe.exe;.`" --collect-all `"customtkinter`" gui.py"

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
