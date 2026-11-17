"""Assemble a distributable patch without copying machine profiles or vendor SDK files."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/QuietMint-RTSS'
required=[ROOT/'build/bridge/FrameViewBridge.dll',ROOT/'build/bridge/FrameViewBridge64.exe',ROOT/'build/Skins/QuietMintCN.usf']
for f in required:
    if not f.is_file():raise SystemExit(f'Missing build output: {f.relative_to(ROOT)}; see docs/BUILD.md')
if OUT.exists():raise SystemExit('dist/QuietMint-RTSS exists; move it aside before packaging to avoid stale files.')
OUT.mkdir(parents=True)
shutil.copytree(ROOT/'src/localization/CHN',OUT/'Payload/Localization/CHN')
shutil.copytree(ROOT/'assets/overlay',OUT/'Payload/Plugins/Client/Overlays')
shutil.copytree(ROOT/'assets/fonts',OUT/'Fonts')
(OUT/'Payload/Skins').mkdir(parents=True)
shutil.copy2(required[2],OUT/'Payload/Skins'/required[2].name)
for f in required[:2]:shutil.copy2(f,OUT/'Payload/Plugins/Client'/f.name)
for n in ['Patch.ps1','安装补丁.cmd','还原补丁.cmd','检查组件.cmd']:shutil.copy2(ROOT/'scripts'/n,OUT/n)
for n in ['LICENSE','THIRD_PARTY_NOTICES.md']:shutil.copy2(ROOT/n,OUT/n)
shutil.copy2(ROOT/'docs/INSTALL.md',OUT/'使用说明.md')
for f,n in [('hud.png','HUD-Preview.png'),('skin.png','皮肤预览.png')]:shutil.copy2(ROOT/'docs/images'/f,OUT/n)
items=[{'Path':str(f.relative_to(OUT)),'SHA256':hashlib.sha256(f.read_bytes()).hexdigest().upper()} for base in ['Payload','Fonts'] for f in sorted((OUT/base).rglob('*')) if f.is_file()]
(OUT/'payload-hashes.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8-sig')
archive=ROOT/'dist/QuietMint-RTSS-patch.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(OUT.rglob('*')):
        if f.is_file():z.write(f,'QuietMint-RTSS/'+f.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive)
