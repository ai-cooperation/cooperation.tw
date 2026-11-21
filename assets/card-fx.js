/*
 * 卡片轉場（課程卡 .ccard、作品卡 .pcard）：
 *   點卡 → 圖片從原位放大到畫面中央 → 有 data-fx-video 就播約 4 秒短片（Flow 由同張圖生成）
 *   → 淡出 → 換到目的頁，目的頁從同色底淡入（_quarto.yml header 的 fx-in 片段）。
 * 2026-11-21 使用者裁定：不加光掃、浮塵、熱氣等額外特效，不提供轉場樣式切換，只做淡出。
 * 沒有短片的卡片只停一下就淡出；短片還沒載好就不等，維持靜態圖。滑鼠移到卡片上就先預載。
 * 任何點擊、Esc、Enter 直接前往目的頁；系統「減少動態效果」時不播轉場。
 */
(function () {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var cards = document.querySelectorAll('a.ccard, a.pcard');
  if (!cards.length) return;

  var T_LIFT = 700, T_VIDEO = 3600, T_STILL = 700, T_OUT = 700;
  window.__fxMetrics = window.__fxMetrics || [];

  function ease(t) { return 1 - Math.pow(1 - t, 3); }
  function clamp(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  function go(href) {
    try { sessionStorage.setItem('fx-in', '1'); } catch (e) { /* 無痕模式等：目的頁就不淡入 */ }
    location.href = href;
  }

  function play(card) {
    var src = card.querySelector('img');
    var href = card.getAttribute('href');
    var title = (card.querySelector('h3') || {}).textContent || '';
    var r = src.getBoundingClientRect();
    var vw = innerWidth, vh = innerHeight;
    var w = Math.min(vw * (vw < 761 ? 0.92 : 0.72), 980), h = w * r.height / r.width;
    if (h > vh * 0.62) { h = vh * 0.62; w = h * r.width / r.height; }
    var cx = (vw - w) / 2, cy = (vh - h) / 2 - vh * 0.04;
    var t0 = performance.now(), done = false, navigated = false;
    var vsrc = card.dataset.fxVideo;
    var hold = vsrc ? T_VIDEO : T_STILL;

    var el = document.createElement('div');
    el.className = 'fx-overlay';
    el.innerHTML =
      '<div class="fx-fog"></div>' +
      '<div class="fx-stage" style="left:' + cx + 'px;top:' + cy + 'px;width:' + w + 'px;height:' + h + 'px">' +
      '<div class="fx-pic"><img alt="" src="' + (src.currentSrc || src.src) + '">' +
      (vsrc ? '<video class="fx-vid" muted playsinline preload="auto" src="' + vsrc + '"></video>' : '') +
      '</div></div>' +
      '<p class="fx-title" style="top:' + (cy + h + 22) + 'px">' + title.replace(/[<&]/g, '') + '</p>' +
      '<button type="button" class="fx-skip">略過 →</button>';
    document.body.appendChild(el);
    document.body.classList.add('fx-open');
    var stage = el.querySelector('.fx-stage'), vid = el.querySelector('.fx-vid'), vidOn = false;
    var fog = el.querySelector('.fx-fog'), ttl = el.querySelector('.fx-title'), btn = el.querySelector('.fx-skip');

    // 從卡片原位起飛
    var sx = r.width / w, dx = r.left - cx, dy = r.top - cy;
    stage.style.transformOrigin = '0 0';

    function track(a) {
      window.__fxMetrics.push({ a: a, t: Math.round(performance.now() - t0) });
      if (typeof gtag === 'function') gtag('event', 'card_fx', { fx_action: a, transport_type: 'beacon' });
    }
    function skip() { if (!navigated) { navigated = true; done = true; track('skip'); go(href); } }
    el.addEventListener('click', skip);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' || e.key === 'Enter') skip(); });
    addEventListener('pagehide', function () { done = true; }, { once: true });
    track('click');

    function frame(now) {
      if (done) return;
      var t = now - t0, a1 = T_LIFT, a2 = a1 + hold, a3 = a2 + T_OUT;

      // 起飛：卡片原位 → 畫面中央
      var k = ease(clamp(t / a1));
      var s = sx + (1 - sx) * k;
      stage.style.transform = 'translate(' + dx * (1 - k) + 'px,' + dy * (1 - k) + 'px) scale(' + s + ')';

      // 淡出：圖、標題、按鈕一起退，底色補滿
      var o = clamp((t - a2) / T_OUT);
      var show = 1 - o;
      stage.style.opacity = show;
      stage.style.boxShadow = '0 18px 50px rgba(40,49,61,' + (0.22 * k * show).toFixed(3) + ')';
      fog.style.opacity = (0.86 * k + 0.14 * o).toFixed(3);
      ttl.style.opacity = clamp((t - a1 - 200) / 400) * show;
      btn.style.opacity = show;

      if (vid && !vidOn && t >= a1 && vid.readyState >= 2) {
        vidOn = true;
        vid.play().then(function () { vid.classList.add('on'); track('video'); }).catch(function () { vid = null; });
      }
      if (t >= a3 && !navigated) { navigated = true; track('complete'); go(href); return; }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  cards.forEach(function (card) {
    if (!card.querySelector('img')) return;
    if (card.dataset.fxVideo) {
      var pre = function () {
        if (card.__fxPre) return; card.__fxPre = 1;
        var l = document.createElement('link'); l.rel = 'preload'; l.as = 'video'; l.href = card.dataset.fxVideo; document.head.appendChild(l);
      };
      card.addEventListener('pointerenter', pre); card.addEventListener('touchstart', pre, { passive: true }); card.addEventListener('focus', pre);
    }
    card.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      try { play(card); } catch (err) { location.href = card.getAttribute('href'); }
    });
  });
})();
