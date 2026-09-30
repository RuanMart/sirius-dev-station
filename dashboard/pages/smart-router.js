async function renderSmartRouter() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <div class="page-title">Smart Router</div>
        <div class="page-subtitle">Intelligent task routing — auto-suggest or manually pick an agent</div>
      </div>
    </div>
    <div class="card" style="margin-bottom:20px">
      <div class="card-header">
        <div class="card-title">Route a Task</div>
      </div>
      <div class="form-group">
        <label class="form-label">Describe your task</label>
        <textarea class="form-textarea" id="routerTaskInput" placeholder="e.g., Deploy the CloudMart infrastructure to GCP..." rows="3"></textarea>
      </div>
      <div class="flex gap-3" style="align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:1;min-width:180px">
          <label class="form-label">Route to Agent</label>
          <select class="form-select" id="routerAgentSelect">
            <option value="auto">🤖 Auto (AI suggests)</option>
            <option value="opencode">🔧 opencode (GLM 5.3 Flash Max)</option>
            <option value="hermes">⚡ Hermes (GLM 5.3 Flash Max)</option>
            <option value="agy">🧠 agy (Gemini 3.8 Flash High)</option>
          </select>
        </div>
        <div class="form-group" style="width:200px">
          <label class="form-label">Target Repo</label>
          <select class="form-select" id="routerRepoSelect">
            <option value="sirius">sirius (Root / Context)</option>
            <option value="sirius-mcp">sirius-mcp (TypeScript / MCP)</option>
            <option value="sirius-api">sirius-api (Java 21 / Spring)</option>
            <option value="sirius-landing">sirius-landing (Next.js 15)</option>
          </select>
        </div>
        <button class="btn btn-primary" onclick="suggestRouter()" style="margin-bottom:16px">🤖 Suggest Agent</button>
        <button class="btn btn-ghost" onclick="routeTask(false)" style="margin-bottom:16px">📋 Route Only</button>
        <button class="btn btn-gradient" id="btnRouteExecute" onclick="routeTask(true)" style="margin-bottom:16px">⚡ Route & Execute</button>
      </div>
    </div>
    <div id="routerResult"></div>
    <div class="section-title" style="margin-top:20px">Routing Rules</div>
    <div class="card">
      <table>
        <tr><th>Agent</th><th>Model & Setup</th><th>Best For</th><th>Keywords</th></tr>
        <tr><td><strong>🔧 opencode</strong></td><td><code>GLM 5.3 Flash (Max)</code></td><td>Code, DevOps, multi-repo dev, git, build, tests</td><td class="text-muted text-sm">code, deploy, git, test, build, script, refactor</td></tr>
        <tr><td><strong>⚡ Hermes</strong></td><td><code>GLM 5.3 Flash (Max)</code></td><td>Memory, scheduling, channels, background ops, context</td><td class="text-muted text-sm">memory, schedule, cron, reminder, brain, audit</td></tr>
        <tr><td><strong>🧠 agy</strong></td><td><code>Gemini 3.8 Flash (High)</code></td><td>Research, BMAD planning, architecture specs, PRDs</td><td class="text-muted text-sm">research, architecture, bmad, analyze, prd, spec</td></tr>
      </table>
    </div>
  `;
}

async function suggestRouter() {
  const task = document.getElementById('routerTaskInput').value.trim();
  if (!task) { showToast('Describe your task first', 'warning'); return; }
  const btn = document.querySelector('button[onclick="suggestRouter()"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Thinking...'; }
  try {
    const data = await api.suggestRouter(task);
    const result = document.getElementById('routerResult');
    const agentIcons = { opencode: '🔧', hermes: '⚡', agy: '🧠' };
    const confidenceColors = { high: 'var(--green)', medium: 'var(--yellow)', low: 'var(--text-muted)' };
    result.innerHTML = `
      <div class="card" style="border-color:${confidenceColors[data.confidence] || 'var(--border)'};margin-bottom:12px">
        <div class="router-suggestion" style="border:none;padding:0;background:none">
          <div>
            <div class="router-suggestion-agent" style="font-size:18px">
              ${agentIcons[data.suggested_agent] || '🤖'} ${data.suggested_agent}
            </div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
              Confidence: <span style="color:${confidenceColors[data.confidence] || 'var(--text-muted)'}">${data.confidence}</span>
              ${data.confidence === 'high' ? '✅' : data.confidence === 'medium' ? '⚠️' : '❓'}
            </div>
          </div>
          <div style="flex:1;text-align:right">
            <span class="badge badge-accent">Best Match</span>
          </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
          ${Object.entries(data.scores || {}).map(([agent, score]) => `
            <span class="badge ${score > 0 ? 'badge-success' : 'badge-info'}">
              ${agentIcons[agent] || '🤖'} ${agent}: ${score}
            </span>
          `).join('')}
        </div>
      </div>
    `;
    document.getElementById('routerAgentSelect').value = data.suggested_agent || 'auto';
  } catch (err) {
    showToast('Suggestion failed: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🤖 Suggest Agent'; }
  }
}

async function routeTask(execute = false) {
  const task = document.getElementById('routerTaskInput').value.trim();
  if (!task) { showToast('Describe your task first', 'warning'); return; }
  let agent = document.getElementById('routerAgentSelect').value;
  if (agent === 'auto') {
    showToast('Click "Suggest Agent" first or pick an agent manually', 'warning');
    return;
  }
  const repo = document.getElementById('routerRepoSelect')?.value || 'sirius';
  const executeBtn = document.getElementById('btnRouteExecute');
  if (execute && executeBtn) {
    executeBtn.disabled = true;
    executeBtn.textContent = `⏳ Running with ${agent}...`;
  }
  const result = document.getElementById('routerResult');
  const agentIcons = { opencode: '🔧', hermes: '⚡', agy: '🧠' };

  if (execute) {
    result.innerHTML = `
      <div class="card" style="margin-top:8px;border-color:var(--accent)">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="spinner"></div>
          <div>
            <div style="font-weight:600">Executing task with ${agentIcons[agent] || ''} ${agent}...</div>
            <div class="text-muted text-sm">Target repo: <code>${repo}</code> (Max reasoning effort active)</div>
          </div>
        </div>
      </div>
    `;
  }

  try {
    const data = await api.routeTask(task, agent, execute, repo);
    showToast(execute ? `✅ Task completed by ${agent}!` : `✅ Task routed to ${agent}`, 'success');

    if (execute && data.executed && data.response) {
      result.innerHTML = `
        <div class="card" style="margin-top:8px;border-color:var(--green)">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid var(--border);padding-bottom:8px">
            <div style="display:flex;align-items:center;gap:8px">
              <span style="font-size:20px">${agentIcons[agent] || '🤖'}</span>
              <strong>${agent}</strong>
              <span class="badge badge-success">Completed</span>
              <span class="text-muted text-sm">Repo: <code>${repo}</code></span>
            </div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-sm btn-ghost" onclick="navigator.clipboard.writeText(document.getElementById('taskResponseContent').innerText); showToast('Copied to clipboard!', 'info')">📋 Copy</button>
              <button class="btn btn-sm btn-primary" onclick="window.location.hash='#/chat'">💬 Open in Chat</button>
            </div>
          </div>
          <div id="taskResponseContent" style="white-space:pre-wrap;font-size:13px;line-height:1.6;color:var(--text);max-height:450px;overflow-y:auto;background:var(--bg-card);padding:12px;border-radius:6px;border:1px solid var(--border)">${escapeHtml(data.response)}</div>
        </div>
      `;
    } else {
      result.innerHTML = `
        <div class="card" style="margin-top:8px;border-color:var(--green)">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="display:flex;align-items:center;gap:12px">
              <span style="font-size:24px">✅</span>
              <div>
                <div style="font-weight:600">Task Routed to ${agentIcons[agent] || ''} ${agent}</div>
                <div class="text-muted text-sm">${data.message} • Target: <code>${repo}</code></div>
              </div>
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn btn-gradient btn-sm" onclick="routeTask(true)">⚡ Run Now with ${agent}</button>
              <button class="btn btn-ghost btn-sm" onclick="window.location.hash='#/chat'">💬 Open Chat</button>
            </div>
          </div>
        </div>
      `;
    }
  } catch (err) {
    showToast('Execution failed: ' + err.message, 'error');
    if (result) {
      result.innerHTML = `
        <div class="card" style="margin-top:8px;border-color:var(--red)">
          <div style="color:var(--red);font-weight:600">⚠ Error executing task</div>
          <div class="text-muted text-sm" style="margin-top:4px">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
  } finally {
    if (executeBtn) {
      executeBtn.disabled = false;
      executeBtn.textContent = '⚡ Route & Execute';
    }
  }
}

