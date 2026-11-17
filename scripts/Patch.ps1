param([ValidateSet('Install','Restore','Check')][string]$Action='Check',[string]$Root,[switch]$NoRestart,[switch]$TestMode)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility') -Force
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Management') -Force
$package=$PSScriptRoot
if(-not $Root){
 foreach($key in @('HKLM:\SOFTWARE\WOW6432Node\Unwinder\RTSS','HKLM:\SOFTWARE\Unwinder\RTSS')){
  $r=Get-ItemProperty $key -ErrorAction SilentlyContinue
  if($r.InstallDir -and (Test-Path (Join-Path $r.InstallDir 'RTSS.exe'))){$Root=$r.InstallDir;break}
 }
}
if(-not $Root){throw '未检测到 RTSS，请先从 RTSS 官方页面安装 RTSS 7.3.7。'}
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\')
if(-not (Test-Path (Join-Path $Root 'RTSS.exe'))){throw '指定路径不是 RTSS 安装目录。'}
if(-not $TestMode -and $Action -ne 'Check' -and -not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 $elevated="-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Action $Action -Root `"$Root`""
 $p=Start-Process powershell.exe -Verb RunAs -ArgumentList $elevated -Wait -PassThru
 exit $p.ExitCode
}
$state=if($TestMode){Join-Path $Root 'QuietMint-Test-State'}else{Join-Path $env:LOCALAPPDATA 'QuietMintRTSS\FullPatch'}
$pointer=Join-Path $state 'active.json'
$fontDir=if($TestMode){Join-Path $Root 'TestFonts'}else{Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'}
$fontPath=Join-Path $fontDir 'JetBrainsMono-Medium.ttf'
$fontKey='HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
$fontName='JetBrains Mono Medium (TrueType)'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class MintNative {
 [DllImport("kernel32.dll",EntryPoint="WritePrivateProfileStringW",CharSet=CharSet.Unicode,SetLastError=true)]
 public static extern bool DeleteProfileKey(string section,string key,IntPtr value,string path);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
 public static extern bool WritePrivateProfileString(string section,string key,string value,string path);
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)]public static extern int AddFontResourceEx(string file,uint flags,IntPtr value);
 [DllImport("gdi32.dll",CharSet=CharSet.Unicode)]public static extern bool RemoveFontResourceEx(string file,uint flags,IntPtr value);
 [DllImport("user32.dll")]public static extern IntPtr SendMessageTimeout(IntPtr h,uint msg,IntPtr w,IntPtr l,uint flags,uint timeout,out IntPtr result);
}
'@
function Ini($file,$section,$key,$value){if(-not [MintNative]::WritePrivateProfileString($section,$key,$value,$file)){throw "无法保存设置：$key"}}
function Stop-Server {
 if($TestMode -or $NoRestart){return}
 Get-Process RTSS -ErrorAction SilentlyContinue | Stop-Process -Force
 Start-Sleep -Milliseconds 1200
 Get-Process FrameViewBridge64 -ErrorAction SilentlyContinue | Wait-Process -Timeout 5 -ErrorAction SilentlyContinue
 if(Get-Process FrameViewBridge64 -ErrorAction SilentlyContinue){throw '数据桥接尚未退出，请稍后重试。'}
}
function Start-Server {if(-not $TestMode -and -not $NoRestart){Start-Process (Join-Path $Root 'RTSS.exe') -WindowStyle Hidden}}
function Check-Components {
 Write-Host "RTSS：$Root"
 $version=(Get-Item (Join-Path $Root 'RTSS.exe')).VersionInfo.ProductVersion
 foreach($key in @('HKLM:\SOFTWARE\WOW6432Node\Unwinder\RTSS','HKLM:\SOFTWARE\Unwinder\RTSS')){$installed=Get-ItemProperty $key -ErrorAction SilentlyContinue;if($installed.InstallDir -eq $Root -and $installed.ProductVersion){$version=$installed.ProductVersion;break}}
 Write-Host ('版本：'+$version)
 $sdk=Test-Path "$env:ProgramFiles\NVIDIA Corporation\FrameViewSDK\SDK\Public_Release\FvSDK_x64.dll"
 Write-Host $(if($sdk){'FrameView SDK：已找到'}else{'FrameView SDK：未找到。FPS、CPU/GPU 和时间可用；1%L、RLAT、PCL 需官方 FrameView SDK，缺少时显示 --。'})
 Write-Host 'PCL 还需要游戏支持，主菜单中可能没有有效值。无需运行 MSI Afterburner。'
}
function Restore-Manifest($dir){
 $m=Get-Content (Join-Path $dir 'manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($item in $m.Files){
  $target=[IO.Path]::GetFullPath($item.Target)
  if(-not ($target.StartsWith($Root+'\',[StringComparison]::OrdinalIgnoreCase) -or $target -eq $fontPath)){throw '备份目标不在允许的范围内。'}
  if($item.Existed){New-Item -ItemType Directory -Path (Split-Path $target) -Force|Out-Null;$saved=Join-Path $dir $item.Saved;if(-not(Test-Path $target) -or (Get-FileHash $saved).Hash -ne (Get-FileHash $target).Hash){Copy-Item $saved $target -Force}}
  else{Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue}
 }
 if(-not $TestMode){
  if($m.FontRegistryExisted){New-Item $fontKey -Force|Out-Null;Set-ItemProperty $fontKey $fontName $m.FontRegistryValue}
  else{Remove-ItemProperty $fontKey $fontName -ErrorAction SilentlyContinue}
 }
}
if($Action -eq 'Check'){Check-Components;exit 0}
if($Action -eq 'Restore'){
 if(-not(Test-Path $pointer)){throw '没有本整合包的安装备份，未执行还原。'}
 $active=Get-Content $pointer -Raw -Encoding UTF8|ConvertFrom-Json
 if($active.Root -ne $Root){throw '备份所属的 RTSS 目录与当前目录不一致。'}
 Stop-Server
 if(-not $TestMode){[void][MintNative]::RemoveFontResourceEx($fontPath,0,[IntPtr]::Zero)}
 Restore-Manifest $active.Baseline
 Remove-Item $pointer -Force
 Start-Server
 Write-Host '已还原到首次安装本整合包之前的文件、语言、皮肤、OSD 配置和字体注册。备份仍然保留。' -ForegroundColor Green
 exit 0
}
if(-not(Test-Path (Join-Path $Root 'Plugins\Client\OverlayEditor.dll'))){throw '此安装缺少 OverlayEditor 插件。'}
$inventory=Get-Content (Join-Path $package 'payload-hashes.json') -Raw -Encoding UTF8|ConvertFrom-Json
foreach($item in $inventory){$p=Join-Path $package $item.Path;if(-not(Test-Path $p) -or (Get-FileHash $p).Hash -ne $item.SHA256){throw "补丁文件缺失或校验失败：$($item.Path)"}}
$targets=@()
foreach($f in Get-ChildItem (Join-Path $package 'Payload') -Recurse -File){$rel=$f.FullName.Substring((Join-Path $package 'Payload').Length+1);$targets+=[pscustomobject]@{Source=$f.FullName;Target=(Join-Path $Root $rel)}}
foreach($rel in @('Profiles\Config','Profiles\Global','Plugins\Client\OverlayEditor.cfg')){$targets+=[pscustomobject]@{Source=$null;Target=(Join-Path $Root $rel)}}
$targets+=[pscustomobject]@{Source=(Join-Path $package 'Fonts\JetBrainsMono-Medium.ttf');Target=$fontPath}
# Remove only the known superseded atlas, with backup and reference checking.
$obsolete=@()
$oldPreview=Join-Path $Root 'Plugins\Client\QuietMintPreview.dll'
if(Test-Path $oldPreview){$obsolete+=$oldPreview;$targets+=[pscustomobject]@{Source=$null;Target=$oldPreview}}
$atlas=Join-Path $Root 'Plugins\Client\Overlays\QuietMintA_512_v5.png'
$otherRefs=Get-ChildItem (Join-Path $Root 'Plugins\Client\Overlays') -Filter *.ovl -ErrorAction SilentlyContinue | Where-Object {$_.Name -ne 'QuietMint.ovl'} | Select-String -SimpleMatch 'QuietMintA_512_v5.png'
if((Test-Path $atlas) -and -not $otherRefs){$obsolete+=$atlas;$targets+=[pscustomobject]@{Source=$null;Target=$atlas}}

$baseline=$null
if(Test-Path $pointer){$active=Get-Content $pointer -Raw -Encoding UTF8|ConvertFrom-Json;if($active.Root -ne $Root){throw '检测到另一个目录的补丁备份。'};$baseline=$active.Baseline}
New-Item -ItemType Directory $state -Force|Out-Null
$checkpoint=Join-Path $state ('Backups\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory (Join-Path $checkpoint 'Files') -Force|Out-Null
$records=@();$index=0
foreach($item in $targets){$existed=Test-Path -LiteralPath $item.Target;$saved="Files\$index.bak";if($existed){Copy-Item -LiteralPath $item.Target -Destination (Join-Path $checkpoint $saved)};$records+=[pscustomobject]@{Target=$item.Target;Existed=$existed;Saved=$saved};$index++}
$reg=if($TestMode){$null}else{Get-ItemProperty $fontKey -Name $fontName -ErrorAction SilentlyContinue}
$manifest=[pscustomobject]@{Root=$Root;Files=$records;FontRegistryExisted=($null -ne $reg);FontRegistryValue=$(if($reg){$reg.$fontName}else{$null})}
$manifest|ConvertTo-Json -Depth 6|Set-Content (Join-Path $checkpoint 'manifest.json') -Encoding UTF8
try{
 Stop-Server
 foreach($item in $targets){if($item.Source){New-Item -ItemType Directory (Split-Path $item.Target) -Force|Out-Null;if($item.Target -eq $fontPath -and (Test-Path $fontPath)){continue};if(-not(Test-Path $item.Target) -or (Get-FileHash $item.Target).Hash -ne (Get-FileHash $item.Source).Hash){Copy-Item $item.Source $item.Target -Force}}}
 foreach($old in $obsolete){Remove-Item -LiteralPath $old -Force}
 $config=Join-Path $Root 'Profiles\Config';$global=Join-Path $Root 'Profiles\Global'
 Ini $config 'Settings' 'Skin' 'QuietMintCN.usf';Ini $config 'Settings' 'Language' 'CHN'
 foreach($plugin in @('OverlayEditor.dll','FrameViewBridge.dll')){Ini $config 'Plugins' $plugin '1'}
 if(-not [MintNative]::DeleteProfileKey('Plugins','QuietMintPreview.dll',[IntPtr]::Zero,$config)){throw '无法移除旧预览插件配置项。'}
 Ini (Join-Path $Root 'Plugins\Client\OverlayEditor.cfg') 'Settings' 'Layout' 'QuietMint.ovl'
 foreach($pair in @(@('EnableOSD','1'),@('EnableBgnd','1'),@('EnableFill','0'),@('BaseColor','00E5EBEF'),@('ZoomRatio','1'),@('RefreshPeriod','250'),@('IntegerFramerate','1'))){Ini $global 'OSD' $pair[0] $pair[1]}
 # Preserve existing positions, per-game settings, limits, and startup preferences.
 $globalText=Get-Content $global -Raw -ErrorAction SilentlyContinue
 if($globalText -notmatch '(?m)^PositionX='){Ini $global 'OSD' 'PositionX' '-1';Ini $global 'OSD' 'PositionY' '1'}
 Ini $global 'Statistics' 'FramerateAveragingInterval' '500'
 Ini $global 'Font' 'Face' 'JetBrains Mono Medium';Ini $global 'Font' 'Height' '-16';Ini $global 'Font' 'Weight' '400'
 foreach($renderer in @('RendererDirect3D8','RendererDirect3D9','RendererDirect3D10','RendererDirect3D11','RendererDirect3D12','RendererOpenGL','RendererVulkan')){Ini $global $renderer 'Implementation' '2'}
 if(-not $TestMode){
  New-Item $fontKey -Force|Out-Null;if(-not $reg){Set-ItemProperty $fontKey $fontName $fontPath}
  [void][MintNative]::AddFontResourceEx($fontPath,0,[IntPtr]::Zero)
  $result=[IntPtr]::Zero;[void][MintNative]::SendMessageTimeout([IntPtr]0xffff,0x1d,[IntPtr]::Zero,[IntPtr]::Zero,2,1000,[ref]$result)
 }
 if(-not $baseline){$baseline=$checkpoint}
 else {
  # New files introduced by an upgrade also need a pre-install restore record.
  $baseManifest=Get-Content (Join-Path $baseline 'manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
  foreach($r in $records){if($r.Target -notin $baseManifest.Files.Target){$name='Files\upgrade-'+[guid]::NewGuid().ToString()+'.bak';if($r.Existed){Copy-Item (Join-Path $checkpoint $r.Saved) (Join-Path $baseline $name)};$baseManifest.Files+= [pscustomobject]@{Target=$r.Target;Existed=$r.Existed;Saved=$name}}}
  $baseManifest|ConvertTo-Json -Depth 6|Set-Content (Join-Path $baseline 'manifest.json') -Encoding UTF8
 }
 [pscustomobject]@{Root=$Root;Baseline=$baseline;LastCheckpoint=$checkpoint}|ConvertTo-Json|Set-Content $pointer -Encoding UTF8
 Start-Server
 Write-Host "静谧薄荷整合补丁安装完成。还原基线：$baseline" -ForegroundColor Green
 Check-Components
}catch{Write-Host '安装失败，正在回滚本次文件修改。' -ForegroundColor Yellow;Restore-Manifest $checkpoint;Start-Server;throw}
