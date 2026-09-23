[CmdletBinding()]
param([string]$AppsPath="$env:ProgramFiles\Apollo\config\apps.json")
$ErrorActionPreference='Stop'
$exe=Join-Path $PSScriptRoot 'SteamControllerLab.exe'
if(!(Test-Path $exe)){throw 'Build SteamControllerLab.exe first'}
$data=Get-Content -Raw -LiteralPath $AppsPath | ConvertFrom-Json
$name='Steam Controller Lab'
$entry=[ordered]@{
 name=$name
 uuid='0C72EFDC-3CB1-4B49-B213-0E985694CECA'
 cmd=('"'+$exe+'"')
 'working-dir'=$PSScriptRoot
 'auto-detach'=$false
 'wait-all'=$false
 'exit-timeout'=5
 'gamepad'='disabled'
 'allow-client-commands'=$false
 'exclude-global-prep-cmd'=$false
}
$old=@($data.apps | Where-Object {$_.uuid -eq $entry.uuid})
if(@($data.apps | Where-Object {$_.name -eq $name -and $_.uuid -ne $entry.uuid}).Count){throw 'Another app already uses this name; refusing to overwrite it'}
$data.apps=@($data.apps | Where-Object {$_.uuid -ne $entry.uuid})+@([pscustomobject]$entry)
$backup=$AppsPath+'.before-controller-lab-'+(Get-Date -Format yyyyMMdd-HHmmss)
Copy-Item -LiteralPath $AppsPath -Destination $backup
$tmp=$AppsPath+'.controller-lab.tmp'
$json=$data | ConvertTo-Json -Depth 40
[IO.File]::WriteAllText($tmp,$json,[Text.UTF8Encoding]::new($false))
[IO.File]::Replace($tmp,$AppsPath,($backup+".replaced"))
Write-Output "Added Steam Controller Lab. Backup: $backup"
Write-Output 'Only this app disables ordinary Xbox-style forwarding; its native HID uses the prototype relay.'
