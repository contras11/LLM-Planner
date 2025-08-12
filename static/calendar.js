function initializeCalendar(PX_PER_MIN, START_H, GRID_CELL_MIN, END_H) {
  const GRID = GRID_CELL_MIN;
  const TOTAL_PX = (END_H - START_H) * 60 * PX_PER_MIN;

  let tooltip; 
  let ghost; 
  let ghostHost;

  function ensureTooltip() {
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'drag-tooltip';
      tooltip.style.display = 'none';
      document.body.appendChild(tooltip);
    }
    return tooltip;
  }

  function showTip(x, y, text) { 
    const t = ensureTooltip(); 
    t.textContent = text; 
    t.style.left = (x + 12) + 'px'; 
    t.style.top = (y + 12) + 'px'; 
    t.style.display = 'block'; 
  }

  function hideTip() { 
    if (tooltip) tooltip.style.display = 'none'; 
  }

  function ensureGhost(host) {
    if (!ghost || ghostHost !== host) {
      removeGhost();
      ghost = document.createElement('div');
      ghost.className = 'ghost-bar';
      host.querySelector('div[style*="position: relative"]').appendChild(ghost);
      ghostHost = host;
    }
    return ghost;
  }

  function removeGhost() { 
    if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost); 
    ghost = null; 
    ghostHost = null; 
  }

  function nearestGridMin(m) { 
    return Math.round(m / GRID) * GRID; 
  }

  function clamp(v, a, b) { 
    return Math.max(a, Math.min(b, v)); 
  }

  function pxToMin(px) { 
    return px / PX_PER_MIN; 
  }

  function toLocalISO(d) { 
    const p = n => String(n).padStart(2, '0'); 
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + "T" + p(d.getHours()) + ":" + p(d.getMinutes()); 
  }

  function pickDayColByPoint(x, y) {
    const cols = Array.from(document.querySelectorAll('.day-col'));
    for (const col of cols) {
      const r = col.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) return col;
    }
    return null;
  }

  function setup() {
    const root = document.getElementById('calendar-output');
    if (!root) return;

    // Escで月へ
    document.onkeydown = (e) => {
      const ui = document.getElementById('ui-intent');
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      if (e.key === 'Escape') { 
        if (ui) { 
          ui.textContent = 'to-month'; 
          ui.dispatchEvent(new Event('input')); 
        } 
      }
      // Undo/Redo
      if ((isMac && e.metaKey && e.key.toLowerCase() === 'z') || (!isMac && e.ctrlKey && e.key.toLowerCase() === 'z')) {
        e.preventDefault(); 
        if (ui) { 
          ui.textContent = 'undo'; 
          ui.dispatchEvent(new Event('input')); 
        }
      }
      if ((isMac && e.metaKey && e.key.toLowerCase() === 'y') || (!isMac && e.ctrlKey && e.key.toLowerCase() === 'y')) {
        e.preventDefault(); 
        if (ui) { 
          ui.textContent = 'redo'; 
          ui.dispatchEvent(new Event('input')); 
        }
      }
    };

    // 期間ラベルクリックで月へ
    const header = document.getElementById('current-month-year');
    if (header) {
      header.onclick = () => { 
        const ui = document.getElementById('ui-intent'); 
        if (ui) { 
          ui.textContent = 'to-month'; 
          ui.dispatchEvent(new Event('input')); 
        } 
      };
    }

    const bars = root.querySelectorAll('.event-bar');
    bars.forEach(bar => {
      bar.onmousedown = null; 
      const handle = bar.querySelector('.resize-handle'); 
      if (handle) handle.onmousedown = null;
      let dragging = false, resizing = false, startY = 0, origTop = 0, origH = 0, origDay = bar.dataset.day, origDayIdx = parseInt(bar.dataset.dayIndex);

      // ダブルクリックで編集オープン
      bar.ondblclick = () => {
        const sink = document.getElementById('edit-open-store');
        if (sink) { 
          sink.textContent = bar.dataset.id; 
          sink.dispatchEvent(new Event('input')); 
        }
      };

      // ドラッグ移動
      bar.onmousedown = (ev) => {
        if (ev.target.classList.contains('resize-handle')) return;
        ev.preventDefault(); 
        dragging = true; 
        bar.classList.add('dragging');
        startY = ev.clientY; 
        origTop = parseFloat(getComputedStyle(bar).top);

        document.onmousemove = (mv) => {
          if (!dragging) return;
          const dy = mv.clientY - startY;
          let newTop = origTop + dy;
          const maxTop = TOTAL_PX - parseFloat(getComputedStyle(bar).height);
          newTop = clamp(newTop, 0, maxTop);
          bar.style.top = newTop + 'px';

          const topMin = nearestGridMin(pxToMin(newTop));
          const host = pickDayColByPoint(mv.clientX, mv.clientY) || document.querySelector(`.day-col[data-day="${bar.dataset.day}"]`);
          const durMin = nearestGridMin(pxToMin(parseFloat(getComputedStyle(bar).height)));
          const g = ensureGhost(host);
          g.style.top = (topMin) + 'px'; 
          g.style.height = Math.max(durMin, GRID) + 'px';

          const s = new Date(host.dataset.day + 'T00:00:00'); 
          s.setHours(START_H, 0, 0, 0); 
          s.setMinutes(s.getMinutes() + topMin);
          const e = new Date(s.getTime() + Math.max(durMin, GRID) * 60000);
          showTip(mv.clientX, mv.clientY, host.dataset.day + '  ' + s.toTimeString().slice(0, 5) + '–' + e.toTimeString().slice(0, 5));
        };

        document.onmouseup = (up) => {
          if (!dragging) return; 
          dragging = false; 
          bar.classList.remove('dragging');
          document.onmousemove = null; 
          document.onmouseup = null; 
          hideTip(); 
          removeGhost();

          const newTopPx = parseFloat(getComputedStyle(bar).top);
          const mins = nearestGridMin(pxToMin(newTopPx));
          const host = pickDayColByPoint(up.clientX, up.clientY) || document.querySelector(`.day-col[data-day="${bar.dataset.day}"]`);
          const s = new Date(host.dataset.day + 'T00:00:00'); 
          s.setHours(START_H, 0, 0, 0); 
          s.setMinutes(s.getMinutes() + mins);
          const durMin = nearestGridMin(pxToMin(parseFloat(getComputedStyle(bar).height)));
          const e = new Date(s.getTime() + Math.max(durMin, GRID) * 60000);

          const sink = document.getElementById('drag-update-store');
          if (sink) { 
            sink.textContent = JSON.stringify({id: bar.dataset.id, start: toLocalISO(s), end: toLocalISO(e)}); 
            sink.dispatchEvent(new Event('input')); 
          }
        };
      };

      // リサイズ（下辺）
      if (handle) {
        handle.onmousedown = (ev) => {
          ev.preventDefault(); 
          resizing = true; 
          bar.classList.add('dragging'); 
          startY = ev.clientY; 
          origH = parseFloat(getComputedStyle(bar).height);
          
          document.onmousemove = (mv) => {
            if (!resizing) return;
            const dy = mv.clientY - startY;
            let newH = origH + dy;
            const maxH = TOTAL_PX - parseFloat(getComputedStyle(bar).top);
            newH = Math.max(GRID, Math.min(maxH, newH)); 
            bar.style.height = newH + 'px';

            const topMin = nearestGridMin(pxToMin(parseFloat(getComputedStyle(bar).top)));
            const host = pickDayColByPoint(mv.clientX, mv.clientY) || document.querySelector(`.day-col[data-day="${bar.dataset.day}"]`);
            const g = ensureGhost(host); 
            g.style.top = (topMin) + 'px'; 
            g.style.height = nearestGridMin(pxToMin(newH)) + 'px';

            const s = new Date(host.dataset.day + 'T00:00:00'); 
            s.setHours(START_H, 0, 0, 0); 
            s.setMinutes(s.getMinutes() + topMin);
            const e = new Date(s.getTime() + nearestGridMin(pxToMin(newH)) * 60000);
            showTip(mv.clientX, mv.clientY, host.dataset.day + '  ' + s.toTimeString().slice(0, 5) + '–' + e.toTimeString().slice(0, 5));
          };

          document.onmouseup = (up) => {
            if (!resizing) return; 
            resizing = false; 
            bar.classList.remove('dragging');
            document.onmousemove = null; 
            document.onmouseup = null; 
            hideTip(); 
            removeGhost();

            const topPx = parseFloat(getComputedStyle(bar).top);
            const heightPx = parseFloat(getComputedStyle(bar).height);
            const mins = nearestGridMin(pxToMin(topPx));
            const durMin = nearestGridMin(pxToMin(heightPx));
            const host = pickDayColByPoint(up.clientX, up.clientY) || document.querySelector(`.day-col[data-day="${bar.dataset.day}"]`);
            const s = new Date(host.dataset.day + 'T00:00:00'); 
            s.setHours(START_H, 0, 0, 0); 
            s.setMinutes(s.getMinutes() + mins);
            const e = new Date(s.getTime() + Math.max(durMin, GRID) * 60000);

            const sink = document.getElementById('drag-update-store');
            if (sink) { 
              sink.textContent = JSON.stringify({id: bar.dataset.id, start: toLocalISO(s), end: toLocalISO(e)}); 
              sink.dispatchEvent(new Event('input')); 
            }
          };
        };
      }
    });
  }

  const obs = new MutationObserver(() => setup());
  obs.observe(document.documentElement, {childList: true, subtree: true});
  setup();
}
