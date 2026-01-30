// Language switcher for AI Cooperation website
// Auto-detects browser language and provides manual toggle

(function () {
  const STORAGE_KEY = "aico-lang";
  const ZH_PREFIX = "/zh/";
  const SITE_BASE = "/cooperation.tw/"; // GitHub Pages base path

  function getPath() {
    return window.location.pathname;
  }

  function isZhPage() {
    const path = getPath();
    return path.includes(ZH_PREFIX);
  }

  function getAlternatePath() {
    const path = getPath();
    if (isZhPage()) {
      // zh → en: remove /zh/ segment
      return path.replace(/\/zh\//, "/");
    } else {
      // en → zh: insert /zh/ after base path
      const base = path.indexOf(SITE_BASE);
      if (base !== -1) {
        const after = base + SITE_BASE.length;
        return path.slice(0, after) + "zh/" + path.slice(after);
      }
      // fallback: just prepend /zh/
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
    if (saved) return; // user already chose

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

  // Create language toggle button
  function createToggle() {
    const navbar = document.querySelector(".navbar-nav.navbar-nav-scroll");
    const navRight =
      document.querySelector(".navbar-collapse .ms-auto") ||
      document.querySelector(".navbar-nav:last-child");

    // Find the right side of navbar
    const container =
      document.querySelector(".navbar .container-fluid") ||
      document.querySelector(".navbar .container");
    if (!container) return;

    const btn = document.createElement("a");
    btn.className = "nav-link lang-toggle";
    btn.href = getAlternatePath();
    btn.style.cssText =
      "cursor:pointer; font-weight:600; padding:0.25rem 0.75rem; border:1px solid rgba(255,255,255,0.3); border-radius:4px; margin-left:0.5rem; font-size:0.85rem; color: #F4F6F8; text-decoration: none;";

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

    // Insert into navbar right section
    const rightNav = document.querySelector(
      ".navbar-collapse .navbar-nav:not(.navbar-nav-scroll)"
    );
    if (rightNav) {
      const li = document.createElement("li");
      li.className = "nav-item";
      li.appendChild(btn);
      rightNav.insertBefore(li, rightNav.firstChild);
    } else {
      container.appendChild(btn);
    }
  }

  // Update navbar links for zh pages
  function updateNavbarForZh() {
    if (!isZhPage()) return;

    const zhLabels = {
      Methodology: "方法論",
      Framework: "架構",
      Skills: "技能",
      Lab: "Lab",
      Service: "服務",
      Blog: "部落格",
    };

    document.querySelectorAll(".navbar-nav .nav-link").forEach(function (link) {
      const text = link.textContent.trim();
      if (zhLabels[text]) {
        link.textContent = zhLabels[text];
      }

      // Update hrefs to point to zh/ versions
      const href = link.getAttribute("href");
      if (href && !href.includes("/zh/") && !href.startsWith("http")) {
        // Convert relative paths to zh/ paths
        const base = getPath().substring(
          0,
          getPath().indexOf(SITE_BASE) + SITE_BASE.length
        );
        if (href.startsWith(base)) {
          link.setAttribute(
            "href",
            href.replace(SITE_BASE, SITE_BASE + "zh/")
          );
        }
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
