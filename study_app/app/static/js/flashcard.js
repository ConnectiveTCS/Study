/**
 * flashcard.js  —  SM-2 study session UI
 * Handles card display, 3-D flip animation, and AJAX rating submission.
 */

/**
 * @param {Array}  cards   — [{id, front, back, interval, ease_factor}]
 * @param {string} rateUrl — Flask endpoint URL for POST /flashcards/rate
 */
function initStudySession(cards, rateUrl) {
  if (!cards || cards.length === 0) {
    document.getElementById("study-area").style.display = "none";
    document.getElementById("session-done").style.display = "block";
    return;
  }

  const studyArea = document.getElementById("study-area");
  const doneBanner = document.getElementById("session-done");
  const counter = document.getElementById("card-counter");
  const progressFill = document.getElementById("progress-fill");

  let queue = [...cards]; // mutable copy
  let current = 0; // index into queue
  let flipped = false;

  function render() {
    if (current >= queue.length) {
      studyArea.style.display = "none";
      doneBanner.style.display = "block";
      return;
    }

    const card = queue[current];
    counter.textContent = `${current + 1} / ${queue.length}`;
    progressFill.style.width = `${Math.round((current / queue.length) * 100)}%`;
    flipped = false;

    studyArea.innerHTML = `
      <div class="flip-scene" id="flip-scene" onclick="flipCard()" role="button"
           aria-label="Card front — click to reveal answer" tabindex="0">
        <div class="flip-card" id="flip-card">
          <div class="flip-face front">
            <span>${escapeHtml(card.front)}</span>
          </div>
          <div class="flip-face back">
            <span>${escapeHtml(card.back)}</span>
          </div>
        </div>
      </div>
      <p class="flip-hint">Click card to reveal answer</p>
      <div class="rating-buttons" id="rating-buttons" style="display:none;" aria-label="Rate this card">
        <button class="rating-btn rating-again" onclick="rate(0)" aria-label="Again (forgot)">Again<br><span style="font-size:0.7rem;font-weight:400;">&lt;1 d</span></button>
        <button class="rating-btn rating-hard"  onclick="rate(2)" aria-label="Hard">Hard<br><span style="font-size:0.7rem;font-weight:400;">+few d</span></button>
        <button class="rating-btn rating-good"  onclick="rate(4)" aria-label="Good">Good<br><span style="font-size:0.7rem;font-weight:400;">+${card.interval}d</span></button>
        <button class="rating-btn rating-easy"  onclick="rate(5)" aria-label="Easy">Easy<br><span style="font-size:0.7rem;font-weight:400;">+long</span></button>
      </div>
    `;

    // Keyboard support
    document
      .getElementById("flip-scene")
      .addEventListener("keydown", function (e) {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          flipCard();
        }
      });
  }

  window.flipCard = function () {
    if (flipped) return;
    flipped = true;
    document.getElementById("flip-card").classList.add("flipped");
    document.getElementById("rating-buttons").style.display = "grid";
    document
      .getElementById("flip-scene")
      .setAttribute("aria-label", "Card back — now rate your recall");
  };

  window.rate = function (quality) {
    const card = queue[current];
    // Disable buttons immediately to prevent double-click
    document
      .querySelectorAll(".rating-btn")
      .forEach((b) => (b.disabled = true));

    fetch(rateUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ card_id: card.id, quality }),
    })
      .then((r) => r.json())
      .then(() => {
        // If "Again" (quality < 3) re-queue card near the end
        if (quality < 3) {
          queue.push(card);
        }
        current++;
        render();
      })
      .catch(() => {
        // On error, still advance
        current++;
        render();
      });
  };

  // Keyboard shortcuts for rating (after flip)
  document.addEventListener("keydown", function (e) {
    if (!flipped) return;
    const map = { 1: 0, 2: 2, 3: 4, 4: 5 };
    if (map[e.key] !== undefined) rate(map[e.key]);
  });

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  render();
}
