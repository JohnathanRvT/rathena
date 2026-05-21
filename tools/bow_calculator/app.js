// Pre-Renewal Bow Calculator — Full Auto-Optimizer
// Automatically ranks every bow with optimal arrow + card combination

let selectedRankItem = null;

// ─── Element Damage Table (Attacker Arrow Element vs Defender Element, Lv1) ───
const ELEMENT_TABLE = {
    "Neutral": { "Neutral": 1.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 0.25, "Undead": 1.0 },
    "Water":   { "Neutral": 1.0, "Water": 0.5, "Earth": 1.0, "Fire": 2.0, "Wind": 0.5, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 1.0,  "Undead": 1.0 },
    "Earth":   { "Neutral": 1.0, "Water": 1.0, "Earth": 0.5, "Fire": 0.5, "Wind": 2.0, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 1.0,  "Undead": 1.0 },
    "Fire":    { "Neutral": 1.0, "Water": 0.5, "Earth": 2.0, "Fire": 0.5, "Wind": 1.0, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 1.0,  "Undead": 1.5 },
    "Wind":    { "Neutral": 1.0, "Water": 2.0, "Earth": 0.5, "Fire": 1.0, "Wind": 0.5, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 1.0,  "Undead": 1.0 },
    "Poison":  { "Neutral": 1.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 0.0, "Holy": 0.5, "Shadow": 0.5, "Ghost": 1.0,  "Undead": 0.5 },
    "Holy":    { "Neutral": 1.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 1.25, "Holy": 0.0, "Shadow": 1.5, "Ghost": 1.0,  "Undead": 1.5 },
    "Shadow":  { "Neutral": 1.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 0.5, "Holy": 1.5, "Shadow": 0.0, "Ghost": 1.0,  "Undead": 0.5 },
    "Ghost":   { "Neutral": 0.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 1.0, "Holy": 1.0, "Shadow": 1.0, "Ghost": 1.25, "Undead": 1.0 },
    "Undead":  { "Neutral": 1.0, "Water": 1.0, "Earth": 1.0, "Fire": 1.0, "Wind": 1.0, "Poison": 0.5, "Holy": 1.5, "Shadow": 0.5, "Ghost": 1.0,  "Undead": 0.0 }
};

// Bow Size Penalties: Small 100%, Medium 100%, Large 75%
const SIZE_PENALTY = {
    "Small": 1.0,
    "Medium": 1.0,
    "Large": 0.75
};

const SAFE_REFINE = { 1: 7, 2: 6, 3: 5, 4: 4 };
const REFINE_ATK_PER_LEVEL = { 1: 2, 2: 3, 3: 5, 4: 7 };

// ─── Utility Functions ────────────────────────────────────────────────────────

function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

/**
 * Generate combinations WITH repetition (order-independent).
 * For n items choosing k: C(n+k-1, k) results.
 * Much smaller than permutations (n^k), since card slot order doesn't matter.
 */
function generateCombosWithRep(items, slots) {
    const results = [];
    function gen(combo, startIdx, depth) {
        if (depth === slots) {
            results.push([...combo]);
            return;
        }
        for (let i = startIdx; i < items.length; i++) {
            combo.push(items[i]);
            gen(combo, i, depth + 1);
            combo.pop();
        }
    }
    gen([], 0, 0);
    return results;
}

// ─── Initialize ───────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    const debouncedOptimize = debounce(runOptimization, 200);

    // Player stat inputs → re-run full optimization
    ["dex-input", "str-input", "luk-input"].forEach(id => {
        document.getElementById(id).addEventListener("input", debouncedOptimize);
    });

    // Refine slider → only update the detail panel (ranking always uses safe refine)
    document.getElementById("refine-input").addEventListener("input", () => {
        document.getElementById("refine-val").textContent =
            `+${document.getElementById("refine-input").value}`;
        updateDetailsPanel();
    });

    // Target monster inputs → re-run full optimization
    ["target-size", "target-race", "target-element", "target-class"].forEach(id => {
        document.getElementById(id).addEventListener("change", runOptimization);
    });
    document.getElementById("target-def").addEventListener("input", debouncedOptimize);

    // Safe Refine shortcut
    document.getElementById("btn-safe-refine").addEventListener("click", () => {
        if (!selectedRankItem) return;
        const safe = SAFE_REFINE[selectedRankItem.bow.WeaponLevel] || 4;
        document.getElementById("refine-input").value = safe;
        document.getElementById("refine-val").textContent = `+${safe}`;
        updateDetailsPanel();
    });

    // Run first optimization
    runOptimization();
});

// ─── Damage Calculation Core (Pre-Renewal) ────────────────────────────────────

function calculatePhysicalDamage(bow, arrow, refine, cards, stats, target) {
    // 1. Status ATK = DEX + floor(DEX/10)^2 + floor(STR/5) + floor(LUK/5)
    const dex = stats.dex;
    const dexMilestone = Math.floor(dex / 10);
    const statusAtk = dex + (dexMilestone * dexMilestone)
                    + Math.floor(stats.str / 5)
                    + Math.floor(stats.luk / 5);

    // 2. Refine ATK
    const baseRefineBonus = REFINE_ATK_PER_LEVEL[bow.WeaponLevel] || 7;
    let refineAtk = refine * baseRefineBonus;

    // Over-refine average random bonus
    const safeRef = SAFE_REFINE[bow.WeaponLevel] || 4;
    let avgOverrefineBonus = 0;
    if (refine > safeRef) {
        const overRefMaxRand = { 1: 3, 2: 5, 3: 8, 4: 14 };
        const maxRand = overRefMaxRand[bow.WeaponLevel] || 14;
        avgOverrefineBonus = (refine - safeRef) * (1 + maxRand) / 2;
    }

    // 3. Arrow ATK
    const arrowAtk = arrow ? arrow.Attack : 0;

    // 4. Flat ATK from cards
    let flatAtkCards = 0;
    cards.forEach(c => {
        if (c && c.Modifier && c.Modifier.type === "flat_atk") {
            flatAtkCards += c.Modifier.value;
        }
    });

    // Total weapon ATK
    const totalWeaponAtk = bow.Attack + refineAtk + avgOverrefineBonus + arrowAtk + flatAtkCards;

    // 5. Size penalty
    const sizePenalty = SIZE_PENALTY[target.size] || 1.0;
    const baseSubtotal = statusAtk + (totalWeaponAtk * sizePenalty);

    // 6. Card multipliers (additive within group, multiplicative across groups)
    let raceMult = 1.0, eleMult = 1.0, sizeMult = 1.0, rangedMult = 1.0, classMult = 1.0;

    cards.forEach(c => {
        if (!c || !c.Modifier) return;
        const m = c.Modifier;
        if      (m.type === "race"    && m.target === target.race)    raceMult  += m.value / 100;
        else if (m.type === "element" && m.target === target.element) eleMult   += m.value / 100;
        else if (m.type === "size"    && m.target === target.size)    sizeMult  += m.value / 100;
        else if (m.type === "ranged")                                 rangedMult += m.value / 100;
        else if (m.type === "class"   && m.target === target.class)  classMult += m.value / 100;
    });

    // 7. Bow-Arrow combo bonuses
    let hasCombo = false;
    if (arrow) {
        if (bow.AegisName.includes("Hunter_Bow") && arrow.AegisName === "Hunting_Arrow") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Orc_Archer_Bow") && arrow.AegisName === "Steel_Arrow") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Elven_Bow") && arrow.AegisName === "Arrow_Of_Elf") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Burning_Bow") && arrow.AegisName === "Fire_Arrow") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Frozen_Bow") && arrow.AegisName === "Crystal_Arrow") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Earth_Bow") && arrow.AegisName === "Stone_Arrow") {
            hasCombo = true;
        } else if (bow.AegisName.includes("Gust_Bow") && arrow.AegisName === "Arrow_Of_Wind") {
            hasCombo = true;
        }
    }

    if (hasCombo) {
        let comboBonus = 0.50;
        if (bow.AegisName.includes("Burning_Bow") || bow.AegisName.includes("Frozen_Bow") ||
            bow.AegisName.includes("Earth_Bow")   || bow.AegisName.includes("Gust_Bow")) {
            comboBonus = 0.25;
        }
        rangedMult += comboBonus;
    }

    // 8. Element property modifier (arrow element vs target element)
    const arrowElement = arrow ? arrow.Element : "Neutral";
    const elementTable = ELEMENT_TABLE[arrowElement] || ELEMENT_TABLE["Neutral"];
    const elementPropertyMod = elementTable[target.element] || 1.0;

    // 9. Combined damage
    const rawDamage = baseSubtotal * raceMult * eleMult * sizeMult * rangedMult * classMult * elementPropertyMod;

    // 10. Hard DEF percentage reduction
    const finalDamage = Math.max(1, Math.floor(rawDamage * ((100 - target.def) / 100)));

    return {
        statusAtk,
        weaponAtk: totalWeaponAtk,
        sizePenalty,
        flatAtkCards,
        multipliers: { race: raceMult, element: eleMult, size: sizeMult, ranged: rangedMult, class: classMult, property: elementPropertyMod },
        hasCombo,
        finalDamage
    };
}

// ─── Input Helpers ────────────────────────────────────────────────────────────

function getPlayerStats() {
    return {
        dex: parseInt(document.getElementById("dex-input").value) || 1,
        str: parseInt(document.getElementById("str-input").value) || 1,
        luk: parseInt(document.getElementById("luk-input").value) || 1
    };
}

function getTargetStats() {
    return {
        size:    document.getElementById("target-size").value,
        race:    document.getElementById("target-race").value,
        element: document.getElementById("target-element").value,
        def:     parseInt(document.getElementById("target-def").value) || 0,
        class:   document.getElementById("target-class").value
    };
}

function getRefineLevel() {
    return parseInt(document.getElementById("refine-input").value) || 0;
}

// ─── Optimization Engine ──────────────────────────────────────────────────────

function runOptimization() {
    // Show loading overlay
    document.getElementById("loading-overlay").classList.add("active");

    // Defer computation so the loading UI can paint
    requestAnimationFrame(() => {
        setTimeout(() => {
            performOptimization();
            document.getElementById("loading-overlay").classList.remove("active");
        }, 20);
    });
}

function performOptimization() {
    const stats  = getPlayerStats();
    const target = getTargetStats();

    // 1. Filter cards relevant to this target
    const relevantCards = CARD_DATABASE.filter(c => {
        const m = c.Modifier;
        return (
            (m.type === "race"    && m.target === target.race)    ||
            (m.type === "element" && m.target === target.element) ||
            (m.type === "size"    && m.target === target.size)    ||
            (m.type === "ranged")                                 ||
            (m.type === "flat_atk")                               ||
            (m.type === "class"   && m.target === target.class)
        );
    });

    // Fallback to generic damage cards if nothing specific matches
    if (relevantCards.length === 0) {
        CARD_DATABASE.forEach(c => {
            if (c.Modifier.type === "ranged" || c.Modifier.type === "flat_atk") {
                relevantCards.push(c);
            }
        });
    }

    // 2. Pre-generate card combinations per slot count (0–4)
    //    Using combinations-with-repetition for massive perf improvement
    const cardCombosBySlots = {};
    for (let s = 0; s <= 4; s++) {
        if (s === 0 || relevantCards.length === 0) {
            cardCombosBySlots[s] = [[]];
        } else {
            cardCombosBySlots[s] = generateCombosWithRep(relevantCards, s);
        }
    }

    // 3. For each bow, find the best (arrow + card combo) that maximises damage
    const bowRanks = [];

    BOW_DATABASE.forEach(bow => {
        const safeRef = SAFE_REFINE[bow.WeaponLevel] || 4;
        const combos  = cardCombosBySlots[Math.min(bow.Slots, 4)] || [[]];

        let bestDamage = 0;
        let bestArrow  = ARROW_DATABASE[0] || null;
        let bestCards  = [];

        for (let a = 0; a < ARROW_DATABASE.length; a++) {
            const arrow = ARROW_DATABASE[a];
            for (let c = 0; c < combos.length; c++) {
                const res = calculatePhysicalDamage(bow, arrow, safeRef, combos[c], stats, target);
                if (res.finalDamage > bestDamage) {
                    bestDamage = res.finalDamage;
                    bestArrow  = arrow;
                    bestCards  = combos[c];
                }
            }
        }

        bowRanks.push({
            bow,
            refineUsed: safeRef,
            damage: bestDamage,
            cardsUsed: bestCards,
            arrowUsed: bestArrow
        });
    });

    // 4. Sort descending by damage
    bowRanks.sort((a, b) => b.damage - a.damage);

    // 5. Render ranking list
    renderRanking(bowRanks);

    // 6. Auto-select: keep previously selected bow if still present, else pick #1
    const prevId  = selectedRankItem ? selectedRankItem.bow.Id : null;
    const resel   = prevId ? bowRanks.find(r => r.bow.Id === prevId) : null;
    selectBow(resel || bowRanks[0]);
}

// ─── Selection & Detail View ──────────────────────────────────────────────────

function selectBow(rankItem) {
    if (!rankItem) return;
    selectedRankItem = rankItem;

    // Set refine slider to this bow's safe refine
    document.getElementById("refine-input").value = rankItem.refineUsed;
    document.getElementById("refine-val").textContent = `+${rankItem.refineUsed}`;

    // Show detail panel
    document.getElementById("weapon-details-empty").style.display  = "none";
    document.getElementById("weapon-details-content").style.display = "block";

    updateDetailsPanel();

    // Highlight active item in rank list
    document.querySelectorAll(".best-bow-item").forEach(el => el.classList.remove("selected"));
    const el = document.querySelector(`[data-bow-id="${rankItem.bow.Id}"]`);
    if (el) {
        el.classList.add("selected");
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function updateDetailsPanel() {
    if (!selectedRankItem) return;

    const item   = selectedRankItem;
    const stats  = getPlayerStats();
    const target = getTargetStats();
    const refine = getRefineLevel();

    // Recalculate with current refine slider (may differ from safe refine)
    const res = calculatePhysicalDamage(item.bow, item.arrowUsed, refine, item.cardsUsed, stats, target);

    // ── Header
    document.getElementById("selected-bow-name").textContent = item.bow.Name;
    document.getElementById("selected-bow-badge").textContent = `Lv${item.bow.WeaponLevel}`;
    document.getElementById("selected-bow-meta").innerHTML =
        `Base ATK <strong>${item.bow.Attack}</strong> &nbsp;·&nbsp; ${item.bow.Slots} Slot${item.bow.Slots !== 1 ? "s" : ""} &nbsp;·&nbsp; Safe Refine <strong>+${item.refineUsed}</strong>`;

    // ── Best Arrow
    document.getElementById("selected-arrow-name").textContent = item.arrowUsed.Name;
    document.getElementById("selected-arrow-detail").textContent =
        `ATK ${item.arrowUsed.Attack}  ·  ${item.arrowUsed.Element} Element`;

    // ── Optimal Cards
    const cardsContainer = document.getElementById("detail-cards-container");
    cardsContainer.innerHTML = "";
    if (item.bow.Slots === 0) {
        cardsContainer.innerHTML = '<div class="no-slots-msg">No card slots on this weapon</div>';
    } else if (item.cardsUsed.length === 0) {
        cardsContainer.innerHTML = '<div class="no-slots-msg">No beneficial cards found</div>';
    } else {
        item.cardsUsed.forEach(card => {
            const pill = document.createElement("div");
            pill.className = "slot-circle filled";
            pill.textContent = card.Name.replace(" Card", "");
            cardsContainer.appendChild(pill);
        });
    }

    // ── Stat boxes
    document.getElementById("stat-status-atk").textContent  = res.statusAtk;
    document.getElementById("stat-weapon-atk").textContent  = Math.floor(res.weaponAtk);
    document.getElementById("stat-ele-mod").textContent      = `${Math.round(res.multipliers.property * 100)}%`;
    document.getElementById("stat-size-penalty").textContent = `${Math.round(res.sizePenalty * 100)}%`;

    // ── Damage breakdown
    document.getElementById("detail-base-atk").textContent   = item.bow.Attack;
    const refineAndFlatAtk = Math.floor(res.weaponAtk - item.bow.Attack - item.arrowUsed.Attack);
    document.getElementById("detail-refine-atk").textContent = refineAndFlatAtk;
    document.getElementById("detail-arrow-atk").textContent  = item.arrowUsed.Attack;

    const m = res.multipliers;
    document.getElementById("detail-card-multipliers").textContent =
        `Race ×${m.race.toFixed(2)} · Ele ×${m.element.toFixed(2)} · Size ×${m.size.toFixed(2)} · Ranged ×${m.ranged.toFixed(2)}`;

    // ── Combo notice
    const comboNotice = document.getElementById("combo-notice");
    if (res.hasCombo) {
        comboNotice.style.display = "block";
        comboNotice.innerHTML = `🔥 <strong>COMBO ACTIVE</strong> — ${item.bow.Name} + ${item.arrowUsed.Name}`;
    } else {
        comboNotice.style.display = "none";
    }

    // ── Final damage
    document.getElementById("detail-final-damage").textContent = res.finalDamage;

    // ── Chart
    drawSVGChart(stats, target);
}

// ─── Ranking Renderer ─────────────────────────────────────────────────────────

function renderRanking(bowRanks) {
    const container = document.getElementById("ranked-bows-container");
    container.innerHTML = "";

    const topDamage = bowRanks[0] ? bowRanks[0].damage : 1;

    bowRanks.forEach((item, index) => {
        const div = document.createElement("div");
        div.className = "best-bow-item" + (index === 0 ? " first-place" : "");
        div.dataset.bowId = item.bow.Id;

        // Format card list
        let cardsText = "No cards";
        if (item.cardsUsed.length > 0) {
            const counts = {};
            item.cardsUsed.forEach(c => {
                const name = c.Name.replace(" Card", "");
                counts[name] = (counts[name] || 0) + 1;
            });
            cardsText = Object.entries(counts).map(([n, ct]) => `${ct}× ${n}`).join(", ");
        }

        const pct = Math.round((item.damage / topDamage) * 100);

        div.innerHTML = `
            <div class="bow-item-left">
                <div class="rank-number">${index + 1}</div>
                <div class="bow-item-info">
                    <h3>${item.bow.Name} <span class="badge badge-level">Lv${item.bow.WeaponLevel}</span></h3>
                    <div class="item-meta">ATK ${item.bow.Attack} · +${item.refineUsed} Safe · ${item.bow.Slots} slot${item.bow.Slots !== 1 ? "s" : ""}</div>
                    <div class="item-arrow">🏹 ${item.arrowUsed.Name} <span class="arrow-ele-tag">${item.arrowUsed.Element}</span></div>
                    <div class="item-cards">💎 ${cardsText}</div>
                </div>
            </div>
            <div class="bow-item-right">
                <div class="damage-val">${item.damage}</div>
                <div class="comparison-percentage">${pct}%</div>
            </div>
        `;

        div.addEventListener("click", () => selectBow(item));
        container.appendChild(div);
    });
}

// ─── SVG Chart: Damage vs DEX Milestones ──────────────────────────────────────

function drawSVGChart(stats, target) {
    if (!selectedRankItem) return;

    const item = selectedRankItem;
    const chartContainer = document.getElementById("chart-container");
    chartContainer.innerHTML = '<h3 class="chart-title">Damage vs DEX Milestones</h3>';

    const currentDex = stats.dex;
    const refine = getRefineLevel();
    const dexSteps = [
        Math.max(10, currentDex - 20),
        Math.max(10, currentDex - 10),
        currentDex,
        currentDex + 10,
        currentDex + 20,
        currentDex + 30
    ];

    const damageData = dexSteps.map(d => {
        const stepStats = { ...stats, dex: d };
        return calculatePhysicalDamage(item.bow, item.arrowUsed, refine, item.cardsUsed, stepStats, target).finalDamage;
    });

    const width = 330, height = 120, padding = 20;
    const graphWidth = width - padding * 2;
    const graphHeight = height - padding * 2;

    const maxDamage = Math.max(...damageData) || 1;
    const minDamage = Math.min(...damageData) || 0;
    const range = maxDamage - minDamage * 0.8 || 1;

    let points = "", gridLines = "", labels = "";

    dexSteps.forEach((dex, i) => {
        const x = padding + (i / (dexSteps.length - 1)) * graphWidth;
        const y = padding + graphHeight - ((damageData[i] - minDamage * 0.8) / range) * graphHeight;
        points += `${x},${y} `;

        gridLines += `<line x1="${x}" y1="${padding}" x2="${x}" y2="${padding + graphHeight}" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;

        const isCurrent = dex === currentDex;
        const color  = isCurrent ? "var(--accent-color)" : "var(--text-secondary)";
        const weight = isCurrent ? "800" : "400";
        labels += `<text x="${x}" y="${height - 2}" fill="${color}" font-weight="${weight}" font-size="8.5" text-anchor="middle">${dex}</text>`;
    });

    const dots = dexSteps.map((d, i) => {
        const x = padding + (i / (dexSteps.length - 1)) * graphWidth;
        const y = padding + graphHeight - ((damageData[i] - minDamage * 0.8) / range) * graphHeight;
        const isCurrent = d === currentDex;
        return `<circle cx="${x}" cy="${y}" r="${isCurrent ? 4.5 : 3.5}" fill="${isCurrent ? "var(--accent-color)" : "#0b0813"}" stroke="var(--accent-color)" stroke-width="2"/>`;
    }).join("");

    const svg = `
        <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow:visible">
            <defs>
                <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stop-color="var(--accent-color)" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="var(--accent-color)" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            ${gridLines}
            <polygon points="${padding},${padding + graphHeight} ${points} ${padding + graphWidth},${padding + graphHeight}" fill="url(#chart-grad)"/>
            <polyline points="${points}" fill="none" stroke="var(--accent-color)" stroke-width="2"/>
            ${dots}
            ${labels}
        </svg>`;

    const wrapper = document.createElement("div");
    wrapper.innerHTML = svg;
    chartContainer.appendChild(wrapper);
}
