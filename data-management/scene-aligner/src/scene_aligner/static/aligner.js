  const $ = id => document.getElementById(id);
  const PLAYBACK_RATES = [0.5, 1, 2, 4, 8, 16];
  let currentRateIdx = 3;  // 4×
  // HTML-escape any string before interpolating it into innerHTML.
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  let currentDs = null;
  let currentCamera = '';
  let currentTopic = '';
  let currentEpisode = 0;
  let defaultCamera = '';

  function shortCam(k) {
    return k.replace(/^observation\.images\.image_/, '')
            .replace(/^observation\.images\./, '');
  }

  function pushState() {
    $('ref-op-val').textContent  = $('ref-op').value  + '%';
    $('live-op-val').textContent = $('live-op').value + '%';
    fetch('/api/state', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        dataset:     currentDs ? currentDs.id : '',
        camera:      currentCamera,
        topic:       currentTopic,
        episode:     currentEpisode,
        ref_op:      $('ref-op').value  / 100,
        live_op:     $('live-op').value / 100,
        invert_ref:  $('invert-ref').checked,
        invert_live: $('invert-live').checked,
      }),
    }).then(r => r.ok ? r.json() : null).then(s => {
      if (!s) return;
      // Clear local sparkline whenever the server confirms a selection change.
      if (s.dataset !== window.__lastDataset || s.camera !== window.__lastCamera || s.episode !== window.__lastEpisode) {
        rawPoints.length = 0; smoothPoints.length = 0;
        sessionBest = null; lastSmoothSeen = null; lastScoreT = 0;
        window.__lastDataset = s.dataset;
        window.__lastCamera  = s.camera;
        window.__lastEpisode = s.episode;
      }
    }).catch(() => {});
  }
  ['ref-op','live-op'].forEach(id => $(id).addEventListener('input', pushState));
  ['invert-ref','invert-live'].forEach(id => $(id).addEventListener('change', pushState));

  function populateCameras(ds, prefer) {
    const sel = $('camera');
    sel.innerHTML = '<option value=""></option>';
    (ds.cameras || []).forEach(k => {
      const o = document.createElement('option');
      o.value = k; o.textContent = shortCam(k);
      o.title = k;
      sel.appendChild(o);
    });
    let pick = '';
    if (prefer && (ds.cameras || []).includes(prefer)) pick = prefer;
    else if (defaultCamera && (ds.cameras || []).includes(defaultCamera)) pick = defaultCamera;
    else if ((ds.cameras || []).length) pick = ds.cameras[0];
    sel.value = pick;
    sel.disabled = (ds.cameras || []).length <= 1;
    currentCamera = pick;
    // Auto-pick the ROS topic most similar to the chosen camera.
    const auto = pickBestTopic(currentCamera);
    if (auto && auto !== currentTopic) {
      currentTopic = auto;
      const tsel = $('ros-topic');
      if (tsel) tsel.value = auto;
    }
  }
  $('camera').addEventListener('change', () => {
    currentCamera = $('camera').value;
    // Auto-pick the ROS topic most similar to the newly selected camera.
    const auto = pickBestTopic(currentCamera);
    if (auto && auto !== currentTopic) {
      currentTopic = auto;
      $('ros-topic').value = auto;
    }
    pushState();
  });

  // Longest common substring length, case-insensitive. Used to auto-match
  // the ROS topic that looks most like the selected dataset camera key.
  function lcsLen(a, b) {
    a = a.toLowerCase(); b = b.toLowerCase();
    const m = a.length, n = b.length;
    if (!m || !n) return 0;
    let best = 0;
    let prev = new Uint16Array(n + 1);
    let curr = new Uint16Array(n + 1);
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        curr[j] = a[i - 1] === b[j - 1] ? prev[j - 1] + 1 : 0;
        if (curr[j] > best) best = curr[j];
      }
      [prev, curr] = [curr, prev];
    }
    return best;
  }

  // Discovered Image-only topic list (cached from the last /api/topics call).
  let availableTopics = [];

  function pickBestTopic(cameraKey) {
    if (!cameraKey || !availableTopics.length) return '';
    const short = shortCam(cameraKey);
    let best = '', bestScore = -1;
    for (const t of availableTopics) {
      const score = lcsLen(short, t);
      if (score > bestScore) { bestScore = score; best = t; }
    }
    // Require at least 3 shared characters to count as a meaningful match.
    return bestScore >= 3 ? best : '';
  }

  function refreshTopics() {
    return fetch('/api/topics').then(r => r.ok ? r.json() : null).then(d => {
      const sel = $('ros-topic');
      const prev = currentTopic || sel.value;
      const all = (d && d.topics) || [];
      const topics = all.filter(t => (t.types || []).includes('sensor_msgs/msg/Image'));
      availableTopics = topics.map(t => t.name);
      sel.innerHTML = `<option value="">(none — ${topics.length} camera topic(s) discovered)</option>`;
      topics.forEach(t => {
        const o = document.createElement('option');
        o.value = t.name;
        o.textContent = t.name;
        sel.appendChild(o);
      });
      // Preserve prior selection if still present; otherwise auto-match to camera.
      let pick = '';
      if (prev && availableTopics.includes(prev)) pick = prev;
      else pick = pickBestTopic(currentCamera);
      sel.value = pick;
      if (pick !== currentTopic) {
        currentTopic = pick;
        pushState();
      }
    }).catch(() => {});
  }
  $('ros-topic').addEventListener('change', () => {
    currentTopic = $('ros-topic').value;
    pushState();
  });
  $('refresh-topics').addEventListener('click', refreshTopics);
  refreshTopics();

  function setActive(ds, preferCamera) {
    currentDs = ds;
    populateCameras(ds, preferCamera);
    const acq = fmtAcquired(ds.acquired_at);
    const epLabel = `<span style="color:#93c5fd">ep ${esc(String(currentEpisode).padStart(4,'0'))}</span>`;
    $('current').innerHTML = `<strong style="color:#fff">${esc(ds.name)}</strong>` +
      ` · ${epLabel}` +
      ` <span style="color:#888">📅 ${esc(acq)} (${esc(relAge(ds.acquired_at))})</span>`;
    document.querySelectorAll('.card').forEach(c => {
      c.classList.toggle('active', c.dataset.id === ds.id);
    });
    // Enable the reference controls now that a reference is loaded.
    document.querySelectorAll('label.ref-ctl').forEach(el => el.classList.add('enabled'));
    $('ref-op').disabled = false;
    $('invert-ref').disabled = false;
    $('score').classList.remove('hidden');
    pushState();
  }

  // Magnifying-glass loupe over the composite stream.
  const ZOOM = 3;
  const stage = $('stage');
  const lens = $('lens');
  const lensImg = $('lens-img');
  const lensR = 140;  // matches CSS width/2

  stage.addEventListener('mouseenter', () => lens.classList.add('on'));
  stage.addEventListener('mouseleave', () => lens.classList.remove('on'));
  stage.addEventListener('mousemove', e => {
    const r = stage.getBoundingClientRect();
    const cx = e.clientX - r.left;
    const cy = e.clientY - r.top;
    if (cx < 0 || cy < 0 || cx > r.width || cy > r.height) {
      lens.classList.remove('on');
      return;
    }
    lens.classList.add('on');
    lens.style.left = cx + 'px';
    lens.style.top  = cy + 'px';
    // Inner img is a Z× zoomed object-fit:contain copy of the stage image.
    lensImg.style.width  = (r.width  * ZOOM) + 'px';
    lensImg.style.height = (r.height * ZOOM) + 'px';
    lensImg.style.left   = (lensR - cx * ZOOM) + 'px';
    lensImg.style.top    = (lensR - cy * ZOOM) + 'px';
  });

  function fmt(n) {
    if (n == null) return '—';
    if (typeof n === 'number') return n.toLocaleString();
    return n;
  }

  function fmtAcquired(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const pad = n => String(n).padStart(2, '0');
    const date = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
    const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return `${date} ${time}`;
  }
  function relAge(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    const sec = (Date.now() - d.getTime()) / 1000;
    if (sec < 60) return 'just now';
    if (sec < 3600) return Math.floor(sec/60) + 'm ago';
    if (sec < 86400) return Math.floor(sec/3600) + 'h ago';
    if (sec < 86400*30) return Math.floor(sec/86400) + 'd ago';
    if (sec < 86400*365) return Math.floor(sec/86400/30) + 'mo ago';
    return Math.floor(sec/86400/365) + 'y ago';
  }

  function makeCard(ds) {
    const card = document.createElement('div');
    card.className = 'card' + (ds.has_video ? ' has-video' : '');
    card.dataset.id = ds.id;

    const media = document.createElement('div');
    media.className = 'media';
    const img = document.createElement('img');
    img.src = ds.has_video ? `/api/dataset/${encodeURI(ds.id)}/thumbnail` : '';
    img.alt = ds.name;
    media.appendChild(img);
    if (ds.has_video) {
      const play = document.createElement('div');
      play.className = 'play';
      play.textContent = '▶';
      media.appendChild(play);
      let hoverTimer = null;
      media.addEventListener('mouseenter', () => {
        hoverTimer = setTimeout(() => startPreview(media, ds), 150);
      });
      media.addEventListener('mouseleave', () => {
        if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
        stopPreview(media);
      });
      // Same effect as the "Browse episodes" button.
      media.addEventListener('click', e => {
        // Ignore clicks on the inline scrub bar so seeking doesn't open the modal.
        if (e.target.closest('.scrub, .speed')) return;
        openEpisodes(ds);
      });
    }
    card.appendChild(media);

    const body = document.createElement('div');
    body.className = 'body';
    body.innerHTML = `
      <div class="acquired">📅 ${esc(fmtAcquired(ds.acquired_at))}<span class="rel">${esc(relAge(ds.acquired_at))}</span></div>
      <div class="name">${esc(ds.id)}</div>
      <dl>
        <dt>robot</dt><dd>${esc(fmt(ds.robot_type))}</dd>
        <dt>episodes</dt><dd>${esc(fmt(ds.total_episodes))}</dd>
        <dt>frames</dt><dd>${esc(fmt(ds.total_frames))}</dd>
        <dt>tasks</dt><dd>${esc(fmt(ds.total_tasks))}</dd>
        <dt>fps</dt><dd>${esc(fmt(ds.fps))}</dd>
        <dt>codebase</dt><dd>${esc(fmt(ds.codebase_version))}</dd>
      </dl>
      ${ds.has_video ? '' : '<span class="badge">no camera videos</span>'}
      <div class="actions">
        <button class="btn ghost details">Details</button>
        <button class="btn select" ${ds.has_video ? '' : 'disabled'}>Browse episodes →</button>
      </div>`;
    body.querySelector('.select').addEventListener('click', () => {
      openEpisodes(ds);
    });
    body.querySelector('.details').addEventListener('click', () => openDrawer(ds));
    card.appendChild(body);
    return card;
  }

  // ---------------- Episode picker -----------------
  const epModal = document.createElement('div');
  epModal.id = 'ep-modal';
  epModal.innerHTML = `
    <div class="topbar">
      <h2 id="ep-title">Episodes</h2>
      <div style="display:flex;gap:.5rem;align-items:center">
        <label style="color:#888;font-size:.8rem">camera
          <select id="ep-camera"
                  style="background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:6px;padding:.25rem .4rem;font:inherit;margin-left:.3rem"></select>
        </label>
        <input id="ep-search" type="search" placeholder="Filter by index or task…"
               style="background:#2a2a2a;color:#ddd;border:1px solid #444;border-radius:6px;padding:.3rem .6rem;font:inherit"/>
        <button class="btn ghost" id="ep-back">← Datasets</button>
        <button class="btn ghost" id="ep-close">Close</button>
      </div>
    </div>
    <div class="filterbar" id="ep-filterbar"></div>
    <div id="ep-grid"></div>`;
  document.body.appendChild(epModal);

  let epDataset = null;
  let epCamera = '';
  let allEpisodes = [];
  let epAvailableLabels = [];
  let epActiveLabelFilter = new Set();
  let epIncludeUnlabeled = false;
  let epShowDetails = false;
  let epObserver = null;

  function populateEpCameras(ds, prefer) {
    const sel = $('ep-camera');
    sel.innerHTML = '';
    (ds.cameras || []).forEach(k => {
      const o = document.createElement('option');
      o.value = k; o.textContent = shortCam(k); o.title = k;
      sel.appendChild(o);
    });
    let pick = '';
    if (prefer && (ds.cameras || []).includes(prefer)) pick = prefer;
    else if ((ds.cameras || []).length) pick = ds.cameras[0];
    sel.value = pick;
    sel.disabled = (ds.cameras || []).length <= 1;
    epCamera = pick;
  }

  function openEpisodes(ds) {
    epDataset = ds;
    document.getElementById('ep-title').textContent =
      `Episodes — ${ds.name}`;
    document.getElementById('modal').classList.remove('open');
    epModal.classList.add('open');
    document.getElementById('ep-search').value = '';
    epActiveLabelFilter = new Set();
    epIncludeUnlabeled = false;
    populateEpCameras(ds, currentCamera);
    fetch(`/api/episodes?dataset=${encodeURIComponent(ds.id)}`)
      .then(r => r.json())
      .then(d => {
        allEpisodes = d.episodes;
        // Use server-provided available_labels if any; else derive from episodes.
        const seen = new Set(d.available_labels || []);
        for (const ep of allEpisodes) for (const t of (ep.labels || [])) seen.add(t);
        epAvailableLabels = [...seen].sort();
        renderFilterBar();
        applyEpFilters();
      });
  }
  function closeEpisodes() { epModal.classList.remove('open'); }
  document.getElementById('ep-close').addEventListener('click', closeEpisodes);
  document.getElementById('ep-back').addEventListener('click', () => {
    closeEpisodes();
    document.getElementById('modal').classList.add('open');
  });
  document.getElementById('ep-search').addEventListener('input', applyEpFilters);
  document.getElementById('ep-camera').addEventListener('change', () => {
    epCamera = document.getElementById('ep-camera').value;
    applyEpFilters();
  });

  function renderFilterBar() {
    const bar = document.getElementById('ep-filterbar');
    if (!epAvailableLabels.length && !allEpisodes.length) { bar.innerHTML = ''; return; }
    const counts = Object.create(null);
    let unlabeled = 0;
    for (const ep of allEpisodes) {
      const labels = ep.labels || [];
      if (!labels.length) { unlabeled++; continue; }
      for (const t of labels) counts[t] = (counts[t] || 0) + 1;
    }
    const chips = epAvailableLabels.map(lbl => {
      const cls = 'toggle ' + (epActiveLabelFilter.has(lbl) ? 'on' : '');
      const tagCls = 'tag ' + esc(lbl.toLowerCase());
      const n = counts[lbl] || 0;
      return `<span class="${cls}" data-lbl="${esc(lbl)}">` +
             `<span class="${tagCls}" style="margin-right:4px">${esc(lbl)}</span>` +
             `<span style="color:#888;font-size:0.7rem">${n}</span></span>`;
    }).join('');
    const unCls = 'toggle ' + (epIncludeUnlabeled ? 'on' : '');
    const detCls = 'toggle ' + (epShowDetails ? 'on' : '');
    bar.innerHTML =
      `<span style="color:#666">tags:</span>${chips}` +
      `<span class="${unCls}" data-lbl="__none__">unlabeled ` +
      `<span style="color:#888;font-size:0.7rem">${unlabeled}</span></span>` +
      `<span class="count" id="ep-count"></span>` +
      `<label class="ep-display"><input type="checkbox" data-lbl="__details__"${epShowDetails ? ' checked' : ''}> show details</label>`;
    bar.querySelectorAll('.toggle, input[data-lbl]').forEach(el => {
      el.addEventListener('click', () => {
        const lbl = el.dataset.lbl;
        if (lbl === '__none__') {
          epIncludeUnlabeled = !epIncludeUnlabeled;
        } else if (lbl === '__details__') {
          epShowDetails = !epShowDetails;
          document.getElementById('ep-grid').classList.toggle('with-details', epShowDetails);
          renderFilterBar();
          return;
        } else if (epActiveLabelFilter.has(lbl)) {
          epActiveLabelFilter.delete(lbl);
        } else {
          epActiveLabelFilter.add(lbl);
        }
        renderFilterBar();
        applyEpFilters();
      });
    });
  }

  function applyEpFilters() {
    const q = document.getElementById('ep-search').value.trim().toLowerCase();
    const filtered = allEpisodes.filter(ep => {
      if (q) {
        const matches = String(ep.idx).includes(q) ||
          (ep.tasks || []).some(t => String(t).toLowerCase().includes(q)) ||
          (ep.labels || []).some(t => String(t).toLowerCase().includes(q));
        if (!matches) return false;
      }
      const labels = ep.labels || [];
      const anyFilter = epActiveLabelFilter.size > 0 || epIncludeUnlabeled;
      if (!anyFilter) return true;
      if (labels.length === 0) return epIncludeUnlabeled;
      return labels.some(t => epActiveLabelFilter.has(t));
    });
    const cEl = document.getElementById('ep-count');
    if (cEl) cEl.textContent = `${filtered.length} / ${allEpisodes.length}`;
    renderEpisodes(filtered);
  }

  function renderEpisodes(eps) {
    const grid = document.getElementById('ep-grid');
    grid.innerHTML = '';
    if (epObserver) epObserver.disconnect();
    epObserver = new IntersectionObserver(entries => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.querySelectorAll('img[data-src]').forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          });
          epObserver.unobserve(e.target);
        }
      }
    }, { rootMargin: '300px' });

    const cam = epCamera || (epDataset.cameras || [])[0] || '';
    const fps = epDataset.fps || 30;
    eps.forEach(ep => {
      const card = document.createElement('div');
      card.className = 'ep-card';
      const tparam = cam ? `&camera=${encodeURIComponent(cam)}` : '';
      const dur = ep.duration_s || (ep.length / fps);
      const taskStr = (ep.tasks || []).join(', ') || '—';
      const labels = ep.labels || [];
      const tagsHtml = labels.length
        ? labels.map(t => `<span class="tag ${esc(t.toLowerCase())}">${esc(t)}</span>`).join('')
        : '<span class="tag unlabeled">unlabeled</span>';
      const cm = (ep.cameras || {})[cam] || {};
      const ts = (cm.from_timestamp != null)
        ? `t=${(cm.from_timestamp).toFixed(2)}s..${(cm.to_timestamp).toFixed(2)}s`
        : '';
      const detailsHtml = `
          <div class="details">
            <div>frames ${esc(ep.dataset_from_index)}–${esc(ep.dataset_to_index)}</div>
            ${ts ? `<div>${esc(ts)}</div>` : ''}
            <div>chunk ${esc(cm.chunk_index ?? '—')} / file ${esc(cm.file_index ?? '—')}</div>
          </div>`;
      const thumbBase = `/api/episode/thumbnail?dataset=${encodeURIComponent(epDataset.id)}&episode=${ep.idx}${tparam}`;
      card.innerHTML = `
        <div class="media">
          <div class="thumb"><img data-src="${thumbBase}&which=first" alt="ep ${esc(ep.idx)} first"><span class="badge">first</span></div>
          <div class="thumb"><img data-src="${thumbBase}&which=last"  alt="ep ${esc(ep.idx)} last"><span class="badge">last</span></div>
        </div>
        <div class="body">
          <div class="idx">ep ${esc(String(ep.idx).padStart(4,'0'))}</div>
          <div class="meta">${esc(ep.length)} frames · ${esc(dur.toFixed(1))}s</div>
          <div class="task" title="${esc(taskStr)}">${esc(taskStr)}</div>
          <div class="tags">${tagsHtml}</div>
          ${detailsHtml}
        </div>`;
      card.addEventListener('click', () => {
        currentEpisode = ep.idx;
        setActive(epDataset, epCamera);
        closeEpisodes();
      });
      // Hover preview: load chunk MP4, jump to from_ts, loop within episode.
      const media = card.querySelector('.media');
      let hoverTimer = null;
      media.addEventListener('mouseenter', () => {
        hoverTimer = setTimeout(() => startEpPreview(media, ep, cam), 200);
      });
      media.addEventListener('mouseleave', () => {
        if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
        const v = media.querySelector('video');
        if (v) { v.pause(); v.removeAttribute('src'); v.load(); v.remove(); }
        media.querySelectorAll('.time, .scrub, .speed').forEach(e => e.remove());
        media.querySelectorAll('.thumb').forEach(t => t.style.display = '');
      });
      grid.appendChild(card);
      epObserver.observe(card);
    });
    // IntersectionObserver only fires when an element transitions INTO the
    // viewport; cards already visible at observe-time wouldn't trigger.
    // Force-load thumbnails for those.
    requestAnimationFrame(() => {
      const vh = window.innerHeight;
      grid.querySelectorAll('.ep-card').forEach(card => {
        const r = card.getBoundingClientRect();
        if (r.top < vh + 300 && r.bottom > -300) {
          card.querySelectorAll('img[data-src]').forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          });
        }
      });
    });
  }

  function startEpPreview(media, ep, cam) {
    if (media.querySelector('video')) return;
    const tparam = cam ? `&camera=${encodeURIComponent(cam)}` : '';
    const v = document.createElement('video');
    v.src = `/api/episode/video?dataset=${encodeURIComponent(epDataset.id)}&episode=${ep.idx}${tparam}`;
    v.muted = true; v.playsInline = true; v.autoplay = true;
    v.controls = false;
    const cm = ep.cameras[cam] || {};
    const fromTs = cm.from_timestamp || 0;
    const toTs   = cm.to_timestamp || (fromTs + (ep.duration_s || 1));
    v.addEventListener('loadedmetadata', () => {
      v.currentTime = fromTs;
      v.playbackRate = PLAYBACK_RATES[currentRateIdx];
    });
    media.querySelectorAll('.thumb').forEach(t => t.style.display = 'none');
    media.appendChild(v);
    attachVideoControls(media, v, { from: fromTs, to: toTs });
  }
  // ---------------- /Episode picker -----------------

  let drawerDs = null;
  function openDrawer(ds) {
    drawerDs = ds;
    $('drawer-title').textContent = ds.id;
    const sum = $('drawer-summary');
    sum.innerHTML = `
      <dt>acquired</dt><dd>${esc(fmtAcquired(ds.acquired_at))} <span style="color:#888">(${esc(relAge(ds.acquired_at))})</span></dd>
      <dt>id</dt><dd>${esc(ds.id)}</dd>
      <dt>robot</dt><dd>${esc(fmt(ds.robot_type))}</dd>
      <dt>episodes</dt><dd>${esc(fmt(ds.total_episodes))}</dd>
      <dt>frames</dt><dd>${esc(fmt(ds.total_frames))}</dd>
      <dt>tasks</dt><dd>${esc(fmt(ds.total_tasks))}</dd>
      <dt>fps</dt><dd>${esc(fmt(ds.fps))}</dd>
      <dt>codebase</dt><dd>${esc(fmt(ds.codebase_version))}</dd>
      <dt>cameras</dt><dd>${esc((ds.cameras || []).map(shortCam).join(', ') || '—')}</dd>`;
    $('drawer-use').disabled = !ds.has_video;
    $('drawer-raw').textContent = 'loading…';
    fetch(`/api/dataset/${encodeURI(ds.id)}/raw`)
      .then(r => r.json())
      .then(j => { $('drawer-raw').textContent = JSON.stringify(j, null, 2); })
      .catch(e => { $('drawer-raw').textContent = 'error: ' + e; });
    $('drawer').classList.add('open');
  }
  $('close-drawer').addEventListener('click', () => $('drawer').classList.remove('open'));
  $('drawer-use').addEventListener('click', () => {
    if (!drawerDs) return;
    $('drawer').classList.remove('open');
    $('modal').classList.remove('open');
    openEpisodes(drawerDs);
  });

  function stopPreview(media) {
    const v = media.querySelector('video');
    if (!v) return;
    v.pause();
    v.removeAttribute('src');
    v.load();
    v.remove();
    media.querySelectorAll('.time, .scrub, .speed').forEach(e => e.remove());
    media.querySelector('img').style.display = '';
    const p = media.querySelector('.play'); if (p) p.style.display = '';
  }
  function fmtTime(s) {
    if (!isFinite(s)) return '--:--';
    const m = Math.floor(s / 60);
    const ss = Math.floor(s % 60);
    return m + ':' + String(ss).padStart(2, '0');
  }
  function startPreview(media, ds) {
    if (media.querySelector('video')) return;
    const video = document.createElement('video');
    video.src = `/api/dataset/${encodeURI(ds.id)}/video`;
    video.autoplay = true; video.muted = true; video.loop = true;
    video.playsInline = true; video.controls = false;
    video.addEventListener('loadedmetadata', () => {
      video.playbackRate = PLAYBACK_RATES[currentRateIdx];
    });
    media.querySelector('img').style.display = 'none';
    const p = media.querySelector('.play'); if (p) p.style.display = 'none';
    media.appendChild(video);
    attachVideoControls(media, video);
  }

  // Adds time/scrub/speed controls to a `.media` already containing a <video>.
  // opts.from / opts.to bound the scrubber and (when both finite) clamp
  // playback to a sub-range, looping back to `from` on overrun. Without
  // bounds, scrubber spans the whole file and looping is left to the caller
  // (e.g. native <video loop>).
  function attachVideoControls(media, video, opts) {
    opts = opts || {};
    const from = (typeof opts.from === 'number') ? opts.from : 0;
    const to   = (typeof opts.to   === 'number' && isFinite(opts.to)) ? opts.to : null;

    const time = document.createElement('div');
    time.className = 'time';
    time.textContent = '--:-- / --:--';
    media.appendChild(time);

    const speed = document.createElement('button');
    speed.type = 'button';
    speed.className = 'speed';
    speed.title = 'Playback speed (click to cycle)';
    const refreshSpeed = () => { speed.textContent = PLAYBACK_RATES[currentRateIdx] + '×'; };
    refreshSpeed();
    speed.addEventListener('click', e => {
      e.stopPropagation();
      currentRateIdx = (currentRateIdx + 1) % PLAYBACK_RATES.length;
      const r = PLAYBACK_RATES[currentRateIdx];
      document.querySelectorAll('.media .speed').forEach(b => { b.textContent = r + '×'; });
      document.querySelectorAll('.media video').forEach(v => { v.playbackRate = r; });
    });
    media.appendChild(speed);

    const scrub = document.createElement('input');
    scrub.type = 'range'; scrub.className = 'scrub';
    scrub.min = String(from);
    scrub.max = String(to != null ? to : from);
    scrub.step = '0.05';
    scrub.value = String(from);
    media.appendChild(scrub);

    let scrubbing = false;
    scrub.addEventListener('pointerdown', () => { scrubbing = true; });
    const endScrub = () => { scrubbing = false; };
    scrub.addEventListener('pointerup',     endScrub);
    scrub.addEventListener('pointercancel', endScrub);
    scrub.addEventListener('input', () => { video.currentTime = parseFloat(scrub.value); });
    scrub.addEventListener('click', e => e.stopPropagation());

    const update = () => {
      const max = (to != null) ? to : (isFinite(video.duration) ? video.duration : 0);
      const maxStr = String(max);
      if (scrub.max !== maxStr) scrub.max = maxStr;
      if (!scrubbing) scrub.value = String(video.currentTime);
      const cur = Math.max(0, video.currentTime - from);
      const span = Math.max(0, max - from);
      time.textContent = fmtTime(cur) + ' / ' + fmtTime(span)
                       + ` · ${PLAYBACK_RATES[currentRateIdx]}×`;
    };
    video.addEventListener('timeupdate', update);
    video.addEventListener('loadedmetadata', update);

    if (to != null) {
      video.addEventListener('timeupdate', () => {
        if (video.currentTime >= to) video.currentTime = from;
      });
    }
  }

  $('open-picker').addEventListener('click', () => $('modal').classList.add('open'));
  $('close-picker').addEventListener('click', () => $('modal').classList.remove('open'));
  $('open-help').addEventListener('click', () => $('help-modal').classList.add('open'));
  $('close-help').addEventListener('click', () => $('help-modal').classList.remove('open'));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      if ($('help-modal').classList.contains('open')) $('help-modal').classList.remove('open');
      else if ($('drawer').classList.contains('open')) $('drawer').classList.remove('open');
      else if ($('ep-modal').classList.contains('open')) $('ep-modal').classList.remove('open');
      else $('modal').classList.remove('open');
    }
  });

  fetch('/api/datasets').then(r => r.json()).then(data => {
    const grid = $('grid');
    grid.innerHTML = '';
    data.datasets.forEach(ds => grid.appendChild(makeCard(ds)));
    // Auto-subscribe to the first camera of the first dataset so the live
    // feed shows immediately, even before the operator picks an episode.
    // The reference overlay stays empty until they choose one.
    const firstWithCam = data.datasets.find(d => (d.cameras || []).length > 0);
    if (firstWithCam && !currentCamera) {
      currentCamera = firstWithCam.cameras[0];
      populateCameras(firstWithCam, currentCamera);
    }
    pushState();
  });

  // Alignment-score polling + sparkline + auto-zoom + best-yet tracking.
  const scoreCanvas = $('score-canvas');
  const sctx = scoreCanvas.getContext('2d');
  // Raw history (server-supplied), capped to canvas width.
  const rawPoints = [];
  // EMA-smoothed history (for display).
  const smoothPoints = [];
  const EMA_ALPHA = 0.4;
  // Rolling window stats for auto-zoom.
  const ZOOM_WINDOW = 60;     // ~12s at 5 Hz
  let sessionBest = null;     // best smoothed value seen since last reset
  let lastSmoothSeen = null;
  let lastScoreT = 0;

  function scaleY(v, lo, hi, H) {
    if (hi <= lo) return H / 2;
    return H - ((v - lo) / (hi - lo)) * H;
  }

  function drawSpark(lo, hi) {
    const W = scoreCanvas.width, H = scoreCanvas.height;
    sctx.clearRect(0, 0, W, H);
    if (smoothPoints.length < 2) return;
    // Best-yet horizontal line.
    if (sessionBest != null && sessionBest >= lo && sessionBest <= hi) {
      sctx.strokeStyle = 'rgba(255,255,255,0.4)';
      sctx.setLineDash([3, 3]);
      sctx.beginPath();
      const yb = scaleY(sessionBest, lo, hi, H);
      sctx.moveTo(0, yb); sctx.lineTo(W, yb);
      sctx.stroke();
      sctx.setLineDash([]);
    }
    // Raw (faint).
    sctx.strokeStyle = 'rgba(96,165,250,0.3)'; sctx.lineWidth = 1;
    sctx.beginPath();
    const Nr = rawPoints.length;
    for (let i = 0; i < Nr; i++) {
      const x = (i / Math.max(Nr - 1, 1)) * W;
      const y = scaleY(rawPoints[i], lo, hi, H);
      if (i === 0) sctx.moveTo(x, y); else sctx.lineTo(x, y);
    }
    sctx.stroke();
    // Smoothed (bold).
    sctx.strokeStyle = '#60a5fa'; sctx.lineWidth = 1.5;
    sctx.beginPath();
    const Ns = smoothPoints.length;
    for (let i = 0; i < Ns; i++) {
      const x = (i / Math.max(Ns - 1, 1)) * W;
      const y = scaleY(smoothPoints[i], lo, hi, H);
      if (i === 0) sctx.moveTo(x, y); else sctx.lineTo(x, y);
    }
    sctx.stroke();
  }

  function colorForRel(rel) {
    // rel in [0,1]: 0 → red, 0.5 → yellow, 1 → green
    const g = Math.round(255 * Math.min(1, 2 * rel));
    const r = Math.round(255 * Math.min(1, 2 * (1 - rel)));
    return `rgb(${r},${g},80)`;
  }

  let sparklineSeq = 0;

  $('score-reset').addEventListener('click', () => {
    sparklineSeq++;
    rawPoints.length = 0;
    smoothPoints.length = 0;
    sessionBest = null;
    lastSmoothSeen = null;
    lastScoreT = 0;
    drawSpark(0, 1);
  });

  async function pollScore() {
    if ($('score').classList.contains('hidden')) return;
    const mySeq = sparklineSeq;
    try {
      const r = await fetch('/api/score?since=' + lastScoreT);
      const d = await r.json();
      if (mySeq !== sparklineSeq) return;  // reset happened mid-flight
      if (d.history && d.history.length) {
        for (const [t, v] of d.history) {
          rawPoints.push(v);
          const prev = smoothPoints.length ? smoothPoints[smoothPoints.length - 1] : v;
          const sv = prev * (1 - EMA_ALPHA) + v * EMA_ALPHA;
          smoothPoints.push(sv);
          if (sessionBest == null || sv > sessionBest) sessionBest = sv;
          lastScoreT = Math.max(lastScoreT, t);
        }
        while (rawPoints.length    > scoreCanvas.width) rawPoints.shift();
        while (smoothPoints.length > scoreCanvas.width) smoothPoints.shift();
      }
      const vSmooth = smoothPoints.length ? smoothPoints[smoothPoints.length - 1] : null;

      if (vSmooth == null) {
        $('score-value').textContent = '—';
        $('score-meta').textContent = d.low_texture ? 'low texture' : '';
        $('score-delta').textContent = '';
        $('score-bar').style.width = '0%';
        $('score-best-mark').style.display = 'none';
        return;
      }

      // Auto-zoom from sliding window with margin.
      const win = smoothPoints.slice(-ZOOM_WINDOW);
      let lo = Math.min(...win), hi = Math.max(...win);
      const span = Math.max(hi - lo, 0.005);
      const margin = span * 0.20;
      lo = Math.max(0, lo - margin);
      hi = Math.min(1, hi + margin);

      $('score-value').textContent = vSmooth.toFixed(3);
      const rel = (vSmooth - lo) / Math.max(hi - lo, 1e-9);
      $('score-value').style.color = colorForRel(Math.max(0, Math.min(1, rel)));

      $('score-bar').style.width = (Math.max(0, Math.min(1, rel)) * 100) + '%';
      if (sessionBest != null && sessionBest >= lo && sessionBest <= hi) {
        const relBest = (sessionBest - lo) / Math.max(hi - lo, 1e-9);
        $('score-best-mark').style.left = (relBest * 100) + '%';
        $('score-best-mark').style.display = 'block';
      } else {
        $('score-best-mark').style.display = 'none';
      }

      const dBest = vSmooth - sessionBest;
      const dEl = $('score-delta');
      if (Math.abs(dBest) < 0.0005) {
        dEl.className = 'delta flat'; dEl.textContent = '= best';
      } else if (dBest > 0) {
        dEl.className = 'delta up';
        dEl.textContent = '▲ +' + dBest.toFixed(3);
      } else {
        dEl.className = 'delta down';
        dEl.textContent = '▼ ' + dBest.toFixed(3);
      }

      $('score-meta').textContent = '';
      drawSpark(lo, hi);
    } catch (e) {
      $('score-meta').textContent = 'error';
    }
  }
  setInterval(pollScore, 250);
  pollScore();
