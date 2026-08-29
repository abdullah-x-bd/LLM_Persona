from __future__ import annotations
import argparse,base64,hashlib,os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
AAD=b"LLM_Persona_CAMS_requests_v1"
def key_from_secret(secret:str)->bytes:return hashlib.sha256(secret.encode()).digest()
def encrypt(inp:Path,out:Path,secret:str):
    nonce=os.urandom(12);pt=inp.read_bytes();blob=nonce+AESGCM(key_from_secret(secret)).encrypt(nonce,pt,AAD);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(base64.b64encode(blob).decode(),encoding="ascii")
def decrypt(inp:Path,out:Path,secret:str):
    blob=base64.b64decode(inp.read_text(encoding="ascii"));nonce,ct=blob[:12],blob[12:];pt=AESGCM(key_from_secret(secret)).decrypt(nonce,ct,AAD);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(pt)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("mode",choices=["encrypt","decrypt"]);ap.add_argument("--in",dest="inp",required=True);ap.add_argument("--out",required=True);ap.add_argument("--secret-env",default="CAMS_BUNDLE_KEY");a=ap.parse_args();secret=os.getenv(a.secret_env)
    if not secret:raise RuntimeError(f"{a.secret_env} is not set")
    (encrypt if a.mode=="encrypt" else decrypt)(Path(a.inp),Path(a.out),secret)
if __name__=="__main__":main()
