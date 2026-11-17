from pathlib import Path
import subprocess,json,hashlib,tempfile
ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'dist/QuietMint-RTSS'
fixture=Path(tempfile.mkdtemp(prefix='full-patch-fixture-',dir=ROOT/'build'))
for rel,data in {
 'RTSS.exe':b'isolated-test-fixture',
 'Plugins/Client/QuietMintPreview.dll':b'previous preview plugin',
 'Plugins/Client/OverlayEditor.dll':b'original-editor',
 'Profiles/Global':b'[OSD]\r\nPositionX=31\r\nPositionY=47\r\n[Framerate]\r\nLimit=361\r\n',
 'Profiles/Config':b'[Settings]\r\nSkin=default.usf\r\nLanguage=ENG\r\n[Plugins]\r\nQuietMintPreview.dll=1\r\n',
 'Profiles/Overwatch.exe.cfg':b'[Framerate]\r\nLimit=450\r\n',
 'Localization/CHN/Translation/RTSS.exe/Dialogs':b'original-localization',
 'UserNote.txt':b'never change unrelated files',
 'Plugins/Client/Overlays/QuietMintA_512_v5.png':b'old atlas for cleanup restore test',
}.items():
 p=fixture/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def snapshot():return {str(p.relative_to(fixture)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file() and 'QuietMint-Test-State' not in p.parts}
original=snapshot()
def run(action,success=True):
 p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(PACKAGE/'Patch.ps1'),'-Action',action,'-Root',str(fixture),'-TestMode','-NoRestart'],capture_output=True)
 if (p.returncode==0)!=success:raise RuntimeError(p.stdout.decode('utf-8',errors='replace')+p.stderr.decode('utf-8',errors='replace'))
 return p
run('Install')
active=json.loads((fixture/'QuietMint-Test-State/active.json').read_text(encoding='utf-8-sig'))
assert (fixture/'Profiles/Overwatch.exe.cfg').read_bytes()==b'[Framerate]\r\nLimit=450\r\n'
assert b'Limit=361' in (fixture/'Profiles/Global').read_bytes()
assert not (fixture/'Plugins/Client/QuietMintPreview.dll').exists()
assert b'QuietMintPreview.dll=' not in (fixture/'Profiles/Config').read_bytes()
assert not (fixture/'Plugins/Client/Overlays/QuietMintA_512_v5.png').exists()
assert (fixture/'Plugins/Client/Overlays/QuietMintAtlas.png').exists()
run('Install')
assert json.loads((fixture/'QuietMint-Test-State/active.json').read_text(encoding='utf-8-sig'))['Baseline']==active['Baseline']
run('Restore')
assert snapshot()==original,(set(snapshot())-set(original))
# Force an install failure after some payload files have been copied.
skins=fixture/'Skins'
if skins.exists():skins.rmdir()
skins.write_bytes(b'blocked directory for rollback test')
before=snapshot();run('Install',False);assert snapshot()==before
skins.unlink()
print('PASS: first install, repeated install with stable baseline, exact file restore, preserved limits and unrelated files, rollback after partial-copy failure.')
