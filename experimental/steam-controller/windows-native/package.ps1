$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$wdk="$env:USERPROFILE\controller-forwarding\wdk-packages"
$sign="$wdk\microsoft.windows.sdk.cpp\c\bin\10.0.26100.0\x64\signtool.exe"
$cat="$wdk\microsoft.windows.wdk.x64\c\bin\10.0.26100.0\x86\Inf2Cat.exe"
New-Item -ItemType Directory -Force package | Out-Null
Copy-Item MoonmachineSteamHid.dll,MoonmachineSteamHid.inf package
$cert=Get-ChildItem Cert:\CurrentUser\My | Where-Object Subject -eq 'CN=Moonmachine Steam HID development' | Select-Object -First 1
if(!$cert){$cert=New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=Moonmachine Steam HID development' -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddDays(90) -KeyExportPolicy NonExportable}
$cert.Thumbprint | Set-Content certificate-thumbprint.txt
Export-Certificate -Cert $cert -FilePath package\MoonmachineSteamHid.cer | Out-Null
& $sign sign /sha1 $cert.Thumbprint /fd SHA256 package\MoonmachineSteamHid.dll
if($LASTEXITCODE){throw 'DLL signing failed'}
& $cat /driver:package /os:10_X64 /uselocaltime
if($LASTEXITCODE){throw 'catalog generation failed'}
& $sign sign /sha1 $cert.Thumbprint /fd SHA256 package\MoonmachineSteamHid.cat
if($LASTEXITCODE){throw 'catalog signing failed'}
