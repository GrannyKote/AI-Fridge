// Демонстрационные данные кладовой. hoursLeft < 0 — продукт просрочен.
const PRODUCTS = [
  { id: 1, name: "Кефир 2.5%", amount: "0.5 л", category: "dairy", emoji: "🥛", hoursLeft: -72 },
  { id: 2, name: "Молоко 2.5%", amount: "0.8 л", category: "dairy", emoji: "🥛", hoursLeft: -24 },
  { id: 3, name: "Куриное филе", amount: "300 г", category: "meat", emoji: "🍗", hoursLeft: 15 },
  { id: 4, name: "Сметана 20%", amount: "150 г", category: "dairy", emoji: "🥛", hoursLeft: 48 },
  { id: 5, name: "Творог 5%", amount: "200 г", category: "dairy", emoji: "🧀", hoursLeft: 52 },
  { id: 6, name: "Помидоры черри", amount: "250 г", category: "veg", emoji: "🍅", hoursLeft: 70 },
  { id: 7, name: "Фарш говяжий", amount: "400 г", category: "meat", emoji: "🥩", hoursLeft: 76 },
  { id: 8, name: "Сыр Гауда", amount: "220 г", category: "dairy", emoji: "🧀", hoursLeft: 94 },
  { id: 9, name: "Хлеб бородинский", amount: "400 г", category: "grocery", emoji: "🍞", hoursLeft: 120 },
  { id: 10, name: "Лосось слабосолёный", amount: "200 г", category: "meat", emoji: "🐟", hoursLeft: 144 },
  { id: 11, name: "Огурцы", amount: "500 г", category: "veg", emoji: "🥒", hoursLeft: 168 },
  { id: 12, name: "Йогурт греческий", amount: "4 × 120 г", category: "dairy", emoji: "🥣", hoursLeft: 192 },
  { id: 13, name: "Колбаса варёная", amount: "350 г", category: "meat", emoji: "🌭", hoursLeft: 216 },
  { id: 14, name: "Яйца С1", amount: "10 шт", category: "grocery", emoji: "🥚", hoursLeft: 288 },
  { id: 15, name: "Морковь", amount: "1 кг", category: "veg", emoji: "🥕", hoursLeft: 336 },
  { id: 16, name: "Яблоки", amount: "1.2 кг", category: "veg", emoji: "🍎", hoursLeft: 384 },
  { id: 17, name: "Масло сливочное", amount: "180 г", category: "dairy", emoji: "🧈", hoursLeft: 504 },
  { id: 18, name: "Картофель", amount: "2 кг", category: "veg", emoji: "🥔", hoursLeft: 720 },
  { id: 19, name: "Пельмени", amount: "800 г", category: "frozen", emoji: "🥟", hoursLeft: 2160 },
  { id: 20, name: "Рис басмати", amount: "900 г", category: "grocery", emoji: "🍚", hoursLeft: 4320 },
];

const SOON_THRESHOLD_HOURS = 96;

const GROUPS = [
  {
    key: "expired",
    title: "Просрочено",
    icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4 2.5 20h19L12 4Z"/><path d="M12 10v4M12 17h.01"/></svg>',
  },
  {
    key: "soon",
    title: "Скоро испортится",
    icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 2h6"/></svg>',
  },
  {
    key: "fresh",
    title: "Свежие",
    icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 12.5 5 5L20 6.5"/></svg>',
  },
];

const groupsEl = document.getElementById("groups");
const emptyEl = document.getElementById("empty");
const chipsEl = document.getElementById("chips");
const searchEl = document.getElementById("search");
const toastEl = document.getElementById("toast");
const cardTemplate = document.getElementById("card-template");

let products = [...PRODUCTS];
let activeCategory = "all";
let query = "";

function statusOf(product) {
  if (product.hoursLeft < 0) return "expired";
  return product.hoursLeft <= SOON_THRESHOLD_HOURS ? "soon" : "fresh";
}

function badgeTextOf(product) {
  const hours = product.hoursLeft;
  if (hours < 0) return `⚠️ Просрочен ${Math.ceil(-hours / 24)} дн.`;
  if (hours < 24) return `⏱ ${hours} ч.`;
  return `⏳ ${Math.round(hours / 24)} дн.`;
}

function renderStats() {
  const counts = { total: products.length, soon: 0, expired: 0 };
  for (const product of products) {
    const status = statusOf(product);
    if (status !== "fresh") counts[status] += 1;
  }
  for (const [key, value] of Object.entries(counts)) {
    document.querySelector(`[data-stat="${key}"]`).textContent = value;
  }
}

function createCard(product) {
  const status = statusOf(product);
  const card = cardTemplate.content.firstElementChild.cloneNode(true);

  card.dataset.id = product.id;
  card.classList.toggle("card--expired", status === "expired");

  const thumb = card.querySelector(".card__thumb");
  thumb.classList.add(`card__thumb--${product.category}`);
  thumb.textContent = product.emoji;

  card.querySelector(".card__title").textContent = product.name;
  card.querySelector(".card__amount").textContent = product.amount;

  const badge = card.querySelector(".card__badge");
  badge.classList.add(`card__badge--${status}`);
  badge.textContent = badgeTextOf(product);

  return card;
}

function render() {
  const normalizedQuery = query.trim().toLowerCase();
  const visible = products.filter((product) => {
    const matchesCategory = activeCategory === "all" || product.category === activeCategory;
    const matchesQuery = product.name.toLowerCase().includes(normalizedQuery);
    return matchesCategory && matchesQuery;
  });

  groupsEl.replaceChildren();

  for (const group of GROUPS) {
    const items = visible.filter((product) => statusOf(product) === group.key);
    if (items.length === 0) continue;

    const section = document.createElement("section");
    section.className = `group group--${group.key}`;
    section.innerHTML = `
      <h2 class="group__head">${group.icon}${group.title} · ${items.length}</h2>
      <div class="group__list"></div>
    `;

    const list = section.querySelector(".group__list");
    for (const product of items) list.append(createCard(product));

    groupsEl.append(section);
  }

  emptyEl.hidden = visible.length > 0;
  renderStats();
}

let toastTimer;
function showToast(message) {
  toastEl.textContent = message;
  toastEl.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("is-visible"), 2000);
}

chipsEl.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;

  activeCategory = chip.dataset.category;
  for (const item of chipsEl.children) item.classList.toggle("is-active", item === chip);
  chip.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
  render();
});

searchEl.addEventListener("input", (event) => {
  query = event.target.value;
  render();
});

groupsEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;

  const id = Number(button.closest(".card").dataset.id);
  const product = products.find((item) => item.id === id);
  if (!product) return;

  products = products.filter((item) => item.id !== id);
  render();
  showToast(button.dataset.action === "use" ? `«${product.name}» использован` : `«${product.name}» удалён`);
});

render();
