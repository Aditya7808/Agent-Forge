/* ShoppingGPT — vanilla JS frontend.
   Handles theme, autosizing textarea, message rendering with simple markdown,
   product card rendering, voice input via Web Speech API, and persisted theme. */

(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const messagesEl = $("#messages");
  const formEl = $("#composerForm");
  const inputEl = $("#messageInput");
  const sendBtn = $("#sendBtn");
  const charCount = $("#charCount");
  const newChatBtn = $("#newChat");
  const themeBtn = $("#themeToggle");
  const micBtn = $("#micBtn");
  const statusDot = $("#status");
  const statusLabel = $("#statusLabel");
  const msgTpl = $("#msgTemplate");
  const cardTpl = $("#cardTemplate");

  const STORAGE_KEYS = { theme: "sg.theme" };
  const ROUTE_LABELS = {
    products: "catalogue",
    policy: "policy",
    recommend: "stylist",
    chitchat: "chat",
  };

  // Theme
  const savedTheme = localStorage.getItem(STORAGE_KEYS.theme);
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  themeBtn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(STORAGE_KEYS.theme, next);
  });

  // Empty state
  function renderEmpty() {
    messagesEl.innerHTML = `
      <div class="empty">
        <div class="empty__hero">
          <span class="empty__kicker">Ready when you are</span>
          <h2>What are you in the mood for?</h2>
          <p>Search the catalogue, pull up a policy, or describe an occasion and I'll style the look.</p>
        </div>
        <div class="empty__grid">
          <button class="suggestion" data-prompt="Show me white cotton shirts under $40">
            <span class="suggestion__tag">Catalogue</span>
            <span class="suggestion__title">White cotton shirts under $40</span>
            <span class="suggestion__hint">filter by color, fabric, price</span>
          </button>
          <button class="suggestion" data-prompt="Recommend a winter outfit under $200">
            <span class="suggestion__tag">Stylist</span>
            <span class="suggestion__title">A winter outfit under $200</span>
            <span class="suggestion__hint">complete looks, occasion-led</span>
          </button>
          <button class="suggestion" data-prompt="What is your return policy?">
            <span class="suggestion__tag">Policy</span>
            <span class="suggestion__title">Return &amp; exchange policy</span>
            <span class="suggestion__hint">windows, conditions, refunds</span>
          </button>
          <button class="suggestion" data-prompt="Find me a leather jacket in size L">
            <span class="suggestion__tag">Catalogue</span>
            <span class="suggestion__title">Leather jacket, size L</span>
            <span class="suggestion__hint">stock, sizes, alternatives</span>
          </button>
        </div>
      </div>`;
    messagesEl.querySelectorAll(".suggestion").forEach((c) =>
      c.addEventListener("click", () => sendMessage(c.dataset.prompt))
    );
  }
  renderEmpty();

  // Quick prompts in sidebar
  $$(".quick").forEach((b) =>
    b.addEventListener("click", () => sendMessage(b.dataset.prompt))
  );

  // Composer behaviour
  function autosize() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 220) + "px";
    charCount.textContent = `${inputEl.value.length} / 2000`;
    sendBtn.disabled = !inputEl.value.trim();
  }
  inputEl.addEventListener("input", autosize);
  autosize();

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      formEl.requestSubmit();
    }
  });

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    sendMessage(text);
  });

  newChatBtn.addEventListener("click", async () => {
    try {
      await fetch("/api/reset", { method: "POST" });
    } catch (_) {}
    renderEmpty();
    inputEl.value = "";
    autosize();
    inputEl.focus();
  });

  // Voice input
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    let listening = false;
    micBtn.addEventListener("click", () => {
      if (listening) {
        rec.stop();
      } else {
        try { rec.start(); listening = true; micBtn.style.color = "var(--accent)"; }
        catch (_) {}
      }
    });
    rec.onresult = (event) => {
      const t = event.results[0][0].transcript;
      inputEl.value = (inputEl.value ? inputEl.value + " " : "") + t;
      autosize();
    };
    rec.onend = () => { listening = false; micBtn.style.color = ""; };
    rec.onerror = () => { listening = false; micBtn.style.color = ""; };
  } else {
    micBtn.style.opacity = "0.4";
    micBtn.title = "Voice input not supported in this browser";
  }

  // Markdown — minimal, safe
  function escape(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function renderMarkdown(text) {
    let s = escape(text);
    s = s.replace(/```([^`]+)```/g, (_, code) => `<pre><code>${code}</code></pre>`);
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|\s)\*([^*\n]+)\*/g, "$1<em>$2</em>");
    s = s.replace(/\[(P\d{3})\]/g, '<code class="prod-code">$1</code>');
    s = s.replace(/(^|\n)\s*[-•]\s+(.*?)(?=\n|$)/g, "$1<li>$2</li>");
    s = s.replace(/(<li>.*?<\/li>)(\s*<li>)/gs, "$1$2");
    s = s.replace(/(<li>[\s\S]*?<\/li>)/g, (m) => `<ul>${m}</ul>`).replace(/<\/ul>\s*<ul>/g, "");
    return s;
  }

  function timeNow() {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // Track whether the user has scrolled away from the bottom. If they have,
  // we don't yank them back when new content arrives — only stay pinned when
  // they were already at (or near) the bottom.
  let stickToBottom = true;
  const NEAR_BOTTOM_PX = 80;

  function isNearBottom() {
    const dist = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
    return dist <= NEAR_BOTTOM_PX;
  }

  messagesEl.addEventListener("scroll", () => {
    stickToBottom = isNearBottom();
  });

  function scrollToBottom(smooth = true) {
    // rAF ensures we measure after layout (images, product cards, fonts).
    requestAnimationFrame(() => {
      messagesEl.scrollTo({
        top: messagesEl.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    });
  }

  function appendMessage({ role, content, route, products }) {
    if (messagesEl.querySelector(".empty")) messagesEl.innerHTML = "";
    const wasPinned = stickToBottom || role === "user";
    const node = msgTpl.content.firstElementChild.cloneNode(true);
    node.classList.add(`msg--${role}`);
    node.querySelector(".msg__role").textContent =
      role === "user" ? "You" : "ShoppingGPT";
    node.querySelector(".msg__time").textContent = timeNow();
    if (role === "user") {
      node.querySelector(".msg__avatar").textContent = "Y";
    }
    if (route && role === "assistant") {
      const r = node.querySelector(".msg__route");
      r.textContent = ROUTE_LABELS[route] || route;
      r.hidden = false;
    }
    node.querySelector(".msg__content").innerHTML = renderMarkdown(content);

    if (products && products.length) {
      const wrap = node.querySelector(".msg__products");
      wrap.hidden = false;
      products.forEach((p) => wrap.appendChild(renderCard(p)));
    }
    messagesEl.appendChild(node);
    if (wasPinned) {
      stickToBottom = true;
      scrollToBottom();
    }
    return node;
  }

  function appendTyping() {
    const wasPinned = stickToBottom;
    const node = msgTpl.content.firstElementChild.cloneNode(true);
    node.classList.add("msg--assistant", "msg--typing");
    node.querySelector(".msg__role").textContent = "ShoppingGPT";
    node.querySelector(".msg__time").textContent = timeNow();
    node.querySelector(".msg__content").innerHTML =
      '<span class="typing"><span></span><span></span><span></span></span>';
    messagesEl.appendChild(node);
    if (wasPinned) scrollToBottom();
    return node;
  }

  function renderCard(p) {
    const a = cardTpl.content.firstElementChild.cloneNode(true);
    const img = a.querySelector(".product-card__img");
    img.dataset.glyph = p.product_code || "";
    a.querySelector(".product-card__name").textContent = p.product_name || "Unnamed product";
    const meta = [];
    if (p.color) meta.push(p.color);
    if (p.size) meta.push(`size ${p.size}`);
    if (p.material) meta.push(p.material);
    if (p.brand) meta.push(`brand ${p.brand}`);
    a.querySelector(".product-card__meta").textContent = meta.join(" · ");
    const price = a.querySelector(".product-card__price");
    price.textContent =
      p.price != null ? `$${Number(p.price).toLocaleString()}` : "—";
    const stock = a.querySelector(".product-card__stock");
    if (p.stock_quantity === 0) {
      stock.textContent = "Out of stock";
      stock.classList.add("is-out");
    } else if (p.stock_quantity <= 10) {
      stock.textContent = `${p.stock_quantity} left`;
      stock.classList.add("is-low");
    } else {
      stock.textContent = `${p.stock_quantity} in stock`;
    }
    return a;
  }

  function setStatus(state, label) {
    statusDot.classList.toggle("is-error", state === "error");
    statusLabel.textContent = label;
  }

  async function sendMessage(text) {
    appendMessage({ role: "user", content: text });
    inputEl.value = "";
    autosize();
    inputEl.focus();
    const typing = appendTyping();
    setStatus("ok", "Thinking…");

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      let data = null;
      try { data = await resp.json(); } catch (_) { /* not JSON */ }
      typing.remove();

      if (!resp.ok) {
        const detail = (data && (data.error || data.detail)) ||
          `The server replied with status ${resp.status}.`;
        appendMessage({
          role: "assistant",
          content:
            "Something went wrong while answering that.\n\n" +
            "Details: " + detail + "\n\n" +
            "Tip: if you just started the app, the very first request may " +
            "take a few seconds while OpenAI clients warm up.",
        });
        setStatus("error", `HTTP ${resp.status}`);
        return;
      }
      appendMessage({
        role: "assistant",
        content: data.reply,
        route: data.route,
        products: data.products,
      });
      setStatus("ok", `Online · ${data.elapsed_ms}ms`);
    } catch (err) {
      typing.remove();
      appendMessage({
        role: "assistant",
        content:
          "I cannot reach the backend at " + window.location.origin + ".\n\n" +
          "Most likely the Flask server is not running. To start it:\n\n" +
          "1. Open a terminal in the project folder.\n" +
          "2. Run:  pip install -r requirements.txt\n" +
          "3. Make sure your .env file has OPENAI_API_KEY set.\n" +
          "4. Run:  python app.py\n" +
          "5. Reload this page.\n\n" +
          "If the server is running, check the terminal for an error message.",
      });
      setStatus("error", "Offline");
    }
  }

  // Probe the backend on boot so the status pill reflects reality.
  (async function probe() {
    try {
      const r = await fetch("/api/health", { cache: "no-store" });
      if (r.ok) {
        const j = await r.json();
        setStatus("ok", `Online · ${j.app || "ready"}`);
      } else {
        setStatus("error", `HTTP ${r.status}`);
      }
    } catch (_) {
      setStatus("error", "Offline");
    }
  })();
})();
