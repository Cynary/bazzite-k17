# Run on the Windows HOST while streaming, after selecting the new Xbox Series
# backend. Windows PowerShell 5.1, not PowerShell 7. No driver installation here.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Gaming.Input.Gamepad,Windows.Gaming.Input,ContentType=WindowsRuntime] | Out-Null
[Windows.Gaming.Input.GamepadVibration,Windows.Gaming.Input,ContentType=WindowsRuntime] | Out-Null
$pads = @([Windows.Gaming.Input.Gamepad]::Gamepads)
if ($pads.Count -eq 0) { throw 'No Windows.Gaming.Input gamepads. Start the stream and check the virtual Xbox Series driver.' }
Write-Host "$($pads.Count) gamepad(s) detected. If more than one is present, disconnect other controllers before testing."
if ($pads.Count -ne 1) { throw 'Refusing to choose among multiple gamepads.' }
$pad = $pads[0]
$old = $pad.Vibration
$steps = @(
    @('LEFT GRIP only',0.35,0,0,0),
    @('RIGHT GRIP only',0,0.35,0,0),
    @('LEFT TRIGGER only',0,0,0.35,0),
    @('RIGHT TRIGGER only',0,0,0,0.35),
    @('LEFT GRIP + RIGHT TRIGGER',0.35,0,0,0.35),
    @('RIGHT TRIGGER continues; grip stops',0,0,0,0.35),
    @('LEFT GRIP + RIGHT TRIGGER',0.35,0,0,0.35),
    @('LEFT GRIP continues; trigger stops',0.35,0,0,0)
)
try {
    Read-Host 'Hold the controller and press Enter. Each pulse lasts one second; Ctrl+C stops' | Out-Null
    foreach ($step in $steps) {
        Write-Host $step[0]
        $v = New-Object Windows.Gaming.Input.GamepadVibration
        $v.LeftMotor = $step[1]; $v.RightMotor = $step[2]
        $v.LeftTrigger = $step[3]; $v.RightTrigger = $step[4]
        $pad.Vibration = $v
        Start-Sleep -Milliseconds 1000
    }
} finally {
    $pad.Vibration = New-Object Windows.Gaming.Input.GamepadVibration
}
Write-Host 'Stopped all motors. Report which steps you felt; accepted commands alone do not prove forwarding.'
