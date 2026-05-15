#!/usr/bin/env python3
import os
import re
import argparse
import sys
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print("Error: The 'PyYAML' module is required but not installed.")
    print("Please install it using: pip install PyYAML")
    sys.exit(1)

# Detect rAthena Root
def get_rathena_root():
    # Start from the script's directory
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current): # Stop at root
        if os.path.isdir(os.path.join(current, 'db')) and os.path.isdir(os.path.join(current, 'npc')):
            return current
        current = os.path.dirname(current)
    # Fallback to CWD
    return os.getcwd()

ROOT = get_rathena_root()

class ItemDatabase:
    def __init__(self):
        self.items = {}

    def load_from_yml(self, filepath):
        abs_path = os.path.join(ROOT, filepath)
        if not os.path.exists(abs_path):
            return
        with open(abs_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'Body' in data:
                for item in data['Body']:
                    aegis_name = item.get('AegisName')
                    if not aegis_name:
                        continue

                    buy = item.get('Buy')
                    sell = item.get('Sell')

                    if sell is not None:
                        actual_sell = sell
                    elif buy is not None:
                        actual_sell = buy // 2
                    else:
                        actual_sell = 0

                    self.items[aegis_name] = {
                        'id': item.get('Id'),
                        'name': item.get('Name'),
                        'sell': actual_sell
                    }

class MonsterDatabase:
    def __init__(self):
        self.mobs = {}

    def load_from_yml(self, filepath):
        abs_path = os.path.join(ROOT, filepath)
        if not os.path.exists(abs_path):
            return
        with open(abs_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'Body' in data:
                for mob in data['Body']:
                    mob_id = mob.get('Id')
                    if not mob_id:
                        continue

                    drops = mob.get('Drops', [])
                    mvp_drops = mob.get('MvpDrops', [])

                    self.mobs[mob_id] = {
                        'name': mob.get('Name'),
                        'drops': (drops if drops else []) + (mvp_drops if mvp_drops else [])
                    }

class MapSpawnDatabase:
    def __init__(self):
        self.spawns = {} # map_name -> [ {mob_id, count} ]

    def load_from_conf(self, conf_path):
        abs_path = os.path.join(ROOT, conf_path)
        if not os.path.exists(abs_path):
            print(f"Warning: Monster script config not found: {abs_path}")
            return

        with open(abs_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('npc:'):
                    npc_path = line.split(':', 1)[1].strip()
                    self.load_from_script(npc_path)

    def load_from_script(self, script_path):
        abs_path = os.path.join(ROOT, script_path)
        if not os.path.exists(abs_path):
            return

        # Regex for: map,x,y,xs,ys	(monster|boss_monster)	name	id,count,time...
        # Variations in whitespace and optional time/event fields.
        spawn_re = re.compile(r'^([^,]+),[\d,]+\s+(?:monster|boss_monster)\s+[^\t]+\s+(\d+),(\d+)')

        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('//'):
                    continue

                # Some scripts use tabs, some use spaces.
                # Normalize line to handle different spacing between fields.
                match = spawn_re.match(line)
                if match:
                    map_name = match.group(1)
                    mob_id = int(match.group(2))
                    count = int(match.group(3))

                    if map_name not in self.spawns:
                        self.spawns[map_name] = []
                    self.spawns[map_name].append({'mob_id': mob_id, 'count': count})

class ZenyCalculator:
    def __init__(self, item_db, mob_db, spawn_db):
        self.item_db = item_db
        self.mob_db = mob_db
        self.spawn_db = spawn_db

    def calculate_oc_modifier(self, level):
        if level <= 0: return 0.0
        rate = 5 + level * 2 - (1 if level == 10 else 0)
        return rate / 100.0

    def calculate_mob_zeny(self, mob_id, base_rate=1, oc_level=0, gum=False):
        if mob_id not in self.mob_db.mobs:
            return 0.0

        mob = self.mob_db.mobs[mob_id]
        oc_mod = self.calculate_oc_modifier(oc_level)
        drop_bonus = 100 + (100 if gum else 0)

        total_zeny = 0.0
        for drop in mob['drops']:
            item_name = drop.get('Item')
            drop_rate = drop.get('Rate', 0)

            if item_name not in self.item_db.items:
                continue

            item = self.item_db.items[item_name]
            sell_price = item['sell']

            effective_rate = (drop_rate * base_rate * drop_bonus) / 1000000.0
            if effective_rate > 1.0: effective_rate = 1.0

            price = sell_price * (1.0 + oc_mod)
            total_zeny += price * effective_rate

        return total_zeny

    def get_all_mobs_zeny(self, base_rate=1, oc_level=0, gum=False):
        results = []
        for mob_id, mob in self.mob_db.mobs.items():
            zeny = self.calculate_mob_zeny(mob_id, base_rate, oc_level, gum)
            if zeny > 0:
                results.append({
                    'id': mob_id,
                    'name': mob['name'],
                    'zeny': zeny
                })
        return sorted(results, key=lambda x: x['zeny'], reverse=True)

    def get_all_maps_zeny(self, base_rate=1, oc_level=0, gum=False):
        results = []
        mob_zeny_cache = {}

        for map_name, spawns in self.spawn_db.spawns.items():
            total_map_zeny = 0.0
            for spawn in spawns:
                mid = spawn['mob_id']
                if mid not in mob_zeny_cache:
                    mob_zeny_cache[mid] = self.calculate_mob_zeny(mid, base_rate, oc_level, gum)
                total_map_zeny += mob_zeny_cache[mid] * spawn['count']

            if total_map_zeny > 0:
                results.append({
                    'map': map_name,
                    'zeny': total_map_zeny
                })
        return sorted(results, key=lambda x: x['zeny'], reverse=True)

def main():
    parser = argparse.ArgumentParser(description='rAthena Zeny Rate Calculator')
    parser.add_argument('--pre-re', action='store_true', help='Use Pre-Renewal database and NPC paths')
    parser.add_argument('--base-rate', type=int, default=1, help='Base server drop rate (e.g. 1, 10, 100)')
    parser.add_argument('--oc', type=int, default=0, choices=range(0, 11), help='Merchant Overcharge level (0-10)')
    parser.add_argument('--gum', action='store_true', help='Enable Bubble Gum (+100%% drop rate)')
    parser.add_argument('--top-mobs', type=int, default=10, help='Number of top mobs to display')
    parser.add_argument('--top-maps', type=int, default=10, help='Number of top maps to display')
    parser.add_argument('--mob', type=str, help='Search for a specific monster by name')
    parser.add_argument('--map', type=str, help='Search for a specific map by name')

    args = parser.parse_args()

    mode_dir = "pre-re" if args.pre_re else "re"
    print(f"Loading databases ({'Pre-Renewal' if args.pre_re else 'Renewal'}) from: {ROOT}")

    item_db = ItemDatabase()
    item_db.load_from_yml(f'db/{mode_dir}/item_db_etc.yml')
    item_db.load_from_yml(f'db/{mode_dir}/item_db_equip.yml')
    item_db.load_from_yml(f'db/{mode_dir}/item_db_usable.yml')

    mob_db = MonsterDatabase()
    mob_db.load_from_yml(f'db/{mode_dir}/mob_db.yml')

    spawn_db = MapSpawnDatabase()
    spawn_db.load_from_conf(f'npc/{mode_dir}/scripts_monsters.conf')

    calc = ZenyCalculator(item_db, mob_db, spawn_db)

    if args.mob:
        print(f"\n--- Search results for Mob: {args.mob} ---")
        found = False
        for mob_id, mob in mob_db.mobs.items():
            if args.mob.lower() in mob['name'].lower():
                zeny = calc.calculate_mob_zeny(mob_id, args.base_rate, args.oc, args.gum)
                print(f"Mob: {mob['name']} ({mob_id}) - Average Zeny: {zeny:.2f} z")
                found = True
        if not found:
            print("No monster found.")
    else:
        print(f"\n--- Top {args.top_mobs} Mobs by Average Zeny per Kill ---")
        print(f"(Config: Base Rate {args.base_rate}x, OC Level {args.oc}, Bubble Gum: {'Yes' if args.gum else 'No'})")
        top_mobs = calc.get_all_mobs_zeny(args.base_rate, args.oc, args.gum)
        for i, mob in enumerate(top_mobs[:args.top_mobs]):
            print(f"{i+1}. {mob['name']} ({mob['id']}): {mob['zeny']:.2f} z")

    if args.map:
        print(f"\n--- Search results for Map: {args.map} ---")
        found = False
        for map_name, spawns in spawn_db.spawns.items():
            if args.map.lower() in map_name.lower():
                total_map_zeny = 0.0
                for spawn in spawns:
                    total_map_zeny += calc.calculate_mob_zeny(spawn['mob_id'], args.base_rate, args.oc, args.gum) * spawn['count']
                print(f"Map: {map_name} - Total Zeny: {total_map_zeny:.2f} z")
                found = True
        if not found:
            print("No map found.")
    else:
        print(f"\n--- Top {args.top_maps} Maps by Total Zeny (per full spawn) ---")
        top_maps = calc.get_all_maps_zeny(args.base_rate, args.oc, args.gum)
        if not top_maps:
            print("No map spawns found. Check npc/re/scripts_monsters.conf or npc/pre-re/scripts_monsters.conf")
        for i, m in enumerate(top_maps[:args.top_maps]):
            print(f"{i+1}. {m['map']}: {m['zeny']:.2f} z")

if __name__ == "__main__":
    main()
