// BookWise front-end: favourites, star rating, toast, mobile menu. No external libraries.
(function () {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const loggedIn = document.body.dataset.auth === "1";

  function toast(msg) {
    const t = document.getElementById("toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2200);
  }

  async function api(method, url, body) {
    const res = await fetch(url, {
      method, credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ")");
    return data;
  }

  function needLogin() {
    window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
  }

  // ---- favourites (heart buttons on cards + big button on detail page)
  document.querySelectorAll("[data-book].fav-btn, .fav-btn-large").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!loggedIn) return needLogin();
      try {
        const r = await api("POST", "/api/books/" + btn.dataset.book + "/favorite");
        document.querySelectorAll('[data-book="' + btn.dataset.book + '"].fav-btn').forEach((b) => b.classList.toggle("active", r.favorite));
        const big = document.getElementById("fav-large");
        if (big && big.dataset.book === btn.dataset.book) {
          big.textContent = r.favorite ? "♥ In your favourites" : "♡ Add to favourites";
          big.classList.toggle("btn-primary", r.favorite); big.classList.toggle("btn-ghost", !r.favorite);
        }
        toast(r.favorite ? "Added to favourites" : "Removed from favourites");
      } catch (err) { toast(err.message); }
    });
  });

  // ---- star rating
  const box = document.getElementById("star-input");
  if (box) {
    const stars = [...box.querySelectorAll(".star")];
    const clear = document.getElementById("clear-rating");
    const paint = (v) => stars.forEach((s, i) => s.classList.toggle("on", i < v));
    paint(Number(box.dataset.value));
    stars.forEach((s) => {
      s.addEventListener("mouseenter", () => paint(Number(s.dataset.value)));
      s.addEventListener("mouseleave", () => paint(Number(box.dataset.value)));
      s.addEventListener("click", async () => {
        try {
          const r = await api("POST", "/api/books/" + box.dataset.book + "/rate", { rating: Number(s.dataset.value) });
          box.dataset.value = r.my_rating; paint(r.my_rating); clear.hidden = false;
          document.getElementById("avg-rating").textContent = r.avg_rating.toFixed(1);
          document.getElementById("rating-count").textContent = r.ratings_count;
          toast("Thanks! You rated this " + r.my_rating + " ★");
        } catch (err) { toast(err.message); }
      });
    });
    clear.addEventListener("click", async () => {
      try {
        const r = await api("DELETE", "/api/books/" + box.dataset.book + "/rate");
        box.dataset.value = 0; paint(0); clear.hidden = true;
        document.getElementById("avg-rating").textContent = r.avg_rating.toFixed(1);
        document.getElementById("rating-count").textContent = r.ratings_count;
        toast("Rating removed");
      } catch (err) { toast(err.message); }
    });
  }

  // ---- mobile menu
  const toggle = document.querySelector(".nav-toggle");
  toggle.addEventListener("click", () => {
    const open = document.getElementById("nav-links").classList.toggle("open");
    toggle.setAttribute("aria-expanded", open);
  });
})();
