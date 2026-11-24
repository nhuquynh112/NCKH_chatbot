"""Run original P+FT on the frozen 100-case control inputs, with per-conversation deadlines."""
import os,sys,json,csv,subprocess,time,hashlib,statistics,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
BACKEND=Path(r'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\HT_model7B\backend')
sys.path.insert(0,str(BACKEND))
os.environ.update(PYTHONDONTWRITEBYTECODE='1',ENVIRONMENT='test',WARM_AI_ON_STARTUP='false',PYTHONIOENCODING='utf-8')
from comparison_demo import verify_context
from local_demo import digest,write_new
context=json.loads((ROOT/'context.json').read_text(encoding='utf-8'))
phase=sys.argv[1];assert phase in ('smoke','main')
out=ROOT/'runs'/phase;out.mkdir(parents=True,exist_ok=False)
worker_path=ROOT/'worker_pft.py';harness={'parent':digest(Path(__file__)),'worker':digest(worker_path)}
manifest={'status':'running','started_utc':datetime.now(timezone.utc).isoformat(),'method':'P+FT','phase':phase,'generation':{'temperature':0,'num_predict':384,'num_ctx':4096,'repeat_penalty':1.0},'single_case_deadline_seconds':120,'conversation_deadline_seconds':600,'each_model_call_timeout_seconds':120,'harness_sha256':harness,'limits':context['role'],'corpus_sha256':context['corpus_sha256'],'input_sha256':context['test_input_sha256'],'control_source':context['control_source'],'semantic_scores':'unreviewed; no human scores or accuracy inferred','warmup':'S01, S31 (forces a model call in the P control), H01; these smoke outputs are preserved separately and excluded from the main 100 observations.'}
write_new(out/'manifest.json',manifest)
with urllib.request.urlopen('http://127.0.0.1:8011/health',timeout=5) as r:health=json.load(r)
assert health['status']=='ready' and health['adapter_loaded']
for key in ('model','adapter_sha256','checkpoint_sha256'):assert health[key]==context['supplementary_identity'][key]
write_new(out/'runtime_health.json',health)
if phase=='main':
 smoke=json.loads((ROOT/'runs/smoke/summary.json').read_text(encoding='utf-8'))
 assert smoke['smoke_contract_passed']
cases=list(context['test_cases'].values()) if phase=='main' else [context['test_cases'][key] for key in context['smoke_ids']]
records=[]
fields=['method','case_id','question','history','answer','status','mode','llm_called','setup_llm_called','latency_ms','wall_ms','case_deadline_seconds','model','quantization','score_0_2','reviewer','notes']
with (out/'results.jsonl').open('x',encoding='utf-8') as raw,(out/'results.csv').open('x',encoding='utf-8-sig',newline='') as cf:
 writer=csv.DictWriter(cf,fieldnames=fields);writer.writeheader()
 for case in cases:
  verify_context(context)
  assert digest(ROOT/'frozen_products.db')==context['database_sha256']
  assert all(digest(ROOT/'corpus'/name)==h for name,h in context['corpus_sha256'].items())
  work=out/case['id'];work.mkdir()
  request={'method':'P+FT','case':case,'database':context['database'],'corpus':context['corpus'],'timeout':120,'snapshot_timestamp':context['snapshot_timestamp'],'ollama_url':'http://127.0.0.1:11434','hf_url':'http://127.0.0.1:8011','plain_prompt':Path(context['plain_prompt']).read_text(encoding='utf-8')}
  write_new(work/'request.json',request)
  deadline=600 if case['history_questions'] else 120
  started=time.perf_counter()
  try:
   p=subprocess.run([sys.executable,'-X','utf8','-B',str(worker_path),str(work/'request.json'),str(work/'response.json')],cwd=BACKEND,env=os.environ.copy(),capture_output=True,timeout=deadline)
   (work/'worker.log').write_bytes(p.stdout+b'\n'+p.stderr)
   if p.returncode or not (work/'response.json').exists():raise RuntimeError('Worker failed; inspect worker.log')
   result=json.loads((work/'response.json').read_text(encoding='utf-8'))
  except subprocess.TimeoutExpired as exc:
   (work/'worker.log').write_bytes((exc.stdout or b'')+b'\n'+(exc.stderr or b''))
   result={'status':'timeout','answer':'','error':'Whole-case deadline exceeded','calls':[],'history':[]}
  except Exception as exc:result={'status':'error','answer':'','error':str(exc),'calls':[],'history':[]}
  history=result.get('history',[])
  if case['history_questions'] and not history:
   progress=sorted(work.glob('setup-*-started.json'))
   if progress:
    last=json.loads(progress[-1].read_text(encoding='utf-8'));history=last['history']+[{'role':'user','content':last['question']}]
    complete=progress[-1].with_name(progress[-1].name.replace('-started','-completed'))
    if complete.exists():history+=[{'role':'assistant','content':json.loads(complete.read_text(encoding='utf-8'))['answer']}]
  record={'method':'P+FT','case_id':case['id'],'question':case['question'],'history_questions':case['history_questions'],'actual_history':history,'case_deadline_seconds':deadline,'wall_ms':(time.perf_counter()-started)*1000,'result':result}
  write_new(work/'record.json',record)
  records.append(record);raw.write(json.dumps(record,ensure_ascii=False)+'\n');raw.flush()
  writer.writerow({'method':'P+FT','case_id':case['id'],'question':case['question'],'history':json.dumps(history,ensure_ascii=False),'answer':result.get('answer',''),'status':result['status'],'mode':result.get('mode'),'llm_called':result.get('llm_called',False),'setup_llm_called':result.get('setup_llm_called',False),'latency_ms':result.get('latency_ms'),'wall_ms':record['wall_ms'],'case_deadline_seconds':deadline,'model':(result.get('identity') or {}).get('model'),'quantization':(result.get('identity') or {}).get('quantization')});cf.flush()
  (ROOT/'progress.json').write_text(json.dumps({'phase':phase,'completed':len(records),'total':len(cases),'case_id':case['id'],'status':result['status'],'llm_called':result.get('llm_called',False),'updated_utc':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
  print(f'{phase} {len(records)}/{len(cases)} {case["id"]} {result["status"]} llm={result.get("llm_called",False)}',flush=True)
  if result['status']=='not_ready':raise RuntimeError('Model/retriever not ready; stopping before collecting invalid attempts')
from collections import Counter
summary={'method':'P+FT','phase':phase,'attempts':len(records),'statuses':dict(Counter(r['result']['status'] for r in records)),'final_llm_called_cases':sum(bool(r['result'].get('llm_called')) for r in records),'setup_llm_called_cases':sum(bool(r['result'].get('setup_llm_called')) for r in records),'semantic_scores':'unreviewed'}
if phase=='smoke':
 success=all(r['result']['status'] in ('ok','no_rule_match') for r in records)
 h=next(r for r in records if r['case_id']=='H01')
 role_ok=[t['role'] for t in h['actual_history']]==['user','assistant']*len(h['history_questions'])
 genuine_call=any(r['result'].get('llm_called') and any(c.get('generation_evidence',{}).get('adapter_sha256')==context['supplementary_identity']['adapter_sha256'] for c in r['result'].get('calls',[]) if c.get('generation_evidence')) for r in records)
 summary['smoke_contract_passed']=success and role_ok and genuine_call
write_new(out/'summary.json',summary)
manifest.update(status='completed',finished_utc=datetime.now(timezone.utc).isoformat(),rows=len(records));(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary),flush=True)
if phase=='smoke' and not summary['smoke_contract_passed']:raise SystemExit(2)
