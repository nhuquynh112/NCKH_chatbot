"""Validate and publish actual supplementary observations; never fabricate semantic scores."""
import json,csv,hashlib,statistics,shutil,sys,subprocess,unicodedata
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
REPO=Path(r'D:\NCKH\2026_Chatbot\Code\NCKH_chatbot')
BACKEND=REPO/'HT_model7B/backend'
ctx=json.loads((ROOT/'context.json').read_text(encoding='utf-8'))
main=ROOT/'runs/main'
manifest=json.loads((main/'manifest.json').read_text(encoding='utf-8'))
assert manifest['status']=='completed' and manifest['rows']==100
records=[json.loads(l) for l in (main/'results.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
controls=[json.loads(l) for l in (ROOT/'controls_400.original.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
controls={r['case_id']:r for r in controls if r['method']=='P'}
assert len(records)==100 and len(controls)==100
assert [r['case_id'] for r in records]==list(ctx['test_cases'])
assert set(controls)==set(ctx['test_cases'])
assert hashlib.sha256((ROOT/'worker_pft.py').read_bytes()).hexdigest()==manifest['harness_sha256']['worker']
assert hashlib.sha256((ROOT/'run_pft.py').read_bytes()).hexdigest()==manifest['harness_sha256']['parent']
verified_calls=0;verified_history_pairs=0
for r in records:
 case=ctx['test_cases'][r['case_id']];result=r['result'];work=main/r['case_id']
 assert r['question']==case['question']==controls[r['case_id']]['question']
 assert r['history_questions']==case['history_questions']==controls[r['case_id']]['history_questions']
 if (work/'response.json').exists():assert json.loads((work/'response.json').read_text(encoding='utf-8'))==result
 else:assert result['status'] in ('timeout','error')
 if result['status'] in ('ok','no_rule_match'):
  assert result['pipeline_class']=='benchmark.methods.RagMethod'
  assert result['identity']['semantic_enabled'] and result['identity']['documents']==299
  for key in ('model','adapter_sha256','checkpoint_sha256'):assert result['identity'][key]==ctx['supplementary_identity'][key]
  assert [t['role'] for t in r['actual_history']]==['user','assistant']*len(case['history_questions'])
  assert [t['content'] for t in r['actual_history'] if t['role']=='user']==case['history_questions']
 for i,q in enumerate(case['history_questions'],1):
  path=work/f'setup-{i:02}-completed.json'
  if path.exists():
   step=json.loads(path.read_text(encoding='utf-8'))
   assert r['actual_history'][2*i-2]=={'role':'user','content':q}
   assert r['actual_history'][2*i-1]=={'role':'assistant','content':step['answer']}
   verified_history_pairs+=1
 for call in result.get('calls',[]):
  assert call['generation']=={'temperature':0,'num_predict':384,'num_ctx':4096,'repeat_penalty':1.0}
  evidence=call.get('generation_evidence')
  if evidence:
   for key in ('model','adapter_sha256','checkpoint_sha256'):assert evidence[key]==ctx['supplementary_identity'][key]
   verified_calls+=1
sys.path.insert(0,str(BACKEND))
from comparison_demo import verify_context
verify_context(ctx)
for name,h in ctx['corpus_sha256'].items():assert hashlib.sha256((ROOT/'corpus'/name).read_bytes()).hexdigest()==h
assert hashlib.sha256((ROOT/'frozen_products.db').read_bytes()).hexdigest()==ctx['database_sha256']

def percentile(a,p):
 a=sorted(a);x=(len(a)-1)*p;low=int(x);high=min(low+1,len(a)-1)
 return a[low]+(a[high]-a[low])*(x-low) if a else None

def summarize(rows):
 good=[r for r in rows if r['result']['status'] in ('ok','no_rule_match')]
 lat=[r['result']['latency_ms'] for r in good if r['result'].get('latency_ms') is not None]
 wall=[r['wall_ms'] for r in good]
 return {'attempts':len(rows),'statuses':dict(Counter(r['result']['status'] for r in rows)),
 'error_timeout_not_ready_rate':sum(r['result']['status'] not in ('ok','no_rule_match') for r in rows)/len(rows),
 'final_llm_called_cases':sum(bool(r['result'].get('llm_called')) for r in rows),
 'setup_llm_called_cases':sum(bool(r['result'].get('setup_llm_called')) for r in rows),
 'retrieval_error_cases':sum(bool(r['result'].get('retrieval_errors')) for r in rows),
 'final_pipeline_latency_successful':{'n':len(lat),'mean_ms':statistics.mean(lat) if lat else None,'median_ms':statistics.median(lat) if lat else None,'p95_ms':percentile(lat,.95) if len(lat)>=20 else None},
 'whole_case_wall_successful':{'n':len(wall),'mean_ms':statistics.mean(wall) if wall else None,'median_ms':statistics.median(wall) if wall else None,'p95_ms':percentile(wall,.95) if len(wall)>=20 else None}}

run=json.loads((ROOT/'training_run.original.json').read_text(encoding='utf-8'))
summary={'role':'supplementary_P_FT_not_one_of_four_main_methods','dataset_version':'4.0-draft','cases':100,'product_count':150,'documents':299,
 'input_sha256':ctx['test_input_sha256'],'corpus_sha256':ctx['corpus_sha256'],'generation':manifest['generation'],
 'deadlines':{'single_case_seconds':120,'whole_conversation_seconds':600,'per_model_call_seconds':120},
 'P_control':summarize(list(controls.values())),'P_FT':summarize(records),
 'models':{'P':ctx['expected_identity'],'P_FT':json.loads((main/'runtime_health.json').read_text(encoding='utf-8'))},
 'training':{'retrained_for_this_run':False,'started_utc':run['started_utc'],'train_rows':run['source']['train_rows'],'validation_rows':run['source']['validation_rows'],'epoch':run['training_metrics']['epoch'],'trainable_parameters':run['trainable_parameters'],'lora':run['lora'],'max_length':run['max_length'],'historical_validation_loss_before':run['validation_before']['eval_loss'],'historical_validation_loss_after':run['validation_after']['eval_loss'],'source':run['source']['source'],'source_train_sha256':run['source']['train_sha256'],'source_validation_sha256':run['source']['validation_sha256']},
 'validation':{'same_100_input_scripts_as_P':True,'same_frozen_corpus_and_database_as_P':True,'verified_model_calls':verified_calls,'verified_actual_history_pairs':verified_history_pairs,'semantic_review':'unreviewed','semantic_accuracy':None,'quality_score_0_2':None},
 'exact_answer_matches_P':sum(r['result'].get('answer','')==controls[r['case_id']]['result'].get('answer','') for r in records),
 'harness_sha256':manifest['harness_sha256'],'code_sha256':ctx['code_sha256'],
 'limits':['Historical QLoRA NF4/BF16 adapter versus Ollama original FP16 P: precision, runtime and upstream checkpoint differ. No isolated fine-tuning causal claim.',
 'Different collection dates and desktop GPU workloads; latency comparisons are descriptive only.',
 'Three smoke cases preceded the P+FT main run, including a real model call. Smoke responses are retained separately, not selected as main answers.',
 '100 author-constructed development cases, not an independently authored holdout. No automatic semantic quality score or human score is invented.',
 'Every H method generates its own setup responses from the same user script; only final responses are scored when reviewed.']}
summary['aggregation']={'latency_population':'status ok/no_rule_match only; pipeline final turn excludes setup; whole-case wall time includes setup and subprocess overhead','p95_method':'linear interpolation at (n-1)*0.95; omitted for fewer than 20 successful samples','semantic_scores':'not inferred from successful execution, text equality, routing or keyword checks'}
common=[r['case_id'] for r in records if r['result']['status'] in ('ok','no_rule_match') and controls[r['case_id']]['result']['status'] in ('ok','no_rule_match')]
by_id={r['case_id']:r for r in records}
common_llm=[key for key in common if controls[key]['result'].get('llm_called') and by_id[key]['result'].get('llm_called')]
summary['paired_completed']={'case_ids':common,'P_control':summarize([controls[key] for key in common]),'P_FT':summarize([by_id[key] for key in common])}
summary['paired_final_llm_completed']={'case_ids':common_llm,'P_control':summarize([controls[key] for key in common_llm]),'P_FT':summarize([by_id[key] for key in common_llm])}
summary['error_cases']=[{'case_id':r['case_id'],'status':r['result']['status'],'error':r['result'].get('error')} for r in records if r['result']['status'] not in ('ok','no_rule_match')]
summary['context_diagnostic']=json.loads((ROOT/'S47_context_diagnostic.json').read_text(encoding='utf-8'))
head=subprocess.check_output(['git','-c','safe.directory='+REPO.as_posix(),'-C',str(REPO),'rev-parse','HEAD'],text=True).strip();summary['source_git_head']=head
out=REPO/'outputs/benchmark_pft_100_20261104';out.mkdir(exist_ok=True)
with (main/'results.csv').open(encoding='utf-8-sig',newline='') as f:
 reader=csv.DictReader(f);columns=reader.fieldnames;csv_rows=list(reader)
with (out/'PFT_100.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=columns+['error']);writer.writeheader()
 for row in csv_rows:
  err=by_id[row['case_id']]['result'].get('error');writer.writerow({**row,'error':json.dumps(err,ensure_ascii=False) if err else ''})
fields=['case_id','question','P_history','PFT_history','P_answer','PFT_answer','P_status','PFT_status','P_llm_called','PFT_llm_called','P_latency_ms','PFT_latency_ms','P_wall_ms','PFT_wall_ms','exact_answer_match','P_error','PFT_error']
with (out/'comparison_P_PFT.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
 for r in records:
  p=controls[r['case_id']];pr=p['result'];fr=r['result']
  writer.writerow({'case_id':r['case_id'],'question':r['question'],'P_history':json.dumps(p.get('actual_history',[]),ensure_ascii=False),'PFT_history':json.dumps(r['actual_history'],ensure_ascii=False),'P_answer':pr.get('answer',''),'PFT_answer':fr.get('answer',''),'P_status':pr['status'],'PFT_status':fr['status'],'P_llm_called':pr.get('llm_called',False),'PFT_llm_called':fr.get('llm_called',False),'P_latency_ms':pr.get('latency_ms'),'PFT_latency_ms':fr.get('latency_ms'),'P_wall_ms':p['wall_ms'],'PFT_wall_ms':r['wall_ms'],'exact_answer_match':pr.get('answer','')==fr.get('answer',''),'P_error':json.dumps(pr.get('error'),ensure_ascii=False) if pr.get('error') else '', 'PFT_error':json.dumps(fr.get('error'),ensure_ascii=False) if fr.get('error') else ''})
(out/'statistics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
ms=lambda x:'N/A' if x is None else f'{x:.2f}'
md=['# Benchmark bổ sung P+FT — 100 ca, ngày 04/11/2026','',
 'P+FT dùng adapter 7B lịch sử đã hoàn tất ngày 14/10/2026. Không huấn luyện lại trong lượt này. Catalog mới được đưa qua RAG: 150 sản phẩm, 299 tài liệu; bộ đề v4.0-draft gồm 100 ca, trong đó 20 ca hội thoại tự sinh lịch sử.','',
 'Giữ nguyên pipeline P, generation temperature=0, context=4096, max output=384, repeat penalty=1. Câu đơn/mỗi lần gọi model tối đa 120 giây; toàn bộ ca H tối đa 600 giây. Câu hỏi, corpus và database đóng băng trùng lượt P đã thu ngày 28/10/2026.','',
 '## Kết quả thực thi','',
 '| Chỉ tiêu | P — 7B FP16 gốc | P+FT — 7B NF4/BF16 |','|---|---:|---:|']
for label,key in [('Số ca','attempts'),('Ca có thử gọi LLM ở lượt cuối','final_llm_called_cases'),('Ca có gọi LLM ở lượt thiết lập','setup_llm_called_cases'),('Ca có lỗi embedding/truy xuất','retrieval_error_cases')]:md.append(f'| {label} | {summary["P_control"][key]} | {summary["P_FT"][key]} |')
for label,key in [('Trung vị pipeline lượt cuối (ms)','median_ms'),('P95 pipeline lượt cuối (ms)','p95_ms'),('Trung bình pipeline lượt cuối (ms)','mean_ms')]:md.append(f'| {label} | {ms(summary["P_control"]["final_pipeline_latency_successful"][key])} | {ms(summary["P_FT"]["final_pipeline_latency_successful"][key])} |')
md += ['', 'Trạng thái P: '+json.dumps(summary['P_control']['statuses'],ensure_ascii=False)+'. Trạng thái P+FT: '+json.dumps(summary['P_FT']['statuses'],ensure_ascii=False)+'.',
 f"Phản hồi cuối trùng nguyên văn với P: {summary['exact_answer_matches_P']}/100. Đây là mức trùng văn bản, không phải độ chính xác.",
 'Thời gian pipeline trên chỉ dùng các ca hoàn tất; số mẫu, wall time toàn ca và tỷ lệ lỗi có trong statistics.json. Lượt cuối có thể đi qua luật/FAQ mà không gọi LLM; việc chọn P+FT không có nghĩa cả 100 câu đều sinh bằng model.','',
 '## Model và dữ liệu fine-tune lịch sử','',
 f"Adapter LoRA rank {run['lora']['rank']}, alpha {run['lora']['alpha']}, target q_proj/v_proj, learning rate {run['lora']['learning_rate']}; {run['source']['train_rows']} mẫu train, {run['source']['validation_rows']} mẫu validation từ {run['source']['source']}; {run['training_metrics']['epoch']} epoch, max length {run['max_length']}.",
 'Checkpoint: '+ctx['supplementary_identity']['base_repo']+', revision '+ctx['supplementary_identity']['base_revision']+'.',
 'Adapter SHA256: `'+ctx['supplementary_identity']['adapter_sha256']+'`.',
 'Checkpoint SHA256: `'+ctx['supplementary_identity']['checkpoint_sha256']+'`.',
 f"Loss validation lịch sử trên 9 mẫu: {run['validation_before']['eval_loss']:.6f} trước và {run['validation_after']['eval_loss']:.6f} sau fine-tune; không phải kết quả chất lượng của bộ 100 ca mới.",'',
 '## Dữ liệu để chấm và giới hạn diễn giải','',
 '- PFT_100.csv: câu trả lời thật, lịch sử user/assistant, trạng thái và latency; score_0_2/reviewer/notes để trống.',
 '- comparison_P_PFT.csv: 100 cặp phản hồi P và P+FT, mỗi phương pháp có lịch sử thực tế riêng.',
 '- statistics.json: chỉ số thực thi, model identity, package versions, hash dữ liệu/code và provenance.',
 '- Chưa có điểm chất lượng 0–2 hoặc accuracy P+FT. Cần chấm thêm các phản hồi mới; không dùng lại điểm hoặc kappa của bộ bốn phương pháp để gán cho P+FT.',
 '- P+FT là thử nghiệm bổ sung. NF4/BF16 và Transformers/PEFT khác FP16/Ollama của P; không quy toàn bộ khác biệt cho fine-tuning. Thời điểm thu thập, warm-up và tải GPU cũng khác nên latency chỉ mang tính mô tả.',
 '- Corpus/case đóng băng và dữ liệu train được giữ riêng. Không đưa câu hỏi, đáp án hoặc điểm người chấm vào train/RAG.',
 '- Model server đã xác minh adapter active, identity đúng hash; ba ca smoke S01/S31/H01 có trước lượt chính, lưu riêng và không trộn vào 100 phản hồi.','',
 'Lượt này chỉ xuất số liệu và phản hồi để đánh giá bổ sung; kết quả chính B0/B1/B2/P và hai phiếu đã chấm được giữ nguyên.']
extra=['## Đối chiếu trên cùng tập ca hoàn tất','',
 'Bảng tổng thể ở trên có 100 ca thành công của P và 99 của P+FT. Để tránh so thời gian trên hai mẫu khác nhau, dưới đây tính lại trên các mã ca cùng hoàn tất. Các chênh lệch vẫn chỉ mang tính mô tả do khác runtime/precision và thời điểm thu thập.','',
 '| Tập ca và chỉ tiêu | P | P+FT |','|---|---:|---:|']
for name,key in [('Cùng hoàn tất','paired_completed'),('Cùng hoàn tất và có gọi LLM cuối','paired_final_llm_completed')]:
 group=summary[key]
 extra.append(f"| {name}: số ca | {len(group['case_ids'])} | {len(group['case_ids'])} |")
 for label,metric in [('Trung vị','median_ms'),('Trung bình','mean_ms'),('P95','p95_ms')]:
  extra.append(f"| {name}: {label} pipeline cuối (ms) | {ms(group['P_control']['final_pipeline_latency_successful'][metric])} | {ms(group['P_FT']['final_pipeline_latency_successful'][metric])} |")
d=summary['context_diagnostic']
extra += ['', '## Ca lỗi S47','',
 f"S47 bị server từ chối trước generation: input có {d['input_tokens']} token, cần dự phòng {d['reserved_output_tokens']} token đầu ra, tổng {d['required_total_tokens']} vượt context {d['requested_context']}. Lỗi gốc: Context exceeds limit; no silent prompt truncation.",
 'Đây là lỗi kiểm tra giới hạn prompt của runtime HF, không phải lỗi embedding hoặc timeout. Server không tự cắt prompt; không suy đoán việc Ollama đã xử lý/cắt ngữ cảnh ở lượt P vì log cũ không có đủ bằng chứng tokenization đó.',
 'Giữ ca lỗi trong mẫu 100 ca, tỷ lệ lỗi 1%. Không tăng riêng context hoặc chọn lượt chạy lại thành công để thay mẫu. P+FT có 35 ca thử gọi LLM cuối, 34 ca gọi cuối hoàn tất; CSV có cột error và S47 không có câu trả lời thay thế.','']
pos=md.index('## Model và dữ liệu fine-tune lịch sử');md[pos:pos]=extra
(out/'BAO_CAO.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'output':str(out),'P_FT':summary['P_FT'],'model_calls_verified':verified_calls,'history_pairs_verified':verified_history_pairs,'exact_answer_matches_P':summary['exact_answer_matches_P']},ensure_ascii=False))
