// 共用前端函式：用來與後端 API 溝通並渲染基本 UI
async function getJSON(url){
  const res = await fetch(url, {credentials: 'same-origin'});
  return await res.json();
}

async function postJSON(url, data){
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data),
    credentials: 'same-origin'
  });
  return await res.json();
}

async function patchJSON(url, data){
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data),
    credentials: 'same-origin'
  });
  // Try parse JSON, otherwise return text for better error visibility
  let parsed = null;
  let text = null;
  try{
    parsed = await res.json();
  }catch(e){
    try{
      text = await res.text();
    }catch(e2){
      text = null;
    }
  }
  return {status: res.status, ok: parsed && parsed.ok ? parsed.ok : false, json: parsed, text: text};
}

// ======= Device: render & toggle =======
async function renderDeviceList(){
  const container = document.getElementById('device-list');
  if(!container) return;
  container.textContent = '載入中...';

  try{
    // get auto control config to determine whether AC toggles should be disabled
    let autoCfg = {};
    try{ autoCfg = await getAutoConfig() || {}; }catch(e){ autoCfg = {}; }
    const autoEnabled = !!autoCfg.monitor_enabled;

    const data = await getJSON('/device/list');
    console.log('device list response:', data);
    if(!data || !data.ok){
      const msg = data && data.msg ? data.msg : '取得設備失敗';
      container.textContent = '取得設備失敗: ' + msg;
      return;
    }

    const devices = data.devices || [];
    if(devices.length === 0){
      container.innerHTML = '<p>目前沒有設備。</p>';
      return;
    }

    let html = '<table class="device-table" style="width:100%;border-collapse:collapse">';
    html += '<tr><th>名稱</th><th>類型</th><th>位置</th><th>狀態</th><th>操作</th></tr>';
    for(const d of devices){
      const isOn = d.status && d.status.is_on;
      html += `<tr style="border-top:1px solid #eee"><td>${d.device_name}</td><td>${d.device_type}</td><td>${d.location||''}</td><td>${isOn? '開' : '關'}</td>`;
      // 使用 device_id 作為操作識別，避免以名稱為鍵造成的編碼問題
      // 若自動控制開啟，且為冷氣，則禁用操作按鈕（灰色）
      let toggleAttrs = `data-id="${d.device_id}" data-name="${encodeURIComponent(d.device_name)}" data-on="${!isOn}" onclick="toggleDevice(this)"`;
      let toggleDisabled = '';
      let toggleStyle = '';
      if(autoEnabled && d.device_type === 'air_conditioner'){
        toggleDisabled = 'disabled';
        toggleStyle = 'style="opacity:0.5;cursor:not-allowed"';
        // remove onclick to prevent accidental clicks
        toggleAttrs = `data-id="${d.device_id}" data-name="${encodeURIComponent(d.device_name)}" data-on="${!isOn}"`;
      }
      html += `<td><button ${toggleAttrs} ${toggleDisabled} ${toggleStyle}>${isOn? '關閉' : '開啟'}</button> <button data-id="${d.device_id}" data-name="${encodeURIComponent(d.device_name)}" onclick="deleteDevice(this)" style="margin-left:8px">刪除</button></td></tr>`;
    }
    html += '</table>';
    container.innerHTML = html;
  }catch(e){
    container.textContent = '錯誤: '+e;
  }
}

// 刪除裝置（帶確認）
// delete flow: show custom modal, then perform delete on confirm
let __pendingDelete = null; // {id, name, row}

async function deleteDevice(btn){
  const id = btn.dataset.id ? parseInt(btn.dataset.id) : null;
  if(!id) return showAlert('找不到裝置 ID');
  const name = btn.dataset.name ? decodeURIComponent(btn.dataset.name) : id;
  const row = btn.closest('tr');
  __pendingDelete = {id, name, row};
  showDeleteModal(name);
}

function showDeleteModal(name){
  const modal = document.getElementById('delete-modal');
  if(!modal) return confirmFallback(name);
  const label = modal.querySelector('.delete-modal-label');
  if(label) label.textContent = `確定要刪除裝置：${name}？`;
  // display as flex so the overlay centers the inner dialog
  modal.style.display = 'flex';
}

function hideDeleteModal(){
  const modal = document.getElementById('delete-modal');
  if(modal) modal.style.display = 'none';
  __pendingDelete = null;
}

async function confirmDelete(){
  if(!__pendingDelete) return hideDeleteModal();
  const {id, name, row} = __pendingDelete;
  const btn = document.querySelector(`#delete-btn-${id}`);
  // disable any visual indicator if present
  try{
    const res = await fetch(`/device/remove/${id}`, {method: 'DELETE', credentials: 'same-origin'});
    let json = null;
    try{ json = await res.json(); }catch(e){ json = null; }
    if(res.ok && json && json.ok){
      if(row) row.remove();
      const msg = document.getElementById('device-msg');
      if(msg) msg.textContent = `已刪除裝置 ${name}`;
      hideDeleteModal();
      return;
    } else {
      const err = json && json.msg ? json.msg : `HTTP ${res.status}`;
      showAlert('刪除失敗: ' + err);
    }
  }catch(e){
    showAlert('Network error: ' + e);
  }finally{
    hideDeleteModal();
  }
}

function confirmFallback(name){
  if(confirm(`確定要刪除裝置：${name}？`)){
    // fallback to previous behavior (shouldn't happen normally)
  }
}

// small alert area fallback (non-blocking)
function showAlert(msg){
  const el = document.getElementById('device-msg');
  if(el){ el.textContent = msg; }
  else alert(msg);
}

async function toggleDevice(btn){
  const id = btn.dataset.id ? parseInt(btn.dataset.id) : null;
  const name = btn.dataset.name ? decodeURIComponent(btn.dataset.name) : null;
  const on = btn.dataset.on === 'true';
  btn.disabled = true;
  try{
    // 優先使用 device_id
    const payload = id ? {device_id: id, on} : {name, on};
    const res = await patchJSON('/device/toggle', payload);
    console.log('toggle response:', res);
    if(res && res.ok){
      // Try to update the UI in-place using returned toggled info
      if(res.json && res.json.toggled){
        const t = res.json.toggled;
        // find the row that contains this button
        const row = btn.closest('tr');
        if(row){
          // update status cell (4th column)
          const statusCell = row.children[3];
          if(statusCell) statusCell.textContent = t.is_on ? '開' : '關';
          // update button label and data-on
          btn.textContent = t.is_on ? '關閉' : '開啟';
          btn.dataset.on = (!t.is_on).toString();
        }
      } else {
        // fallback: full re-render
        await renderDeviceList();
      }
    } else {
      // Build a helpful error message including HTTP status and body
      let errMsg = '';
      if(res){
        errMsg += `HTTP ${res.status} `;
        if(res.json && res.json.msg) errMsg += res.json.msg;
        else if(res.text) errMsg += res.text;
        else errMsg += JSON.stringify(res.json || res);
      } else {
        errMsg = 'No response from server';
      }
      alert('操作失敗: ' + errMsg);
    }
  }catch(e){
    alert('Network error: ' + e);
  } finally {
    btn.disabled = false;
  }
}

// ======= Usage: daily =======
async function renderUsageDaily(start_date, end_date){
  const container = document.getElementById('usage-results');
  if(!container) return;
  container.textContent = '載入中...';
  try{
    const q = `/usage/daily?start_date=${start_date}&end_date=${end_date}`;
    const data = await getJSON(q);
    if(!data || Object.keys(data).length===0){
      container.innerHTML = '<p>無資料</p>';
      return;
    }

    let html = '';
    const keys = Object.keys(data).sort();
    for(const day of keys){
      const d = data[day];
      html += `<div style="border:1px solid #eee;padding:8px;margin:6px 0"><strong>${day}</strong>：用電 ${d.kwh} kWh，共計 ${d.cost_sum} 元`;
      if(d.devices && d.devices.length){
        html += '<ul>';
        for(const it of d.devices){ html += `<li>${it.device_name}：${it.kwh} kWh / ${it.cost} 元</li>` }
        html += '</ul>';
      }
      html += '</div>';
    }
    container.innerHTML = html;
    // 同時載入原始 logs
    renderRawUsage(start_date, end_date);
  }catch(e){
    container.textContent = '錯誤: '+e;
  }
}

async function getRawUsage(start_date, end_date){
  const q = `/usage/logs?start_date=${start_date}&end_date=${end_date}`;
  return await getJSON(q);
}

async function renderRawUsage(start_date, end_date){
  const container = document.getElementById('usage-raw');
  if(!container) return;
  container.innerHTML = '';
  return;
  // 原始 Power Logs 功能已移除
}

// ======= Auto: decide / check / monitor / config =======
async function decideTemp(t){
  const url = `/auto/decide?temp=${encodeURIComponent(t)}`;
  return await getJSON(url);
}

async function checkAuto(){
  return await getJSON('/auto/check');
}

async function startMonitor(interval){
  const body = interval ? {interval} : {};
  return await postJSON('/auto/monitor/start', body);
}

async function stopMonitor(){
  return await postJSON('/auto/monitor/stop', {});
}

async function monitorStatus(){
  return await getJSON('/auto/monitor/status');
}

async function getAutoConfig(){
  return await getJSON('/auto/config');
}

async function updateAutoConfig(cfg){
  return await postJSON('/auto/config', cfg);
}

// ======= POST helpers: add device / add usage =======
async function addDevice(payload){
  try{
    const res = await postJSON('/device/add', payload);
    return res;
  }catch(e){
    return {ok:false, msg: String(e)};
  }
}

async function addUsage(payload){
  try{
    const res = await postJSON('/usage/add', payload);
    return res;
  }catch(e){
    return {ok:false, msg: String(e)};
  }
}

// expose some functions for inline onclick handlers
window.renderDeviceList = renderDeviceList;
window.toggleDevice = toggleDevice;
window.renderUsageDaily = renderUsageDaily;
window.decideTemp = decideTemp;
window.checkAuto = checkAuto;
window.startMonitor = startMonitor;
window.stopMonitor = stopMonitor;
window.monitorStatus = monitorStatus;
window.getAutoConfig = getAutoConfig;
window.updateAutoConfig = updateAutoConfig;
window.addDevice = addDevice;
window.addUsage = addUsage;
