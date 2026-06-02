# foot (Go) 项目设置脚本
# 从 Gitee 克隆并编译 foot 项目

$footDir = "E:\APP\foot"
$giteeUrl = "https://gitee.com/aoe5188/foot.git"

Write-Host "=== foot (Go) Setup Script ===" -ForegroundColor Cyan
Write-Host ""

# 检查 Git 是否安装
try {
    $gitVersion = git --version
    Write-Host "✓ Git installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git not found. Please install Git first." -ForegroundColor Red
    Write-Host "  Download from: https://git-scm.com/download/win"
    exit 1
}

# 检查 Go 是否安装
try {
    $goVersion = go version
    Write-Host "✓ Go installed: $goVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Go not found. Please install Go first." -ForegroundColor Red
    Write-Host "  Download from: https://go.dev/dl/"
    exit 1
}

Write-Host ""

# 克隆项目
if (Test-Path $footDir) {
    Write-Host "⚠ foot directory already exists: $footDir" -ForegroundColor Yellow
    $response = Read-Host "Do you want to delete and re-clone? (y/n)"
    if ($response -eq "y") {
        Write-Host "Removing existing directory..."
        Remove-Item -Path $footDir -Recurse -Force
    } else {
        Write-Host "Skipping clone. Using existing directory."
        cd $footDir
    }
}

if (-not (Test-Path $footDir)) {
    Write-Host "Cloning foot from Gitee..." -ForegroundColor Cyan
    Write-Host "Repository: $giteeUrl"
    
    try {
        git clone $giteeUrl $footDir
        Write-Host "✓ Clone successful" -ForegroundColor Green
    } catch {
        Write-Host "✗ Clone failed: $_" -ForegroundColor Red
        exit 1
    }
}

# 进入目录
cd $footDir
Write-Host ""
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Cyan

# 检查项目结构
Write-Host ""
Write-Host "Project structure:" -ForegroundColor Cyan
Get-ChildItem | Select-Object Name, Length | Format-Table

# 下载依赖
Write-Host ""
Write-Host "Downloading Go dependencies..." -ForegroundColor Cyan
try {
    go mod download
    Write-Host "✓ Dependencies downloaded" -ForegroundColor Green
} catch {
    Write-Host "⚠ Failed to download dependencies: $_" -ForegroundColor Yellow
    Write-Host "  Continuing anyway..."
}

# 编译
Write-Host ""
Write-Host "Building foot.exe..." -ForegroundColor Cyan
try {
    go build -o foot.exe
    Write-Host "✓ Build successful" -ForegroundColor Green
} catch {
    Write-Host "✗ Build failed: $_" -ForegroundColor Red
    exit 1
}

# 检查可执行文件
if (Test-Path "foot.exe") {
    $fileInfo = Get-Item "foot.exe"
    Write-Host "✓ foot.exe created: $($fileInfo.Length) bytes" -ForegroundColor Green
} else {
    Write-Host "✗ foot.exe not found" -ForegroundColor Red
    exit 1
}

# 测试运行
Write-Host ""
Write-Host "Testing foot.exe..." -ForegroundColor Cyan
try {
    $output = & .\foot.exe --help 2>&1
    Write-Host "✓ foot.exe is executable" -ForegroundColor Green
    Write-Host ""
    Write-Host "Help output:" -ForegroundColor Cyan
    Write-Host $output
} catch {
    Write-Host "⚠ Could not run foot.exe: $_" -ForegroundColor Yellow
}

# 完成
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Configure foot (check config files in $footDir)"
Write-Host "2. Run: cd $footDir && .\foot.exe"
Write-Host "3. Test integration: python E:\APP\ELO\scripts\test_foot_integration.py"
Write-Host ""
