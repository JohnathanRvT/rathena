import yaml
import os
import re

def load_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_item_db(base_path, files):
    items = {}
    name_to_id = {}
    for f in files:
        full_path = os.path.join(base_path, f)
        data = load_yaml(full_path)
        if not data or 'Body' not in data:
            continue
        for item in data['Body']:
            item_id = item.get('Id')
            if item_id:
                items[item_id] = item
                name_to_id[item.get('AegisName')] = item_id
    return items, name_to_id

def parse_arrow_db(file_path):
    crafts = {}
    data = load_yaml(file_path)
    if not data or 'Body' not in data:
        return crafts
    for entry in data['Body']:
        source = entry.get('Source')
        make = entry.get('Make', [])
        crafts[source] = [(m.get('Item'), m.get('Amount')) for m in make]
    return crafts

def parse_produce_db(file_path):
    ing_to_res = {}
    res_to_ing = {}

    if not os.path.exists(file_path):
        return ing_to_res, res_to_ing

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            parts = line.split(',')
            if len(parts) < 7:
                continue

            try:
                res_id = int(parts[1])
                if res_id == 0: continue
                item_lv = int(parts[2])

                ingredients = []
                for i in range(5, len(parts), 2):
                    if i + 1 >= len(parts):
                        break
                    try:
                        ing_id = int(parts[i])
                        amount = int(parts[i+1])
                        ingredients.append((ing_id, amount))

                        if ing_id not in ing_to_res:
                            ing_to_res[ing_id] = []
                        ing_to_res[ing_id].append((res_id, item_lv))
                    except ValueError:
                        continue

                res_to_ing[res_id] = ingredients
            except ValueError:
                continue

    return ing_to_res, res_to_ing

def parse_mob_db(file_path, name_to_id):
    item_drops = {}
    data = load_yaml(file_path)
    if not data or 'Body' not in data:
        return item_drops

    for mob in data['Body']:
        mob_name = mob.get('Name')
        drops = mob.get('Drops', [])
        mvp_drops = mob.get('MvpDrops', [])

        all_drops = []
        for d in drops:
            all_drops.append((d.get('Item'), d.get('Rate'), False))
        for d in mvp_drops:
            all_drops.append((d.get('Item'), d.get('Rate'), True))

        for item_name, rate, is_mvp in all_drops:
            item_id = name_to_id.get(item_name)
            if item_id:
                if item_id not in item_drops:
                    item_drops[item_id] = []
                item_drops[item_id].append({
                    'mob': mob_name,
                    'rate': rate,
                    'mvp': is_mvp
                })

    for item_id in item_drops:
        item_drops[item_id].sort(key=lambda x: x['rate'], reverse=True)

    return item_drops

def parse_quest_scripts(quest_dir):
    quest_items = {}
    if not os.path.exists(quest_dir):
        return quest_items

    pattern = re.compile(r'(getitem|delitem|countitem)\s+(\d+)')

    for root, _, files in os.walk(quest_dir):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                quest_name = file.replace('.txt', '').replace('quest_', '').replace('_', ' ').title()
                with open(file_path, 'r', encoding='latin-1') as f:
                    try:
                        content = f.read()
                        matches = pattern.findall(content)
                        for _, item_id_str in matches:
                            item_id = int(item_id_str)
                            if item_id not in quest_items:
                                quest_items[item_id] = set()
                            quest_items[item_id].add(quest_name)
                    except UnicodeDecodeError:
                        continue

    return {k: sorted(list(v)) for k, v in quest_items.items()}

def parse_item_combos(file_path, name_to_id, items):
    # Mapping of Item ID -> List of Combos
    item_combos = {}
    data = load_yaml(file_path)
    if not data or 'Body' not in data:
        return item_combos

    for entry in data['Body']:
        script = entry.get('Script', '').strip()
        script = script.replace('bonus ', '').replace('bonus2 ', '').replace(';', '')

        combos_list = entry.get('Combos', [])
        for combo_entry in combos_list:
            combo_items_names = combo_entry.get('Combo', [])
            combo_items_ids = []
            for name in combo_items_names:
                iid = name_to_id.get(name)
                if iid:
                    combo_items_ids.append(iid)

            if len(combo_items_ids) >= 2:
                for iid in combo_items_ids:
                    if iid not in item_combos:
                        item_combos[iid] = []

                    # Other items in this combo
                    others = [items[oid].get('Name') for oid in combo_items_ids if oid != iid]
                    item_combos[iid].append({
                        'others': others,
                        'bonus': script
                    })
    return item_combos

def get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos):
    lines = []

    # 1. Base stats
    if item.get('Type') == 'Weapon':
        lines.append(f"Class: {item.get('SubType', 'N/A')}")
        lines.append(f"Attack: {item.get('Attack', 0)}")
        if item.get('MagicAttack'):
            lines.append(f"Magic Attack: {item.get('MagicAttack')}")
        lines.append(f"Property: {item.get('Property', 'Neutral')}")
        lines.append(f"Weapon Level: {item.get('WeaponLevel', 1)}")
    elif item.get('Type') == 'Armor':
        lines.append(f"Class: {item.get('SubType', 'Armor')}")
        lines.append(f"Defense: {item.get('Defense', 0)}")
        locs = item.get('Locations', {})
        loc_str = ", ".join([k.replace('_', ' ') for k, v in locs.items() if v])
        if loc_str:
            lines.append(f"Location: {loc_str}")

    # 2. Requirements
    if item.get('EquipLevelMin'):
        lines.append(f"Required Level: {item.get('EquipLevelMin')}")

    if item.get('Jobs'):
        jobs = item.get('Jobs', {})
        if jobs.get('All'):
            lines.append("Jobs: All")
        else:
            job_list = [k for k, v in jobs.items() if v]
            if job_list:
                lines.append(f"Jobs: {', '.join(job_list)}")

    lines.append(f"Weight: {item.get('Weight', 0) / 10}")

    # 3. Prices
    buy = item.get('Buy')
    sell = item.get('Sell')
    if buy is None and sell is not None:
        buy = sell * 2
    if sell is None and buy is not None:
        sell = buy // 2

    if buy: lines.append(f"Buy: {buy}z")
    if sell: lines.append(f"Sell: {sell}z")

    # 4. Crafting / Usage
    aegis_name = item.get('AegisName')
    if aegis_name in arrow_crafts:
        lines.append("--- Arrow Crafting ---")
        for res_name, amount in arrow_crafts[aegis_name]:
            res_item = items.get(name_to_id.get(res_name), {})
            res_display = res_item.get('Name', res_name)
            lines.append(f"Yields: {res_display} x{amount}")

    item_id = item.get('Id')
    if item_id in ing_to_res:
        lines.append("--- Used In Production ---")
        seen_res = set()
        for res_id, _ in ing_to_res[item_id]:
            if res_id in seen_res: continue
            res_item = items.get(res_id, {})
            res_display = res_item.get('Name', f"Item {res_id}")
            lines.append(f"- {res_display}")
            seen_res.add(res_id)

    if item_id in res_to_ing:
        lines.append("--- Production Recipe ---")
        for ing_id, amount in res_to_ing[item_id]:
            ing_item = items.get(ing_id, {})
            ing_display = ing_item.get('Name', f"Item {ing_id}")
            lines.append(f"- {ing_display} x{amount}")

    # 5. Combos
    if item_id in item_combos:
        lines.append("--- Set Bonus ---")
        for combo in item_combos[item_id]:
            others_str = " + ".join(combo['others'])
            lines.append(f"With {others_str}:")
            lines.append(f"  {combo['bonus']}")

    # 6. Quests
    if item_id in quest_items:
        lines.append("--- Quest Related ---")
        for q in quest_items[item_id][:3]:
            lines.append(f"- {q}")
        if len(quest_items[item_id]) > 3:
            lines.append(f"... and {len(quest_items[item_id]) - 3} more.")

    # 7. Drops
    if item_id in item_drops:
        lines.append("--- Dropped By ---")
        for drop in item_drops[item_id][:5]:
            mvp_str = " (MVP)" if drop['mvp'] else ""
            rate = drop['rate'] / 100
            lines.append(f"- {drop['mob']}: {rate}%{mvp_str}")
        if len(item_drops[item_id]) > 5:
            lines.append(f"... and {len(item_drops[item_id]) - 5} more.")

    # 8. Original Script
    if item.get('Script'):
        lines.append("--- Effect ---")
        script = item.get('Script').strip()
        script = script.replace('bonus ', '').replace('bonus2 ', '').replace(';', '')
        lines.append(script)

    return "\\n".join(lines)

def generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("tbl_item_info = {\n")
        for item_id in sorted(items.keys()):
            item = items[item_id]
            desc = get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos)

            f.write(f"  [{item_id}] = {{\n")
            f.write(f"    unidentifiedDisplayName = [[{item.get('Name')}]],\n")
            f.write(f"    unidentifiedResourceName = [[{item.get('AegisName')}]],\n")
            f.write(f"    unidentifiedDescriptionName = {{ [[]] }},\n")
            f.write(f"    identifiedDisplayName = [[{item.get('Name')}]],\n")
            f.write(f"    identifiedResourceName = [[{item.get('AegisName')}]],\n")
            f.write(f"    identifiedDescriptionName = {{\n")
            for line in desc.split("\\n"):
                line = line.replace("[[", "").replace("]]", "")
                f.write(f"      [[{line}]],\n")
            f.write(f"    }},\n")
            f.write(f"    slotCount = {item.get('Slots', 0)},\n")
            f.write(f"    ClassNum = {item.get('View', 0)}\n")
            f.write(f"  }},\n")
        f.write("}\n\n")
        f.write("function main()\n")
        f.write("  for ItemID, it in pairs(tbl_item_info) do\n")
        f.write("    result, msg = AddItem(ItemID, it.unidentifiedDisplayName, it.unidentifiedResourceName, it.unidentifiedDescriptionName, it.identifiedDisplayName, it.identifiedResourceName, it.identifiedDescriptionName, it.slotCount, it.ClassNum)\n")
        f.write("    if not result then\n")
        f.write("      return false, msg\n")
        f.write("    end\n")
        f.write("  end\n")
        f.write("  return true, \"ok\"\n")
        f.write("end\n")

def main():
    base_db_path = 'db/pre-re'
    item_files = ['item_db_etc.yml', 'item_db_equip.yml', 'item_db_usable.yml']
    arrow_db_path = 'db/create_arrow_db.yml'
    produce_db_path = 'db/pre-re/produce_db.txt'
    mob_db_path = 'db/pre-re/mob_db.yml'
    combo_db_path = 'db/pre-re/item_combos.yml'
    quest_dir = 'npc/pre-re/quests'
    output_file = 'itemInfo.lua'

    print("Loading item databases...")
    items, name_to_id = parse_item_db(base_db_path, item_files)
    print(f"Loaded {len(items)} items.")

    print("Loading arrow crafting database...")
    arrow_crafts = parse_arrow_db(arrow_db_path)

    print("Loading production database...")
    ing_to_res, res_to_ing = parse_produce_db(produce_db_path)

    print("Loading monster database for drops...")
    item_drops = parse_mob_db(mob_db_path, name_to_id)

    print("Parsing quest scripts for item relevance...")
    quest_items = parse_quest_scripts(quest_dir)

    print("Loading item combos...")
    item_combos = parse_item_combos(combo_db_path, name_to_id, items)

    print(f"Generating {output_file}...")
    generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, output_file)
    print("Done.")

if __name__ == "__main__":
    main()
