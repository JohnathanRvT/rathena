def calculate_gear_score(item_id, refine, cards, item_db):
    if item_id not in item_db:
        return 0

    item = item_db[item_id]
    score = 0

    # Base score from item level
    score += (item.get('wlv', 0) + item.get('alv', 0)) * 100

    # Stat bonuses
    score += item.get('atk', 0)
    score += item.get('def', 0) * 5
    score += item.get('matk', 0)

    # Refine bonus
    if refine > 0:
        score += (refine * refine) * 10

    # Card bonus
    for card_id in cards:
        if card_id != 0:
            score += 50

    return score

def get_total_gear_score(inventory_items, item_db):
    total_score = 0
    # inventory_items is a list of dicts with {nameid, refine, cards}
    # We should avoid double counting the same item instance if multiple slots are occupied,
    # but the DB usually gives us unique instances in 'inventory' table.

    for item in inventory_items:
        # We only count items that are equipped
        if item.get('equip', 0) > 0:
            total_score += calculate_gear_score(
                item['nameid'],
                item.get('refine', 0),
                [item.get('card0', 0), item.get('card1', 0), item.get('card2', 0), item.get('card3', 0)],
                item_db
            )

    return total_score
