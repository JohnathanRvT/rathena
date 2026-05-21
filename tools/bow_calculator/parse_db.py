import re
import os
import json

# Setup paths
workspace_dir = r"c:\dev\Ragnarok-Portable\Ragnarok-Portable\Ragnarok\Emulator"
equip_db_path = os.path.join(workspace_dir, "db", "pre-re", "item_db_equip.yml")
etc_db_path = os.path.join(workspace_dir, "db", "pre-re", "item_db_etc.yml")
output_path = os.path.join(workspace_dir, "tools", "bow_calculator", "db_data.js")

# Helper function to parse simple YAML blocks
def parse_yaml_db(file_path):
    print(f"Reading {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return []

    items = []
    current_item = None
    in_script = False
    script_lines = []
    in_locations = False
    locations = {}

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            
            # Start of a new item
            if line.startswith("  - Id:"):
                # Save previous item
                if current_item is not None:
                    if in_script:
                        current_item["Script"] = "\n".join(script_lines)
                    current_item["Locations"] = locations
                    items.append(current_item)
                
                # Start new item
                item_id = int(stripped.split(":", 1)[1].strip())
                current_item = {"Id": item_id}
                in_script = False
                script_lines = []
                in_locations = False
                locations = {}
                continue

            if current_item is None:
                continue

            # Handle script block
            if stripped.startswith("Script: |"):
                in_script = True
                script_lines = []
                continue
            
            if in_script:
                # If line is indented by more than 4 spaces (or 6 for script), it's part of script
                # If it's a key-value pair of the next attribute, it will have less indentation or no leading spaces
                indent = len(line) - len(line.lstrip())
                if indent >= 6 and stripped:
                    script_lines.append(stripped)
                    continue
                else:
                    in_script = False
                    current_item["Script"] = "\n".join(script_lines)

            # Handle locations block
            if stripped.startswith("Locations:"):
                in_locations = True
                continue

            if in_locations:
                indent = len(line) - len(line.lstrip())
                if indent >= 6 and ":" in stripped:
                    loc_key, loc_val = stripped.split(":", 1)
                    locations[loc_key.strip()] = loc_val.strip().lower() == "true"
                    continue
                else:
                    in_locations = False

            # Parse simple key-value pairs
            if ":" in stripped and not stripped.startswith("#"):
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip()
                
                # Type conversions
                if val.isdigit():
                    val = int(val)
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                
                current_item[key] = val

        # Append last item
        if current_item is not None:
            if in_script:
                current_item["Script"] = "\n".join(script_lines)
            current_item["Locations"] = locations
            items.append(current_item)

    print(f"Parsed {len(items)} items from {os.path.basename(file_path)}")
    return items

# Execute parsers
equip_items = parse_yaml_db(equip_db_path)
etc_items = parse_yaml_db(etc_db_path)

# Filter Bows
bows = []
for item in equip_items:
    if item.get("Type") == "Weapon" and item.get("SubType") == "Bow":
        bows.append({
            "Id": item.get("Id"),
            "AegisName": item.get("AegisName"),
            "Name": item.get("Name"),
            "Attack": item.get("Attack", 0),
            "Slots": item.get("Slots", 0),
            "WeaponLevel": item.get("WeaponLevel", 1),
            "EquipLevelMin": item.get("EquipLevelMin", 1),
            "Script": item.get("Script", "")
        })

# Filter Arrows
arrows = []
for item in etc_items:
    if item.get("Type") == "Ammo" and item.get("SubType") == "Arrow":
        # Extract arrow element from Script if present
        script = item.get("Script", "")
        element = "Neutral"
        if "Ele_Fire" in script:
            element = "Fire"
        elif "Ele_Water" in script:
            element = "Water"
        elif "Ele_Wind" in script:
            element = "Wind"
        elif "Ele_Earth" in script:
            element = "Earth"
        elif "Ele_Holy" in script:
            element = "Holy"
        elif "Ele_Dark" in script:
            element = "Shadow"
        elif "Ele_Ghost" in script:
            element = "Ghost"
        elif "Ele_Poison" in script:
            element = "Poison"
        elif "Ele_Undead" in script:
            element = "Undead"
            
        arrows.append({
            "Id": item.get("Id"),
            "AegisName": item.get("AegisName"),
            "Name": item.get("Name"),
            "Attack": item.get("Attack", 0),
            "Element": element
        })

# Filter Weapon Cards and Parse Modifiers
cards = []
for item in etc_items:
    if item.get("Type") == "Card" and item.get("Locations", {}).get("Right_Hand") == True:
        script = item.get("Script", "")
        card_id = item.get("Id")
        aegis_name = item.get("AegisName")
        name = item.get("Name")
        
        # Parse modifiers from Script
        modifier = None
        
        # 1. Race modifiers (e.g. bonus2 bAddRace,RC_DemiHuman,20;)
        race_match = re.search(r"bAddRace\s*,\s*RC_([a-zA-Z0-9_]+)\s*,\s*(\d+)", script)
        if race_match:
            race = race_match.group(1)
            # Normalize common races
            race_map = {
                "DemiHuman": "Demi-Human",
                "Brute": "Brute",
                "Insect": "Insect",
                "Fish": "Fish",
                "Dragon": "Dragon",
                "Plant": "Plant",
                "Formless": "Formless",
                "Angel": "Angel",
                "Demon": "Demon",
                "Undead": "Undead",
                "Player_Human": "Demi-Human",
                "DemiPlayer": "Demi-Human"
            }
            norm_race = race_map.get(race, race)
            modifier = {"type": "race", "target": norm_race, "value": int(race_match.group(2))}
            
        # 2. Element modifiers (e.g. bonus2 bAddEle,Ele_Fire,20;)
        ele_match = re.search(r"bAddEle\s*,\s*Ele_([a-zA-Z0-9_]+)\s*,\s*(\d+)", script)
        if not modifier and ele_match:
            ele = ele_match.group(1)
            ele_map = {
                "Fire": "Fire", "Water": "Water", "Earth": "Earth", "Wind": "Wind",
                "Dark": "Shadow", "Holy": "Holy", "Ghost": "Ghost", "Poison": "Poison", "Undead": "Undead"
            }
            norm_ele = ele_map.get(ele, ele)
            modifier = {"type": "element", "target": norm_ele, "value": int(ele_match.group(2))}
            
        # 3. Size modifiers (e.g. bonus2 bAddSize,Size_Small,15;)
        size_match = re.search(r"bAddSize\s*,\s*Size_([a-zA-Z0-9_]+)\s*,\s*(\d+)", script)
        if not modifier and size_match:
            size = size_match.group(1)
            modifier = {"type": "size", "target": size, "value": int(size_match.group(2))}
            
        # 4. Ranged physical damage (e.g. bonus bLongAtkRate,10;)
        ranged_match = re.search(r"bLongAtkRate\s*,\s*(\d+)", script)
        if not modifier and ranged_match:
            modifier = {"type": "ranged", "target": "Ranged", "value": int(ranged_match.group(1))}
            
        # 5. Flat ATK (e.g. bonus bBaseAtk,20;)
        atk_match = re.search(r"bBaseAtk\s*,\s*(\d+)", script)
        if not modifier and atk_match:
            modifier = {"type": "flat_atk", "target": "ATK", "value": int(atk_match.group(1))}
            
        # 6. Boss/Class modifier (e.g. bonus2 bAddClass,Class_Boss,25;)
        class_match = re.search(r"bAddClass\s*,\s*Class_Boss\s*,\s*(\d+)", script)
        if not modifier and class_match:
            modifier = {"type": "class", "target": "Boss", "value": int(class_match.group(1))}

        # Fallback/Hardcoded standard cards if regex fails but they are famous cards
        if not modifier:
            if "Hydra" in name:
                modifier = {"type": "race", "target": "Demi-Human", "value": 20}
            elif "Goblin" in name:
                modifier = {"type": "race", "target": "Brute", "value": 20}
            elif "Caramel" in name:
                modifier = {"type": "race", "target": "Insect", "value": 20}
            elif "Flora" in name:
                modifier = {"type": "race", "target": "Fish", "value": 20}
            elif "Peco" in name and "Egg" in name:
                modifier = {"type": "race", "target": "Formless", "value": 20}
            elif "Vadon" in name:
                modifier = {"type": "element", "target": "Fire", "value": 20}
            elif "Drainliar" in name:
                modifier = {"type": "element", "target": "Water", "value": 20}
            elif "Kaho" in name:
                modifier = {"type": "element", "target": "Earth", "value": 20}
            elif "Mandragora" in name:
                modifier = {"type": "element", "target": "Wind", "value": 20}
            elif "Santa" in name and "Poring" in name:
                modifier = {"type": "element", "target": "Shadow", "value": 20}
            elif "Orc" in name and "Skeleton" in name:
                modifier = {"type": "element", "target": "Holy", "value": 20}
            elif "Archer" in name and "Skeleton" in name:
                modifier = {"type": "ranged", "target": "Ranged", "value": 10}
            elif "Cruiser" in name:
                modifier = {"type": "crit_damage", "target": "Crit", "value": 10}
            elif "Minorous" in name:
                modifier = {"type": "size", "target": "Large", "value": 15}
            elif "Skeleton" in name and "Worker" in name:
                modifier = {"type": "size", "target": "Medium", "value": 15}
            elif "Desert" in name and "Wolf" in name:
                modifier = {"type": "size", "target": "Small", "value": 15}
            elif "Abysmal" in name and "Knight" in name:
                modifier = {"type": "class", "target": "Boss", "value": 25}
            elif "Andre" in name:
                modifier = {"type": "flat_atk", "target": "ATK", "value": 20}

        # Include card if we successfully mapped its modifier
        if modifier:
            cards.append({
                "Id": card_id,
                "AegisName": aegis_name,
                "Name": name,
                "Modifier": modifier
            })

# Let's ensure directories exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Write output file
with open(output_path, "w", encoding="utf-8") as f:
    f.write("/* Auto-generated database from rAthena pre-renewal YAML files */\n\n")
    f.write(f"const BOW_DATABASE = {json.dumps(bows, indent=2)};\n\n")
    f.write(f"const ARROW_DATABASE = {json.dumps(arrows, indent=2)};\n\n")
    f.write(f"const CARD_DATABASE = {json.dumps(cards, indent=2)};\n")

print(f"Successfully generated database! Saved to {output_path}")
print(f"Bows count: {len(bows)}")
print(f"Arrows count: {len(arrows)}")
print(f"Cards count: {len(cards)}")
