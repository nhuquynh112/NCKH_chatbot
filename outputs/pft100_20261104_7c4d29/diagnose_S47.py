import json,os
from pathlib import Path
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
root=Path(__file__).resolve().parent
r=json.loads((root/'runs/main/S47/response.json').read_text(encoding='utf-8'))
call=next(c for c in r['calls'] if c.get('error'))
from transformers import AutoTokenizer
p=json.loads((root/'profile.local.json').read_text(encoding='utf-8'))
t=AutoTokenizer.from_pretrained(p['checkpoint_path'],local_files_only=True,trust_remote_code=False)
messages=[{'role':'system','content':call['system_prompt']},{'role':'user','content':call['user_prompt']}]
encoded=t.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_dict=True)
tokens=encoded['input_ids']
diagnostic={'case_id':'S47','input_tokens':len(tokens),'reserved_output_tokens':384,'requested_context':4096,'required_total_tokens':len(tokens)+384,'source_error':call['error'],'diagnostic_only_no_generation':True}
assert diagnostic['required_total_tokens']>4096
(root/'S47_context_diagnostic.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(diagnostic,ensure_ascii=False))
