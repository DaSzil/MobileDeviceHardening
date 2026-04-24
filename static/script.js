let allResults = [];
let activeFilter = 'ALL';
let pollInterval = null;

// Initial UI
document.getElementById('device-info').style.display = 'none';
document.getElementById('score-section').style.display = 'none';
document.getElementById('results-section').style.display = 'none';

async function runBulkRemediation() {
  const selectedCheckboxes = document.querySelectorAll('.remediation-checkbox:checked');
  if (selectedCheckboxes.length === 0){
    showToast("Please select at least one rule in order to modify it.");
    return;
  }
  const selectedFixes = selectedCheckboxes.length;
  const confirmed = await showModal(`Modify ${selectedFixes} selected settings?`);
  if (!confirmed)
    return;

  document.getElementById('fix-btn').disabled = true;
  document.getElementById('status').textContent = "Executing selected fixes...";

  for (const cb of selectedCheckboxes){
    const ruleId = cb.getAttribute('data-id');
    try{
        await fetch('/api/remediate', {
            method: 'POST',
            headers: {'Content-Type' : 'application/json'},
            body: JSON.stringify({ id: ruleId })
        });
        console.log(`Succesfully modified rule ${ruleId}`);
    } catch (err){
        console.error(`Error: Can\'t apply fix for ${ruleId}`);
    }
  }
  showToast("Selected modifications applied. Verifying...");
  setTimeout(() => {
    runAudit()
  }, 1000);
}


function toggleAll(masterCheckbox) {
    const checkboxes = document.querySelectorAll('.remediation-checkbox');
    checkboxes.forEach(cb => {
        if (!cb.disabled){
            cb.checked = masterCheckbox.checked;
            updateSelection(cb.getAttribute('data-id'), masterCheckbox.checked)
        }
    });
}



function runAudit() {
    document.getElementById('run-btn').disabled = true;
    document.getElementById('status').textContent = 'Running audit...';

    fetch('/api/reset', { method: 'POST' })
        .then(() => fetch('/api/run', { method: 'POST' }))
        .then(() => {
            pollInterval = setInterval(pollStatus, 1000);
        })
        .catch(() => {
            document.getElementById('status').textContent = 'Error: could not start audit.';
            document.getElementById('run-btn').disabled = false;
        });
}

function pollStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'done') {
                clearInterval(pollInterval);
                document.getElementById('run-btn').disabled = false;
                document.getElementById('fix-btn').disabled = false;
                document.getElementById('status').textContent = 'Audit complete.';
                renderDevice(data.device);
                renderScore(data.score);
                allResults = data.results || [];
                renderResults(allResults);
                document.getElementById('select-all-checkbox').checked = false;
                document.getElementById('device-info').style.display = 'block';
                document.getElementById('score-section').style.display = 'block';
                document.getElementById('results-section').style.display = 'block';
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                document.getElementById('run-btn').disabled = false;
                document.getElementById('status').textContent = 'Error: Check terminal for details.';
            }
        });
}

function renderDevice(d) {
    if (!d) return;

    document.getElementById('d-manufacturer').textContent = d.manufacturer || '—';
    document.getElementById('d-model').textContent        = d.model        || '—';
    document.getElementById('d-android').textContent      = d.android      || '—';
    document.getElementById('d-patch').textContent        = d.patch        || '—';
    document.getElementById('d-serial').textContent       = d.serial       || '—';
    document.getElementById('d-platform').textContent     = d.platform     || '—';

    // Change "Android Version" label dynamically based on platform
    document.getElementById('label-os').textContent =
        d.platform === 'iOS' ? 'iOS Version' : 'Android Version';

    // Hide security patch for iOS since it's N/A
    document.getElementById('patch-field').style.display =
        d.platform === 'iOS' ? 'none' : 'block';
}

function renderScore(score) {
    if (score === null || score === undefined) return;
    document.getElementById('score-text').textContent = score + '%';
    document.getElementById('score-bar').style.width = score + '%';
}

function setFilter(f) {
    activeFilter = f;
    renderResults(allResults);
}

function renderResults(results) {
    const filtered = activeFilter === 'ALL'
        ? results
        : results.filter(r => r.status === activeFilter);

    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';

    filtered.forEach((r, i) => {
        let cls = 'manual';
        if (r.status === 'PASS') cls = 'pass';
        else if (r.status === 'FAIL') cls = 'fail';
        else if (r.status === 'N/A') cls = 'na';

        // Checkbox logic
        let checkboxHtml = "";
        if (r.fixable && r.status === "FAIL") {
            const isChecked = r.selected ? 'checked' : '';
            checkboxHtml = `<input type="checkbox"
                                   class="remediation-checkbox"
                                   data-id="${r.id}"
                                   ${isChecked}
                                   onclick="event.stopPropagation()">`;
        } else {
            checkboxHtml = `<input type="checkbox" disabled>`;
        }

        const tr = document.createElement('tr');
        tr.className = 'fade-in result-row';
        tr.style.animationDelay = (i * 40) + 'ms';
        tr.style.cursor = 'pointer';

        tr.innerHTML = `
        <td>${checkboxHtml}</td>
        <td><strong>${r.id}</strong></td>
        <td>${r.title || ''} <span class="expand-arrow">▸</span></td>
        <td class="${cls}">${r.status}</td>
        <td><div class="truncate" title="${r.found}">${r.found}</div></td>
        <td>${r.fixable ? '<span class="badge-fix">Fixable</span>' : '<span class="badge-manual">Manual</span>'}</td> `;

        const dr = document.createElement('tr');
        dr.className = 'detail-row';
        dr.style.display = 'none';
        dr.innerHTML = `
            <td colspan="6">
                <div class="detail-box">
                    <div class="detail-line"><span class="detail-label">Description</span><span>${r.description || ''}</span></div>
                    <div class="detail-line"><span class="detail-label">Rationale</span><span>${r.rationale || ''}</span></div>
                    <div class="detail-line"><span class="detail-label">Desired Value</span><span>${r.desired || '-'}</span></div>
                </div>
            </td>`;

        tr.addEventListener('click', () => {
            const isOpen = dr.style.display !== 'none';
            dr.style.display = isOpen ? 'none' : 'table-row';
            tr.querySelector('.expand-arrow').textContent = isOpen ? '▸' : '▾';
        });

        tbody.appendChild(tr);
        tbody.appendChild(dr);
        const childCb = tr.querySelector('.remediation-checkbox');
        if (childCb) {
            childCb.addEventListener('change', (e) => {
                // 1. Save the state to the data array
                updateSelection(r.id, e.target.checked);

                // 2. Update the Master Checkbox state
                const masterCb = document.getElementById('select-all-checkbox');
                if (masterCb) {
                    // Count how many are currently checked in the data array
                    const totalFixable = allResults.filter(rule => rule.fixable && rule.status === "FAIL").length;
                    const selectedCount = allResults.filter(rule => rule.selected).length;

                    // Scenario: Deselected all manually
                    if (selectedCount === 0) {
                        masterCb.checked = false;
                        masterCb.indeterminate = false;
                    }
                    // Scenario: Selected all manually
                    else if (selectedCount === totalFixable) {
                        masterCb.checked = true;
                        masterCb.indeterminate = false;
                    }
                    // Scenario: "1 or more" but not all (Optional: use indeterminate dash)
                    else {
                        masterCb.checked = true; // Your specific request: 1 or more = checked
                        // masterCb.indeterminate = true; // Use this instead if you want a dash (-)
                    }
                }
            });
        }
    });
}


function checkConnection() {
    if (document.getElementById('status').textContent === 'Running audit...') return;
    fetch('/api/ping_device')
        .then(r => r.json())
        .then(data => {
            const light = document.getElementById('conn-light');
            const text = document.getElementById('conn-text');
            const runBtn = document.getElementById('run-btn');
            if (data.connected) {
                light.className = 'indicator-light light-green';
                text.textContent = 'Device Connected & Ready';
                runBtn.disabled = false;
            } else {
                light.className = 'indicator-light light-red';
                text.textContent = 'No Device Detected';
                runBtn.disabled = true;
            }
        });
}

// Custom Notifications
function showToast(message) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function showModal(message) {
    return new Promise((resolve) => {
        document.getElementById('modal-message').innerHTML = message;
        document.getElementById('custom-modal').style.display = 'flex';  // must be flex, not block
        document.getElementById('modal-confirm').onclick = () => {
            closeModal();
            resolve(true);
        };
    });
}

function closeModal() {
    document.getElementById('custom-modal').style.display = 'none';
}


function updateSelection(id, isChecked) {
    // Find the rule in our main data array and update its 'selected' property
    const rule = allResults.find(r => r.id === id);
    if (rule) {
        rule.selected = isChecked;
    }
}

// Start polling
checkConnection();
setInterval(checkConnection, 2000);