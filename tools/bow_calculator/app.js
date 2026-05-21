// Pre-Renewal Bow Calculator Application Logic

// DOM Elements
let currentBow = null;
let currentArrow = null;
let activeCards = [];
let targetSlotIndex = 0; // index of slot currently being edited

// Element damage multipliers table (Attacker Element vs Defender Element)
// Row: Attacker (Arrow), Column: Defender (Monster)
// 10 elements: Neutral, Water, Earth, Fire, Wind, Poison, Holy, Shadow, Ghost, Undead
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

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    // Populate Bow Select
    const bowSelect = document.getElementById("bow-select");
    BOW_DATABASE.sort((a, b) => b.Attack - a.Attack).forEach(bow => {
        const option = document.createElement("option");
        option.value = bow.Id;
        option.textContent = `${bow.Name} (ATK ${bow.Attack}, ${bow.Slots} slots, Lv${bow.WeaponLevel})`;
        bowSelect.appendChild(option);
    });

    // Populate Arrow Select
    const arrowSelect = document.getElementById("arrow-select");
    ARROW_DATABASE.sort((a, b) => b.Attack - a.Attack).forEach(arrow => {
        const option = document.createElement("option");
        option.value = arrow.Id;
        option.textContent = `${arrow.Name} (ATK ${arrow.Attack}, Element: ${arrow.Element})`;
        arrowSelect.appendChild(option);
    });

    // Setup Event Listeners
    bowSelect.addEventListener("change", handleBowChange);
    arrowSelect.addEventListener("change", handleArrowChange);
    
    // Stats Event Listeners
    ["dex-input", "str-input", "luk-input", "refine-input"].forEach(id => {
        document.getElementById(id).addEventListener("input", () => {
            if (id === "refine-input") {
                document.getElementById("refine-val").textContent = `+${document.getElementById(id).value}`;
            }
            updateCalculations();
        });
    });

    // Target Event Listeners
    ["target-size", "target-race", "target-element", "target-def"].forEach(id => {
        document.getElementById(id).addEventListener("change", updateCalculations);
        if (id === "target-def") {
            document.getElementById(id).addEventListener("input", updateCalculations);
        }
    });

    // Safe Refine Button
    document.getElementById("btn-safe-refine").addEventListener("click", setSafeRefine);

    // Optimize Cards Button
    document.getElementById("btn-optimize-cards").addEventListener("click", autoOptimizeCards);

    // Card Modal Close
    document.getElementById("modal-close").addEventListener("click", closeModal);
    window.addEventListener("click", (e) => {
        if (e.target === document.getElementById("card-modal")) {
            closeModal();
        }
    });

    // Initial setups
    if (BOW_DATABASE.length > 0) {
        bowSelect.value = 1718; // Default to Hunter Bow
        if (!bowSelect.value && BOW_DATABASE.length > 0) {
            bowSelect.selectedIndex = 0;
        }
        handleBowChange();
    }
    
    if (ARROW_DATABASE.length > 0) {
        arrowSelect.value = 1774; // Default to Hunting Arrow
        if (!arrowSelect.value && ARROW_DATABASE.length > 0) {
            arrowSelect.selectedIndex = 0;
        }
        handleArrowChange();
    }

    updateCalculations();
});

// Event Handlers
function handleBowChange() {
    const bowId = parseInt(document.getElementById("bow-select").value);
    currentBow = BOW_DATABASE.find(b => b.Id === bowId);
    
    if (!currentBow) return;

    // Reset cards array to match slots
    activeCards = Array(currentBow.Slots).fill(null);

    // Render Slot Visualizers
    renderSlots();
    
    // Reset Refine Slider max value according to weapon level
    // In Pre-re, weapons can go to +10
    const refineInput = document.getElementById("refine-input");
    refineInput.max = 10;
    
    updateCalculations();
}

function handleArrowChange() {
    const arrowId = parseInt(document.getElementById("arrow-select").value);
    currentArrow = ARROW_DATABASE.find(a => a.Id === arrowId);
    updateCalculations();
}

function setSafeRefine() {
    if (!currentBow) return;
    
    // Pre-re safe levels: Lv1 (+7), Lv2 (+6), Lv3 (+5), Lv4 (+4)
    const safeLevels = { 1: 7, 2: 6, 3: 5, 4: 4 };
    const safeRefine = safeLevels[currentBow.WeaponLevel] || 4;
    
    document.getElementById("refine-input").value = safeRefine;
    document.getElementById("refine-val").textContent = `+${safeRefine}`;
    
    updateCalculations();
}

// Render slot dots/buttons
function renderSlots() {
    const container = document.getElementById("slots-container");
    container.innerHTML = "";
    
    if (currentBow.Slots === 0) {
        container.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.9rem;">No slots available on this weapon.</div>';
        return;
    }

    const slotsGrid = document.createElement("div");
    slotsGrid.className = "slots-grid";
    
    for (let i = 0; i < currentBow.Slots; i++) {
        const slot = document.createElement("div");
        slot.className = "slot-circle" + (activeCards[i] ? " filled" : "");
        slot.innerHTML = activeCards[i] ? activeCards[i].Name.replace(" Card", "") : `[ Slot ${i+1} ]`;
        slot.addEventListener("click", () => openCardModal(i));
        slotsGrid.appendChild(slot);
    }
    
    container.appendChild(slotsGrid);
}

// Modal handling
function openCardModal(slotIndex) {
    targetSlotIndex = slotIndex;
    const modal = document.getElementById("card-modal");
    const optionsContainer = document.getElementById("card-options-list");
    optionsContainer.innerHTML = "";

    // Clear Card Option
    const clearOpt = document.createElement("div");
    clearOpt.className = "card-option";
    clearOpt.innerHTML = `
        <div>
            <h4>Clear Slot</h4>
            <p>Remove card from this slot</p>
        </div>
        <div class="card-value">-</div>
    `;
    clearOpt.addEventListener("click", () => {
        activeCards[targetSlotIndex] = null;
        renderSlots();
        closeModal();
        updateCalculations();
    });
    optionsContainer.appendChild(clearOpt);

    // List Weapon Cards
    CARD_DATABASE.sort((a, b) => a.Name.localeCompare(b.Name)).forEach(card => {
        const opt = document.createElement("div");
        opt.className = "card-option";
        
        let bonusText = "";
        const m = card.Modifier;
        if (m.type === "race") bonusText = `+${m.value}% to ${m.target}`;
        else if (m.type === "element") bonusText = `+${m.value}% to ${m.target} targets`;
        else if (m.type === "size") bonusText = `+${m.value}% to ${m.target} targets`;
        else if (m.type === "ranged") bonusText = `+${m.value}% Ranged Physical Damage`;
        else if (m.type === "flat_atk") bonusText = `+${m.value} Flat Weapon ATK`;
        else if (m.type === "class") bonusText = `+${m.value}% to ${m.target} targets`;
        else if (m.type === "crit_damage") bonusText = `+${m.value}% Crit Damage`;

        opt.innerHTML = `
            <div>
                <h4>${card.Name}</h4>
                <p>${bonusText}</p>
            </div>
            <div class="card-value">${m.type.toUpperCase()}</div>
        `;
        opt.addEventListener("click", () => {
            activeCards[targetSlotIndex] = card;
            renderSlots();
            closeModal();
            updateCalculations();
        });
        optionsContainer.appendChild(opt);
    });

    modal.classList.add("active");
}

function closeModal() {
    document.getElementById("card-modal").classList.remove("active");
}

// Damage Calculation Core
function calculatePhysicalDamage(bow, arrow, refine, cards, stats, target) {
    // 1. Pre-Renewal DEX Status ATK Formula for Bows:
    // Status ATK = DEX + floor(DEX / 10)^2 + floor(STR / 5) + floor(LUK / 5)
    const dex = stats.dex;
    const str = stats.str;
    const luk = stats.luk;
    
    const dexMilestone = Math.floor(dex / 10);
    const statusAtk = dex + (dexMilestone * dexMilestone) + Math.floor(str / 5) + Math.floor(luk / 5);

    // 2. Pre-Renewal Refine Bonus:
    // Lv1: +2 ATK per refine. Lv2: +3 ATK. Lv3: +5 ATK. Lv4: +7 ATK.
    const refineBonuses = { 1: 2, 2: 3, 3: 5, 4: 7 };
    const baseRefineBonus = refineBonuses[bow.WeaponLevel] || 7;
    let refineAtk = refine * baseRefineBonus;
    
    // Pre-Renewal over-refine random bonuses can be added for average damage calculations
    const safeLevels = { 1: 7, 2: 6, 3: 5, 4: 4 };
    const safeRef = safeLevels[bow.WeaponLevel] || 4;
    let avgOverrefineBonus = 0;
    if (refine > safeRef) {
        const overRefAmt = refine - safeRef;
        // Max random bonus per level of over-refine: Lv1 (3), Lv2 (5), Lv3 (8), Lv4 (14)
        const overRefMaxRand = { 1: 3, 2: 5, 3: 8, 4: 14 };
        const maxRand = overRefMaxRand[bow.WeaponLevel] || 14;
        // Average random overrefine bonus = (1 + Max) / 2 per overrefine level
        avgOverrefineBonus = overRefAmt * (1 + maxRand) / 2;
    }

    // 3. Arrow ATK
    const arrowAtk = arrow ? arrow.Attack : 0;

    // 4. Flat ATK Cards (e.g. Andre Card, +20 ATK)
    let flatAtkCards = 0;
    cards.forEach(c => {
        if (c && c.Modifier && c.Modifier.type === "flat_atk") {
            flatAtkCards += c.Modifier.value;
        }
    });

    // Total Weapon ATK = Bow Base ATK + Refine ATK + Overrefine Bonus + Arrow ATK + Flat ATK Cards
    const totalWeaponAtk = bow.Attack + refineAtk + avgOverrefineBonus + arrowAtk + flatAtkCards;

    // 5. Size Penalty for Bows: Small 100%, Medium 100%, Large 75%
    const sizePenalty = SIZE_PENALTY[target.size] || 1.0;

    // Apply size penalty to weapon portion
    const baseSubtotal = statusAtk + (totalWeaponAtk * sizePenalty);

    // 6. Card Multipliers (additively within same category, multiplicatively across categories)
    let raceMult = 1.0;
    let eleMult = 1.0;
    let sizeMult = 1.0;
    let rangedMult = 1.0;
    let classMult = 1.0;

    // Gather multipliers from active cards
    cards.forEach(c => {
        if (!c || !c.Modifier) return;
        const m = c.Modifier;
        
        if (m.type === "race" && m.target === target.race) {
            raceMult += (m.value / 100);
        } else if (m.type === "element" && m.target === target.element) {
            eleMult += (m.value / 100);
        } else if (m.type === "size" && m.target === target.size) {
            sizeMult += (m.value / 100);
        } else if (m.type === "ranged") {
            rangedMult += (m.value / 100);
        } else if (m.type === "class" && m.target === target.class) {
            classMult += (m.value / 100);
        }
    });

    // 7. Bow-Arrow Specific Combos (e.g., Hunter Bow + Hunting Arrow is a +50% ranged physical bonus)
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
        // Special element bow combos (Burning, Frozen, Earth, Gust) give +25% ranged damage,
        // while Elven, Hunter, and Orc Archer Bow give +50% ranged damage.
        let comboBonus = 0.50;
        if (bow.AegisName.includes("Burning_Bow") || bow.AegisName.includes("Frozen_Bow") || 
            bow.AegisName.includes("Earth_Bow") || bow.AegisName.includes("Gust_Bow")) {
            comboBonus = 0.25;
        }
        rangedMult += comboBonus;
    }

    // 8. Element property modifier (based on equipped Arrow's element vs Target Monster's element)
    const arrowElement = arrow ? arrow.Element : "Neutral";
    const elementTable = ELEMENT_TABLE[arrowElement] || ELEMENT_TABLE["Neutral"];
    const elementPropertyMod = elementTable[target.element] || 1.0;

    // Combine all calculations
    // Formula: Avg Damage = baseSubtotal * RaceMult * EleMult * SizeMult * RangedMult * ClassMult * PropertyMod
    const rawDamage = baseSubtotal * raceMult * eleMult * sizeMult * rangedMult * classMult * elementPropertyMod;

    // 9. Apply Monster Hard DEF and Soft DEF (Pre-Renewal DEF reduction):
    // In Pre-re, Hard DEF reduces damage by percentage: damage * (100 - DEF) / 100
    // Soft DEF reduces damage by a flat subtraction: damage - VIT
    // We'll assume a simplified target DEF calculation to keep it highly realistic:
    const finalDamage = Math.max(1, Math.floor(rawDamage * ((100 - target.def) / 100)));

    return {
        statusAtk: statusAtk,
        weaponAtk: totalWeaponAtk,
        sizePenalty: sizePenalty,
        multipliers: {
            race: raceMult,
            element: eleMult,
            size: sizeMult,
            ranged: rangedMult,
            class: classMult,
            property: elementPropertyMod
        },
        hasCombo: hasCombo,
        finalDamage: finalDamage
    };
}

// Card Optimizer Engine
function autoOptimizeCards() {
    if (!currentBow || currentBow.Slots === 0) {
        alert("This bow has no slots to optimize!");
        return;
    }

    const stats = getPlayerStats();
    const target = getTargetStats();
    
    // Filter the card database to only contain cards relevant to this target
    // to reduce combination search space
    const relevantCards = CARD_DATABASE.filter(c => {
        const m = c.Modifier;
        return (
            (m.type === "race" && m.target === target.race) ||
            (m.type === "element" && m.target === target.element) ||
            (m.type === "size" && m.target === target.size) ||
            (m.type === "ranged") ||
            (m.type === "flat_atk") ||
            (m.type === "class" && m.target === target.class)
        );
    });

    // If no relevant cards found, fallback to general damage cards (Andre, Archer Skeleton)
    if (relevantCards.length === 0) {
        CARD_DATABASE.forEach(c => {
            if (c.Modifier.type === "ranged" || c.Modifier.type === "flat_atk") {
                relevantCards.push(c);
            }
        });
    }

    // Generate combinations of size 'slots' with replacement
    const slots = currentBow.Slots;
    const combinations = [];
    
    function generateCombo(tempCombo, depth) {
        if (depth === slots) {
            combinations.push([...tempCombo]);
            return;
        }
        for (let i = 0; i < relevantCards.length; i++) {
            tempCombo.push(relevantCards[i]);
            generateCombo(tempCombo, depth + 1);
            tempCombo.pop();
        }
    }
    
    generateCombo([], 0);

    // Evaluate combinations
    let bestCombo = null;
    let maxDamage = 0;

    combinations.forEach(combo => {
        const res = calculatePhysicalDamage(currentBow, currentArrow, getRefineLevel(), combo, stats, target);
        if (res.finalDamage > maxDamage) {
            maxDamage = res.finalDamage;
            bestCombo = combo;
        }
    });

    // Apply best combo
    if (bestCombo) {
        activeCards = [...bestCombo];
        renderSlots();
        updateCalculations();
    }
}

// Get states from inputs
function getPlayerStats() {
    return {
        dex: parseInt(document.getElementById("dex-input").value) || 1,
        str: parseInt(document.getElementById("str-input").value) || 1,
        luk: parseInt(document.getElementById("luk-input").value) || 1
    };
}

function getTargetStats() {
    return {
        size: document.getElementById("target-size").value,
        race: document.getElementById("target-race").value,
        element: document.getElementById("target-element").value,
        def: parseInt(document.getElementById("target-def").value) || 0,
        class: "Normal" // Normal / Boss
    };
}

function getRefineLevel() {
    return parseInt(document.getElementById("refine-input").value) || 0;
}

// Recalculate stats and rank all bows
function updateCalculations() {
    if (!currentBow) return;

    const stats = getPlayerStats();
    const target = getTargetStats();
    const refine = getRefineLevel();

    // 1. Calculate active weapon damage
    const res = calculatePhysicalDamage(currentBow, currentArrow, refine, activeCards, stats, target);

    // Update center details card
    document.getElementById("stat-status-atk").textContent = res.statusAtk;
    document.getElementById("stat-weapon-atk").textContent = Math.floor(res.weaponAtk);
    
    // Elemental Property Mod percentage
    const elePercent = Math.round(res.multipliers.property * 100);
    document.getElementById("stat-ele-mod").textContent = `${elePercent}%`;

    // Size penalty percentage
    const sizePercent = Math.round(res.sizePenalty * 100);
    document.getElementById("stat-size-penalty").textContent = `${sizePercent}%`;

    // Multipliers summary detail list
    document.getElementById("detail-base-atk").textContent = currentBow.Attack;
    document.getElementById("detail-refine-atk").textContent = Math.floor(res.weaponAtk - currentBow.Attack - (currentArrow ? currentArrow.Attack : 0));
    document.getElementById("detail-arrow-atk").textContent = currentArrow ? currentArrow.Attack : 0;
    
    // Card multipliers detail
    const m = res.multipliers;
    const cardMultText = `Race: x${m.race.toFixed(2)} | Element: x${m.element.toFixed(2)} | Size: x${m.size.toFixed(2)} | Ranged: x${m.ranged.toFixed(2)}`;
    document.getElementById("detail-card-multipliers").textContent = cardMultText;

    // Display damage value with glowing accent
    const damageValEl = document.getElementById("detail-final-damage");
    damageValEl.textContent = res.finalDamage;
    
    // Render combo notice
    const comboNotice = document.getElementById("combo-notice");
    if (res.hasCombo) {
        comboNotice.style.display = "block";
        comboNotice.textContent = "🔥 ACTIVE BOW + ARROW COMBO (+ ranged damage applied!)";
        comboNotice.style.color = "var(--accent-color)";
    } else {
        comboNotice.style.display = "none";
    }

    // 2. Rank all bows in the database
    // For each bow, we optimize cards for this target and calculate best possible damage
    const bowRanks = [];

    BOW_DATABASE.forEach(bow => {
        // Optimize card configurations for this bow
        let optimizedCards = [];
        if (bow.Slots > 0) {
            // Find best cards for this bow and this target
            const relevantCards = CARD_DATABASE.filter(c => {
                const modifier = c.Modifier;
                return (
                    (modifier.type === "race" && modifier.target === target.race) ||
                    (modifier.type === "element" && modifier.target === target.element) ||
                    (modifier.type === "size" && modifier.target === target.size) ||
                    (modifier.type === "ranged") ||
                    (modifier.type === "flat_atk") ||
                    (modifier.type === "class" && modifier.target === target.class)
                );
            });

            if (relevantCards.length === 0) {
                CARD_DATABASE.forEach(c => {
                    if (c.Modifier.type === "ranged" || c.Modifier.type === "flat_atk") {
                        relevantCards.push(c);
                    }
                });
            }

            // Generate combos
            const combList = [];
            function generateC(tempC, depth) {
                if (depth === bow.Slots) {
                    combList.push([...tempC]);
                    return;
                }
                for (let i = 0; i < relevantCards.length; i++) {
                    tempC.push(relevantCards[i]);
                    generateC(tempC, depth + 1);
                    tempC.pop();
                }
            }
            generateC([], 0);

            // Find max
            let maxD = 0;
            combList.forEach(combo => {
                // Calculate safe refine level for this bow
                const safeLevels = { 1: 7, 2: 6, 3: 5, 4: 4 };
                const safeRef = safeLevels[bow.WeaponLevel] || 4;
                const r = calculatePhysicalDamage(bow, currentArrow, safeRef, combo, stats, target);
                if (r.finalDamage > maxD) {
                    maxD = r.finalDamage;
                    optimizedCards = combo;
                }
            });
        }

        // Calculate damage under safe refine level for the ranked listing
        const safeLevels = { 1: 7, 2: 6, 3: 5, 4: 4 };
        const safeRef = safeLevels[bow.WeaponLevel] || 4;
        const bowRes = calculatePhysicalDamage(bow, currentArrow, safeRef, optimizedCards, stats, target);

        bowRanks.push({
            bow: bow,
            refineUsed: safeRef,
            damage: bowRes.finalDamage,
            cardsUsed: optimizedCards
        });
    });

    // Sort by damage descending
    bowRanks.sort((a, b) => b.damage - a.damage);

    // Render ranked listing
    const rankedContainer = document.getElementById("ranked-bows-container");
    rankedContainer.innerHTML = "";

    const highestDamage = bowRanks[0] ? bowRanks[0].damage : 1;

    bowRanks.forEach((item, index) => {
        const bowItem = document.createElement("div");
        bowItem.className = "best-bow-item" + (index === 0 ? " first-place" : "");
        
        // Format cards text description
        let cardsText = "No cards";
        if (item.cardsUsed.length > 0) {
            const cardCounts = {};
            item.cardsUsed.forEach(c => {
                cardCounts[c.Name.replace(" Card", "")] = (cardCounts[c.Name.replace(" Card", "")] || 0) + 1;
            });
            cardsText = Object.entries(cardCounts).map(([name, count]) => `${count}x ${name}`).join(", ");
        }

        const percentage = Math.round((item.damage / highestDamage) * 100);

        bowItem.innerHTML = `
            <div class="bow-item-left">
                <div class="rank-number">${index + 1}</div>
                <div class="bow-item-info">
                    <h3>${item.bow.Name} <span class="badge badge-level">Lv${item.bow.WeaponLevel}</span></h3>
                    <div class="item-meta">ATK ${item.bow.Attack} | +${item.refineUsed} Refine | ${item.bow.Slots} slots</div>
                    <div class="item-cards">💎 Best setup: ${cardsText}</div>
                </div>
            </div>
            <div class="bow-item-right">
                <div class="damage-val">${item.damage}</div>
                <div class="comparison-percentage">${percentage}% efficacy</div>
            </div>
        `;
        
        // Add click listener to select this bow instantly!
        bowItem.addEventListener("click", () => {
            document.getElementById("bow-select").value = item.bow.Id;
            handleBowChange();
            // Automatically apply the optimized cards from the rank item
            activeCards = [...item.cardsUsed];
            renderSlots();
            
            // Set refine to safe refine level of this bow
            document.getElementById("refine-input").value = item.refineUsed;
            document.getElementById("refine-val").textContent = `+${item.refineUsed}`;
            
            updateCalculations();
        });

        rankedContainer.appendChild(bowItem);
    });

    // Draw dynamic chart comparison inside SVGs
    drawSVGChart(res, stats, target);
}

// Draw dynamic inline SVG bar/line charts inside the container
function drawSVGChart(currentRes, stats, target) {
    const chartContainer = document.getElementById("chart-container");
    chartContainer.innerHTML = '<h3 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem;">Damage vs DEX Milestones</h3>';

    // Calculate damage at different DEX milestones (DEX -20, -10, current, +10, +20, +30)
    const currentDex = stats.dex;
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
        return calculatePhysicalDamage(currentBow, currentArrow, getRefineLevel(), activeCards, stepStats, target).finalDamage;
    });

    // Setup SVG
    const width = 330;
    const height = 120;
    const padding = 20;
    const graphWidth = width - padding * 2;
    const graphHeight = height - padding * 2;

    const maxDamage = Math.max(...damageData) || 1;
    const minDamage = Math.min(...damageData) || 0;

    let points = "";
    let gridLines = "";
    let labels = "";

    dexSteps.forEach((dex, index) => {
        const x = padding + (index / (dexSteps.length - 1)) * graphWidth;
        const y = padding + graphHeight - ((damageData[index] - minDamage * 0.8) / (maxDamage - minDamage * 0.8)) * graphHeight;

        points += `${x},${y} `;

        // Vertical Grid lines
        gridLines += `<line x1="${x}" y1="${padding}" x2="${x}" y2="${padding + graphHeight}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />`;
        
        // DEX Labels below chart
        const isCurrent = dex === currentDex;
        const labelColor = isCurrent ? "var(--accent-color)" : "var(--text-secondary)";
        const labelWeight = isCurrent ? "800" : "400";
        labels += `<text x="${x}" y="${height - 2}" fill="${labelColor}" font-weight="${labelWeight}" font-size="8.5" text-anchor="middle">${dex}</text>`;
    });

    const svg = `
        <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow: visible;">
            <defs>
                <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="var(--accent-color)" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="var(--accent-color)" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            ${gridLines}
            <!-- Area under line -->
            <polygon points="${padding},${padding + graphHeight} ${points} ${padding + graphWidth},${padding + graphHeight}" fill="url(#chart-grad)" />
            <!-- Line path -->
            <polyline points="${points}" fill="none" stroke="var(--accent-color)" stroke-width="2" />
            <!-- Data points -->
            ${dexSteps.map((d, index) => {
                const x = padding + (index / (dexSteps.length - 1)) * graphWidth;
                const y = padding + graphHeight - ((damageData[index] - minDamage * 0.8) / (maxDamage - minDamage * 0.8)) * graphHeight;
                const isCurrent = d === currentDex;
                return `<circle cx="${x}" cy="${y}" r="${isCurrent ? 4.5 : 3.5}" fill="${isCurrent ? "var(--accent-color)" : "#0b0813"}" stroke="var(--accent-color)" stroke-width="2" />`;
            }).join("")}
            <!-- Labels -->
            ${labels}
        </svg>
    `;

    const svgWrapper = document.createElement("div");
    svgWrapper.innerHTML = svg;
    chartContainer.appendChild(svgWrapper);
}
