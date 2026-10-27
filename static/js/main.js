/**
 * JEEVANPATH — Interactive UI & Modal Controllers
 */

document.addEventListener("DOMContentLoaded", function () {
  // --- Modal Open & Close System ---
  const modalTriggers = document.querySelectorAll("[data-modal-target]");
  const modalCloses = document.querySelectorAll("[data-modal-close]");

  modalTriggers.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const targetId = this.getAttribute("data-modal-target");
      const modal = document.getElementById(targetId);
      if (modal) {
        modal.classList.add("active");
      }
    });
  });

  modalCloses.forEach((btn) => {
    btn.addEventListener("click", function () {
      const modal = this.closest(".modal-overlay");
      if (modal) {
        modal.classList.remove("active");
      }
    });
  });

  // Close modal when clicking outside box
  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", function (e) {
      if (e.target === this) {
        this.classList.remove("active");
      }
    });
  });

  // --- Dynamic Livestock Total Counter in Farmer Form ---
  const cattleInput = document.getElementById("input_cattle_count");
  const buffaloInput = document.getElementById("input_buffalo_count");
  const otherInput = document.getElementById("input_other_count");
  const totalDisplay = document.getElementById("display_total_animals");

  function updateTotalCount() {
    if (!totalDisplay) return;
    const c = parseInt(cattleInput ? cattleInput.value : 0) || 0;
    const b = parseInt(buffaloInput ? buffaloInput.value : 0) || 0;
    const o = parseInt(otherInput ? otherInput.value : 0) || 0;
    totalDisplay.textContent = c + b + o;
  }

  if (cattleInput && buffaloInput) {
    [cattleInput, buffaloInput, otherInput].forEach((input) => {
      if (input) {
        input.addEventListener("input", updateTotalCount);
      }
    });
  }

  // --- Demo GPS Autofill helper ---
  const autofillBtns = document.querySelectorAll(".btn-autofill-gps");
  autofillBtns.forEach((btn) => {
    btn.addEventListener("click", function () {
      const latInput = document.getElementById(this.getAttribute("data-lat-id"));
      const lngInput = document.getElementById(this.getAttribute("data-lng-id"));
      const villageSelect = document.getElementById(this.getAttribute("data-village-id"));

      // Random minor jitter around Majuli flood plain for realistic variety
      const baseLat = 26.9400 + Math.random() * 0.12;
      const baseLng = 94.1500 + Math.random() * 0.14;

      if (latInput) latInput.value = baseLat.toFixed(4);
      if (lngInput) lngInput.value = baseLng.toFixed(4);
    });
  });

  // --- Quick Dispatch Modal Pre-fill ---
  const dispatchButtons = document.querySelectorAll(".btn-open-dispatch");
  dispatchButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const farmerId = this.getAttribute("data-farmer-id");
      const farmerName = this.getAttribute("data-farmer-name");
      const animalCount = this.getAttribute("data-animal-count");
      const village = this.getAttribute("data-village");

      const farmerIdInput = document.getElementById("dispatch_farmer_id");
      const farmerInfoBox = document.getElementById("dispatch_farmer_info");

      if (farmerIdInput) farmerIdInput.value = farmerId;
      if (farmerInfoBox) {
        farmerInfoBox.innerHTML = `
          <strong>Farmer:</strong> ${farmerName} (${village})<br>
          <strong>Livestock Needing Evacuation:</strong> <span class="badge badge-critical">${animalCount} Animals</span>
        `;
      }

      const modal = document.getElementById("modal-dispatch-rescue");
      if (modal) modal.classList.add("active");
    });
  });

  // --- Auto-dismiss flash messages after 6s ---
  const flashMessages = document.querySelectorAll(".flash-message");
  flashMessages.forEach((msg) => {
    setTimeout(() => {
      msg.style.opacity = "0";
      msg.style.transition = "opacity 0.5s ease";
      setTimeout(() => msg.remove(), 500);
    }, 6000);
  });
});
