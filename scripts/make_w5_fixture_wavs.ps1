# Offline fixed-input WAVs for the W3/W5 rehearsal: speech synthesised straight to files,
# no microphone, no speaker playback, no capture device. Existing files are never overwritten.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$dir = 'D:\CODE\project\LiveTutor-Lab\benchmarks\raw\voice-input'
function New-Fixture([string]$name, [scriptblock]$build) {
  $path = Join-Path $dir $name
  if (Test-Path -LiteralPath $path) { throw "Preserve existing fixed input: $name" }
  $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
  try {
    $synth.SelectVoice('Microsoft Huihui Desktop')
    $synth.SetOutputToWaveFile($path)
    $builder = New-Object System.Speech.Synthesis.PromptBuilder
    $builder.Culture = [System.Globalization.CultureInfo]::GetCultureInfo('zh-CN')
    & $build $builder
    $synth.Speak($builder)
  } finally { $synth.Dispose() }
  Write-Output "created $name"
}
# W3: a first answer long enough to still be playing when the picture is replaced.
New-Fixture 'daily-w3-picture-detail-20261015.wav' { param($b)
  $b.AppendText('请仔细讲一下当前这张图，每一条箭头的方向都说一说，用中文，不出题。') }
# W5 step 4: the guide sentence with natural mid-sentence pauses (about 0.9 s).
New-Fixture 'daily-w5-step4-pause-20261015.wav' { param($b)
  $b.AppendText('那如果')
  $b.AppendBreak([TimeSpan]::FromMilliseconds(900))
  $b.AppendText('把这个判断改成只在五百以上才抛')
  $b.AppendBreak([TimeSpan]::FromMilliseconds(900))
  $b.AppendText('四零四会怎样？') }
