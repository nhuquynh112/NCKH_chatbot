"""Read original independent XLSX ratings; calculate agreement and cluster-bootstrap CIs.
Python 3 standard library only. Does not run models or write scores to the forms.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import statistics
import xml.etree.ElementTree as ET
import zipfile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read_sheet(path):
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rows = []
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:sheetData/m:row', NS):
            values = {}
            for c in row.findall('m:c', NS):
                col = ''.join(ch for ch in c.attrib['r'] if ch.isalpha())
                if c.find('m:f', NS) is not None and col in ('A','B','C','E','F','H') and int(row.attrib['r']) >= 9:
                    raise ValueError('Dán CHỈ GIÁ TRỊ; cột mã, phản hồi, trạng thái và điểm không được là công thức.')
                v = c.find('m:v', NS)
                value = v.text if v is not None else ''
                if c.attrib.get('t') == 's':
                    value = strings[int(value)]
                elif c.attrib.get('t') == 'inlineStr':
                    value = ''.join(c.find('m:is', NS).itertext())
                values[col] = value or ''
            if int(row.attrib['r']) >= 9 and values.get('A'):
                rows.append(values)
        return rows


def load_ratings(path, mapping):
    ratings = {}
    for r in read_sheet(path):
        bid = r['A']
        if bid not in mapping or bid in ratings:
            raise ValueError(f'{path.name}: mã trùng/không hợp lệ {bid}')
        if r.get('B') != mapping[bid]['case_id']:
            raise ValueError(f'{bid}: mã câu bị thay đổi')
        status = r.get('F', '').strip()
        if status not in ('ok','no_rule_match','error','timeout','not_ready'):
            raise ValueError(f'{bid}: chưa điền trạng thái thực tế')
        if status in ('ok','no_rule_match') and not r.get('E','').strip():
            raise ValueError(f'{bid}: thiếu phản hồi thực tế')
        if r['B'].startswith('H') and not r.get('C','').strip():
            raise ValueError(f'{bid}: thiếu lịch sử THỰC TẾ ở cột C (hoặc ghi nhận lỗi lượt đầu)')
        if not r['B'].startswith('H') and r.get('C','').strip():
            raise ValueError(f'{bid}: câu đơn không được có lịch sử')
        raw = r.get('H', '').strip()
        if raw not in ('0','1','2','0.0','1.0','2.0'):
            raise ValueError(f'{bid}: chưa chấm hoặc điểm không phải 0/1/2')
        score = int(float(raw))
        if status in ('error','timeout','not_ready') and score != 0:
            raise ValueError(f'{bid}: lỗi không có phản hồi phải được chấm 0 theo rubric')
        ratings[bid] = dict(score=score, answer=r.get('E',''), status=status, history=r.get('C',''))
    if set(ratings) != set(mapping):
        raise ValueError(f'{path.name}: phải đủ {len(mapping)} mã, hiện có {len(ratings)}')
    return ratings


def kappa(pairs, weighted=True):
    n = len(pairs)
    if not n:
        return None
    a, b = Counter(x for x,y in pairs), Counter(y for x,y in pairs)
    weight = (lambda x,y: abs(x-y)/2) if weighted else (lambda x,y: float(x!=y))
    observed = sum(weight(x,y) for x,y in pairs)/n
    expected = sum(weight(x,y)*a[x]*b[y] for x in range(3) for y in range(3))/(n*n)
    return None if expected == 0 else 1-observed/expected


def metrics(pairs):
    return dict(kappa_linear=kappa(pairs), kappa_unweighted=kappa(pairs,False),
                exact_agreement=sum(a==b for a,b in pairs)/len(pairs),
                mean_R1=statistics.mean(a for a,b in pairs), mean_R2=statistics.mean(b for a,b in pairs),
                pass_rate_R1=sum(a==2 for a,b in pairs)/len(pairs),
                pass_rate_R2=sum(b==2 for a,b in pairs)/len(pairs))


def percentile(values, q):
    values = sorted(values)
    position = (len(values)-1)*q
    lo = int(position)
    hi = min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(position-lo)


def analyze(records, families, repeats, seed):
    pairs=[(r['R1'],r['R2']) for r in records]
    point=metrics(pairs)
    groups=defaultdict(list)
    for r in records:
        groups[families[r['case_id']]].append((r['R1'],r['R2']))
    clusters=list(groups.values())
    rng=random.Random(seed)
    dist={name:[] for name in point}
    for _ in range(repeats):
        sample=[pair for _ in clusters for pair in rng.choice(clusters)]
        for key,value in metrics(sample).items():
            if value is not None:
                dist[key].append(value)
    result={}
    for key,value in point.items():
        valid=len(dist[key])
        # Never replace undefined kappa with zero or perfect agreement.
        ci=[percentile(dist[key],.025),percentile(dist[key],.975)] if value is not None and valid>=.95*repeats and len(clusters)>1 else None
        result[key]={'estimate':value,'ci95':ci,'valid_bootstrap':valid,'invalid_bootstrap':repeats-valid}
    return dict(n_pairs=len(pairs),n_clusters=len(clusters),metrics=result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('R1',type=Path);p.add_argument('R2',type=Path)
    p.add_argument('--mapping',type=Path,default=Path(__file__).with_name('mapping_RIENG.json'))
    p.add_argument('--families',type=Path,default=Path(__file__).with_name('families.json'))
    p.add_argument('--out',type=Path,default=Path('ket_qua_kappa'))
    p.add_argument('--bootstrap',type=int,default=5000);p.add_argument('--seed',type=int,default=20261023)
    args=p.parse_args()
    if args.bootstrap<1000:
        p.error('Use at least 1000 bootstrap replicates')
    raw=json.loads(args.mapping.read_text(encoding='utf-8'))
    mapping={m['blind_id']:m for m in raw}
    if len(mapping)!=400 or Counter(m['method'] for m in raw)!=Counter({'B0':100,'B1':100,'B2':100,'P':100}):
        raise ValueError('Mapping phải có đúng 4 phương pháp × 100 ca')
    a,b=load_ratings(args.R1,mapping),load_ratings(args.R2,mapping)
    rows=[]
    for bid,m in mapping.items():
        if (a[bid]['answer'],a[bid]['status'],a[bid]['history']) != (b[bid]['answer'],b[bid]['status'],b[bid]['history']):
            raise ValueError(f'{bid}: hai người không nhận cùng phản hồi/trạng thái')
        rows.append({**m,'R1':a[bid]['score'],'R2':b[bid]['score']})
    family_data=json.loads(args.families.read_text(encoding='utf-8'))
    families=family_data['case_to_family']
    if set(families)!={m['case_id'] for m in raw}:
        raise ValueError('Family map không khớp bộ 100 câu')
    result={'status':'independent_ratings_analyzed','confidence_level':.95,'ci_method':'percentile cluster bootstrap by predeclared family; both raters and all methods kept paired',
            'bootstrap_replicates':args.bootstrap,'seed':args.seed,
            'source_sha256':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (args.R1,args.R2,args.mapping,args.families)},
            'overall':analyze(rows,families,args.bootstrap,args.seed),'methods':{}}
    for method in ('B0','B1','B2','P'):
        result['methods'][method]=analyze([r for r in rows if r['method']==method],families,args.bootstrap,args.seed)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'statistics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    disagreements=[r for r in rows if r['R1']!=r['R2']]
    (args.out/'bat_dong.json').write_text(json.dumps(disagreements,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# Đồng thuận giữa hai người chấm','','Điểm độc lập trước hòa giải. Kappa đo độ đồng thuận, không đo độ đúng của chatbot.','','| Nhóm | Số cặp | Đồng ý tuyệt đối | Kappa tuyến tính | CI 95% |','|---|---:|---:|---:|---|']
    for name,item in [('Tất cả',result['overall']),*result['methods'].items()]:
        k=item['metrics']['kappa_linear'];est='N/A' if k['estimate'] is None else f"{k['estimate']:.4f}";ci='N/A' if k['ci95'] is None else f"[{k['ci95'][0]:.4f}; {k['ci95'][1]:.4f}]"
        md.append(f"| {name} | {item['n_pairs']} | {item['metrics']['exact_agreement']['estimate']:.1%} | {est} | {ci} |")
    md+=['',f"Bootstrap {args.bootstrap} lần theo family, seed {args.seed}; không coi 400 phản hồi là 400 câu hỏi độc lập.",'CI mô tả độ bất định khi lấy mẫu lại các family của bộ đề đã biên soạn, không chứng minh khả năng khái quát ra toàn bộ khách hàng. Một số quan hệ ngữ nghĩa giữa family vẫn có thể tồn tại.', 'Kappa N/A khi mẫu không có biến thiên cần thiết. CI N/A nếu trên 5% lần bootstrap không xác định hoặc không đủ cluster. Xem số lần hợp lệ trong statistics.json.',f'Số phản hồi bất đồng: {len(disagreements)}. Giữ nguyên hai phiếu gốc; hòa giải trong tài liệu riêng.','', 'Nguồn phương pháp: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html ; https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html']
    (args.out/'BAO_CAO.md').write_text('\n'.join(md),encoding='utf-8')
    print('Đã tạo',args.out/'BAO_CAO.md')


if __name__=='__main__':
    main()
