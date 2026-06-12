document.addEventListener('DOMContentLoaded', () => {
  const hamburgerIcon = document.getElementById('hamburger-icon');
  const navMenu = document.getElementById('nav-menu');

  function toggleMenu() {
    navMenu.classList.toggle('active');
    hamburgerIcon.classList.toggle('open');
    document.body.classList.toggle('menu-open', navMenu.classList.contains('active'));
  }

  hamburgerIcon.addEventListener('click', toggleMenu);

  // Menü beim Link‑Klick schließen
  navMenu.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      navMenu.classList.remove('active');
      hamburgerIcon.classList.remove('open');
      document.body.classList.remove('menu-open');
    });
  });

  // Schließen, wenn man außerhalb (links neben das Menü) klickt
  document.addEventListener('click', (e) => {
    // Nur ausführen, wenn das Menü überhaupt geöffnet ist
    if (navMenu.classList.contains('active')) {
      // Wenn der Klick NICHT im Menü und NICHT auf dem Hamburger-Icon war
      if (!navMenu.contains(e.target) && !hamburgerIcon.contains(e.target)) {
        navMenu.classList.remove('active');
        hamburgerIcon.classList.remove('open');
        document.body.classList.remove('menu-open');
      }
    }
  });

  // ESC zum Schließen
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navMenu.classList.contains('active')) {
      navMenu.classList.remove('active');
      hamburgerIcon.classList.remove('open');
      document.body.classList.remove('menu-open');
    }
  });
});