# 4R Bot — Windows'a kalıcı kurulum. Yönetici PowerShell'inde bir kez çalıştırılır.
#
#   .\scripts\windows_kur.ps1 -Tunel 4r-bot
#
# Yaptıkları:
#   1. Bot bilgisayar açılınca kendiliğinden başlar (terminal açık kalmak zorunda değil).
#   2. Çökerse 1 dakika içinde yeniden başlar.
#   3. Saat başı sağlık kontrolü + veritabanı yedeği alınır.
#   4. Bilgisayar uyku moduna girmez.
#
# -Tunel verilmezse tünel görevi kurulmaz: hızlı tünelin adresi her yeniden başlatmada
# değişir ve sitedeki widget sessizce ölür. Önce kalıcı tünel oluşturun:
#   cloudflared tunnel login
#   cloudflared tunnel create 4r-bot
#   cloudflared tunnel route dns 4r-bot bot.4r.com.tr
# sonra bu script'i -Tunel 4r-bot ile çalıştırın.

param([string]$Tunel = "")

$ErrorActionPreference = "Stop"
$kok = Split-Path -Parent $PSScriptRoot
$python = Join-Path $kok ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Sanal ortam yok: $python — önce DEPLOY.md Bölüm 2." }

$ayar = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
$kimlik = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

function Kur($ad, $program, $argumanlar, $tetik) {
    $eylem = New-ScheduledTaskAction -Execute $program -Argument $argumanlar -WorkingDirectory $kok
    Register-ScheduledTask -TaskName $ad -Action $eylem -Trigger $tetik -Settings $ayar `
        -Principal $kimlik -Force | Out-Null
    Write-Host "  [+] $ad"
}

Write-Host "Görevler kuruluyor:"
Kur "4R Bot" $python "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" `
    (New-ScheduledTaskTrigger -AtStartup)

$saatlik = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration ([TimeSpan]::MaxValue)
Kur "4R Bakim" $python "scripts\bakim.py" $saatlik

if ($Tunel) {
    $cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
    if (-not $cf) { throw "cloudflared bulunamadı — winget install -e --id Cloudflare.cloudflared" }
    Kur "4R Tunel" $cf "tunnel run $Tunel" (New-ScheduledTaskTrigger -AtStartup)
} else {
    Write-Host "  [!] Tünel görevi kurulmadi (-Tunel verilmedi). Basliktaki notu okuyun." -ForegroundColor Yellow
}

powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
Write-Host "  [+] Uyku modu kapatildi"

Start-ScheduledTask "4R Bot"
Start-Sleep -Seconds 5
try {
    $s = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 15
    Write-Host "`nBot ayakta: atik kodu $($s.atik_kodu), belge $($s.belge)" -ForegroundColor Green
} catch {
    Write-Host "`nBot henuz cevap vermiyor. Gorev Zamanlayici > '4R Bot' gecmisine bakin." -ForegroundColor Red
}
