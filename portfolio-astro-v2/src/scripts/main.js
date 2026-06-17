// Scroll-triggered fade-up for .js-fade elements
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.2 }
);

document.querySelectorAll('.js-fade').forEach((el) => observer.observe(el));

// Creators carousel fade-in on load
document.querySelectorAll('.creator-card').forEach((card, i) => {
  setTimeout(() => card.classList.add('visible'), i * 120);
});
