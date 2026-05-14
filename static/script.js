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

  document.getElementById('fix-btn').disabled = data.device?.platform === 'iOS';
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
    profileRules = [];
    document.getElementById('run-btn').disabled = true;
    document.getElementById('status').textContent = 'Running audit...';
    document.getElementById('loading-overlay').style.display = 'flex';
    document.getElementById('loading-text').textContent = 'Loading...';


    fetch('/api/reset', { method: 'POST' })
        .then(() => fetch('/api/run', { method: 'POST' }))
        .then(() => {
            pollInterval = setInterval(pollStatus, 1000);
        })
        .catch(() => {
            document.getElementById('status').textContent = 'Error: could not start audit.';
            document.getElementById('run-btn').disabled = false;
            document.getElementById('loading-overlay').style.display = 'none';
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
                document.getElementById('loading-overlay').style.display = 'none'
                document.getElementById('run-btn').disabled = false;
                document.getElementById('fix-btn').disabled = false;
                document.getElementById('status').textContent = 'Audit complete.';
                renderDevice(data.device);
                const iosBtn = document.getElementById('ios-profile-btn');
                if (iosBtn) iosBtn.disabled = data.device?.platform !== 'iOS';
                renderScore(data.score);
                allResults = data.results || [];
                renderResults(allResults);
                document.getElementById('select-all-checkbox').checked = false;
                document.getElementById('device-info').style.display = 'block';
                document.getElementById('score-section').style.display = 'block';
                document.getElementById('results-section').style.display = 'block';
                if (data.platform === 'ios') {
                    document.getElementById('run-btn').textContent   = 'View Recommendations';
                    document.getElementById('fix-btn').style.display = 'none';
                    document.getElementById('ios-profile-btn').style.display = 'inline-block';
                }
                else {
                    document.getElementById('run-btn').textContent   = 'Run Audit';
                    document.getElementById('fix-btn').disabled      = false;
                    document.getElementById('fix-btn').style.display = 'inline-block';
                    document.getElementById('ios-profile-btn').style.display = 'none';
                }
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                document.getElementById('loading-overlay').style.display = 'none';
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

            if (data.connected) {
                light.className  = 'indicator-light light-green';
                runBtn.disabled  = false;

                if (data.platform === 'ios') {
                    text.textContent     = 'iOS Device Connected & Ready';
                    runBtn.textContent   = 'View Recommendations';
                    fixBtn.style.display = 'none';
                    iosBtn.style.display = 'inline-block';
                } else {
                    text.textContent     = 'Android Device Connected & Ready';
                    runBtn.textContent   = 'Run Audit';
                    fixBtn.style.display = 'inline-block';
                    iosBtn.style.display = 'none';
                }

            } else {
                light.className      = 'indicator-light light-red';
                text.textContent     = 'No Device Detected';
                runBtn.disabled      = true;
                runBtn.textContent   = 'Run Audit';
                fixBtn.style.display = 'inline-block';
                iosBtn.style.display = 'none';
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

    showToast(`Generating profile with ${selected.length} rules...`);

    fetch('/api/ios/generate_profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected, institutional: false })
    })
    .then(r => r.blob())
    .then(blob => {
        // Trigger download
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = 'cis_hardening.mobileconfig';
        a.click();
        URL.revokeObjectURL(url);
        closeProfileModal();
        showToast("Profile downloaded. Install via Settings → VPN & Device Management.");
    })
    .catch(() => showToast("Error generating profile."));
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
