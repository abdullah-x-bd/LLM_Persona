from __future__ import annotations
import argparse,base64,gzip,hashlib,json,os
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

INFO=b'LLM_Persona_multisurvey_v1'

def secret():
    v=os.getenv('OPENROUTER_API_KEY')
    if not v: raise RuntimeError('OPENROUTER_API_KEY is not set')
    return v

def private_key():
    seed=hashlib.sha256(('LLM_Persona_bundle_v2|'+secret()).encode()).digest()
    return x25519.X25519PrivateKey.from_private_bytes(seed)

def decrypt_public_bundle(path:Path,slug:str,kind:str)->bytes:
    blob=base64.b64decode(path.read_text(encoding='ascii'),validate=True)
    if len(blob)<61: raise ValueError('Encrypted bundle too small')
    eph,nonce,ct=blob[:32],blob[32:44],blob[44:]
    shared=private_key().exchange(x25519.X25519PublicKey.from_public_bytes(eph))
    key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=INFO).derive(shared)
    aad=f'LLM_Persona_{slug}_{kind}_v1'.encode()
    return gzip.decompress(AESGCM(key).decrypt(nonce,ct,aad))

def rows_from_bytes(raw:bytes):
    return [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]

def extract(bundle:Path,slug:str,out:Path,start:int,count:int|None):
    rows=rows_from_bytes(decrypt_public_bundle(bundle,slug,'requests'))
    pairs=[(r['anon_id'],r['condition']) for r in rows]
    if len(pairs)!=len(set(pairs)): raise AssertionError('Duplicate request pairs in bundle')
    selected=rows[start:] if count is None else rows[start:start+count]
    if not selected: raise AssertionError('Requested shard is empty')
    if count is not None and len(selected)!=count: raise AssertionError(f'Expected {count} rows, got {len(selected)}')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8') as f:
        for r in selected:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'survey':slug,'total':len(rows),'start':start,'selected':len(selected)}))

def truth(bundle:Path,slug:str,out:Path):
    raw=decrypt_public_bundle(bundle,slug,'truth'); rows=rows_from_bytes(raw)
    if len({r['anon_id'] for r in rows})!=len(rows): raise AssertionError('Duplicate truth anon_id')
    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(raw)
    print(json.dumps({'survey':slug,'truth_rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}))

def result_key(slug,model):
    return hashlib.sha256((f'LLM_Persona_multisurvey_results_v1|{slug}|{model}|'+secret()).encode()).digest()

def encrypt_results(inp:Path,out:Path,slug:str,model:str,chunk:int):
    raw=inp.read_bytes() if inp.exists() else b''; nonce=os.urandom(12)
    aad=f'LLM_Persona_{slug}_{model}_chunk_{chunk:03d}'.encode(); comp=gzip.compress(raw,9)
    blob=nonce+AESGCM(result_key(slug,model)).encrypt(nonce,comp,aad)
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(base64.b64encode(blob).decode(),encoding='ascii')
    print(json.dumps({'survey':slug,'model':model,'chunk':chunk,'rows':len([x for x in raw.splitlines() if x.strip()])}))

def decrypt_result(path:Path,slug:str,model:str,chunk:int):
    blob=base64.b64decode(path.read_text(encoding='ascii'),validate=True); nonce,ct=blob[:12],blob[12:]
    aad=f'LLM_Persona_{slug}_{model}_chunk_{chunk:03d}'.encode()
    return gzip.decompress(AESGCM(result_key(slug,model)).decrypt(nonce,ct,aad))

def combine(root:Path,slug:str,model:str,expected:int,out:Path,manifest:Path):
    successful={}; files=[]
    for path in root.rglob('*.results.enc.b64'):
        name=path.name
        if not name.startswith(f'{slug}__{model}__chunk-'):continue
        chunk=int(name.split('chunk-')[1].split('.')[0]); files.append(path)
        for line in decrypt_result(path,slug,model,chunk).decode().splitlines():
            if not line.strip():continue
            r=json.loads(line)
            if 'error' not in r: successful[(r['anon_id'],r['condition'])]=r
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8') as f:
        for k in sorted(successful):f.write(json.dumps(successful[k],ensure_ascii=False)+'\n')
    m={'survey':slug,'model':model,'artifact_files':len(files),'successful_unique_requests':len(successful),'expected':expected,'complete':len(successful)==expected,
       'prompt_tokens':sum(int(r.get('prompt_tokens') or 0) for r in successful.values()),'completion_tokens':sum(int(r.get('completion_tokens') or 0) for r in successful.values())}
    m['total_tokens']=m['prompt_tokens']+m['completion_tokens']; manifest.write_text(json.dumps(m,indent=2)); print(json.dumps(m,indent=2))

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('extract');p.add_argument('--bundle',required=True);p.add_argument('--survey',required=True);p.add_argument('--out',required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int)
    p=sub.add_parser('truth');p.add_argument('--bundle',required=True);p.add_argument('--survey',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('encrypt-results');p.add_argument('--in',dest='inp',required=True);p.add_argument('--out',required=True);p.add_argument('--survey',required=True);p.add_argument('--model',required=True);p.add_argument('--chunk',type=int,required=True)
    p=sub.add_parser('combine');p.add_argument('--root',required=True);p.add_argument('--survey',required=True);p.add_argument('--model',required=True);p.add_argument('--expected',type=int,required=True);p.add_argument('--out',required=True);p.add_argument('--manifest',required=True)
    a=ap.parse_args()
    if a.cmd=='extract':extract(Path(a.bundle),a.survey,Path(a.out),a.start,a.count)
    elif a.cmd=='truth':truth(Path(a.bundle),a.survey,Path(a.out))
    elif a.cmd=='encrypt-results':encrypt_results(Path(a.inp),Path(a.out),a.survey,a.model,a.chunk)
    elif a.cmd=='combine':combine(Path(a.root),a.survey,a.model,a.expected,Path(a.out),Path(a.manifest))
if __name__=='__main__':main()
