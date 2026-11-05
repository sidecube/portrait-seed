"""Conservative release inventory and accidental-secret check; standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={'README.md','AGENTS.md','PUBLISH.md','LICENSE','SECURITY.md','THIRD_PARTY.md',
            'pyproject.toml','.gitignore','.env.example','requirements-tested.txt','MANIFEST.sha256.json'}
TOP_DIRS={'src','tests','docs','tools','.github'}
EXTENSIONS={'.py','.md','.toml','.yml','.svg','.json','.png','.txt'}
SKIP_DIRS={'.git','.venv','venv','__pycache__','.pytest_cache','build','dist'}
DENIED_EXT={'.gguf','.onnx','.safetensors','.pt','.pth','.db','.sqlite','.sqlite3','.pem','.key','.log'}


def release_files():
    selected=[]
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.endswith('.egg-info') for part in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError('Symlink is not permitted: '+rel.as_posix())
        if path.is_dir():
            if rel.parts[0] not in TOP_DIRS:
                raise ValueError('Unexpected directory: '+rel.parts[0])
            continue
        if path.name.startswith('.env') and path.name!='.env.example':
            raise ValueError('Environment file must not be released: '+rel.as_posix())
        if path.suffix.lower() in DENIED_EXT or 'private-data' in rel.parts:
            raise ValueError('Private/runtime file must not be released: '+rel.as_posix())
        if len(rel.parts)==1:
            if path.name not in ROOT_FILES:
                raise ValueError('Unexpected root file: '+rel.as_posix())
        elif rel.parts[0] not in TOP_DIRS or path.suffix not in EXTENSIONS:
            raise ValueError('Unexpected package file: '+rel.as_posix())
        if path.suffix=='.png' and rel.as_posix()!='docs/images/overview.png':
            raise ValueError('Only the commissioned overview PNG is allowed: '+rel.as_posix())
        selected.append(path)
    return selected


def audit(files):
    patterns=[r'sk-'+r'(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',
              r'-----BEGIN '+r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
              r'gh[pousr]_'+r'[A-Za-z0-9]{30,}',
              r'github_pat_'+r'[A-Za-z0-9_]{30,}',
              r'(?i)(?:C:[/\\]Users[/\\]|10\.66\.66\.|192\.168\.|'+'true'+'nas)']
    for path in files:
        if path.suffix=='.png':
            continue
        text=path.read_text(encoding='utf-8')
        for pattern in patterns:
            if re.search(pattern,text):
                raise ValueError('Possible secret or private-machine detail in '+path.relative_to(ROOT).as_posix())
        if path.suffix=='.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
                if target.startswith(('http:','https:','#','mailto:')):
                    continue
                resolved=(path.parent/target.split('#',1)[0]).resolve()
                if not resolved.is_relative_to(ROOT.resolve()) or not resolved.exists():
                    raise ValueError('Broken/outside documentation link in '+path.name+': '+target)


def manifest(files):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.name!='MANIFEST.sha256.json'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--write-manifest',action='store_true')
    parser.add_argument('--verify-manifest',action='store_true')
    args=parser.parse_args()
    try:
        files=release_files()
        audit(files)
        expected=manifest(files)
        target=ROOT/'MANIFEST.sha256.json'
        if args.verify_manifest and json.loads(target.read_text(encoding='utf-8'))!=expected:
            raise ValueError('Manifest mismatch; review changed files before publishing')
        if args.write_manifest:
            target.write_text(json.dumps(expected,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'checked_files':len(expected),'secrets_scan':'passed','relative_links':'passed'}))
        return 0
    except (ValueError,OSError) as error:
        print(str(error),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
