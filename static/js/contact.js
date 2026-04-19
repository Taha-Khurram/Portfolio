// FAQ Toggle
document.querySelectorAll(".faq-question").forEach(button => {
  button.addEventListener("click", () => {
    const faqCard = button.parentElement;
    faqCard.classList.toggle("active");
  });
});

// Handle Netlify Form Success Message
document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('success') === 'true') {
    // Create success message
    const flashContainer = document.createElement('div');
    flashContainer.className = 'flash-container';
    flashContainer.innerHTML = '<div class="alert alert-success">Thank you for reaching out! Your message has been sent successfully.</div>';

    // Insert after contact header
    const contactHeader = document.querySelector('.contact-header');
    if (contactHeader) {
      contactHeader.after(flashContainer);
    }

    // Remove success param from URL
    window.history.replaceState({}, document.title, window.location.pathname);

    // Auto fade after 4s
    setTimeout(() => {
      flashContainer.style.transition = "opacity 0.6s ease";
      flashContainer.style.opacity = "0";
      setTimeout(() => flashContainer.remove(), 600);
    }, 4000);
  }

  // Legacy flash message handling
  const alertBox = document.querySelector(".flash-container");
  if (alertBox && !urlParams.get('success')) {
    setTimeout(() => {
      alertBox.style.transition = "opacity 0.6s ease";
      alertBox.style.opacity = "0";
      setTimeout(() => alertBox.remove(), 600);
    }, 4000);
  }
});
