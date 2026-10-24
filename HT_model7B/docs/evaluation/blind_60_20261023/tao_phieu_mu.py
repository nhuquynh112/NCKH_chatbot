"""Create two independently ordered, blinded review packets from completed runs."""
import argparse
import json
from pathlib import Path
import random
import secrets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('responses', type=Path, help='JSONL: system_id, case_id, answer, status (ok/error)')
    ap.add_argument('output', type=Path, help='New directory; must not already exist')
    args = ap.parse_args()
    base = Path(__file__).resolve().parent
    cases = {c['id']: c for c in json.loads((base/'questions.json').read_text())['cases']}
    keys = {k['id']: k for k in json.loads((base/'answer_key.json').read_text())}
    responses = [json.loads(line) for line in args.responses.read_text().splitlines() if line.strip()]
    seen = set()
    for r in responses:
        if not isinstance(r.get('system_id'), str) or not r['system_id'].strip():
            raise ValueError('system_id must be nonempty')
        if r.get('case_id') not in cases or not isinstance(r.get('answer'), str):
            raise ValueError('Invalid case_id or answer')
        if r.get('status') not in ('ok', 'error'):
            raise ValueError('status must be ok/error; retain failed responses')
        if r['status'] == 'ok' and not r['answer'].strip():
            raise ValueError('Empty answer must use status=error')
        case = cases[r['case_id']]
        history = r.get('history', [])
        if case.get('history_questions'):
            questions = case['history_questions']
            if not isinstance(history, list):
                raise ValueError('History must be a list of actual messages')
            if r.get('setup_status') == 'error':
                if (r['status'] != 'error' or r['answer'] or len(history)%2 != 1
                    or not 1 <= len(history) <= 2*len(questions)-1):
                    raise ValueError('Setup error: retain completed pairs and failed user turn; status=error, answer empty')
            elif r.get('setup_status') == 'ok':
                if len(history) != 2*len(questions):
                    raise ValueError('History case requires every actual prior assistant response')
            else:
                raise ValueError('History case requires setup_status=ok/error')
            for i,turn in enumerate(history):
                if not isinstance(turn, dict):
                    raise ValueError('Every history turn must be an object')
                if i%2 == 0:
                    if turn != {'role':'user','content':questions[i//2]}:
                        raise ValueError('Prior user turns must match the scenario in order')
                elif (turn.get('role') != 'assistant' or not isinstance(turn.get('content'),str)
                      or not turn['content'].strip()):
                    raise ValueError('Retain the actual nonempty assistant reply for every completed turn')
        elif history:
            raise ValueError('Single-turn case must not have history')
        identity = (r['system_id'], r['case_id'])
        if identity in seen:
            raise ValueError('Duplicate system/case')
        seen.add(identity)
    systems = sorted({r['system_id'] for r in responses})
    if not systems or any({c for s,c in seen if s == system} != set(cases) for system in systems):
        raise ValueError(f'Every system requires all {len(cases)} cases, including errors')
    args.output.mkdir(parents=True, exist_ok=False)
    private = args.output/'DIEU_PHOI_KHONG_GUI_NGUOI_CHAM'
    private.mkdir()
    packets = []
    mapping = []
    for r in responses:
        blind = secrets.token_hex(8)
        c, k = cases[r['case_id']], keys[r['case_id']]
        packets.append(dict(blind_id=blind, case_id=c['id'], history=r.get('history', []),
                            setup_status=r.get('setup_status'), question=c['question'],
                            answer=r['answer'] if r['status']=='ok' else '[Không có phản hồi hợp lệ]',
                            reference_answer=k['reference_answer'], required_criteria=k['required_criteria'],
                            source_refs=k['source_refs'], score=None, unsupported_claim=None,
                            context_error=None, notes=''))
        mapping.append(dict(blind_id=blind,system_id=r['system_id'],case_id=c['id'],status=r['status']))
    (private/'mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
    for reviewer in ['R1','R2']:
        folder=args.output/reviewer
        folder.mkdir()
        ordered=list(packets)
        random.SystemRandom().shuffle(ordered)
        (folder/'phieu_cham.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in ordered))
        md=['# Phiếu chấm '+reviewer,'','Chấm độc lập: điểm 0/1/2; có/không phát biểu ngoài nguồn; lỗi ngữ cảnh có/không hoặc N/A với câu đơn.','']
        for p in ordered:
            md += ['## '+p['blind_id']+' — '+p['case_id'],'']
            md += [h['role']+': '+h['content'] for h in p['history']]
            if p.get('setup_status') == 'error':
                md += ['Một lượt trước câu cuối gặp lỗi; dừng ca, giữ các lượt thực tế đã hoàn thành.']
            md += ['', '**Câu hỏi:** '+p['question'],'','**Phản hồi:**',p['answer'],'','**Tham chiếu:** '+p['reference_answer'],'','**Tiêu chí:** '+' '.join(p['required_criteria']),'','Điểm: ___ | Ngoài nguồn: ___ | Lỗi ngữ cảnh: ___','Ghi chú: ___','']
        (folder/'PHIEU_CHAM.md').write_text('\n'.join(md))
    print(f'Created {len(packets)} responses per reviewer in {args.output}. Keep mapping private.')


if __name__ == '__main__':
    main()
