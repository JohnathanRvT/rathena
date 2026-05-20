using System;
using System.Collections.Generic;
using System.Linq;
using rAthena.Simulator.Core.Models;

namespace rAthena.Simulator.Core
{
    public class Calculator
    {
        public static CharacterStats CalculateStats(CharacterBuild build, SimulatorData data)
        {
            var job = data.Jobs.FirstOrDefault(j => j.Name == build.Job);
            var aspdData = data.Aspd.FirstOrDefault(a => a.JobName == build.Job);
            var weapon = data.Items.FirstOrDefault(i => i.Id == build.WeaponId);
            var stats = new CharacterStats();

            // 1. Base Stats + Buffs + Bonuses from Job Level
            int totalStr = build.Str;
            int totalAgi = build.Agi;
            int totalVit = build.Vit;
            int totalInt = build.Int;
            int totalDex = build.Dex;
            int totalLuk = build.Luk;

            if (build.HasBlessing) { totalStr += 10; totalInt += 10; totalDex += 10; }
            if (build.HasAgiUp) { totalAgi += 12; }

            if (job != null)
            {
                var bonuses = job.Bonuses.Where(b => b.Level <= build.JobLevel);
                totalStr += bonuses.Sum(b => b.Str);
                totalAgi += bonuses.Sum(b => b.Agi);
                totalVit += bonuses.Sum(b => b.Vit);
                totalInt += bonuses.Sum(b => b.Int);
                totalDex += bonuses.Sum(b => b.Dex);
                totalLuk += bonuses.Sum(b => b.Luk);
            }

            stats.TotalStr = totalStr;
            stats.TotalAgi = totalAgi;
            stats.TotalVit = totalVit;
            stats.TotalInt = totalInt;
            stats.TotalDex = totalDex;
            stats.TotalLuk = totalLuk;

            // 2. HP/SP
            if (job != null)
            {
                double baseHp = 1;
                var hpEntry = job.BaseHp.OrderByDescending(h => h.Level).FirstOrDefault(h => h.Level <= build.BaseLevel);
                if (hpEntry != null) baseHp = hpEntry.Value;

                double baseSp = 1;
                var spEntry = job.BaseSp.OrderByDescending(s => s.Level).FirstOrDefault(s => s.Level <= build.BaseLevel);
                if (spEntry != null) baseSp = spEntry.Value;

                stats.MaxHp = (int)Math.Floor(baseHp * (1 + totalVit / 100.0));
                stats.MaxSp = (int)Math.Floor(baseSp * (1 + totalInt / 100.0));
            }

            // 3. ATK
            bool isRanged = IsRangedWeapon(build.WeaponType);
            int main = isRanged ? totalDex : totalStr;
            int sub = isRanged ? totalStr : totalDex;

            int baseAtk = main + (main / 10) * (main / 10) + sub / 5 + totalLuk / 5;
            stats.Atk = baseAtk;

            if (weapon != null)
            {
                int wAtk = weapon.Attack;
                // Refine bonus (Pre-re: Lv1: +2, Lv2: +3, Lv3: +5, Lv4: +7)
                int refineBonus = 0;
                switch (weapon.WeaponLevel)
                {
                    case 1: refineBonus = build.WeaponRefine * 2; break;
                    case 2: refineBonus = build.WeaponRefine * 3; break;
                    case 3: refineBonus = build.WeaponRefine * 5; break;
                    case 4: refineBonus = build.WeaponRefine * 7; break;
                }
                stats.WeaponAtk = wAtk + refineBonus;
            }

            // 4. MATK
            stats.MinMatk = totalInt + (totalInt / 7) * (totalInt / 7);
            stats.MaxMatk = totalInt + (totalInt / 5) * (totalInt / 5);

            // 5. ASPD
            int baseDelay = 2000;
            if (aspdData != null && aspdData.BaseAspd.ContainsKey(build.WeaponType))
                baseDelay = aspdData.BaseAspd[build.WeaponType];

            double amotion = baseDelay - baseDelay * (4.0 * totalAgi + totalDex) / 1000.0;

            double aspdRate = 1.0;
            if (build.UseAspdPotion) aspdRate -= 0.10;

            amotion *= aspdRate;
            stats.Aspd = 200 - (amotion / 10.0);
            if (stats.Aspd > 190) stats.Aspd = 190;

            // 6. Hit/Flee
            stats.Hit = build.BaseLevel + totalDex;
            stats.Flee = build.BaseLevel + totalAgi;

            // 7. Cast Time Reduction
            stats.VariableCastTimeRatio = Math.Max(0, 1.0 - (totalDex / 150.0));

            return stats;
        }

        private static bool IsRangedWeapon(string weaponType)
        {
            string[] ranged = { "Bow", "Revolver", "Rifle", "Gatling", "Shotgun", "Grenade" };
            return ranged.Contains(weaponType);
        }

        public static double CalculateTTK(CharacterStats stats, MobData mob, CharacterBuild build)
        {
            double damagePerAction;
            double actionsPerSecond;

            if (build.CombatStyle == "Auto-Attack")
            {
                damagePerAction = CalculatePhysicalDamage(stats, mob, build);
                actionsPerSecond = 50.0 / (200.0 - stats.Aspd);
            }
            else
            {
                damagePerAction = CalculateSkillDamage(stats, mob, build);
                double castTime = 1.0 * stats.VariableCastTimeRatio;
                double afterCastDelay = 0.5;
                actionsPerSecond = 1.0 / (castTime + afterCastDelay);
            }

            double hitChance = (80.0 + stats.Hit - mob.Dex) / 100.0;
            hitChance = Math.Clamp(hitChance, 0.05, 1.0);

            double dps = damagePerAction * actionsPerSecond * hitChance;
            if (dps <= 0) return double.PositiveInfinity;

            double combatTime = mob.Hp / dps;
            double travelTime = 5.0;

            return combatTime + travelTime;
        }

        private static double CalculatePhysicalDamage(CharacterStats stats, MobData mob, CharacterBuild build)
        {
            double totalAtk = stats.Atk + stats.WeaponAtk;
            double elementMod = GetElementModifier(build.WeaponType, mob.Element);

            // Def reduction then Vit subtraction
            double damage = totalAtk * elementMod * (100 - mob.Defense) / 100.0 - mob.Vit;
            if (damage < 1) damage = 1;
            return damage;
        }

        private static double CalculateSkillDamage(CharacterStats stats, MobData mob, CharacterBuild build)
        {
            double multiplier = 3.0;
            return CalculatePhysicalDamage(stats, mob, build) * multiplier;
        }

        private static double GetElementModifier(string weapon, string mobElement)
        {
            if (mobElement == "Ghost") return 0.25;
            if (mobElement == "Undead") return 1.25;
            return 1.0;
        }
    }
}
