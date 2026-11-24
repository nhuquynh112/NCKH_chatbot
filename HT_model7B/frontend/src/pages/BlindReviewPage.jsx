import React, { useState } from 'react';
import { Bot, Send } from 'lucide-react';

function latestRecords(runs) {
  const records = {};
  for (const run of runs) {
    const key = `${run.case_id}:${run.system_id}`;
    if (!records[key] || records[key].created_at < run.created_at) records[key] = run;
  }
  return records;
}

export default function BlindReviewPage({ config, initialSession, requestApi, MessageView, onSessionChange }) {
  const latest = [...initialSession.runs].sort((a, b) => a.created_at.localeCompare(b.created_at)).at(-1);
  const [systemId, setSystemId] = useState(latest?.system_id || initialSession.systems[0].system_id);
  const [caseId, setCaseId] = useState(latest?.case_id || 'S01');
  const [question, setQuestion] = useState(latest?.question || '');
  const [historyText, setHistoryText] = useState(JSON.stringify(latest?.fixed_history || [], null, 2));
  const [records, setRecords] = useState(() => latestRecords(initialSession.runs));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const system = initialSession.systems.find(row => row.system_id === systemId);
  const record = records[`${caseId}:${systemId}`];
  const result = record?.result;
  let history = [];
  try { const value = JSON.parse(historyText); if (Array.isArray(value)) history = value; } catch { /* Validated when sending. */ }
  const savedCases = [...new Set(Object.values(records).map(row => row.case_id))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

  function loadInput(id, selectedSystem = systemId) {
    const own = records[`${id}:${selectedSystem}`];
    const other = Object.values(records).find(row => row.case_id === id);
    setCaseId(id);
    setQuestion(own?.question || other?.question || question);
    // Never carry another anonymous system's generated replies into this one.
    setHistoryText(JSON.stringify(own?.fixed_history || [], null, 2));
    setError('');
  }

  function nextCase() {
    let number = 1;
    while (savedCases.includes(`TEST${String(number).padStart(2, '0')}`)) number++;
    setCaseId(`TEST${String(number).padStart(2, '0')}`);
    setQuestion('');
    setHistoryText('[]');
    setError('');
  }

  async function run(event) {
    event.preventDefault();
    setError('');
    try {
      if (!/^[A-Za-z0-9_-]{1,80}$/.test(caseId) || !question.trim()) throw new Error('Nhập mã câu hợp lệ và câu hỏi.');
      const turns = JSON.parse(historyText);
      if (!Array.isArray(turns) || turns.some(turn => !['user', 'assistant'].includes(turn.role) || typeof turn.content !== 'string' || !turn.content.trim())) {
        throw new Error('Lịch sử cần là mảng JSON có role user/assistant và content. Câu độc lập dùng [].');
      }
      setBusy(true);
      const current = await requestApi('/api/demo/blind/runs', {
        session_id: initialSession.session_id, system_id: systemId, case_id: caseId, question, history: turns,
      }, (config.timeout_seconds + 20) * 1000);
      setRecords(previous => ({ ...previous, [`${caseId}:${systemId}`]: current }));
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function newSession() {
    setBusy(true);
    setError('');
    try { onSessionChange(await requestApi('/api/demo/sessions', {})); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const displayed = record || { question, fixed_history: history };
  return (
    <main className="benchmark-demo bd-blind-review">
      <header className="bd-header">
        <div><p className="bd-brand">TechCare Electronics <span>ĐÁNH GIÁ ẨN DANH</span></p>
          <h1>Đánh giá phản hồi chatbot</h1>
          <p className="bd-notice">Chấm nội dung phản hồi theo mã trợ lý. Mã được xáo trộn riêng cho mỗi phiên; nội dung câu trả lời được giữ nguyên.</p></div>
        <span className="bd-status">Chế độ chấm mù</span>
      </header>

      <section className="bd-toolbar" aria-label="Điều khiển đánh giá">
        <label>Trợ lý<select aria-label="Trợ lý ẩn danh" value={systemId} disabled={busy} onChange={event => { setSystemId(event.target.value); loadInput(caseId, event.target.value); }}>
          {initialSession.systems.map(row => <option key={row.system_id} value={row.system_id}>{row.label}</option>)}
        </select></label>
        <button className="bd-secondary" disabled={busy} onClick={nextCase}>Câu tiếp theo</button>
        <button className="bd-secondary" disabled={busy} onClick={newSession}>Phiên đánh giá mới</button>
        <a href={`${config.api}/api/demo/sessions/${initialSession.session_id}/export.csv`} download>Tải phiếu CSV ẩn danh</a>
      </section>

      <form className="bd-manual" aria-label="Nhập câu đánh giá" onSubmit={run}>
        <div className="bd-manual-row">
          <label>Mã câu<input aria-label="Mã câu" value={caseId} disabled={busy} onChange={event => setCaseId(event.target.value)} /></label>
          <label>Câu đã lưu<select aria-label="Câu đã lưu" value={savedCases.includes(caseId) ? caseId : ''} disabled={busy} onChange={event => loadInput(event.target.value)}>
            <option value="" disabled>Chọn mã câu</option>{savedCases.map(id => <option key={id} value={id}>{id}</option>)}
          </select></label>
          <span>{Object.values(records).filter(row => row.system_id === systemId).length} câu đã chạy ở trợ lý đang chọn</span>
        </div>
        <label>Câu hỏi<textarea aria-label="Câu hỏi kiểm thử" rows={3} value={question} disabled={busy} onChange={event => setQuestion(event.target.value)} /></label>
        <details><summary>Lịch sử đầu vào (JSON)</summary>
          <p>Câu độc lập dùng []. Với hội thoại, dùng đúng phản hồi thực tế của trợ lý đang chọn; mỗi lượt hỏi dùng mã riêng. Đổi trợ lý sẽ không tự lấy lịch sử của trợ lý trước.</p>
          <textarea aria-label="Lịch sử đầu vào" rows={5} value={historyText} disabled={busy} onChange={event => setHistoryText(event.target.value)} />
        </details>
        <button className="bd-primary bd-blind-submit" disabled={busy} type="submit"><Send size={15} aria-hidden="true" />Gửi câu hỏi</button>
      </form>

      {error && <p className="bd-error" role="alert">{error}</p>}
      {busy && <p className="bd-progress" role="status">Đang xử lý…</p>}
      <section className="bd-grid bd-single" aria-label="Phản hồi ẩn danh">
        <article className="bd-card" data-case={caseId}>
          <div className="bd-card-heading"><h2>{system.label} · {caseId}</h2></div>
          <div className="bd-chat-window">
            <div className="bd-chat-header"><div className="bd-chat-title"><Bot size={24} aria-hidden="true" /><div><h3>Trợ lý AI</h3><p>Luôn sẵn sàng hỗ trợ</p></div></div></div>
            <div className="bd-conversation">
              {displayed.fixed_history.map((turn, index) => <MessageView key={index} role={turn.role} content={turn.content} />)}
              {displayed.question && <MessageView role="user" content={displayed.question} />}
              {result?.answer && <div className="bd-answer"><MessageView role="assistant" content={result.answer} /></div>}
              {!result && <p className="bd-empty">{busy ? 'Đang xử lý…' : 'Nhập câu hỏi để bắt đầu.'}</p>}
              {result && !['ok', 'no_rule_match'].includes(result.status) && <p className="bd-error">Lượt này chưa hoàn tất. Ghi nhận trạng thái khi chấm.</p>}
            </div>
          </div>
          {record && <footer className="bd-card-footer"><span>Trạng thái: {result.status}</span><span>Mã phản hồi: {record.run_id}</span></footer>}
        </article>
      </section>
    </main>
  );
}
