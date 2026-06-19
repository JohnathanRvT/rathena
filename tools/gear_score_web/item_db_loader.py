import yaml
import os

def load_item_db(root_path):
    item_db = {}
    paths = [
        'db/re/item_db_equip.yml',
        'db/re/item_db_usable.yml',
        'db/re/item_db_etc.yml'
    ]

    for rel_path in paths:
        full_path = os.path.join(root_path, rel_path)
        if not os.path.exists(full_path):
            continue

        with open(full_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if not data or 'Body' not in data:
                continue

            for item in data['Body']:
                item_id = item.get('Id')
                if item_id is None:
                    continue

                item_db[item_id] = {
                    'name': item.get('Name', 'Unknown'),
                    'atk': item.get('Attack', 0),
                    'matk': item.get('MagicAttack', 0),
                    'def': item.get('Defense', 0),
                    'wlv': item.get('WeaponLevel', 0),
                    'alv': item.get('ArmorLevel', 0)
                }

    return item_db

if __name__ == "__main__":
    # Test loading
    db = load_item_db(".")
    print(f"Loaded {len(db)} items.")
    if 1101 in db:
        print(f"Item 1101: {db[1101]}")
