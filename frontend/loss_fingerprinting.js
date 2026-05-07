// ═══════════════════════════════════════
    // DATA
    // ═══════════════════════════════════════
    const FINGERPRINT_META = {
      'Ghost Load': { type:'Ghost Load', bc:'bg-ghost', icon:'🌙', chart:'ghost', 
        desc:'Commercial machinery operating exclusively during nighttime hours via unmetered connection.', 
        action:'Night inspection between 10 PM and 2 AM. Check for heavy commercial equipment running off-hours. Bring load testing kit.',
        form:'FORM 47B — Commercial Fraud Notice' },
      'Phase Bypass': { type:'Phase Bypass', bc:'bg-phase', icon:'⚡', chart:'phase',
        desc:'One of three electrical phases tapped before meter entry. Consumption has dropped to exactly 66% of baseline and remains there consistently.',
        action:'Inspect LT line connections before meter entry point. Look for unauthorized tap. Bring phase tester and wire detection device.',
        form:'FORM 47B — Electricity Theft Notice' },
      'Billing Freeze': { type:'Billing Freeze', bc:'bg-freeze', icon:'🔒', chart:'freeze',
        desc:'Cumulative meter reading shows identical value across consecutive billing cycles.',
        action:'Verify meter display is active and advancing. Check if meter reader submitted manual readings. Bring replacement meter unit.',
        form:'Meter Replacement Order + Fraud Enquiry' },
      'Meter Tamper': { type:'Meter Tamper', bc:'bg-tamper', icon:'🔧', chart:'tamper',
        desc:'Unnaturally smooth consumption decline. Variance analysis indicates physical interference with meter measurement.',
        action:'Inspect meter body for magnets, external devices, and physical damage. Check seal integrity. Bring magnet detector kit.',
        form:'FORM 47B + Tamper Evidence Report' },
      'Slow Bleed': { type:'Slow Bleed', bc:'bg-bleed', icon:'📉', chart:'bleed',
        desc:'Consistently below peer group average for months. No billing defaults or lifestyle changes to explain the gap.',
        action:'Full physical line inspection from service pole to meter. Bring wire tracing equipment. Long-duration chronic theft suspected.',
        form:'FORM 47B — Chronic Theft Notice' }
    };

    const ZONE_COORDS = {
      'z1': {cx: 490, cy: 228},
      'z2': {cx: 520, cy: 162},
      'z3': {cx: 400, cy: 350},
      'z4': {cx: 543, cy: 295},
      'z5': {cx: 255, cy: 355},
      'z6': {cx: 255, cy: 138},
    };

    let M = [];

    const ZONES = ['KORAMANGALA', 'HSR LAYOUT', 'PEENYA', 'WHITEFIELD', 'JAYANAGAR',
      'ELECTRONIC CITY', 'MALLESHWARAM', 'INDIRANAGAR', 'RAJAJINAGAR', 'HEBBAL', 'BANASHANKARI'];

    // ═══════════════════════════════════════
    // LOADER
    // ═══════════════════════════════════════
    const loadSteps = [
      'Loading distribution network topology...',
      'Connecting to smart meter data stream...',
      'Initializing anomaly detection engine...',
      'Running fingerprint classifier (82.4% accuracy)...',
      'Generating zone risk heatmap...',
      'Platform ready — 47 alerts detected'
    ];

    let loadIdx = 0, loadPct = 0;
    const lBar = document.getElementById('lBar');
    const lStatus = document.getElementById('lStatus');

    function runLoader() {
      if (loadPct >= 100) {
        lStatus.textContent = loadSteps[5];
        lBar.style.width = '100%';
        setTimeout(() => {
          document.getElementById('loader').classList.add('hide');
          setTimeout(() => {
            document.getElementById('loader').style.display = 'none';
            // Auto-demo: pick first meter after 1.5s
            setTimeout(() => pick(0), 1500);
          }, 800);
        }, 600);
        return;
      }
      loadPct += Math.random() * 18 + 8;
      loadPct = Math.min(loadPct, 100);
      lBar.style.width = loadPct + '%';
      if (loadPct > loadIdx * 18 && loadIdx < loadSteps.length - 1) {
        lStatus.textContent = loadSteps[loadIdx];
        loadIdx++;
      }
      setTimeout(runLoader, 200 + Math.random() * 180);
    }
    setTimeout(runLoader, 800);

    // ═══════════════════════════════════════
    // BUILD ALERT LIST
    // ═══════════════════════════════════════
    function renderDots() {
      document.querySelectorAll('.mdot').forEach(el => el.remove());
      const svg = document.getElementById('svgMap');
      const selRing = document.getElementById('selRing');
      
      M.forEach((m, i) => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'mdot');
        g.setAttribute('id', 'md'+i);
        g.onclick = () => pick(i);
        
        let color = '#ff2d55';
        let rgba = 'rgba(255,45,85,.06)';
        if(m.type === 'Ghost Load') { color = '#00aaff'; rgba = 'rgba(0,170,255,.06)'; }
        if(m.type === 'Billing Freeze') { color = '#9b6bff'; rgba = 'rgba(155,107,255,.06)'; }
        if(m.type === 'Slow Bleed') { color = '#f0a020'; rgba = 'rgba(240,160,32,.06)'; }
        if(m.type === 'Meter Tamper') { color = '#ff6b35'; rgba = 'rgba(255,107,53,.06)'; }
        
        g.innerHTML = `
          <circle cx="${m.cx}" cy="${m.cy}" r="22" fill="${rgba}" class="pr1" style="animation-delay:${Math.random()*2}s"/>
          <circle cx="${m.cx}" cy="${m.cy}" r="14" fill="${rgba}" class="pr2" style="animation-delay:${Math.random()*2}s"/>
          <circle cx="${m.cx}" cy="${m.cy}" r="8" fill="${color}" opacity=".85" filter="url(#glow)"/>
          <circle cx="${m.cx}" cy="${m.cy}" r="3.5" fill="white"/>
        `;
        svg.insertBefore(g, selRing);
      });
    }

    function buildList() {
      const el = document.getElementById('alertList');
      el.innerHTML = '';
      M.forEach((m, i) => {
        const d = document.createElement('div');
        d.className = 'aitem';
        d.style.animationDelay = (i * .07) + 's';
        d.onclick = () => pick(i);
        d.innerHTML = `
      <div class="asev ${m.sev}"></div>
      <div class="ai">
        <div class="az">${m.zone.split(',')[0]}</div>
        <div class="at">${m.type} · ${m.id}</div>
      </div>
      <div class="ar">
        <div class="arl">₹${m.rev.toLocaleString()}</div>
        <div class="arc">${m.conf}% confidence</div>
      </div>`;
        el.appendChild(d);
      });
    }

    async function fetchMeters() {
      try {
        const res = await fetch('http://localhost:8000/api/fingerprints/meters');
        const data = await res.json();
        
        const flaggedEl = document.querySelector('.hs-v.r');
        if(flaggedEl) flaggedEl.textContent = data.total_flagged;
        
        M = data.meters.map(meter => {
          const meta = FINGERPRINT_META[meter.fingerprint_type] || FINGERPRINT_META['Ghost Load'];
          const coords = ZONE_COORDS[meter.zone_id] || {cx: 360, cy: 270};
          return {
            id: meter.meter_id,
            zone: meter.zone_name,
            type: meter.fingerprint_type,
            bc: meta.bc,
            icon: meta.icon,
            conf: Math.round(meter.confidence * 100),
            days: Math.floor(Math.random() * 30) + 5,
            rev: Math.floor(Math.random() * 5000) + 1000,
            sev: meter.confidence > 0.85 ? 'sc' : (meter.confidence > 0.75 ? 'sh' : 'sm'),
            desc: meta.desc,
            action: meta.action,
            form: meta.form,
            chart: meta.chart,
            peer: null,
            cx: coords.cx + (Math.random() * 40 - 20),
            cy: coords.cy + (Math.random() * 40 - 20)
          };
        });
        
        if (current === -1) {
          buildList();
          renderDots();
        }
      } catch (err) {
        console.error("Failed to fetch meters", err);
      }
    }
    
    fetchMeters();
    setInterval(fetchMeters, 5000);

    // ═══════════════════════════════════════
    // CHART DRAWING
    // ═══════════════════════════════════════
    const NS = 'http://www.w3.org/2000/svg';
    const W = 368, H = 110, PL = 34, PB = 22;

    function mkEl(tag, attrs) {
      const el = document.createElementNS(NS, tag);
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      return el;
    }

    function drawRealChart(actual, peer) {
      const svg = document.getElementById('cChart');
      svg.innerHTML = '';
      const aw = W - PL - 6, ah = H - PB - 8;

      // Axes
      svg.appendChild(mkEl('line', { x1: PL, y1: 8, x2: PL, y2: H - PB, stroke: 'rgba(120,160,200,.15)', 'stroke-width': 1 }));
      svg.appendChild(mkEl('line', { x1: PL, y1: H - PB, x2: W - 4, y2: H - PB, stroke: 'rgba(120,160,200,.15)', 'stroke-width': 1 }));

      function scaleY(val, max) { return 8 + ah - (val / max) * ah; }
      function xAt(i, n) { return PL + (i / (n - 1)) * aw; }
      function addLabel(txt, x, y, col = 'rgba(120,160,200,.3)', fs = 8) {
        const t = mkEl('text', { x, y, 'font-family': 'Share Tech Mono,monospace', 'font-size': fs, fill: col, 'letter-spacing': '0.5' });
        t.textContent = txt;
        svg.appendChild(t);
      }
      function polyline(pts, stroke, sw = 1.8, dash = '') {
        const el = mkEl('polyline', {
          points: pts.map(([x, y]) => `${x},${y}`).join(' '),
          stroke, fill: 'none', 'stroke-width': sw, 'stroke-linejoin': 'round'
        });
        if (dash) el.setAttribute('stroke-dasharray', dash);
        svg.appendChild(el);
      }
      function area(pts, fill) {
        const bottom = H - PB;
        const pp = [...pts, [pts[pts.length - 1][0], bottom], [pts[0][0], bottom]];
        const el = mkEl('polygon', {
          points: pp.map(([x, y]) => `${x},${y}`).join(' '),
          fill, opacity: '.18'
        });
        svg.appendChild(el);
      }

      const labels = ['00:00', '06:00', '12:00', '18:00', '23:45'];
      const maxVal = Math.max(...actual, ...peer) * 1.2 || 10;
      const n = actual.length || 96; 
      
      if(actual.length > 1 && peer.length > 1) {
        const ppts = peer.map((v, i) => [xAt(i, n), scaleY(v, maxVal)]);
        const mpts = actual.map((v, i) => [xAt(i, n), scaleY(v, maxVal)]);
        
        // Shade gap
        for (let i = 0; i < actual.length - 1; i++) {
          svg.appendChild(mkEl('polygon', {
            points: `${ppts[i][0]},${ppts[i][1]} ${ppts[i+1][0]},${ppts[i+1][1]} ${mpts[i+1][0]},${mpts[i+1][1]} ${mpts[i][0]},${mpts[i][1]}`,
            fill: 'rgba(255,45,85,.08)'
          }));
        }
        
        polyline(ppts, 'rgba(120,160,200,.35)', 1.5, '4,4');
        area(mpts, '#ff2d55');
        polyline(mpts, '#ff2d55', 1.5);
        
        labels.forEach((l, i) => addLabel(l, xAt(i * (n/4), n) - 10, H - 6));
      }
      addLabel('Peer Avg', PL + 2, 16, 'rgba(120,160,200,.45)', 7.5);
      addLabel('Actual Load', PL + 2, 28, 'rgba(255,45,85,.6)', 7.5);
    }

    // ═══════════════════════════════════════
    // METER SELECTION
    // ═══════════════════════════════════════
    let current = -1;

    async function pick(idx) {
      const m = M[idx];
      if (!m) return;
      current = idx;

      // Update selection ring on map
      const ring = document.getElementById('selRing');
      ring.setAttribute('cx', m.cx);
      ring.setAttribute('cy', m.cy);
      ring.setAttribute('opacity', '1');

      // Dim all dots, highlight selected
      M.forEach((_, i) => {
        const el = document.getElementById('md' + i);
        if (el) el.style.opacity = i === idx ? '1' : '0.35';
      });

      // Fill detail panel
      document.getElementById('dId').textContent = m.id;
      document.getElementById('dZone').textContent = m.zone;

      const badge = document.getElementById('fpBadge');
      badge.className = 'fp-badge ' + m.bc;
      document.getElementById('fpIcon').textContent = m.icon;
      document.getElementById('fpName').textContent = m.type;
      document.getElementById('fpDesc').textContent = m.desc;

      document.getElementById('aText').textContent = m.action;
      document.getElementById('aForm').textContent = m.form;

      const chartTitles = {
        ghost: 'Consumption Pattern — 24-Hour Interval View',
        phase: 'Monthly Consumption — Phase Bypass Signature',
        tamper: 'Monthly Consumption — Tamper Decline Pattern',
        freeze: 'Monthly Consumption — Billing Freeze Signature',
        bleed: 'Monthly Consumption vs Peer Group Average'
      };
      document.getElementById('cTitle').textContent = chartTitles[m.chart] || 'Live Consumption Pattern';

      // Reset animated values
      ['confPct', 'mConf'].forEach(id => document.getElementById(id).textContent = '0%');
      document.getElementById('cbar').style.width = '0%';
      document.getElementById('mRev').textContent = '₹0';
      document.getElementById('mDays').textContent = '0';
      document.getElementById('mType').textContent = m.type;

      // Show panel
      document.getElementById('pDefault').style.display = 'none';
      document.getElementById('pDetail').classList.add('on');

      // Draw real chart from API
      try {
        const res = await fetch(`http://localhost:8000/api/fingerprints/meters/${m.id}`);
        const data = await res.json();
        drawRealChart(
            data.timeseries ? data.timeseries.map(d => d.kwh) : [], 
            data.peer_average ? data.peer_average.map(d => d.kwh) : []
        );
      } catch(e) {
        console.error("Failed to load chart data", e);
        drawRealChart([], []);
      }

      // Animate confidence
      setTimeout(() => {
        document.getElementById('cbar').style.width = m.conf + '%';
        countUp('confPct', 0, m.conf, 1400, v => v + '%');
        countUp('mConf', 0, m.conf, 1400, v => v + '%');
      }, 200);

      // Animate days
      setTimeout(() => countUp('mDays', 0, m.days, 900, v => v + ' days'), 350);

      // Animate revenue
      setTimeout(() => countUp('mRev', 0, m.rev, 1300, v => '₹' + v.toLocaleString()), 500);
    }

    function countUp(id, from, to, dur, fmt) {
      const el = document.getElementById(id);
      const start = performance.now();
      function step(now) {
        const t = Math.min((now - start) / dur, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        el.textContent = fmt(Math.round(from + (to - from) * ease));
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    function goBack() {
      document.getElementById('pDetail').classList.remove('on');
      document.getElementById('pDefault').style.display = 'flex';
      document.getElementById('selRing').setAttribute('opacity', '0');
      M.forEach((_, i) => {
        const el = document.getElementById('md' + i);
        if (el) el.style.opacity = '1';
      });
      current = -1;
    }

    // ═══════════════════════════════════════
    // LIVE TICKERS
    // ═══════════════════════════════════════
    let zoneIdx = 0, scanCount = 6840;

    setInterval(() => {
      zoneIdx = (zoneIdx + 1) % ZONES.length;
      document.getElementById('bZone').textContent = ZONES[zoneIdx];
    }, 2400);

    setInterval(() => {
      scanCount += Math.floor(Math.random() * 120 + 60);
      document.getElementById('bScanned').textContent = scanCount.toLocaleString();
    }, 900);
    /* CURSOR */
    document.addEventListener('mousemove', e => {
      cur.style.left = e.clientX + 'px';
      cur.style.top = e.clientY + 'px';
      cur2.style.left = e.clientX + 'px';
      cur2.style.top = e.clientY + 'px';
    });
    function toggleLoss(el) {
      const item = el.parentElement;

      // Close others (optional but cleaner UX)
      document.querySelectorAll('.loss-item').forEach(i => {
        if (i !== item) i.classList.remove('active');
      });

      // Toggle current
      item.classList.toggle('active');
    }
