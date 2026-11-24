"""Observe the existing P+FT worker without changing its algorithm or generated text."""
import os,sys,json,hashlib
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
BACKEND=Path(r'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot\HT_model7B\backend')
sys.path.insert(0,str(BACKEND))
request_path,response_path=map(Path,sys.argv[1:3])
request=json.loads(request_path.read_text(encoding='utf-8'))
context=json.loads((ROOT/'context.json').read_text(encoding='utf-8'))
assert request['method']=='P+FT'
assert set(request['case'])=={'id','category','question','history','history_questions'}
database=Path(request['database']);corpus=Path(request['corpus'])
assert database.resolve()==(ROOT/'frozen_products.db').resolve()
os.environ.update(DATABASE_URL='sqlite:///file:'+database.as_posix()+'?mode=ro&uri=true',ENVIRONMENT='test',AUTO_SEED='false',WARM_AI_ON_STARTUP='false',PYTHONDONTWRITEBYTECODE='1')
from benchmark import worker,methods
observed={}
def write_new(path,value):
 with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def existing_snapshot(corpus_path,_database_path,snapshot_timestamp=None):
 from app.database import engine
 assert engine.dialect.name=='sqlite' and engine.url.query.get('mode')=='ro'
 import app.product_enrichment as enrichment
 data=enrichment.load_verification_data(corpus_path/'product_verified_specs.json')
 enrichment.load_verification_data=lambda *args,**kwargs:data
 import app.rag.faq_matcher as faq
 faq.load_curated_faqs.__defaults__=(corpus_path/'faq_curated.json',)
 observed['database_mode']='read-only frozen control snapshot'
 return engine
original_factory=methods.build_method
def traced_factory(method,config,prompt):
 runner=original_factory(method,config,prompt)
 assert type(runner).__name__=='RagMethod' and config.CHAT_PROVIDER=='hf_lora'
 observed['pipeline_class']=type(runner).__module__+'.'+type(runner).__name__
 observed['effective_config']={'provider':config.CHAT_PROVIDER,'model':config.chat_model,'embedding':config.embedding_model,'top_k':config.RAG_TOP_K,'threshold':config.MIN_RETRIEVAL_SCORE,'generation':methods.GENERATION.copy()}
 preflight=runner.preflight
 def checked():
  state=preflight()
  for key in ('model','adapter_sha256','checkpoint_sha256'):assert state[key]==context['supplementary_identity'][key],key
  assert state['adapter_loaded'] and state['quantization']=='NF4/BF16'
  assert state['semantic_enabled'] and state['documents']==299
  assert state['embedding_identity']['digest']==context['expected_identity']['embedding_identity']['digest']
  return state
 runner.preflight=checked
 original_ask=runner.ask
 setup_count=len(request['case']['history_questions']);index=0
 def tracked(question,history):
  nonlocal index
  if index>=setup_count:return original_ask(question,history)
  index+=1;prefix=response_path.parent/f'setup-{index:02}'
  write_new(str(prefix)+'-started.json',{'question':question,'history':deepcopy(history)})
  result=original_ask(question,history)
  write_new(str(prefix)+'-completed.json',{'question':question,'history':deepcopy(history),'answer':result['answer']})
  return result
 runner.ask=tracked
 return runner
worker.seed_snapshot=existing_snapshot
methods.build_method=traced_factory
result=worker.run_case(request)
result.update(observed)
result['harness_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
write_new(response_path,result)
