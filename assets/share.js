/*
 * 導覽列的分享按鈕：放在搜尋圖示旁邊，手機收合選單時也看得到（PWA 沒有網址列，靠它分享）。
 * 有系統分享面板（手機、Safari、Edge）就叫出面板分享目前這頁；沒有就複製網址並短暫提示。
 * 分享的網址去掉查詢參數與 #，避免帶出追蹤或內部參數。
 * 量測：gtag('event','share',{method}) — method 為 native / copy / copy_failed。
 */
(function () {
  var anchor = document.getElementById('quarto-search');
  if (!anchor || document.querySelector('.share-btn')) return;

  var btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'share-btn';
  btn.setAttribute('aria-label', '分享這一頁');
  btn.title = '分享';
  btn.innerHTML = '<i class="bi bi-share" aria-hidden="true"></i>';
  anchor.parentNode.insertBefore(btn, anchor);

  function track(method) {
    if (typeof gtag === 'function') gtag('event', 'share', { method: method, content_type: 'page', item_id: location.pathname });
  }

  function toast(msg) {
    var t = document.createElement('div');
    t.className = 'share-toast';
    t.setAttribute('role', 'status');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('out'); }, 1800);
    setTimeout(function () { t.remove(); }, 2300);
  }

  function copy(url) {
    var ok = function () { track('copy'); toast('已複製連結'); };
    var fail = function () { track('copy_failed'); toast('無法自動複製，請從網址列複製'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(ok, fail);
    } else {
      fail();
    }
  }

  btn.addEventListener('click', function () {
    var url = location.origin + location.pathname;
    var title = document.title;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).then(function () { track('native'); }).catch(function (e) {
        if (e && e.name === 'AbortError') return; // 使用者自己關掉面板
        copy(url);
      });
    } else {
      copy(url);
    }
  });
})();
