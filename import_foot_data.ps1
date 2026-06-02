# foot 历史数据导入脚本
# 用法: .\import_foot_data.ps1 -SqlFile "C:\path\to\foot_data.sql"
# 或者: .\import_foot_data.ps1 -SqlDir "C:\path\to\sql_folder"

param(
    [string]$SqlFile = "",
    [string]$SqlDir  = "",
    [string]$Host    = "127.0.0.1",
    [string]$Port    = "3306",
    [string]$User    = "root",
    [string]$Pass    = "Meta.123",
    [string]$DB      = "foot"
)

$MYSQL = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
$env:PATH += ";C:\Program Files\MySQL\MySQL Server 8.4\bin"

function Run-Sql($file) {
    Write-Host "  导入: $file ..." -NoNewline
    $proc = Start-Process -FilePath $MYSQL `
        -ArgumentList "-h", $Host, "-P", $Port, "-u", $User, "-p$Pass", $DB `
        -RedirectStandardInput $file `
        -RedirectStandardError "$env:TEMP\mysql_err.txt" `
        -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        $err = Get-Content "$env:TEMP\mysql_err.txt" -ErrorAction SilentlyContinue
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "    $err" -ForegroundColor Yellow
    }
    return $proc.ExitCode
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  foot 历史数据导入工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  目标: $User@$Host`:$Port/$DB"
Write-Host ""

# 测试连接
Write-Host "测试数据库连接..." -NoNewline
$test = & $MYSQL -h $Host -P $Port -u $User "-p$Pass" -e "SELECT 1;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host " 失败" -ForegroundColor Red
    Write-Host "请确认 MySQL 正在运行，连接参数正确" -ForegroundColor Yellow
    exit 1
}
Write-Host " OK" -ForegroundColor Green

# 确定要导入的文件列表
$files = @()

if ($SqlFile -ne "" -and (Test-Path $SqlFile)) {
    $files = @($SqlFile)
} elseif ($SqlDir -ne "" -and (Test-Path $SqlDir)) {
    $files = Get-ChildItem $SqlDir -Filter "*.sql" | Sort-Object Name | Select-Object -ExpandProperty FullName
    Write-Host "找到 $($files.Count) 个 SQL 文件"
} else {
    Write-Host "用法示例:" -ForegroundColor Yellow
    Write-Host "  .\import_foot_data.ps1 -SqlFile 'C:\Downloads\foot.sql'"
    Write-Host "  .\import_foot_data.ps1 -SqlDir  'C:\Downloads\foot_sql_files'"
    exit 1
}

if ($files.Count -eq 0) {
    Write-Host "未找到 SQL 文件" -ForegroundColor Red
    exit 1
}

# 执行导入
$start = Get-Date
$ok = 0; $fail = 0

foreach ($f in $files) {
    $code = Run-Sql $f
    if ($code -eq 0) { $ok++ } else { $fail++ }
}

$elapsed = [int]((Get-Date) - $start).TotalSeconds

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  导入完成: 成功 $ok / 失败 $fail / 耗时 ${elapsed}s"
Write-Host "========================================" -ForegroundColor Cyan

# 验证数据量
Write-Host ""
Write-Host "数据验证:"
$tables = @("t_match_his", "t_asia_his", "t_euro_his", "t_analy_result", "t_b_f_score", "t_league")
foreach ($t in $tables) {
    $cnt = & $MYSQL -h $Host -P $Port -u $User "-p$Pass" $DB `
        --skip-column-names -e "SELECT COUNT(*) FROM $t;" 2>$null
    Write-Host ("  {0,-25} {1,10} 行" -f $t, $cnt)
}
