let page = 1;
let pageSize = 10;
let total = 0;
let eventSource = null;

const $ = (id) => document.getElementById(id);

async function request(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || '请求失败');
  return data;
}

async function loadKnowledge() {
  const data = await request(`/api/knowledge?page=${page}&page_size=${pageSize}`);
  total = data.total;
  $('pageInfo').textContent = `第 ${data.page} 页 / 共 ${Math.max(1, Math.ceil(total / pageSize))} 页`;
  $('knowledgeList').innerHTML = data.items.map(item => `
    <article class="item">
      <div class="item-title">
        <span>${escapeHtml(item.title)}</span>
        <span>
          <button class="secondary" onclick="editKnowledge(${item.id})">编辑</button>
          <button class="danger" onclick="deleteKnowledge(${item.id})">删除</button>
        </span>
      </div>
      <div class="item-meta">ID ${item.id} · ${item.source_type} · chunks ${item.chunk_count}</div>
      <div class="item-content">${escapeHtml(item.content.slice(0, 260))}</div>
    </article>
  `).join('') || '<p>暂无知识库，请先新增或上传 txt。</p>';
}

async function editKnowledge(id) {
  const item = await request(`/api/knowledge/${id}`);
  $('knowledgeId').value = item.id;
  $('title').value = item.title;
  $('content').value = item.content;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function deleteKnowledge(id) {
  if (!confirm('确认删除这个知识库？')) return;
  await request(`/api/knowledge/${id}`, { method: 'DELETE' });
  await loadKnowledge();
}

function resetForm() {
  $('knowledgeId').value = '';
  $('title').value = '';
  $('content').value = '';
}

$('knowledgeForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const id = $('knowledgeId').value;
  const payload = { title: $('title').value, content: $('content').value };
  await request(id ? `/api/knowledge/${id}` : '/api/knowledge', {
    method: id ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  resetForm();
  await loadKnowledge();
});

$('uploadForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData();
  form.append('title', $('uploadTitle').value);
  form.append('file', $('file').files[0]);
  const res = await fetch('/api/knowledge/upload', { method: 'POST', body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || '上传失败');
  $('uploadTitle').value = '';
  $('file').value = '';
  await loadKnowledge();
});

$('searchBtn').addEventListener('click', async () => {
  const query = $('query').value.trim();
  $('result').textContent = '检索中...';
  const data = await request('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 5 }),
  });
  $('result').textContent = JSON.stringify(data, null, 2);
});

$('streamBtn').addEventListener('click', () => {
  const query = $('query').value.trim();
  if (!query) { $('result').textContent = '请输入 query'; return; }
  if (eventSource) eventSource.close();
  $('result').textContent = '';
  eventSource = new EventSource(`/api/search/stream?query=${encodeURIComponent(query)}&top_k=5`);
  eventSource.addEventListener('status', e => $('result').textContent += JSON.parse(e.data).message + '\n');
  eventSource.addEventListener('meta', e => $('result').textContent += `backend: ${JSON.parse(e.data).embedding_backend}\n\n`);
  eventSource.addEventListener('document', e => {
    const data = JSON.parse(e.data);
    $('result').textContent += `\n# ${data.title} (${data.score})\n`;
  });
  eventSource.addEventListener('token', e => $('result').textContent += JSON.parse(e.data).text);
  eventSource.addEventListener('error', e => {
    if (e.data) $('result').textContent += '\nERROR: ' + JSON.parse(e.data).message;
    eventSource.close();
  });
  eventSource.addEventListener('done', () => eventSource.close());
});

$('resetBtn').addEventListener('click', resetForm);
$('refreshBtn').addEventListener('click', loadKnowledge);
$('prevPage').addEventListener('click', async () => { if (page > 1) { page -= 1; await loadKnowledge(); } });
$('nextPage').addEventListener('click', async () => { if (page * pageSize < total) { page += 1; await loadKnowledge(); } });

function escapeHtml(text) {
  return String(text).replace(/[&<>'"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
}

loadKnowledge().catch(err => $('knowledgeList').textContent = err.message);
