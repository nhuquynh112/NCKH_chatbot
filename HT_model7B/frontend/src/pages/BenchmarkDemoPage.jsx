import React, { useEffect, useRef, useState } from 'react';
import { Bot, Send, X } from 'lucide-react';
import BlindReviewPage from './BlindReviewPage';
import './BenchmarkDemoPage.css';

const API = import.meta.env.VITE_BENCHMARK_API_URL || 'http://127.0.0.1:8012';
const METHODS = ['B0', 'B1', 'B2', 'P'];
const NAMES = { B0: 'Rule-based chatbot', B1: 'LLM không sử dụng RAG', B2: 'Basic RAG', P: 'Kiến trúc đề xuất · model gốc' };

async function request(path, body, timeout = 110000) {
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(API).hostname)) {
    throw new Error('Demo chỉ kết nối máy chủ local.');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
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
  const [question, setQuestion] = useState('');
  const [historyText, setHistoryText] = useState('[]');
  const [showAll, setShowAll] = useState(false);
  const [blindSession, setBlindSession] = useState(null);
  const [usePack, setUsePack] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [batchProgress, setBatchProgress] = useState('');
  const stopBatch = useRef(false);

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
        if (settings.blinded) {
          localStorage.setItem(storageKey, current.session_id);
          setConfig(settings);
          setBlindSession(current);
          return;
        }
        const saved = {};
        for (const run of current.runs || []) {
          const key = `${run.case_id}:${run.method}`;
          if (!saved[key] || saved[key].created_at < run.created_at) saved[key] = run;
        }
        localStorage.setItem(storageKey, current.session_id);
        setConfig(settings);
        setSession(current.session_id);
        setRecords(saved);
        setUsePack(!!settings.test_cases?.length);
        setSessions(await request('/api/demo/sessions'));
        if (settings.interactive) {
          setMethod('B0');
          const latest = (current.runs || []).at(-1);
          setCaseId(latest?.case_id || 'TEST01');
          setQuestion(latest?.question || '');
          setHistoryText(JSON.stringify(latest?.fixed_history || [], null, 2));
          if (settings.test_cases?.length) setCaseId(settings.test_cases.some(row => row.id === latest?.case_id) ? latest.case_id : settings.test_cases[0].id);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    open();
    return () => { cancelled = true; };
  }, []);

  let manualHistory = [];
  try { manualHistory = JSON.parse(historyText); } catch { /* Validated before sending. */ }
  const packedCase = config?.test_cases?.find(row => row.id === caseId);
  const selectedCase = usePack && packedCase
    ? { case_id: packedCase.id, question: packedCase.question, history: packedCase.history, group: packedCase.category }
    : config?.interactive
    ? { case_id: caseId, group: 'Câu hỏi do nhóm nhập', question, history: Array.isArray(manualHistory) ? manualHistory : [] }
    : config?.cases.find(item => item.case_id === caseId);
  const savedCases = [...new Map(Object.values(records).map(record => [record.case_id, record])).values()]
    .sort((a, b) => a.case_id.localeCompare(b.case_id, undefined, { numeric: true }));

  function loadCase(id) {
    const saved = savedCases.find(item => item.case_id === id);
    if (!saved) return;
    setCaseId(id);
    setQuestion(saved.question);
    setHistoryText(JSON.stringify(saved.fixed_history, null, 2));
    setError('');
  }

  function nextCase() {
    if (usePack) {
      const items = config.test_cases;
      setCaseId(items[(items.findIndex(row => row.id === caseId) + 1) % items.length].id);
      setError('');
      return;
    }
    let number = 1;
    while (savedCases.some(item => item.case_id === `TEST${String(number).padStart(2, '0')}`)) number++;
    setCaseId(`TEST${String(number).padStart(2, '0')}`);
    setQuestion('');
    setHistoryText('[]');
    setError('');
  }

  async function newSession() {
    setBusy('session');
    setError('');
    try {
      const current = await request('/api/demo/sessions', {});
      localStorage.setItem(`techcare_benchmark_demo:${config.instance_id}`, current.session_id);
      setSession(current.session_id);
      setRecords({});
      setSessions(await request('/api/demo/sessions'));
      if (config.interactive) { setCaseId(usePack ? config.test_cases[0].id : 'TEST01'); setQuestion(''); setHistoryText('[]'); }
    } catch (err) { setError(err.message); } finally { setBusy(''); }
  }

  async function run(selectedMethods) {
    setError('');
    try {
      const input = { case_id: caseId };
      if (config.interactive && !usePack) {
        if (!/^[A-Za-z0-9_-]{1,80}$/.test(caseId) || !question.trim()) throw new Error('Nhập mã câu hợp lệ và câu hỏi.');
        const history = JSON.parse(historyText);
        if (!Array.isArray(history) || history.some(turn => !['user', 'assistant'].includes(turn.role) || typeof turn.content !== 'string' || !turn.content.trim())) {
          throw new Error('Lịch sử cần là mảng JSON có role user/assistant và content. Câu độc lập dùng [].');
        }
        input.question = question;
        input.history = history;
      }
      for (const currentMethod of selectedMethods) {
        setBusy(currentMethod);
        const limit = usePack && packedCase?.history_questions.length ? (config.conversation_timeout_seconds || config.timeout_seconds) : config.timeout_seconds;
        const record = await request(usePack ? '/api/demo/dataset/runs' : '/api/demo/runs', { session_id: session, method: currentMethod, ...input }, (limit + 20) * 1000);
        setRecords(previous => ({ ...previous, [`${caseId}:${currentMethod}`]: record }));
      }
    } catch (err) { setError(err.message); } finally { setBusy(''); }
  }

  async function reopenSession(id) {
    setBusy('session'); setError('');
    try {
      const current = await request(`/api/demo/sessions/${id}`);
      const saved = {};
      for (const row of [...current.runs].sort((a, b) => a.created_at.localeCompare(b.created_at))) saved[`${row.case_id}:${row.method}`] = row;
      localStorage.setItem(`techcare_benchmark_demo:${config.instance_id}`, current.session_id);
      setSession(current.session_id); setRecords(saved);
      const latest = [...current.runs].sort((a, b) => a.created_at.localeCompare(b.created_at)).at(-1);
      if (latest) {
        setUsePack(latest.input_mode === 'test_pack'); setCaseId(latest.case_id); setMethod(latest.method);
        setQuestion(latest.question); setHistoryText(JSON.stringify(latest.fixed_history, null, 2));
      }
    } catch (err) { setError(err.message); } finally { setBusy(''); }
  }

  async function runRemaining() {
    stopBatch.current = false; setError('');
    try {
      const pending = config.test_cases.filter(row => !records[`${row.id}:${method}`]);
      for (const [index, row] of pending.entries()) {
        if (stopBatch.current) break;
        setBusy(method); setCaseId(row.id); setBatchProgress(`${index + 1}/${pending.length} · ${row.id}`);
        const limit = row.history_questions.length ? (config.conversation_timeout_seconds || config.timeout_seconds) : config.timeout_seconds;
        const record = await request('/api/demo/dataset/runs', { session_id: session, method, case_id: row.id }, (limit + 20) * 1000);
        setRecords(previous => ({ ...previous, [`${row.id}:${method}`]: record }));
      }
    } catch (err) { setError(err.message); } finally { setBusy(''); setBatchProgress(''); }
  }

  if (!config || (config.blinded && !blindSession)) {
    return <main className="benchmark-demo"><header className="bd-header"><div><p className="bd-brand">TechCare Electronics</p><h1>Đánh giá phản hồi chatbot</h1></div></header>
      {error ? <p className="bd-error" role="alert">{error}</p> : <p className="bd-progress" role="status">Đang kết nối…</p>}</main>;
  }

  if (config.blinded && blindSession) {
    return <BlindReviewPage key={blindSession.session_id} config={{ ...config, api: API }} initialSession={blindSession}
      requestApi={request} MessageView={Message} onSessionChange={current => {
        localStorage.setItem(`techcare_benchmark_demo:${config.instance_id}`, current.session_id);
        setBlindSession(current);
      }} />;
  }

  return (
    <main className="benchmark-demo">
      <header className="bd-header">
        <div>
          <p className="bd-brand">TechCare Electronics <span>NGHIÊN CỨU · LOCAL</span></p>
          <h1>Đối chiếu bốn phương pháp chatbot</h1>
          <p className="bd-notice">{config?.interactive ? 'Chạy từng phương pháp với cùng bộ câu hỏi. Lưu câu trước khi chuyển phương pháp; tải CSV để tự chấm điểm.' : 'Lượt chạy web mới trên snapshot benchmark. Phản hồi được giữ nguyên từ pipeline; P+FT là thử nghiệm riêng.'}</p>
        </div>
        <div className="bd-status">{config ? 'Snapshot đã đối chiếu' : 'Đang kết nối demo…'}</div>
      </header>

      <section className="bd-toolbar" aria-label="Điều khiển demo">
        {!config?.interactive && <label>Ca kiểm thử
          <select aria-label="Ca kiểm thử" value={caseId} disabled={!!busy || !config} onChange={event => { setCaseId(event.target.value); setError(''); }}>
            {(config?.cases || []).map(item => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.group}</option>)}
          </select>
        </label>}
        <label>Phương pháp
          <select aria-label="Phương pháp" value={method} disabled={!!busy || !config} onChange={event => setMethod(event.target.value)}>
            {METHODS.map(item => <option key={item} value={item}>{item} · {NAMES[item]}</option>)}
          </select>
        </label>
        <button className="bd-secondary" disabled={!!busy || !session} onClick={() => run([method])}>Chạy phương pháp</button>
        <button className="bd-primary" disabled={!!busy || !session} onClick={() => run(METHODS)}>Chạy cả 4 phương pháp</button>
        <button className="bd-secondary" disabled={!!busy || !config} onClick={newSession}>Phiên demo mới</button>
        {config.interactive && <label>Phiên đã lưu<select aria-label="Phiên đã lưu" value={session || ''} disabled={!!busy} onChange={event => reopenSession(event.target.value)}>
          {sessions.map(row => <option key={row.session_id} value={row.session_id}>{row.created_at} · {row.run_count} lượt · {row.session_id.slice(0, 8)}</option>)}
        </select></label>}
        {config?.interactive && <label className="bd-check"><input type="checkbox" checked={showAll} onChange={event => setShowAll(event.target.checked)} disabled={!!busy} />Hiện cả 4 khung</label>}
        {session && <a href={`${API}/api/demo/sessions/${session}/export.csv`} download>Tải CSV chấm điểm</a>}
        {session && <a href={`${API}/api/demo/sessions/${session}`} target="_blank" rel="noreferrer">Kết quả JSON</a>}
      </section>

      {config?.interactive && !!config.test_cases?.length && <section className="bd-manual">
        <label><span><input type="checkbox" checked={usePack} disabled={!!busy} onChange={event => { setUsePack(event.target.checked); setCaseId(event.target.checked ? config.test_cases[0].id : 'TEST01'); }} /> Dùng bộ {config.test_cases.length} ca gốc (tự chạy hội thoại H)</span></label>
        {usePack && <><label>Ca trong bộ đề<select aria-label="Ca trong bộ đề" disabled={!!busy} value={caseId} onChange={event => setCaseId(event.target.value)}>
          {config.test_cases.map(row => <option key={row.id} value={row.id}>{row.id} · {row.question}</option>)}
        </select></label><p>{packedCase?.question}</p>
          {!!packedCase?.history_questions.length && <p>Hệ thống tự hỏi {packedCase.history_questions.length} lượt trước, giữ câu trả lời thật của phương pháp đang chạy, rồi hỏi câu cuối. Không cần dán JSON.</p>}
          <button disabled={!!busy} onClick={nextCase}>Ca tiếp theo</button>{' '}
          <button disabled={!!busy || !session} onClick={runRemaining}>Chạy các ca chưa có kết quả của {method}</button>{' '}
          {!!batchProgress && <button onClick={() => { stopBatch.current = true; }}>Dừng sau ca đang chạy</button>}
          {batchProgress && <p role="status">{batchProgress}</p>}</>}
      </section>}

      {config?.interactive && !usePack && <section className="bd-manual" aria-label="Nhập câu kiểm thử">
        <div className="bd-manual-row">
          <label>Mã câu<input aria-label="Mã câu" value={caseId} disabled={!!busy} onChange={event => setCaseId(event.target.value)} /></label>
          <label>Câu đã lưu ({savedCases.length})<select aria-label="Câu đã lưu" value={savedCases.some(item => item.case_id === caseId) ? caseId : ''} disabled={!!busy} onChange={event => loadCase(event.target.value)}>
            <option value="">Chọn câu đã lưu để chạy phương pháp tiếp theo</option>
            {savedCases.map(item => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.question.slice(0, 85)}</option>)}
          </select></label>
          <button className="bd-secondary" disabled={!!busy} onClick={nextCase}>Câu tiếp theo</button>
          <span>{method}: {new Set(Object.values(records).filter(item => item.method === method).map(item => item.case_id)).size} câu đã chạy</span>
        </div>
        <label>Câu hỏi<textarea aria-label="Câu hỏi kiểm thử" rows={3} value={question} disabled={!!busy} onChange={event => setQuestion(event.target.value)} placeholder="Nhập câu hỏi, rồi bấm Chạy phương pháp ở phía trên." /></label>
        <details><summary>Lịch sử đầu vào cho câu nhiều lượt (JSON)</summary>
          <p>Câu độc lập dùng []. Dùng đúng cùng lịch sử và vai trò cho cả bốn phương pháp. Kết quả câu trước không tự được thêm vào câu sau.</p>
          <textarea aria-label="Lịch sử đầu vào" rows={5} value={historyText} disabled={!!busy} onChange={event => setHistoryText(event.target.value)} />
        </details>
        <p>Cùng mã câu phải giữ nguyên câu hỏi và lịch sử. Để chạy lại 50 câu ở B1/B2/P, đổi phương pháp rồi chọn lần lượt các câu đã lưu.</p>
      </section>}

      {error && <p className="bd-error" role="alert">{error} Không có phản hồi thay thế. Kiểm tra terminal backend demo.</p>}
      {busy && <p className="bd-progress" role="status">{busy === 'session' ? 'Đang tạo phiên demo mới…' : `Đang chạy ${busy} · ${caseId}…`}</p>}

      {config && <section className="bd-config" aria-label="Cấu hình thực nghiệm">
        <span><strong>{caseId}</strong> · {selectedCase?.group}</span>
        <span>B1/B2/P: {config.model}</span>
        <span>B0: không dùng LLM</span>
        <span>{config.documents} tài liệu · ngữ cảnh 4.096 · đầu ra ≤384 token · temperature 0</span>
      </section>}

      {selectedCase?.history.length > 0 && <p className="bd-fixture-note">Đã nạp nguyên {selectedCase.history.length} lượt lịch sử từ bộ test, đúng vai trò user/assistant. Lượt chatbot trong lịch sử là dữ liệu đầu vào cố định, không được sinh lại.</p>}

      <section className={`bd-grid ${config?.interactive && !showAll ? 'bd-single' : ''}`} aria-label="Phản hồi phương pháp">
        {(config?.interactive && !showAll ? [method] : METHODS).map(item => {
          const index = METHODS.indexOf(item);
          const record = records[`${caseId}:${item}`];
          const result = record?.result;
          const failed = result && !['ok', 'no_rule_match'].includes(result.status);
          const methodModel = config?.methods?.find(entry => entry.id === item)?.model;
          const displayedCase = record ? { question: record.question, history: record.actual_history || record.fixed_history } : selectedCase;
          return (
            <article key={item} className={`bd-card ${item === method ? 'bd-selected' : ''}`} data-method={item} data-case={caseId}>
              <div className="bd-card-heading"><span className="bd-panel-letter">{String.fromCharCode(65 + index)}</span><div><h2>{item} — {NAMES[item]}</h2><p>{caseId} · {item === 'B0' ? 'Luật và FAQ' : `${methodModel || 'Chưa xác minh model'} · model gốc`}</p></div></div>
              {closedPanels[item] ? <button className="bd-secondary bd-reopen" onClick={() => setClosedPanels(previous => ({ ...previous, [item]: false }))}>Mở khung chat {item}</button> : <div className="bd-chat-window">
                <div className="bd-chat-header">
                  <div className="bd-chat-title"><Bot aria-hidden="true" size={24} /><div><h3>Trợ lý AI</h3><p>Luôn sẵn sàng hỗ trợ</p></div></div>
                  <button className="bd-chat-close" aria-label={`Đóng khung chat ${item}`} onClick={() => setClosedPanels(previous => ({ ...previous, [item]: true }))}><X aria-hidden="true" size={20} /></button>
                </div>
                <div className="bd-conversation">
                  {displayedCase?.history.map((turn, turnIndex) => <Message key={`fixture-${turnIndex}`} role={turn.role} content={turn.content} fixture />)}
                  {displayedCase?.question && <Message role="user" content={displayedCase.question} />}
                  {result?.answer && <div className="bd-answer" data-testid={`answer-${item}`}><Message role="assistant" content={result.answer} createdAt={record.created_at} /></div>}
                  {!result && <p className="bd-empty">{busy === item ? 'Đang xử lý bằng pipeline thực tế…' : 'Chưa chạy phương pháp này trong ca đã chọn.'}</p>}
                  {failed && <p className="bd-error">Không hoàn tất: {result.error?.message || result.status}. Không có câu trả lời giả lập.</p>}
                </div>
                <div className="bd-chat-composer">
                  <p className="bd-composer-note">{config?.interactive ? 'Nhập câu hỏi ở phần kiểm thử phía trên' : 'Câu hỏi được nạp từ bộ kiểm thử'}</p>
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
                  <p>Model: {result.identity?.model || 'không dùng LLM'} · Lịch sử: {record.history_questions?.length ? 'tự sinh từ hội thoại thực tế' : result.history_matches_fixture ? 'khớp đầu vào' : 'chưa xác minh'}</p>
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
