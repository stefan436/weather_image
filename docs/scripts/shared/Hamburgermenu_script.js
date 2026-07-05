document.addEventListener("DOMContentLoaded", () => {
  const placeholder = document.getElementById('navbar-placeholder');
  if (!placeholder) return;

  // 1. Relativen Pfad dynamisch bestimmen (für GitHub Pages und lokale Entwicklung)
  const isSubfolder = window.location.pathname.includes('/sites/');
  const navbarPath = isSubfolder ? '../scripts/shared/navbar.html' : './scripts/shared/navbar.html';

  // 2. Navbar laden
  fetch(navbarPath)
    .then(response => {
      if (!response.ok) throw new Error(`Navbar konnte nicht geladen werden: ${response.status}`);
      return response.text();
    })
    .then(data => {
      // 3. HTML sicher einfügen
      placeholder.innerHTML = data;
      
      // 4. Logik initialisieren, da das DOM jetzt garantiert existiert
      initNavbarLogik(isSubfolder);
    })
    .catch(err => console.error(err));
});

function initNavbarLogik(isSubfolder) {
  const hamburgerIcon = document.getElementById('hamburger-icon');
  const navMenu = document.getElementById('nav-menu');

  if (!hamburgerIcon || !navMenu) return;

  // Pfade für Unterordner umschreiben
  if (isSubfolder) {
    document.querySelectorAll('.navbar a').forEach(link => {
      const href = link.getAttribute('href');
      if (href && href.startsWith('./')) {
        link.setAttribute('href', href.replace('./', '../'));
      }
    });
  }

  // Menü-Toggles
  function toggleMenu() {
    navMenu.classList.toggle('active');
    hamburgerIcon.classList.toggle('open');
    document.body.classList.toggle('menu-open', navMenu.classList.contains('active'));
  }

  hamburgerIcon.addEventListener('click', toggleMenu);

  navMenu.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      navMenu.classList.remove('active');
      hamburgerIcon.classList.remove('open');
      document.body.classList.remove('menu-open');
    });
  });

  document.addEventListener('click', (e) => {
    if (navMenu.classList.contains('active') && !navMenu.contains(e.target) && !hamburgerIcon.contains(e.target)) {
      navMenu.classList.remove('active');
      hamburgerIcon.classList.remove('open');
      document.body.classList.remove('menu-open');
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navMenu.classList.contains('active')) {
      navMenu.classList.remove('active');
      hamburgerIcon.classList.remove('open');
      document.body.classList.remove('menu-open');
    }
  });
}