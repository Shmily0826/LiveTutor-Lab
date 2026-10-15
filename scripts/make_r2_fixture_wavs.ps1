# Fixed input files only: no microphone, capture device or speaker playback.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$dir = Join-Path (Split-Path -Parent $PSScriptRoot) 'benchmarks/raw/voice-input'
$phrases = [ordered]@{
    'daily-r2-point-20261016.wav' = '请把左边 WEX 到中间 NUD 那条箭头指给我看，在学习材料窗口标出来。'
    'daily-r2-resume-20261016.wav' = '我们上次讲到哪了？'
    'daily-r2-resume-404-20261016.wav' = '接着上次那段代码，如果把判断改成只在五百以上才抛，四零四会怎样？两句话。'
    'daily-r2-interrupt-20261016.wav' = '等一下，先说结论。'
}
foreach ($item in $phrases.GetEnumerator()) {
    $path = Join-Path $dir $item.Key
    if (Test-Path -LiteralPath $path) { throw "Preserve existing fixed input: $($item.Key)" }
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $synth.SelectVoice('Microsoft Huihui Desktop')
        $synth.SetOutputToWaveFile($path)
        $builder = New-Object System.Speech.Synthesis.PromptBuilder
        $builder.Culture = [System.Globalization.CultureInfo]::GetCultureInfo('zh-CN')
        $builder.AppendText($item.Value)
        $synth.Speak($builder)
    } finally { $synth.Dispose() }
    if ((Get-Item -LiteralPath $path).Length -le 44) { throw 'Empty WAV fixture' }
    Write-Output "created $($item.Key)"
}
