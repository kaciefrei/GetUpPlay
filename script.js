const burger = document.getElementById('burger');
const closeBtn = document.getElementById('close');
const NavBar = document.getElementById('NavBar');
const logoNegatif = document.querySelector('.logo-negatif');

const isSmallScreen = window.matchMedia('(max-height: 450px)');

burger.addEventListener('click', () => {
    NavBar.classList.add('active');
    NavBar.style.height = '100vh';
    burger.style.display = "none";
    QSN.style.display = "block";
    Catalogue.style.display = "block";

    if (isSmallScreen.matches) {
        logoNegatif.style.display = 'none';
    }

    document.body.style.overflow = 'hidden';
});

closeBtn.addEventListener('click', () => {
    NavBar.classList.remove('active');
    NavBar.style.height = '10vh';
    burger.style.display = "flex";
    QSN.style.display = "none";
    Catalogue.style.display = "none";

    if (isSmallScreen.matches) {
        logoNegatif.style.display = 'block';
    }
    document.body.style.overflow = 'auto';
});