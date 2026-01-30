// Language switcher for AI Cooperation website
// Auto-detects browser language and provides manual toggle

(function () {
  const STORAGE_KEY = "aico-lang";
  const SITE_BASE = "/cooperation.tw/";

  function getPath() {
    return window.location.pathname;
  }

  function isZhPage() {
    return getPath().includes("/zh/");
  }

  function getAlternatePath() {
    const path = getPath();
    if (isZhPage()) {
      // zh → en: remove /zh/ segment
      return path.replace(/\/zh\//, "/");
    } else {
      // en → zh: insert /zh/ after site base
      const idx = path.indexOf(SITE_BASE);
      if (idx !== -1) {
        const after = idx + SITE_BASE.length;
        return path.slice(0, after) + "zh/" + path.slice(after);
      }
      return path.replace(/\/$/, "") + "/zh/";
    }
  }

  function getBrowserLang() {
    const lang = navigator.language || navigator.languages?.[0] || "";
    return lang.toLowerCase();
  }

  // Auto-redirect on first visit
  function autoRedirect() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return;

    const browserLang = getBrowserLang();
    const isZh =
      browserLang.startsWith("zh") ||
      browserLang === "zh-tw" ||
      browserLang === "zh-hant";
    const onZhPage = isZhPage();

    if (isZh && !onZhPage) {
      localStorage.setItem(STORAGE_KEY, "zh");
      window.location.href = getAlternatePath();
    } else if (!isZh && onZhPage) {
      localStorage.setItem(STORAGE_KEY, "en");
      window.location.href = getAlternatePath();
    }
  }

  // Create language toggle button in navbar
  function createToggle() {
    // Find the right-side navbar list (has ms-auto class)
    var rightNav = document.querySelector(
      ".navbar-collapse .navbar-nav.ms-auto"
    );

    if (!rightNav) {
      // Fallback: find the container and append directly
      var container =
        document.querySelector(".navbar .container-fluid") ||
        document.querySelector(".navbar .container");
      if (!container) return;

      var btn = createButton();
      container.appendChild(btn);
      return;
    }

    var li = document.createElement("li");
    li.className = "nav-item";
    var btn = createButton();
    li.appendChild(btn);
    // Insert as first item in the right nav (before GitHub icon)
    rightNav.insertBefore(li, rightNav.firstChild);
  }

  function createButton() {
    var btn = document.createElement("a");
    btn.className = "nav-link lang-toggle";
    btn.href = getAlternatePath();
    btn.style.cssText =
      "cursor:pointer; font-weight:600; padding:0.25rem 0.75rem; " +
      "border:1px solid rgba(255,255,255,0.3); border-radius:4px; " +
      "margin-left:0.5rem; font-size:0.85rem; color:#F4F6F8; " +
      "text-decoration:none; white-space:nowrap;";

    if (isZhPage()) {
      btn.textContent = "EN";
      btn.title = "Switch to English";
    } else {
      btn.textContent = "中文";
      btn.title = "切換為中文";
    }

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      localStorage.setItem(STORAGE_KEY, isZhPage() ? "en" : "zh");
      window.location.href = getAlternatePath();
    });

    return btn;
  }

  // Update navbar links for zh pages: rewrite hrefs and translate labels
  function updateNavbarForZh() {
    if (!isZhPage()) return;

    var zhLabels = {
      Methodology: "方法論",
      Framework: "架構",
      Skills: "技能",
      Lab: "Lab",
      Service: "服務",
      Blog: "部落格",
    };

    document.querySelectorAll(".navbar-nav .nav-link").forEach(function (link) {
      // Translate menu text
      var span = link.querySelector(".menu-text");
      var text = span ? span.textContent.trim() : link.textContent.trim();
      if (zhLabels[text]) {
        if (span) {
          span.textContent = zhLabels[text];
        } else {
          link.textContent = zhLabels[text];
        }
      }

      // Rewrite hrefs to zh/ versions
      var href = link.getAttribute("href");
      if (!href || href.includes("/zh/") || href.startsWith("http")) return;

      // On zh pages, links are ../section/page.html (going up to root)
      // Rewrite to ./section/page.html (staying within zh/)
      if (href.startsWith("../")) {
        link.setAttribute("href", "./" + href.slice(3));
        return;
      }

      // Handle relative paths like ./methodology/index.html
      if (href.startsWith("./")) {
        link.setAttribute("href", "./zh/" + href.slice(2));
        return;
      }

      // Handle absolute paths like /cooperation.tw/methodology/index.html
      if (href.startsWith(SITE_BASE) && !href.startsWith(SITE_BASE + "zh/")) {
        link.setAttribute(
          "href",
          SITE_BASE + "zh/" + href.slice(SITE_BASE.length)
        );
      }
    });
  }

  // Run
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      autoRedirect();
      createToggle();
      updateNavbarForZh();
    });
  } else {
    autoRedirect();
    createToggle();
    updateNavbarForZh();
  }
})();
