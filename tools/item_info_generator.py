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
                    others = [items[oid].get('Name') for oid in combo_items_ids if oid != iid]
                    item_combos[iid].append({
                        'others': others,
                        'bonus': script
                    })
    return item_combos

def parse_lua_item_info(file_path):
    overrides = {}
    if not os.path.exists(file_path):
        return overrides

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    blocks = re.findall(r'\[(\d+)\]\s*=\s*\{(.*?)\n\s*\},', content, re.DOTALL)
    for item_id_str, block_content in blocks:
        item_id = int(item_id_str)
        item_data = {}

        res_matches = re.findall(r'(\w+)\s*=\s*"([^"]*)"', block_content)
        for field, value in res_matches:
            item_data[field] = value

        res_matches_long = re.findall(r'(\w+)\s*=\s*\[\[(.*?)\]\]', block_content)
        for field, value in res_matches_long:
            item_data[field] = value

        overrides[item_id] = item_data
    return overrides

def get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, tipboxes):
    lines = []

    if item.get('Type') == 'Weapon':
        lines.append(f"Class:^0000FF {item.get('SubType', 'N/A')}^000000")
        lines.append(f"Attack:^009900 {item.get('Attack', 0)}^000000")
        if item.get('MagicAttack'):
            lines.append(f"Magic Attack:^009900 {item.get('MagicAttack')}^000000")
        lines.append(f"Property:^0000FF {item.get('Property', 'Neutral')}^000000")
        lines.append(f"Weapon Level:^009900 {item.get('WeaponLevel', 1)}^000000")
    elif item.get('Type') == 'Armor':
        lines.append(f"Class:^0000FF {item.get('SubType', 'Armor')}^000000")
        lines.append(f"Defense:^009900 {item.get('Defense', 0)}^000000")
        locs = item.get('Locations', {})
        loc_str = ", ".join([k.replace('_', ' ') for k, v in locs.items() if v])
        if loc_str:
            lines.append(f"Location:^0000FF {loc_str}^000000")

    if item.get('EquipLevelMin'):
        lines.append(f"Required Level:^009900 {item.get('EquipLevelMin')}^000000")

    if item.get('Jobs'):
        jobs = item.get('Jobs', {})
        if jobs.get('All'):
            lines.append("Jobs:^0000FF All^000000")
        else:
            job_list = [k for k, v in jobs.items() if v]
            if job_list:
                lines.append(f"Jobs:^0000FF {', '.join(job_list)}^000000")

    lines.append(f"Weight:^009900 {item.get('Weight', 0) / 10}^000000")

    lines.append("^000000________________________^000000")

    buy = item.get('Buy')
    sell = item.get('Sell')
    if buy is None and sell is not None:
        buy = sell * 2
    if sell is None and buy is not None:
        sell = buy // 2

    lines.append(f"NPC Buy: {buy or 0} Zeny")
    lines.append(f"NPC Sell: {sell or 0} Zeny")
    lines.append("Vendor Buy: 0 Zeny")
    lines.append("Vendor Sell: 0 Zeny")

    item_id = item.get('Id')

    # 4. Crafting / Usage
    aegis_name = item.get('AegisName')
    if aegis_name in arrow_crafts:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Arrow Crafting ---^000000")
        for res_name, amount in arrow_crafts[aegis_name]:
            res_item_id = name_to_id.get(res_name)
            res_item = items.get(res_item_id, {})
            res_display = res_item.get('Name', res_name)
            if res_item_id:
                lines.append(f"Yields: <ITEM>{res_display}<INFO>{res_item_id}</INFO></ITEM> x{amount}")
            else:
                lines.append(f"Yields: {res_display} x{amount}")

    if item_id in ing_to_res:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Used In Production ---^000000")
        seen_res = set()
        for res_id, _ in ing_to_res[item_id]:
            if res_id in seen_res: continue
            res_item = items.get(res_id, {})
            res_display = res_item.get('Name', f"Item {res_id}")
            lines.append(f"- <ITEM>{res_display}<INFO>{res_id}</INFO></ITEM>")
            seen_res.add(res_id)

    if item_id in res_to_ing:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Production Recipe ---^000000")
        # Create a tipbox for complex recipes if more than 3 ingredients
        if len(res_to_ing[item_id]) > 3:
            tip_id = 10000 + item_id
            recipe_page = f"Production Recipe for {item.get('Name')}:\\n"
            for ing_id, amount in res_to_ing[item_id]:
                ing_item = items.get(ing_id, {})
                ing_display = ing_item.get('Name', f"Item {ing_id}")
                recipe_page += f"- <ITEM>{ing_display}<INFO>{ing_id}</INFO></ITEM> x{amount}\\n"
            tipboxes[tip_id] = {
                'Title': f"Recipe: {item.get('Name')}",
                'Page': [recipe_page]
            }
            lines.append(f" <TIPBOX>View Production Recipe<INFO>{tip_id}</INFO></TIPBOX>")
        else:
            for ing_id, amount in res_to_ing[item_id]:
                ing_item = items.get(ing_id, {})
                ing_display = ing_item.get('Name', f"Item {ing_id}")
                lines.append(f"- <ITEM>{ing_display}<INFO>{ing_id}</INFO></ITEM> x{amount}")

    # 5. Combos
    if item_id in item_combos:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Set Bonus ---^000000")
        for combo in item_combos[item_id]:
            others_str = " + ".join(combo['others'])
            lines.append(f"With {others_str}:")
            lines.append(f"  ^0000FF{combo['bonus']}^000000")

    # 6. Quests
    if item_id in quest_items:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Quest Related ---^000000")
        # Tipbox for quests if more than 3
        if len(quest_items[item_id]) > 3:
            tip_id = 20000 + item_id
            quest_page = f"Quests involving {item.get('Name')}:\\n"
            for q in quest_items[item_id]:
                quest_page += f"- {q}\\n"
            tipboxes[tip_id] = {
                'Title': f"Quests: {item.get('Name')}",
                'Page': [quest_page]
            }
            lines.append(f" <TIPBOX>View Related Quests<INFO>{tip_id}</INFO></TIPBOX>")
        else:
            for q in quest_items[item_id]:
                lines.append(f"- {q}")

    # 7. Drops
    if item_id in item_drops:
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Dropped By ---^000000")
        for drop in item_drops[item_id][:5]:
            mvp_str = " (MVP)" if drop['mvp'] else ""
            rate = drop['rate'] / 100
            lines.append(f"- {drop['mob']}:^009900 {rate}%^000000{mvp_str}")
        if len(item_drops[item_id]) > 5:
            lines.append(f"... and {len(item_drops[item_id]) - 5} more.")

    # 8. Original Script
    if item.get('Script'):
        lines.append("^FFFFFF_^000000")
        lines.append("^FF0000--- Effect ---^000000")
        script = item.get('Script').strip()
        script = script.replace('bonus ', '').replace('bonus2 ', '').replace(';', '')
        lines.append(f"^0000FF{script}^000000")

    return "\\n".join(lines)

def generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, lua_overrides, tipboxes, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("tbl = {\n")
        for item_id in sorted(items.keys()):
            item = items[item_id]
            desc = get_description(item, items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, tipboxes)

            overrides = lua_overrides.get(item_id, {})
            unid_name = overrides.get('unidentifiedDisplayName', item.get('Name'))
            unid_res = overrides.get('unidentifiedResourceName', item.get('AegisName'))
            id_name = overrides.get('identifiedDisplayName', item.get('Name'))
            id_res = overrides.get('identifiedResourceName', item.get('AegisName'))

            f.write(f"  [{item_id}] = {{\n")
            f.write(f"    unidentifiedDisplayName = \"{unid_name}\",\n")
            f.write(f"    unidentifiedResourceName = \"{unid_res}\",\n")
            f.write(f"    unidentifiedDescriptionName = {{ \"...\" }},\n")
            f.write(f"    identifiedDisplayName = \"{id_name}\",\n")
            f.write(f"    identifiedResourceName = \"{id_res}\",\n")
            f.write(f"    identifiedDescriptionName = {{\n")
            for line in desc.split("\\n"):
                line = line.replace('"', '\\"')
                f.write(f"      \"{line}\",\n")
            f.write(f"    }},\n")
            f.write(f"    slotCount = {item.get('Slots', 0)},\n")
            f.write(f"    ClassNum = {item.get('View', 0)},\n")

            is_costume = False
            locs = item.get('Locations', {})
            for loc in locs:
                if loc.startswith('Costume_') and locs[loc]:
                    is_costume = True
                    break
            f.write(f"    costume = {'true' if is_costume else 'false'},\n")
            f.write(f"  }},\n")
        f.write("}\n")

def generate_tipbox(tipboxes, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Generated TipBox file\n")
        f.write("iSupport = false\n\n")
        f.write("tbl = {\n")
        for tid in sorted(tipboxes.keys()):
            tip = tipboxes[tid]
            f.write(f"  [{tid}] = {{\n")
            f.write(f"    Title = \"{tip['Title']}\",\n")
            f.write(f"    Search = 1,\n")
            # Default image or none
            f.write(f"    Image = \"\",\n")
            f.write(f"    Page = {{\n")
            for page in tip['Page']:
                f.write(f"      \"{page}\",\n")
            f.write(f"    }}\n")
            f.write(f"  }},\n")
        f.write("}\n")

def main():
    base_db_path = 'db/pre-re'
    item_files = ['item_db_etc.yml', 'item_db_equip.yml', 'item_db_usable.yml']
    arrow_db_path = 'db/create_arrow_db.yml'
    produce_db_path = 'db/pre-re/produce_db.txt'
    mob_db_path = 'db/pre-re/mob_db.yml'
    combo_db_path = 'db/pre-re/item_combos.yml'
    quest_dir = 'npc/pre-re/quests'
    input_lua = 'itemInfo.lua'
    output_lua = 'itemInfo_new.lua'
    output_tipbox = 'tipbox.lub'

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

    print("Parsing existing itemInfo.lua for overrides...")
    lua_overrides = parse_lua_item_info(input_lua)

    tipboxes = {}

    print(f"Generating {output_lua}...")
    generate_lua(items, name_to_id, arrow_crafts, ing_to_res, res_to_ing, item_drops, quest_items, item_combos, lua_overrides, tipboxes, output_lua)

    print(f"Generating {output_tipbox}...")
    generate_tipbox(tipboxes, output_tipbox)

    print("Done.")

if __name__ == "__main__":
    main()
