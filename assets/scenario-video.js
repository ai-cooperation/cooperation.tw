/*
 * 情境影片卡：點卡 → 封面放大成全螢幕（過程動畫）→ 播影片 → 播完縮回原卡、原卡下方出現 CTA。
 * 全螢幕時 9:16 影片置中、兩側以同支影片的模糊版填滿（.sv-ambient canvas）。
 *
 * 一張卡啟用的寫法（首頁 #scenarios，其他情境照抄改值即可，JS 不用動）：
 *   <div class="sv-item">
 *     <a class="sv-card" href="<影片網址，無 JS 時直接開影片>"
 *        data-scenario-id="s1" data-scenario-video="<mp4>">
 *       <span class="sv-cover"><img src="<直式封面 9:16>" ...></span>
 *       <span class="sv-body"><span class="sv-kicker">..</span><h3 class="sv-title">..</h3><span class="sv-pain">..</span></span>
 *     </a>
 *     <a class="sv-after" href="<CTA 網址>" hidden>..</a>
 *   </div>
 *
 * 退路：沒有 JS 或任何錯誤 → 卡片是一般連結，直接開影片檔。
 * prefers-reduced-motion → 不做放大動畫、不自動播放，給原生播放控制列。
 * 量測：每個階段送 gtag('event','scenario_video',{sv_action,...})，
 *       window.__svMetrics 記錄點擊到第一個影片畫面的毫秒數（click_to_frame_ms）。
 */
(function () {
  var cards = document.querySelectorAll('a.sv-card[data-scenario-video]');
  if (!cards.length) return;

  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.__svMetrics = window.__svMetrics || [];

  function track(action, card, extra) {
    var p = { sv_action: action, scenario_id: card.dataset.scenarioId || '', page_path: location.pathname };
    for (var k in extra || {}) p[k] = extra[k];
    window.__svMetrics.push(Object.assign({ t: Math.round(performance.now()) }, p));
    if (typeof gtag === 'function') gtag('event', 'scenario_video', Object.assign({ transport_type: 'beacon' }, p));
  }

  function vt(fn) {
    if (reduced || !document.startViewTransition) { fn(); return Promise.resolve(); }
    return document.startViewTransition(fn).finished.catch(function () {});
  }

  function text(card, sel) {
    var n = card.querySelector(sel);
    return n ? n.textContent : '';
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }

  function build(card, after) {
    var cover = card.querySelector('.sv-cover img');
    var el = document.createElement('div');
    el.className = 'sv-overlay';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', text(card, '.sv-title') || '情境影片');
    el.innerHTML =
      '<div class="sv-shell">' +
      '<div class="sv-phone">' +
      '<canvas class="sv-ambient" width="36" height="64" aria-hidden="true"></canvas>' +
      '<video class="sv-video" playsinline preload="auto"' + (cover ? ' poster="' + esc(cover.currentSrc || cover.src) + '"' : '') + (reduced ? ' controls' : '') + '></video>' +
      '<div class="sv-progress" aria-hidden="true"><span></span></div>' +
      '<button type="button" class="sv-sound" hidden>開啟聲音</button>' +
      '<button type="button" class="sv-tap" hidden>點一下播放</button>' +
      '<button type="button" class="sv-close" aria-label="關閉影片，回到頁面">關閉</button>' +
      '</div>' +
      '<div class="sv-side">' +
      '<span class="sv-kicker">' + esc(text(card, '.sv-kicker')) + '</span>' +
      '<p class="sv-side-title">' + esc(text(card, '.sv-title')) + '</p>' +
      '<p class="sv-side-pain">' + esc(text(card, '.sv-pain')) + '</p>' +
      (after ? '<a class="btn-primary sv-cta" href="' + esc(after.getAttribute('href')) + '">' + esc(after.textContent) + '</a>' : '') +
      '</div>' +
      '</div>';
    return el;
  }

  function open(card) {
    var t0 = performance.now();
    var item = card.closest('.sv-item');
    var after = item ? item.querySelector('.sv-after') : null;
    var cover = card.querySelector('.sv-cover');
    var el = build(card, after);
    var phone = el.querySelector('.sv-phone');
    var video = el.querySelector('.sv-video');
    var bar = el.querySelector('.sv-progress span');
    var sound = el.querySelector('.sv-sound');
    var done = false, quart = 0, framed = false;
    track('click', card);

    // 兩側模糊填色：把影片畫到 36x64 的 canvas，CSS 放大加模糊。開播前先畫封面。
    var amb = el.querySelector('.sv-ambient');
    var actx = amb.getContext ? amb.getContext('2d') : null;
    function paint(src) { try { actx.drawImage(src, 0, 0, amb.width, amb.height); } catch (e) { /* 尚無畫面 */ } }
    var coverImg = card.querySelector('.sv-cover img');
    if (actx && coverImg && coverImg.complete) paint(coverImg);
    if (actx && video.requestVideoFrameCallback) {
      var loop = function () { if (done) return; paint(video); video.requestVideoFrameCallback(loop); };
      video.requestVideoFrameCallback(loop);
    } else if (actx) {
      video.addEventListener('timeupdate', function () { paint(video); });
    }

    // 點下去就開始抓影片，跟放大動畫並行。
    video.src = card.dataset.scenarioVideo;

    function onKey(e) { if (e.key === 'Escape') finish('close'); }

    function finish(reason) {
      if (done) return; done = true;
      track(reason, card, { at_s: +video.currentTime.toFixed(1) });
      document.removeEventListener('keydown', onKey);
      video.pause();
      phone.style.viewTransitionName = 'sv-hero';
      vt(function () {
        phone.style.viewTransitionName = '';
        el.remove();
        document.body.classList.remove('sv-open');
        if (cover) cover.style.viewTransitionName = 'sv-hero';
        if (reason === 'complete' && item) item.classList.add('sv-watched');
        if (reason === 'complete' && after) after.hidden = false;
      }).then(function () {
        if (cover) cover.style.viewTransitionName = '';
        (reason === 'complete' && after ? after : card).focus({ preventScroll: true });
      });
    }

    function startVideo() {
      if (reduced) return;
      if (video.requestVideoFrameCallback) {
        video.requestVideoFrameCallback(function () {
          if (framed) return; framed = true;
          track('first_frame', card, { click_to_frame_ms: Math.round(performance.now() - t0) });
        });
      }
      // 點擊算使用者手勢，先試有聲播放；瀏覽器擋下就改靜音播放並露出「開啟聲音」。
      video.muted = false;
      video.play().then(function () { sound.textContent = '靜音'; sound.hidden = false; track('play', card, { muted: false }); }).catch(function (err) {
        track('autoplay_muted', card, { reason: err && err.name || '' });
        video.muted = true;
        sound.hidden = false;
        video.play().then(function () { track('play', card, { muted: true }); }).catch(function () {
          var tap = el.querySelector('.sv-tap');
          tap.hidden = false;
          tap.onclick = function () { tap.hidden = true; video.play(); track('play_after_tap', card); };
          track('autoplay_blocked', card);
        });
      });
    }

    sound.addEventListener('click', function () {
      video.muted = !video.muted;
      sound.textContent = video.muted ? '開啟聲音' : '靜音';
      track(video.muted ? 'mute' : 'unmute', card);
    });
    video.addEventListener('timeupdate', function () {
      if (!video.duration) return;
      var r = video.currentTime / video.duration;
      bar.style.width = (r * 100).toFixed(1) + '%';
      while (quart < 3 && r >= (quart + 1) * 0.25) { quart++; track('progress_' + quart * 25, card); }
    });
    video.addEventListener('ended', function () { finish('complete'); });
    el.querySelector('.sv-close').addEventListener('click', function () { finish('close'); });
    el.addEventListener('click', function (e) { if (e.target === el || e.target.classList.contains('sv-shell')) finish('close'); });
    var cta = el.querySelector('.sv-cta');
    if (cta) cta.addEventListener('click', function () { track('cta', card, { at_s: +video.currentTime.toFixed(1) }); });
    document.addEventListener('keydown', onKey);

    if (cover) cover.style.viewTransitionName = 'sv-hero';
    vt(function () {
      if (cover) cover.style.viewTransitionName = '';
      phone.style.viewTransitionName = 'sv-hero';
      document.body.appendChild(el);
      document.body.classList.add('sv-open');
      // 一放進頁面就播，不等放大動畫結束：首幀越快越好。
      // 不可在 append 之前呼叫 play()：游離的 video 先 play 再被插入頁面，
      // Chrome 會以 AbortError 拒絕有聲播放，只能退回靜音（2026-11-20 實測）。
      startVideo();
    }).then(function () {
      phone.style.viewTransitionName = '';
      el.querySelector('.sv-close').focus({ preventScroll: true });
    });
  }

  cards.forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      try { open(card); } catch (err) { location.href = card.getAttribute('href'); }
    });
  });
})();
