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

def get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing):
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
    # Arrow Crafting
    aegis_name = item.get('AegisName')
    if aegis_name in arrow_crafts:
        lines.append("--- Arrow Crafting ---")
        for res_name, amount in arrow_crafts[aegis_name]:
            res_item = items.get(name_to_id.get(res_name), {})
            res_display = res_item.get('Name', res_name)
            lines.append(f"Yields: {res_display} x{amount}")

    # Production (Ingredient)
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

    # Production (Result)
    if item_id in res_to_ing:
        lines.append("--- Production Recipe ---")
        for ing_id, amount in res_to_ing[item_id]:
            ing_item = items.get(ing_id, {})
            ing_display = ing_item.get('Name', f"Item {ing_id}")
            lines.append(f"- {ing_display} x{amount}")

    # 5. Original Script (simplistic)
    if item.get('Script'):
        lines.append("--- Effect ---")
        script = item.get('Script').strip()
        script = script.replace('bonus ', '').replace(';', '')
        lines.append(script)

    return "\\n".join(lines)

def generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("tbl_item_info = {\n")
        for item_id in sorted(items.keys()):
            item = items[item_id]
            desc = get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing)

            f.write(f"  [{item_id}] = {{\n")
            f.write(f"    unidentifiedDisplayName = [[{item.get('Name')}]],\n")
            f.write(f"    unidentifiedResourceName = [[{item.get('AegisName')}]],\n")
            f.write(f"    unidentifiedDescriptionName = {{ [[]] }},\n")
            f.write(f"    identifiedDisplayName = [[{item.get('Name')}]],\n")
            f.write(f"    identifiedResourceName = [[{item.get('AegisName')}]],\n")
            f.write(f"    identifiedDescriptionName = {{\n")
            # Splitting by \n for multi-line Lua array
            for line in desc.split("\\n"):
                # Escape any brackets in the line
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
    output_file = 'itemInfo.lua'

    print("Loading item databases...")
    items, name_to_id = parse_item_db(base_db_path, item_files)
    print(f"Loaded {len(items)} items.")

    print("Loading arrow crafting database...")
    arrow_crafts = parse_arrow_db(arrow_db_path)

    print("Loading production database...")
    ing_to_res, res_to_ing = parse_produce_db(produce_db_path)

    print(f"Generating {output_file}...")
    generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, output_file)
    print("Done.")

if __name__ == "__main__":
    main()
