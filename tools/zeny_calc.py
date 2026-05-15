#!/usr/bin/env python3
import os
import re
import argparse
import sys
import math
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print("Error: The 'PyYAML' module is required but not installed.")
    print("Please install it using: pip install PyYAML")
    sys.exit(1)

def get_rathena_root():
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, 'db')) and os.path.isdir(os.path.join(current, 'npc')):
            return current
        current = os.path.dirname(current)
    return os.getcwd()

ROOT = get_rathena_root()

class ItemDatabase:
    def __init__(self):
        self.items = {}

    def load_from_yml(self, filepath):
        abs_path = os.path.join(ROOT, filepath)
        if not os.path.exists(abs_path): return
        with open(abs_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'Body' in data:
                for item in data['Body']:
                    aegis_name = item.get('AegisName')
                    if not aegis_name: continue
                    buy, sell = item.get('Buy'), item.get('Sell')
                    actual_sell = sell if sell is not None else (buy // 2 if buy is not None else 0)
                    self.items[aegis_name] = {'id': item.get('Id'), 'name': item.get('Name'), 'sell': actual_sell}

class MonsterDatabase:
    def __init__(self):
        self.mobs = {}

    def load_from_yml(self, filepath):
        abs_path = os.path.join(ROOT, filepath)
        if not os.path.exists(abs_path): return
        with open(abs_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'Body' in data:
                for mob in data['Body']:
                    mob_id = mob.get('Id')
                    if not mob_id: continue
                    drops = mob.get('Drops', [])
                    mvp_drops = mob.get('MvpDrops', [])
                    self.mobs[mob_id] = {
                        'name': mob.get('Name'),
                        'level': mob.get('Level', 1),
                        'hp': mob.get('Hp', 1),
                        'base_exp': mob.get('BaseExp', 0),
                        'job_exp': mob.get('JobExp', 0),
                        'atk': mob.get('Attack', 0),
                        'def': mob.get('Defense', 0),
                        'agi': mob.get('Agi', 1),
                        'dex': mob.get('Dex', 1),
                        'luk': mob.get('Luk', 1),
                        'drops': (drops if drops else []) + (mvp_drops if mvp_drops else [])
                    }

class LevelPenaltyDatabase:
    def __init__(self):
        self.penalties = {}

    def load_from_yml(self, filepath):
        abs_path = os.path.join(ROOT, filepath)
        if not os.path.exists(abs_path): return
        with open(abs_path, 'r') as f:
            data = yaml.safe_load(f)
            if data and 'Body' in data:
                for entry in data['Body']:
                    p_type = entry.get('Type')
                    if p_type not in self.penalties: self.penalties[p_type] = {}
                    for diff_entry in entry.get('LevelDifferences', []):
                        self.penalties[p_type][diff_entry['Difference']] = diff_entry['Rate']

    def get_penalty(self, p_type, diff):
        if p_type not in self.penalties: return 100
        sorted_diffs = sorted(self.penalties[p_type].keys())
        rate = 100
        if diff > 0:
            for d in sorted_diffs:
                if d > 0 and diff >= d: rate = self.penalties[p_type][d]
        elif diff < 0:
            for d in reversed(sorted_diffs):
                if d < 0 and diff <= d: rate = self.penalties[p_type][d]
        return rate

class MapSpawnDatabase:
    def __init__(self):
        self.spawns = {}
        self.spawned_mob_ids = set()

    def load_from_conf(self, conf_path):
        abs_path = os.path.join(ROOT, conf_path)
        if not os.path.exists(abs_path): return
        with open(abs_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('npc:'):
                    self.load_from_script(line.split(':', 1)[1].strip())

    def load_from_script(self, script_path):
        abs_path = os.path.join(ROOT, script_path)
        if not os.path.exists(abs_path): return
        spawn_re = re.compile(r'^([^,]+),[\d,]+\s+(?:monster|boss_monster)\s+[^\t]+\s+(\d+),(\d+)')
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('//'): continue
                match = spawn_re.match(line)
                if match:
                    map_name, mob_id, count = match.group(1), int(match.group(2)), int(match.group(3))
                    if map_name not in self.spawns: self.spawns[map_name] = []
                    self.spawns[map_name].append({'mob_id': mob_id, 'count': count})
                    self.spawned_mob_ids.add(mob_id)

class CombatSimulator:
    def __init__(self, pre_re=False):
        self.pre_re = pre_re

    def get_hit_chance(self, char_hit, mob_flee):
        base = 80 if self.pre_re else 100
        cap = 95 if self.pre_re else 100
        return max(5, min(cap, base + char_hit - mob_flee))

    def get_flee_chance(self, char_flee, mob_hit):
        base = 80 if self.pre_re else 100
        return max(0, min(95, 100 - (base + mob_hit - char_flee)))

    def get_ttk(self, char_atk, char_hit, char_aspd, mob_hp, mob_flee, mob_def):
        hit_chance = self.get_hit_chance(char_hit, mob_flee) / 100.0
        damage_per_hit = max(1, char_atk - mob_def) * hit_chance
        hits_per_sec = 50.0 / (200.0 - char_aspd)
        if damage_per_hit <= 0: return float('inf')
        return mob_hp / (damage_per_hit * hits_per_sec)

class ZenyCalculator:
    def __init__(self, item_db, mob_db, spawn_db, penalty_db=None, pre_re=False):
        self.item_db, self.mob_db, self.spawn_db, self.penalty_db = item_db, mob_db, spawn_db, penalty_db
        self.pre_re = pre_re
        self.combat = CombatSimulator(pre_re)

    def calculate_mob_zeny(self, mob_id, base_drop_rate=1, oc_level=0, gum=False, char_level=None):
        mob = self.mob_db.mobs.get(mob_id)
        if not mob: return 0.0
        oc_mod = (5 + oc_level * 2 - (1 if oc_level == 10 else 0)) / 100.0 if oc_level > 0 else 0
        drop_bonus = 100 + (100 if gum else 0)
        penalty = self.penalty_db.get_penalty('Drop', char_level - mob['level']) if char_level and self.penalty_db else 100
        total = 0.0
        for drop in mob['drops']:
            item = self.item_db.items.get(drop.get('Item'))
            if not item: continue
            rate = (drop.get('Rate', 0) * base_drop_rate * drop_bonus * penalty) / 100000000.0
            total += item['sell'] * (1.0 + oc_mod) * min(0.9, rate)
        return total

    def calculate_mob_exp(self, mob_id, base_exp_rate=1, exp_boost=100, job_exp_boost=100, char_level=None):
        mob = self.mob_db.mobs.get(mob_id)
        if not mob: return 0, 0
        penalty = self.penalty_db.get_penalty('Exp', char_level - mob['level']) if char_level and self.penalty_db else 100
        b_exp = mob['base_exp'] * base_exp_rate * (exp_boost / 100.0) * (penalty / 100.0)
        j_exp = mob['job_exp'] * base_exp_rate * (job_exp_boost / 100.0) * (penalty / 100.0)
        return b_exp, j_exp

    def rank_mobs(self, char_stats, base_drop_rate=1, base_exp_rate=1, oc_level=10, gum=False, exp_boost=100, job_exp_boost=100, optimize_for='zeny', spawned_only=True):
        results = []
        char_level = char_stats.get('level', 1)
        target_ids = self.spawn_db.spawned_mob_ids if spawned_only else self.mob_db.mobs.keys()
        for mob_id in target_ids:
            mob = self.mob_db.mobs.get(mob_id)
            if not mob: continue
            if self.pre_re:
                mob_flee = mob['level'] + mob['agi']
                mob_hit = mob['level'] + mob['dex']
            else:
                mob_flee = mob['level'] + mob['agi'] + mob['luk']//5 + 100
                mob_hit = mob['level'] + mob['dex'] + mob['luk']//3 + 175

            ttk = self.combat.get_ttk(char_stats['atk'], char_stats['hit'], char_stats['aspd'], mob['hp'], mob_flee, mob['def'])
            if ttk == float('inf') or ttk > 60: continue
            zeny = self.calculate_mob_zeny(mob_id, base_drop_rate, oc_level, gum, char_level)
            b_exp, j_exp = self.calculate_mob_exp(mob_id, base_exp_rate, exp_boost, job_exp_boost, char_level)
            kills_per_hr = 3600 / (ttk + 1.5) # 1.5s overhead
            results.append({
                'id': mob_id, 'name': mob['name'], 'level': mob['level'],
                'zeny_hr': zeny * kills_per_hr, 'exp_hr': (b_exp + j_exp) * kills_per_hr,
                'ttk': ttk, 'hit_chance': self.combat.get_hit_chance(char_stats['hit'], mob_flee),
                'flee_chance': self.combat.get_flee_chance(char_stats.get('flee', 0), mob_hit)
            })
        return sorted(results, key=lambda x: x['zeny_hr' if optimize_for == 'zeny' else 'exp_hr'], reverse=True)

    def rank_maps(self, char_stats, base_drop_rate=1, base_exp_rate=1, oc_level=10, gum=False, exp_boost=100, job_exp_boost=100):
        map_results = {}
        char_level = char_stats.get('level', 1)
        mob_cache = {}

        for map_name, spawns in self.spawn_db.spawns.items():
            weighted_zeny_per_kill = 0
            weighted_exp_per_kill = 0
            weighted_ttk = 0
            total_count = 0

            for spawn in spawns:
                mob_id = spawn['mob_id']
                count = spawn['count']
                if mob_id not in mob_cache:
                    mob = self.mob_db.mobs.get(mob_id)
                    if not mob:
                        mob_cache[mob_id] = None
                        continue
                    if self.pre_re:
                        mob_flee = mob['level'] + mob['agi']
                    else:
                        mob_flee = mob['level'] + mob['agi'] + mob['luk']//5 + 100

                    ttk = self.combat.get_ttk(char_stats['atk'], char_stats['hit'], char_stats['aspd'], mob['hp'], mob_flee, mob['def'])
                    if ttk == float('inf') or ttk > 60:
                        mob_cache[mob_id] = None
                        continue

                    zeny = self.calculate_mob_zeny(mob_id, base_drop_rate, oc_level, gum, char_level)
                    b_exp, j_exp = self.calculate_mob_exp(mob_id, base_exp_rate, exp_boost, job_exp_boost, char_level)
                    mob_cache[mob_id] = {'zeny': zeny, 'exp': b_exp + j_exp, 'ttk': ttk}

                if mob_cache[mob_id]:
                    weighted_zeny_per_kill += mob_cache[mob_id]['zeny'] * count
                    weighted_exp_per_kill += mob_cache[mob_id]['exp'] * count
                    weighted_ttk += mob_cache[mob_id]['ttk'] * count
                    total_count += count

            if total_count > 0:
                avg_zeny = weighted_zeny_per_kill / total_count
                avg_exp = weighted_exp_per_kill / total_count
                avg_ttk = weighted_ttk / total_count

                # Higher density reduces overhead (walking time)
                density_factor = min(2.0, max(0.5, total_count / 50.0))
                overhead = 2.0 / density_factor

                kills_per_hr = 3600 / (avg_ttk + overhead)
                map_results[map_name] = {'zeny_hr': avg_zeny * kills_per_hr, 'exp_hr': avg_exp * kills_per_hr}

        return sorted([{'map': k, **v} for k, v in map_results.items()], key=lambda x: x['zeny_hr'], reverse=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pre-re', action='store_true')
    parser.add_argument('--level', type=int, default=100)
    parser.add_argument('--atk', type=int, default=200)
    parser.add_argument('--hit', type=int, default=350)
    parser.add_argument('--aspd', type=int, default=180)
    parser.add_argument('--base-drop', type=int, default=1)
    parser.add_argument('--base-exp', type=int, default=1)
    parser.add_argument('--opt', choices=['zeny', 'exp'], default='zeny')
    parser.add_argument('--map', action='store_true', help='Rank maps instead of mobs')
    args = parser.parse_args()

    mode_dir = "pre-re" if args.pre_re else "re"
    item_db = ItemDatabase()
    for f in ['etc', 'equip', 'usable']: item_db.load_from_yml(f'db/{mode_dir}/item_db_{f}.yml')
    mob_db = MonsterDatabase()
    mob_db.load_from_yml(f'db/{mode_dir}/mob_db.yml')
    penalty_db = LevelPenaltyDatabase()
    if not args.pre_re: penalty_db.load_from_yml('db/re/level_penalty.yml')
    spawn_db = MapSpawnDatabase()
    spawn_db.load_from_conf(f'npc/{mode_dir}/scripts_monsters.conf')

    calc = ZenyCalculator(item_db, mob_db, spawn_db, penalty_db, args.pre_re)
    stats = {'level': args.level, 'atk': args.atk, 'hit': args.hit, 'aspd': args.aspd}

    if args.map:
        ranked = calc.rank_maps(stats, base_drop_rate=args.base_drop, base_exp_rate=args.base_exp)
        print(f"Top Maps for ZENY:")
        for i, m in enumerate(ranked[:15]):
            print(f"{i+1}. {m['map']}: {m['zeny_hr']:.0f} potential/hr")
    else:
        ranked = calc.rank_mobs(stats, base_drop_rate=args.base_drop, base_exp_rate=args.base_exp, optimize_for=args.opt)
        print(f"Top Mobs for {args.opt.upper()}:")
        for i, m in enumerate(ranked[:15]):
            print(f"{i+1}. {m['name']} ({m['id']}): {m['zeny_hr' if args.opt=='zeny' else 'exp_hr']:.0f}/hr")

if __name__ == "__main__":
    main()
