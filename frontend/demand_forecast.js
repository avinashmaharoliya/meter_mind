let zonesData = [];
    let activeZone = null;
    
    async function fetchSummary() {
      try {
        const res = await fetch('https://meter-mind.onrender.com/api/forecast/summary');
        const data = await res.json();
        
        let totalCurrent = 0;
        let peakExpected = 0;
        let peakTime = null;
        
        zonesData = data.zones;
        const listEl = document.getElementById('zoneList');
        listEl.innerHTML = '';
        
        zonesData.forEach((z, i) => {
          totalCurrent += z.current_load_kw;
          if (z.peak_forecast_kw > peakExpected) {
            peakExpected = z.peak_forecast_kw;
            peakTime = new Date(z.peak_forecast_time);
          }
          
          let riskClass = 'risk-normal';
          if(z.risk_level === 'High') riskClass = 'risk-high';
          if(z.risk_level === 'Elevated') riskClass = 'risk-elevated';
          
          const el = document.createElement('div');
          el.className = 'zitem' + (activeZone === z.zone_id ? ' active' : '');
          el.onclick = () => selectZone(z.zone_id, z.zone_name);
          el.innerHTML = `
            <div class="zi-info">
              <div class="zi-name">${z.zone_name}</div>
              <div class="zi-id">ID: ${z.zone_id} | Cap: ${(z.rated_capacity_kw/1000).toFixed(1)}MW</div>
            </div>
            <div class="zi-stats">
              <div class="zi-load">${(z.current_load_kw/1000).toFixed(2)} MW</div>
              <div class="zi-risk ${riskClass}">${z.risk_level} RISK</div>
            </div>
          `;
          listEl.appendChild(el);
        });
        
        document.getElementById('totalLoad').textContent = (totalCurrent/1000).toFixed(2) + ' MW';
        document.getElementById('peakLoad').textContent = (peakExpected/1000).toFixed(2) + ' MW';
        if(peakTime) {
          document.getElementById('peakTime').textContent = peakTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }
        
        const hasHigh = zonesData.some(z => z.risk_level === 'High');
        const rEl = document.getElementById('gridRisk');
        rEl.textContent = hasHigh ? 'CRITICAL' : 'STABLE';
        rEl.style.color = hasHigh ? 'var(--red)' : 'var(--green)';
        
        if (!activeZone && zonesData.length > 0) {
          selectZone(zonesData[0].zone_id, zonesData[0].zone_name);
        }
        
      } catch(e) {
        console.error('Failed to load forecast summary', e);
      }
    }
    
    async function selectZone(zoneId, zoneName) {
      activeZone = zoneId;
      document.getElementById('cZoneName').textContent = zoneName + ' Forecast';
      // update active class
      document.querySelectorAll('.zitem').forEach(el => el.classList.remove('active'));
      const activeEl = Array.from(document.querySelectorAll('.zitem')).find(el => el.innerHTML.includes(zoneId));
      if(activeEl) activeEl.classList.add('active');
      
      try {
        const res = await fetch(`https://meter-mind.onrender.com/api/forecast/zones/${zoneId}`);
        const data = await res.json();
        drawForecastChart(data.forecast);
      } catch(e) {
        console.error('Failed to load zone forecast', e);
      }
    }
    
    function drawForecastChart(forecastArr) {
      const svg = document.getElementById('forecastChart');
      svg.innerHTML = '';
      if(!forecastArr || forecastArr.length === 0) return;
      
      const W = 800, H = 400, PL = 50, PB = 30, PT = 20, PR = 20;
      const aw = W - PL - PR, ah = H - PB - PT;
      
      const maxVal = Math.max(...forecastArr.map(d => d.upper_bound_kw)) * 1.1;
      
      function scaleY(val) { return PT + ah - (val / maxVal) * ah; }
      function xAt(i, n) { return PL + (i / (n - 1)) * aw; }
      function mkEl(tag, attrs) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
        return el;
      }
      
      // grid lines
      for(let i=0; i<=5; i++) {
        const y = PT + (i/5)*ah;
        svg.appendChild(mkEl('line', { x1: PL, y1: y, x2: W-PR, y2: y, stroke: 'rgba(120,160,200,0.1)', 'stroke-width': 1 }));
        const t = mkEl('text', { x: 10, y: y+4, 'font-family': 'Share Tech Mono', 'font-size': 11, fill: 'var(--text3)' });
        t.textContent = (maxVal * (5-i)/5 / 1000).toFixed(1) + 'M';
        svg.appendChild(t);
      }
      
      const n = forecastArr.length;
      
      // confidence interval area
      const upperPts = forecastArr.map((d, i) => `${xAt(i, n)},${scaleY(d.upper_bound_kw)}`);
      const lowerPts = forecastArr.map((d, i) => `${xAt(i, n)},${scaleY(d.lower_bound_kw)}`).reverse();
      const areaPath = upperPts.join(' ') + ' ' + lowerPts.join(' ');
      svg.appendChild(mkEl('polygon', { points: areaPath, fill: 'rgba(0,240,255,0.1)' }));
      
      // pred line
      const predPts = forecastArr.map((d, i) => `${xAt(i, n)},${scaleY(d.predicted_kw)}`).join(' ');
      svg.appendChild(mkEl('polyline', { points: predPts, fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2 }));
      
      // x axis labels
      for(let i=0; i<n; i+=3) {
        const d = new Date(forecastArr[i].timestamp);
        const t = mkEl('text', { x: xAt(i, n)-15, y: H-5, 'font-family': 'Share Tech Mono', 'font-size': 10, fill: 'var(--text2)' });
        t.textContent = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        svg.appendChild(t);
      }
      
      // capacity line
      if(activeZone && zonesData.length > 0) {
        const z = zonesData.find(z => z.zone_id === activeZone);
        if(z) {
          const capY = scaleY(z.rated_capacity_kw);
          if (capY > PT) {
            svg.appendChild(mkEl('line', { x1: PL, y1: capY, x2: W-PR, y2: capY, stroke: 'var(--red)', 'stroke-width': 1.5, 'stroke-dasharray': '6,4' }));
            const ct = mkEl('text', { x: W-PR-80, y: capY-6, 'font-family': 'Share Tech Mono', 'font-size': 10, fill: 'var(--red)' });
            ct.textContent = 'RATED CAPACITY';
            svg.appendChild(ct);
          }
        }
      }
    }
    const loadSteps = [
      'Connecting to Prophet prediction models...',
      'Aggregating smart meter time-series data...',
      'Calculating grid zone capacity limits...',
      'Running 24-hour predictive intervals...',
      'Generating confidence bounds...',
      'Forecast complete — 6 zones active'
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

    fetchSummary();
    setInterval(fetchSummary, 5000);
