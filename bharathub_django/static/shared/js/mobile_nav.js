/**
 * static/shared/js/mobile_nav.js
 *
 * mobile_nav.css తో పాటు వాడే చిన్న టోగుల్ స్క్రిప్ట్ -- మొబైల్ లో
 * ☰ బటన్ (టాప్‌నావ్ లో, లేదా బాటమ్ '.mobile-nav-bar' లో "More")
 * నొక్కితే '.sidebar' డ్రాయర్ ని తెరుస్తుంది/మూస్తుంది.
 *
 * dashboard_base.html లో అన్ని dashboard/సబ్-పేజీలకీ ఒక్కసారే
 * లోడ్ అవుతుంది -- ప్రతి పేజీ ఇదే toggleMobileDrawer() ఫంక్షన్ ని
 * వాడొచ్చు, వేరే గా JS రాయాల్సిన అవసరం లేదు.
 */
(function () {
  "use strict";

  function ensureBackdrop() {
    let backdrop = document.querySelector(".mobile-nav-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "mobile-nav-backdrop";
      document.body.appendChild(backdrop);
      backdrop.addEventListener("click", closeMobileDrawer);
    }
    return backdrop;
  }

  window.openMobileDrawer = function () {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    sidebar.classList.add("mobile-open");
    ensureBackdrop().classList.add("open");
    document.body.style.overflow = "hidden"; // డ్రాయర్ తెరిచినప్పుడు వెనుక పేజీ స్క్రోల్ కాకుండా
  };

  window.closeMobileDrawer = function () {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.classList.remove("mobile-open");
    const backdrop = document.querySelector(".mobile-nav-backdrop");
    if (backdrop) backdrop.classList.remove("open");
    document.body.style.overflow = "";
  };

  window.toggleMobileDrawer = function () {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar && sidebar.classList.contains("mobile-open")) {
      closeMobileDrawer();
    } else {
      openMobileDrawer();
    }
  };

  // సైడ్‌బార్ లో ఏదైనా లింక్/బటన్ నొక్కితే (నావిగేట్ అయ్యేముందు లేదా
  // అదే పేజీలో ట్యాబ్ మారినప్పుడు), డ్రాయర్ ఆటోమేటిక్‌గా మూసేయాలి --
  // లేకపోతే కొత్త పేజీ/సెక్షన్ వెనుక డ్రాయర్ తెరిచే ఉండిపోతుంది.
  document.addEventListener("click", (e) => {
    const link = e.target.closest(".sidebar a, .sidebar button");
    if (link) closeMobileDrawer();
  });

  // వెడల్పు పెంచి (ఉదా: ఫోన్ ని tablet సైజ్ కి తిప్పితే) డెస్క్‌టాప్
  // బ్రేక్‌పాయింట్ దాటితే, డ్రాయర్ open state ఇరుక్కుపోకుండా క్లియర్
  // చేయడం.
  window.addEventListener("resize", () => {
    if (window.innerWidth > 900) closeMobileDrawer();
  });
})();
