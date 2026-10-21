"""Build only in a fresh directory; no package installation or scientific refitting."""
from pathlib import Path
import json, os, shutil, subprocess, tempfile
from verify_integrity import ROOT, verify
print(json.dumps(verify()), flush=True)
compiler = os.environ.get('TEX_COMPILER') or shutil.which('tectonic') or shutil.which('xelatex')
if not compiler:
    raise RuntimeError('Install a separate TeX compiler or set TEX_COMPILER; nothing was installed.')
(ROOT/'outputs').mkdir(exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='paper_build_', dir=ROOT/'outputs'))
source = out/'paper'; shutil.copytree(ROOT/'paper', source)
env = dict(os.environ, SOURCE_DATE_EPOCH='1792454400', FORCE_SOURCE_DATE='1')
for name in ['main','supplementary']:
    target = out/name; target.mkdir()
    tectonic = 'tectonic' in Path(compiler).name.lower()
    cmd = ([compiler,'--untrusted','--keep-logs','--keep-intermediates','--outdir',str(target),name+'.tex']
           if tectonic else [compiler,'-interaction=nonstopmode','-halt-on-error','-file-line-error',
                            '-no-shell-escape','-output-directory='+str(target),name+'.tex'])
    for i in range(1 if tectonic else 3):
        with (target/f'pass_{i}.txt').open('w') as f:
            subprocess.run(cmd,cwd=source/'manuscript',env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    text = (target/(name+'.log')).read_text(errors='replace')
    if any(s in text for s in ['Overfull \\hbox','Overfull \\vbox','undefined references']):
        raise RuntimeError('Document diagnostics require inspection: '+str(target))
print('BUILD_OUTPUT_DIRECTORY='+str(out))
print('Render and inspect both PDFs before claiming a document release.')
