import os,sys,json,shutil,hashlib,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BACKEND=Path(r'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\HT_model7B\backend')
BASELINE=Path(r'D:\NCKH\Codex\case_library_20261028_bab1a96')
sys.path.insert(0,str(BACKEND))
os.environ.update(PYTHONDONTWRITEBYTECODE='1',ENVIRONMENT='test',WARM_AI_ON_STARTUP='false')
from comparison_demo import verify_context
from local_demo import digest,write_new,verify_saved_database
old=json.loads((BASELINE/'official_context_v2.json').read_text(encoding='utf-8'))
verify_context(old)
assert len(old['test_cases'])==100 and old['expected_documents']==299
corpus=ROOT/'corpus';corpus.mkdir()
for name,h in old['corpus_sha256'].items():
 source=Path(old['corpus'])/name
 assert digest(source)==h,name
 shutil.copyfile(source,corpus/name)
 # Current business content must still match the source used for P.
 current=BACKEND/'rag_data_150'/name
 if name.endswith('.json'):
  assert json.loads(current.read_text(encoding='utf-8'))==json.loads(source.read_text(encoding='utf-8')),name
 else:assert current.read_bytes().replace(b'\r\n',b'\n')==source.read_bytes().replace(b'\r\n',b'\n'),name
shutil.copyfile(old['database'],ROOT/'frozen_products.db')
shutil.copyfile(old['test_input_path'],ROOT/'test_inputs.json')
shutil.copyfile(old['plain_prompt'],ROOT/'plain_prompt.txt')
verify_saved_database(ROOT/'frozen_products.db',corpus,old['snapshot_timestamp'])
profile=json.loads((BACKEND/'model_serving/profiles/qwen25_7b.json').read_text(encoding='utf-8'))
profile['checkpoint_path']=r'D:\NCKH\Codex\training_cache\qwen25_7b_nf4'
profile['adapter_path']=r'D:\NCKH\Codex\training_runs\csconda_7b_epoch1_20261014\adapter'
write_new(ROOT/'profile.local.json',profile)
from model_serving.server import verify_artifacts
print('Verifying historical 7B checkpoint and adapter hashes...',flush=True)
identity=verify_artifacts(profile)
run_path=Path(profile['adapter_path']).parent/'run.json'
run=json.loads(run_path.read_text(encoding='utf-8'))
assert run['source']['train_sha256']=='3015d3178dff30acfde712d09657d3b66bec49811d193bf920aba6a2063b6c3e'
assert run['source']['validation_sha256']=='166c79bfbaf0ea7e1e612f0ebaaa6205fb2d195e5118e8240e6ae998fdc24b52'
shutil.copyfile(run_path,ROOT/'training_run.original.json')
controls=[json.loads(l) for l in (BASELINE/'responses_400.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
controls=[r for r in controls if r['method']=='P'];assert len(controls)==100
shutil.copyfile(BASELINE/'responses_400.jsonl',ROOT/'controls_400.original.jsonl')
forced=next(r['case_id'] for r in controls if r['result'].get('llm_called'))
context={**old,'output':str(ROOT),'corpus':str(corpus),'database':str(ROOT/'frozen_products.db'),'test_input_path':str(ROOT/'test_inputs.json'),'plain_prompt':str(ROOT/'plain_prompt.txt'),'supplementary_identity':identity,'single_timeout':120,'conversation_timeout':600,'methods':['P+FT'],'control_source':str(BASELINE/'responses_400.jsonl'),'smoke_ids':['S01',forced,'H01'],'role':'Supplementary historical 7B QLoRA NF4/BF16, compared descriptively with original 7B FP16 P. Precision/runtime/upstream differ; not an isolated causal fine-tuning ablation. No retraining.','data_scope':'Same frozen 150-product/299-document corpus and exact 100 v4.0-draft user scripts as the completed P control; no gold inputs to model.'}
write_new(ROOT/'context.json',context)
write_new(ROOT/'artifact_verification.json',{'identity':identity,'training_status':run['status'],'train_rows':run['source']['train_rows'],'validation_rows':run['source']['validation_rows'],'training_steps':run.get('training_metrics',{}).get('train_steps'),'checkpoint_path':profile['checkpoint_path'],'adapter_path':profile['adapter_path'],'code_matches_control':True,'case_count':100,'documents':299,'smoke_ids':context['smoke_ids']})
print(json.dumps({'status':'prepared','root':str(ROOT),'identity':identity,'smoke_ids':context['smoke_ids'],'run_status':run['status'],'training_fields':list(run.keys())}),flush=True)
