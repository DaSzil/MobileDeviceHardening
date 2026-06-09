let allResults = [];
let activeFilter = 'ALL';
let pollInterval = null;
let deviceRegistry = new Map();
let activeDeviceSerial = null;


// Loading
function showLoading() {
  const el = document.getElementById('loading-overlay');
  el.style.display = 'flex';
  void el.offsetWidth;
  el.classList.add('visible');
}

function hideLoading() {
  const el = document.getElementById('loading-overlay');
  el.classList.remove('visible');
  setTimeout(() => { el.style.display = 'none'; }, 300);
}


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
            body: JSON.stringify({ id: ruleId, serial: activeDeviceSerial })
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

const tooltip = document.createElement('div');
tooltip.className = 'tooltip-box';
tooltip.id = 'global-tooltip';
document.body.appendChild(tooltip);

function showTooltip(e, steps) {
    if (!steps || steps.length === 0) return;

    tooltip.innerHTML = `
        <div class="tooltip-title">How to fix</div>
        <ol>${steps.map(s => `<li>${s}</li>`).join('')}</ol>
    `;
    tooltip.style.display = 'block';
    positionTooltip(e);
}

function positionTooltip(e) {
    const padding  = 14;
    const boxWidth = 280;

    let x = e.clientX + padding;
    let y = e.clientY + padding;

    // Flip left if tooltip would overflow right edge
    if (x + boxWidth > window.innerWidth - padding) {
        x = e.clientX - boxWidth - padding;
    }

    // Flip up if tooltip would overflow bottom edge
    const boxHeight = tooltip.offsetHeight;
    if (y + boxHeight > window.innerHeight - padding) {
        y = e.clientY - boxHeight - padding;
    }

    tooltip.style.left = x + 'px';
    tooltip.style.top  = y + 'px';
}

function hideTooltip() {
    tooltip.style.display = 'none';
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
    if (!activeDeviceSerial) {
        showToast("No active device selected.");
        return;
    }

    const activeDev = deviceRegistry.get(activeDeviceSerial);

    profileRules = [];
    document.getElementById('run-btn').disabled = true;
    document.getElementById('status').textContent = 'Running audit...';
    showLoading();
    document.getElementById('loading-text').textContent = 'Loading...';

    const payload = JSON.stringify({
        serial: activeDeviceSerial,
        platform: activeDev.platform
    });

    fetch('/api/reset', { method: 'POST' })
        .then(() => fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                serial:   activeDeviceSerial,
                platform: activeDev.platform
            })
        }))
        .then(() => {
            pollInterval = setInterval(pollStatus, 1000);
        })
        .catch(() => {
            document.getElementById('status').textContent = 'Error: could not start audit.';
            document.getElementById('run-btn').disabled = false;
            hideLoading();
        });
}

function pollStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'awaiting-trust') {
                document.getElementById('loading-text').textContent =
                    'Accept the Trust dialog on your iPhone, then enter your passcode...';
                return;
            }

            if (data.status === 'done') {
                clearInterval(pollInterval);
                hideLoading();
                document.getElementById('run-btn').disabled = false;
                document.getElementById('fix-btn').disabled = false;
                document.getElementById('status').textContent = 'Audit complete.';

                const revealEl = (id, delay = 0) => {
                    const el = document.getElementById(id);
                    el.style.display = 'block';
                    el.classList.remove('reveal');
                    void el.offsetWidth;
                    el.style.animationDelay = delay + 'ms';
                    el.classList.add('reveal');
                };

                revealEl('device-info', 440);
                revealEl('score-section', 500);
                revealEl('results-section', 560);

                // Stagger each device-field inside device-info
                document.querySelectorAll('.device-field').forEach((el, i) => {
                  el.classList.remove('reveal');
                  void el.offsetWidth;
                  el.classList.add('reveal');
                  el.style.animationDelay = (i * 60) + 'ms';
                });

                // Results heading
                const resultsHeading = document.querySelector('#results-section h1');
                if (resultsHeading) {
                  resultsHeading.classList.remove('reveal');
                  void resultsHeading.offsetWidth;
                  resultsHeading.classList.add('reveal');
                }

                // Store results on the device entry
                if (activeDeviceSerial && deviceRegistry.has(activeDeviceSerial)) {
                    const dev    = deviceRegistry.get(activeDeviceSerial);
                    dev.score    = data.score;
                    dev.results  = data.results || [];
                    dev.device   = data.device  || {};
                    dev.platform = data.platform || dev.platform;
                }

                allResults = data.results || [];
                renderDevice(data.device);
                renderScore(data.score);
                renderResults(allResults);
                renderDeviceTabs();

                document.getElementById('select-all-checkbox').checked = false;
                document.getElementById('device-info').style.display = 'block';
                document.getElementById('score-section').style.display = 'block';
                document.getElementById('results-section').style.display = 'block';

                if (data.platform === 'ios') {
                    document.getElementById('run-btn').textContent = 'View Recommendations';
                    document.getElementById('fix-btn').style.display = 'none';
                    document.getElementById('ios-profile-btn').style.display = 'inline-block';
                    document.getElementById('ios-profile-btn').disabled = false;
                } else {
                    document.getElementById('run-btn').textContent = 'Run Audit';
                    document.getElementById('fix-btn').disabled = false;
                    document.getElementById('fix-btn').style.display = 'inline-block';
                    document.getElementById('ios-profile-btn').style.display = 'none';
                }

            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                hideLoading();
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

    document.getElementById('label-os').textContent =
        d.platform === 'iOS' ? 'iOS Version' : 'Android Version';

    document.getElementById('patch-field').style.display =
        d.platform === 'iOS' ? 'none' : 'flex';


}

function renderScore(score) {
    if (score === null || score === undefined) return;
    const num = parseInt(score);
    document.getElementById('score-text').textContent = score + '%';
    document.getElementById('score-bar').style.width  = score + '%';

    const color = num >= 80 ? '#69db7c' : num >= 50 ? '#ffa94d' : '#ff6b6b';
    document.getElementById('score-bar').style.background = color;
}


// Debouncer
let searchDebounceTimer = null;

document.getElementById('search-input').addEventListener('input', () => {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(applyFilters, 450);
});

function applyFilters() {
  const search = document.getElementById('search-input').value.toLowerCase();
  const filter = document.getElementById('filter-select').value;
  const sort   = document.getElementById('sort-select').value;

  let results = [...allResults];

  // Filter by status
  if (filter !== 'ALL' && filter !== '') results = results.filter(r => r.status === filter);

  // Search by title or ID
  if (search) results = results.filter(r =>
    r.title?.toLowerCase().includes(search) || r.id?.toLowerCase().includes(search)
  );

  // Sort
  if (sort === 'FAIL_FIRST')   results.sort((a, b) => (a.status === 'FAIL'   ? -1 : 1));
  if (sort === 'PASS_FIRST')   results.sort((a, b) => (a.status === 'PASS'   ? -1 : 1));
  if (sort === 'MANUAL_FIRST') results.sort((a, b) => (a.status === 'MANUAL' ? -1 : 1));

  renderResults(results);
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
        <td>${r.level ? `<span class="level-badge level-${r.level}">L${r.level}</span>` : '—'}</td>
        <td>${r.title || ''} <span class="expand-arrow">▸</span></td>
        <td class="${cls}">${r.status}</td>
        <td><div class="truncate" title="${r.found}">${r.found}</div></td>
        <td>${r.fixable ? '<span class="badge-fix">Fixable</span>' : '<span class="badge-manual">Manual</span>'}</td>`;


        const dr = document.createElement('tr');
        dr.className = 'detail-row';
        dr.style.display = 'none';
        dr.innerHTML = `
            <td colspan="7">
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

        // Attach tooltip to status cell for MANUAL rows
        if (r.status === 'MANUAL' && r.steps && r.steps.length > 0) {
            const statusCell = tr.querySelectorAll('td')[3]; // 4th td = Status column
            statusCell.style.cursor = 'help';
            statusCell.style.textDecoration = 'underline dotted';

            statusCell.addEventListener('mouseenter', (e) => showTooltip(e, r.steps));
            statusCell.addEventListener('mousemove',  (e) => positionTooltip(e));
            statusCell.addEventListener('mouseleave', hideTooltip);
        }

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
            const light      = document.getElementById('conn-light');
            const text       = document.getElementById('conn-text');
            const runBtn     = document.getElementById('run-btn');
            const fixBtn     = document.getElementById('fix-btn');
            const iosBtn     = document.getElementById('ios-profile-btn');

            const liveDevices = data.devices || [];
            const connectedSerials = new Set();

            if (liveDevices.length > 0) {
                light.className  = 'indicator-light light-green';
                text.textContent = `${liveDevices.length} Device(s) Connected`;
                runBtn.disabled  = false;

                liveDevices.forEach(d => {
                    connectedSerials.add(d.serial);
                    if (!deviceRegistry.has(d.serial)) {
                        deviceRegistry.set(d.serial, {
                            platform: d.platform,
                            serial: d.serial,
                            name: d.name || d.serial,
                            score: null
                        });
                    }
                    else{
                        deviceRegistry.get(d.serial).name = d.name || d.serial;
                    }
                });

                if (!activeDeviceSerial || !connectedSerials.has(activeDeviceSerial)) {
                    activeDeviceSerial = liveDevices[0].serial;
                }

                const activeDev = deviceRegistry.get(activeDeviceSerial);
                if (activeDev && activeDev.platform === 'ios') {
                    runBtn.textContent   = 'View Recommendations';
                    fixBtn.style.display = 'none';
                    iosBtn.style.display = 'inline-block';
                    iosBtn.disabled = false
                } else {
                    runBtn.textContent   = 'Run Audit';
                    fixBtn.style.display = 'inline-block';
                    iosBtn.style.display = 'none';
                }

            } else {
                light.className      = 'indicator-light light-red';
                text.textContent     = 'No Device Connected';
                runBtn.disabled      = true;
                runBtn.textContent   = 'Run Audit';
                fixBtn.style.display = 'inline-block';
                iosBtn.style.display = 'none';
                activeDeviceSerial   = null;
            }

            for (const serial of deviceRegistry.keys()) {
                if (!connectedSerials.has(serial)) {
                    deviceRegistry.delete(serial);
                }
            }

            renderDeviceTabs();
        })
        .catch(err => console.error("Connection polling error:", err));
}

function renderDeviceTabs() {
    const tabsContainer = document.getElementById('device-tabs');
    if (!tabsContainer) return;

    tabsContainer.innerHTML = '';

    if (deviceRegistry.size === 0) {
        tabsContainer.innerHTML = '<div class="no-devices-msg">No devices connected or audited.</div>';
        return;
    }

    deviceRegistry.forEach((dev, serial) => {
        const tab = document.createElement('div');
        const isActive = serial === activeDeviceSerial ? 'active' : '';
        tab.className = `device-tab ${isActive}`;

        let statusClass = 'running';
        let statusText  = 'Pending Audit';

        if (dev.score !== undefined && dev.score !== null) {
            statusClass = dev.score >= 75 ? 'done-pass' : 'done-fail';
            statusText  = `Score: ${dev.score}%`;
        }

        tab.innerHTML = `
            <div class="tab-platform">${dev.platform || 'Unknown OS'}</div>
            <div class="tab-serial">${dev.name || 'Unknown Device'}</div>
            <div class="tab-status ${statusClass}">${statusText}</div>
        `;

        tab.addEventListener('click', () => {
            activeDeviceSerial = serial;

            const dev = deviceRegistry.get(serial);
            if (dev && dev.results) {
                allResults = dev.results;
                renderDevice(dev.device || {});
                renderScore(dev.score);
                renderResults(allResults);
                document.getElementById('device-info').style.display     = 'block';
                document.getElementById('score-section').style.display   = 'block';
                document.getElementById('results-section').style.display = 'block';

                const runBtn = document.getElementById('run-btn');
                const fixBtn = document.getElementById('fix-btn');
                const iosBtn = document.getElementById('ios-profile-btn');
                if (dev.platform === 'ios') {
                    runBtn.textContent   = 'View Recommendations';
                    fixBtn.style.display = 'none';
                    iosBtn.style.display = 'inline-block';
                } else {
                    runBtn.textContent   = 'Run Audit';
                    fixBtn.style.display = 'inline-block';
                    iosBtn.style.display = 'none';
                }
            } else {
                document.getElementById('status').textContent           = 'Device selected. Press Run Audit to begin.';
                document.getElementById('device-info').style.display    = 'none';
                document.getElementById('score-section').style.display  = 'none';
                document.getElementById('results-section').style.display = 'none';
            }

            renderDeviceTabs();
        });

        tabsContainer.appendChild(tab);
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

let profileRules = [];

function openProfileModal() {
    // Load rules from backend if not already loaded
    if (profileRules.length === 0) {
        fetch('/api/ios/profile_rules')
            .then(r => r.json())
            .then(rules => {
                profileRules = rules;
                renderProfileRules(rules);
            });
    } else {
        renderProfileRules(profileRules);
    }
    document.getElementById('ios-profile-modal').style.display = 'flex';
}

function closeProfileModal() {
    document.getElementById('ios-profile-modal').style.display = 'none';
}

function renderProfileRules(rules) {
    const container = document.getElementById('profile-rule-list');
    container.innerHTML = '';

    // Group rules by their group field
    const groups = {};
    rules.forEach(r => {
        if (!groups[r.group]) groups[r.group] = [];
        groups[r.group].push(r);
    });

    Object.entries(groups).forEach(([groupName, groupRules]) => {
        // Group header
        const header = document.createElement('div');
        header.style.cssText = `
            padding: 6px 12px;
            font-size: 0.72rem;
            font-weight: 600;
            color: #7a7f94;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: #23273a;
            margin-top: 4px;
        `;
        header.textContent = groupName;
        container.appendChild(header);

        // Rules in group
        groupRules.forEach(rule => {
            const row = document.createElement('label');
            row.style.cssText = `
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 7px 12px;
                font-size: 0.82rem;
                cursor: pointer;
                border-bottom: 1px solid #3d4460;
                color: #e0e2e8;
            `;
            row.innerHTML = `
                <input type="checkbox"
                       class="profile-rule-checkbox"
                       data-id="${rule.id}"
                       checked>
                <span style="color:#7a7f94; min-width:52px; font-size:0.75rem;">${rule.id}</span>
                <span>${rule.title}</span>
            `;
            row.addEventListener('mouseenter', () => row.style.background = '#2e3347');
            row.addEventListener('mouseleave', () => row.style.background = '');
            container.appendChild(row);
        });
    });

    // Sync select-all state
    document.getElementById('profile-select-all').checked = true;
}

function toggleAllProfileRules(masterCb) {
    document.querySelectorAll('.profile-rule-checkbox')
        .forEach(cb => cb.checked = masterCb.checked);
}

function downloadProfile() {
    const selected = [];
    document.querySelectorAll('.profile-rule-checkbox:checked')
        .forEach(cb => selected.push(cb.getAttribute('data-id')));

    if (selected.length === 0) {
        showToast("Please select at least one rule.");
        return;
    }
    const generateBtn = document.querySelector('#ios-profile-modal button[onclick="downloadProfile()"]');
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';

    fetch('/api/ios/generate_profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected, institutional: false })
    })
    .then(r => r.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cis_hardening.mobileconfig';
        a.click();
        URL.revokeObjectURL(url);

        // Push to device
        generateBtn.textContent = 'Pushing to device...';
        return fetch('/api/ios/push_profile', { method: 'POST' });
    })
    .then(r => r.json())
    .then(data => {
        showToast(data.message || "Profile pushed.");
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate & Download';
    })
    .catch(() => {
        showToast("Error generating or pushing profile.");
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate & Download';
    });
}


function updateSelection(id, isChecked) {
    // Find the rule in our main data array and update its 'selected' property
    const rule = allResults.find(r => r.id === id);
    if (rule) {
        rule.selected = isChecked;
    }
}

function openWirelessModal() {
  document.getElementById('wireless-modal').style.display = 'flex';
}

function closeWirelessModal() {
  document.getElementById('wireless-modal').style.display = 'none';
  document.getElementById('wp-status').textContent = '';
  document.getElementById('wp-ip').value   = '';
  document.getElementById('wp-port').value = '';
  document.getElementById('wp-connect-port').value = '';
  document.getElementById('wp-code').value = '';
}

function submitPairing() {
    const ip = document.getElementById('wp-ip').value.trim();
    const port = document.getElementById('wp-port').value.trim();
    const connectPort = document.getElementById('wp-connect-port').value.trim();
    const code = document.getElementById('wp-code').value.trim();
    const statusEl = document.getElementById('wp-status');

    if (!ip || !port || !code) {
        statusEl.className = 'status-msg error';
        statusEl.textContent = 'Please fill in all fields.';
        return;
    }

    statusEl.className = 'status-msg loading';
    statusEl.textContent = 'Pairing...';

    fetch('/api/android/wireless_pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip, pairing_port: port, connect_port: connectPort, pairing_code: code })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            statusEl.className = 'status-msg success';
            statusEl.textContent = 'Paired! Device will appear in the sidebar.';
            checkConnection();
            setTimeout(closeWirelessModal, 2000);
        } else {
            statusEl.className = 'status-msg error';
            statusEl.textContent = data.message || 'Pairing failed.';
        }
    })
    .catch(() => {
        statusEl.className = 'status-msg error';
        statusEl.textContent = 'Could not reach the server.';
    });
}


document.querySelectorAll('#wireless-modal input').forEach(input => {
    input.addEventListener('input', () => {
        // Allow dots for IP, digits only otherwise
        if (input.id === 'wp-ip') {
            input.value = input.value.replace(/[^0-9.]/g, '');
        } else {
            input.value = input.value.replace(/[^0-9]/g, '');
        }
    });
});

// Start polling
checkConnection();
setInterval(checkConnection, 2000);
