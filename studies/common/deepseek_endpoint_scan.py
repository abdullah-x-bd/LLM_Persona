from __future__ import annotations

import json, os, urllib.request

BASE='https://openrouter.ai/api/v1'
MODEL='deepseek/deepseek-v4-flash-0731'
REQUIRED={'reasoning','response_format','max_tokens'}


def get_json(url,key):
    req=urllib.request.Request(url,headers={'Authorization':f'Bearer {key}','User-Agent':'LLM-Persona-DeepSeek-Endpoint-Scan/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r: return json.loads(r.read().decode())

def pm(v): return None if v is None else float(v)*1_000_000

def main():
    key=os.environ['OPENROUTER_API_KEY']
    author,slug=MODEL.split('/',1)
    eps=(get_json(f'{BASE}/models/{author}/{slug}/endpoints',key).get('data',{}) or {}).get('endpoints') or []
    out=[]
    for e in eps:
        params=set(e.get('supported_parameters') or [])
        if not REQUIRED.issubset(params): continue
        p=e.get('pricing') or {}
        status=e.get('status')
        out.append({
            'name':e.get('name') or e.get('provider_name'),
            'tag':e.get('tag'),
            'status':status,
            'healthy':not (isinstance(status,(int,float)) and status<0),
            'input_per_m':pm(p.get('prompt')),
            'output_per_m':pm(p.get('completion')),
            'quantization':e.get('quantization'),
            'context_length':e.get('context_length'),
            'max_completion_tokens':e.get('max_completion_tokens'),
            'supported_parameters':sorted(params),
        })
    out.sort(key=lambda x:(not x['healthy'], x['output_per_m'] if x['output_per_m'] is not None else 1e99, x['input_per_m'] if x['input_per_m'] is not None else 1e99, str(x['tag'])))
    print(json.dumps({'model':MODEL,'chat_completions_called':False,'paid_inference_performed':False,'endpoint_count':len(out),'endpoints':out},indent=2,sort_keys=True))
if __name__=='__main__': main()
