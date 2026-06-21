param(
    [string]$Base64Text = "",
    [string]$AudioFile = ""
)

Get-WmiObject Win32_Process -Filter "CommandLine LIKE '%Welcome_Chat.ps1%'" | Where-Object { $_.ProcessId -ne $PID } | ForEach-Object { $_.Terminate() }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName PresentationCore

$decodedText = ""
if ($Base64Text) {
    try {
        $decodedText = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Base64Text))
    } catch {}
}

$form = New-Object Windows.Forms.Form
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.BackColor = [System.Drawing.Color]::Black
$form.Opacity = 0.85
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.StartPosition = 'CenterScreen'
$form.WindowState = [System.Windows.Forms.FormWindowState]::Maximized

if ($decodedText) {
    $label = New-Object Windows.Forms.Label
    $label.Text = $decodedText
    $label.ForeColor = [System.Drawing.Color]::White
    $label.Font = New-Object System.Drawing.Font("Microsoft JhengHei", 60, [System.Drawing.FontStyle]::Bold)
    $label.Dock = [System.Windows.Forms.DockStyle]::Fill
    $label.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    # 允許自動折行
    $label.AutoSize = $false
    $form.Controls.Add($label)
}

$global:startedPlaying = $false
$pollTimer = New-Object Windows.Forms.Timer
$pollTimer.Interval = 500
$pollTimer.add_Tick({
    if ($global:wmp) {
        $state = $global:wmp.playState
        if ($state -eq 3) { $global:startedPlaying = $true }
        if ($global:startedPlaying -and $state -eq 1) { 
            Start-Sleep -Seconds 3
            $form.Close() 
        }
    }
})

$safetyTimer = New-Object Windows.Forms.Timer
$safetyTimer.Interval = 30000 
$safetyTimer.add_Tick({ $form.Close() })

$form.add_Shown({
    $safetyTimer.Start()
    if ($AudioFile -ne "" -and (Test-Path $AudioFile)) {
        $global:wmp = New-Object -ComObject WMPlayer.OCX
        $global:wmp.settings.volume = 100
        $global:wmp.URL = $AudioFile
        $global:wmp.controls.play()
        $pollTimer.Start()
    } else {
        Start-Sleep -Seconds 10
        $form.Close()
    }
})

$form.add_FormClosed({
    if ($global:wmp) {
        try {
            $global:wmp.close()
            [System.Runtime.InteropServices.Marshal]::ReleaseComObject($global:wmp) | Out-Null
        } catch {}
    }
})

[System.Windows.Forms.Application]::Run($form)
