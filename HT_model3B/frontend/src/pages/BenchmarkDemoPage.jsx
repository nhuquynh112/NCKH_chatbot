import React, { useEffect, useState } from 'react';
import { Bot, Send, X } from 'lucide-react';
import './BenchmarkDemoPage.css';

const API = import.meta.env.VITE_BENCHMARK_API_URL || 'http://127.0.0.1:8012';
const METHODS = ['B0', 'B1', 'B2', 'P'];
const NAMES = { B0: 'Rule-based chatbot', B1: 'LLM không sử dụng RAG', B2: 'Basic RAG', P: 'Kiến trúc đề xuất · model gốc' };

async function request(path, body) {
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(API).hostname)) {
    throw new Error('Demo chỉ kết nối máy chủ local.');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 110000);
  try {
    const response = await fetch(API + path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'omit',
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`);
    return data;
  } finally {
    clearTimeout(timer);
  }
}

function Message({ role, content, fixture = false, createdAt }) {
  return (
    <div className={`bd-message bd-${role}`} data-role={role} data-fixture={fixture ? 'true' : 'false'}>
      <span className={fixture ? 'bd-fixture-role' : 'bd-role'}>{role === 'user' ? 'Khách hàng' : 'Chatbot'}{fixture ? ' · lịch sử gốc' : ''}</span>
      <p>{content}</p>
      {createdAt && <time className="bd-message-time" dateTime={createdAt} title="Thời điểm lưu phản hồi demo">{new Date(createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>}
    </div>
  );
}

export default function BenchmarkDemoPage() {
  const [config, setConfig] = useState(null);
  const [session, setSession] = useState(null);
  const [caseId, setCaseId] = useState('TC01');
  const [method, setMethod] = useState('P');
  const [records, setRecords] = useState({});
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [closedPanels, setClosedPanels] = useState({});

  useEffect(() => {
    let cancelled = false;
    async function open() {
      try {
        const settings = await request('/api/demo/config');
        const storageKey = `techcare_benchmark_demo:${settings.instance_id}`;
        const stored = localStorage.getItem(storageKey);
        let current;
        if (stored) {
          try { current = await request(`/api/demo/sessions/${stored}`); } catch { /* New server/session. */ }
        }
        if (!current) current = await request('/api/demo/sessions', {});
        if (cancelled) return;
        const saved = {};
        for (const run of current.runs || []) {
          const key = `${run.case_id}:${run.method}`;
          if (!saved[key] || saved[key].created_at < run.created_at) saved[key] = run;
        }
        localStorage.setItem(storageKey, current.session_id);
        setConfig(settings);
        setSession(current.session_id);
        setRecords(saved);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    open();
    return () => { cancelled = true; };
  }, []);

  const selectedCase = config?.cases.find(item => item.case_id === caseId);

  async function newSession() {
    setBusy('session');
    setError('');
    try {
      const current = await request('/api/demo/sessions', {});
      localStorage.setItem(`techcare_benchmark_demo:${config.instance_id}`, current.session_id);
      setSession(current.session_id);
      setRecords({});
    } catch (err) { setError(err.message); } finally { setBusy(''); }
  }

  async function run(selectedMethods) {
    setError('');
    try {
      for (const currentMethod of selectedMethods) {
        setBusy(currentMethod);
        const record = await request('/api/demo/runs', { session_id: session, method: currentMethod, case_id: caseId });
        setRecords(previous => ({ ...previous, [`${caseId}:${currentMethod}`]: record }));
      }
    } catch (err) { setError(err.message); } finally { setBusy(''); }
  }

  return (
    <main className="benchmark-demo">
      <header className="bd-header">
        <div>
          <p className="bd-brand">TechCare Electronics <span>NGHIÊN CỨU · LOCAL</span></p>
          <h1>Đối chiếu bốn phương pháp chatbot</h1>
          <p className="bd-notice">Lượt chạy web mới trên snapshot benchmark. Phản hồi được giữ nguyên từ pipeline; P+FT là thử nghiệm riêng.</p>
        </div>
        <div className="bd-status">{config ? 'Snapshot đã đối chiếu' : 'Đang kết nối demo…'}</div>
      </header>

      <section className="bd-toolbar" aria-label="Điều khiển demo">
        <label>Ca kiểm thử
          <select aria-label="Ca kiểm thử" value={caseId} disabled={!!busy || !config} onChange={event => { setCaseId(event.target.value); setError(''); }}>
            {(config?.cases || []).map(item => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.group}</option>)}
          </select>
        </label>
        <label>Phương pháp
          <select aria-label="Phương pháp" value={method} disabled={!!busy || !config} onChange={event => setMethod(event.target.value)}>
            {METHODS.map(item => <option key={item} value={item}>{item} · {NAMES[item]}</option>)}
          </select>
        </label>
        <button className="bd-secondary" disabled={!!busy || !session} onClick={() => run([method])}>Chạy phương pháp</button>
        <button className="bd-primary" disabled={!!busy || !session} onClick={() => run(METHODS)}>Chạy cả 4 phương pháp</button>
        <button className="bd-secondary" disabled={!!busy || !config} onClick={newSession}>Phiên demo mới</button>
      </section>

      {error && <p className="bd-error" role="alert">{error} Không có phản hồi thay thế. Kiểm tra terminal backend demo.</p>}
      {busy && <p className="bd-progress" role="status">{busy === 'session' ? 'Đang tạo phiên demo mới…' : `Đang chạy ${busy} · ${caseId}…`}</p>}

      {config && <section className="bd-config" aria-label="Cấu hình thực nghiệm">
        <span><strong>{caseId}</strong> · {selectedCase?.group}</span>
        <span>B1/B2/P: {config.model}</span>
        <span>B0: không dùng LLM</span>
        <span>{config.documents} tài liệu · ngữ cảnh 4.096 · đầu ra ≤384 token · temperature 0</span>
      </section>}

      {selectedCase?.history.length > 0 && <p className="bd-fixture-note">Đã nạp nguyên {selectedCase.history.length} lượt lịch sử từ bộ test, đúng vai trò user/assistant. Lượt chatbot trong lịch sử là dữ liệu đầu vào cố định, không được sinh lại.</p>}

      <section className="bd-grid" aria-label="Bốn phản hồi so sánh">
        {METHODS.map((item, index) => {
          const record = records[`${caseId}:${item}`];
          const result = record?.result;
          const failed = result && !['ok', 'no_rule_match'].includes(result.status);
          return (
            <article key={item} className={`bd-card ${item === method ? 'bd-selected' : ''}`} data-method={item} data-case={caseId}>
              <div className="bd-card-heading"><span className="bd-panel-letter">{String.fromCharCode(65 + index)}</span><div><h2>{item} — {NAMES[item]}</h2><p>{caseId} · {item === 'B0' ? 'Luật và FAQ' : 'Qwen2.5-3B gốc'}</p></div></div>
              {closedPanels[item] ? <button className="bd-secondary bd-reopen" onClick={() => setClosedPanels(previous => ({ ...previous, [item]: false }))}>Mở khung chat {item}</button> : <div className="bd-chat-window">
                <div className="bd-chat-header">
                  <div className="bd-chat-title"><Bot aria-hidden="true" size={24} /><div><h3>Trợ lý AI</h3><p>Luôn sẵn sàng hỗ trợ</p></div></div>
                  <button className="bd-chat-close" aria-label={`Đóng khung chat ${item}`} onClick={() => setClosedPanels(previous => ({ ...previous, [item]: true }))}><X aria-hidden="true" size={20} /></button>
                </div>
                <div className="bd-conversation">
                  {selectedCase?.history.map((turn, turnIndex) => <Message key={`fixture-${turnIndex}`} role={turn.role} content={turn.content} fixture />)}
                  {selectedCase && <Message role="user" content={selectedCase.question} />}
                  {result?.answer && <div className="bd-answer" data-testid={`answer-${item}`}><Message role="assistant" content={result.answer} createdAt={record.created_at} /></div>}
                  {!result && <p className="bd-empty">{busy === item ? 'Đang xử lý bằng pipeline thực tế…' : 'Chưa chạy phương pháp này trong ca đã chọn.'}</p>}
                  {failed && <p className="bd-error">Không hoàn tất: {result.error?.message || result.status}. Không có câu trả lời giả lập.</p>}
                </div>
                <div className="bd-chat-composer">
                  <p className="bd-composer-note">Câu hỏi được nạp từ bộ kiểm thử</p>
                  <div className="bd-input-wrap">
                    <input aria-label={`Tin nhắn ${item}`} placeholder="Nhập tin nhắn..." disabled title="Chọn ca kiểm thử và dùng nút Chạy ở phía trên." />
                    <button className="bd-chat-send" disabled aria-label={`Gửi tin nhắn ${item}`}><Send aria-hidden="true" size={16} /></button>
                  </div>
                </div>
              </div>}
              {record && <footer className="bd-card-footer">
                <span>{result.status} · {result.mode || 'chưa có nhánh trả lời'} · {result.llm_called ? 'Có gọi LLM' : 'Không gọi LLM'}</span>
                {result.latency_ms != null && <span>{new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 0 }).format(result.latency_ms)} ms trong pipeline</span>}
                <details><summary>Nguồn và bằng chứng lượt chạy</summary>
                  <p>Pipeline thực tế: <code>{result.pipeline_class || 'chưa khởi tạo'}</code></p>
                  <p>Model: {result.identity?.model || 'không dùng LLM'} · Lịch sử: {result.history_matches_fixture ? 'khớp bộ test' : 'chưa xác minh'}</p>
                  <p>Mã lượt chạy: {record.run_id}</p>
                  <ul>{(result.sources || []).map((source, sourceIndex) => <li key={`${source.id}-${sourceIndex}`}>{source.title}</li>)}</ul>
                  <a href={`${API}/api/demo/sessions/${session}/runs/${record.run_id}`} target="_blank" rel="noreferrer">Mở JSON kết quả thực tế</a>
                </details>
              </footer>}
            </article>
          );
        })}
      </section>
      {config && <details className="bd-storage"><summary>Thông tin phiên demo và cấu hình</summary>
        <p>Phiên riêng: {session}. Không ghi vào lịch sử khách hàng.</p>
        <p>Bộ câu hỏi: {config.input_source}</p><p>Lưu kết quả mới: {config.output}</p>
        <p>{config.notice}</p>
      </details>}
    </main>
  );
}
