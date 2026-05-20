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
            var stats = new CharacterStats();

            // Base Stats + Bonuses from Job Level
            int totalStr = build.Str;
            int totalAgi = build.Agi;
            int totalVit = build.Vit;
            int totalInt = build.Int;
            int totalDex = build.Dex;
            int totalLuk = build.Luk;

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

            // HP/SP (Simplification of rAthena's formula)
            if (job != null)
            {
                stats.MaxHp = (int)(job.HpFactor * build.BaseLevel * (1 + totalVit / 100.0) + job.HpIncrease);
                stats.MaxSp = (int)(job.SpFactor * build.BaseLevel * (1 + totalInt / 100.0) + job.SpIncrease);
            }

            // ATK (Pre-Renewal)
            bool isRanged = IsRangedWeapon(build.WeaponType);
            int main = isRanged ? totalDex : totalStr;
            int sub = isRanged ? totalStr : totalDex;

            int baseAtk = main + (main / 10) * (main / 10) + sub / 5 + totalLuk / 5;
            stats.Atk = baseAtk;

            // MATK
            stats.MinMatk = totalInt + (totalInt / 7) * (totalInt / 7);
            stats.MaxMatk = totalInt + (totalInt / 5) * (totalInt / 5);

            // ASPD (Pre-Renewal)
            int baseDelay = 2000;
            if (aspdData != null && aspdData.BaseAspd.ContainsKey(build.WeaponType))
                baseDelay = aspdData.BaseAspd[build.WeaponType];

            double amotion = baseDelay - baseDelay * (4.0 * totalAgi + totalDex) / 1000.0;

            double aspdRate = 1.0;
            if (build.UseAspdPotion) aspdRate -= 0.10;

            amotion *= aspdRate;
            stats.Aspd = 200 - (amotion / 10.0);
            if (stats.Aspd > 190) stats.Aspd = 190;

            // Hit/Flee
            stats.Hit = build.BaseLevel + totalDex;
            stats.Flee = build.BaseLevel + totalAgi;

            // Cast Time Reduction: (1 - Dex/150)
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
                // Skill simulation (very basic for now)
                damagePerAction = CalculateSkillDamage(stats, mob, build);
                double castTime = 1.0 * stats.VariableCastTimeRatio; // Heuristic: 1s base cast
                double afterCastDelay = 0.5; // Heuristic
                actionsPerSecond = 1.0 / (castTime + afterCastDelay);
            }

            // Factor in Hit rate (Pre-re: 80 + Hit - Flee)
            double hitChance = (80.0 + stats.Hit - mob.Dex) / 100.0;
            hitChance = Math.Clamp(hitChance, 0.05, 1.0);

            double dps = damagePerAction * actionsPerSecond * hitChance;
            if (dps <= 0) return double.PositiveInfinity;

            double combatTime = mob.Hp / dps;
            double travelTime = 5.0; // Heuristic

            return combatTime + travelTime;
        }

        private static double CalculatePhysicalDamage(CharacterStats stats, MobData mob, CharacterBuild build)
        {
            double atk = stats.Atk;

            // Element modifier (simplified)
            double elementMod = GetElementModifier(build.WeaponType, mob.Element);

            double damage = atk * elementMod * (100 - mob.Defense) / 100.0 - mob.Vit;
            if (damage < 1) damage = 1;
            return damage;
        }

        private static double CalculateSkillDamage(CharacterStats stats, MobData mob, CharacterBuild build)
        {
            // Simple: 200% - 500% damage multiplier
            double multiplier = 3.0;
            return CalculatePhysicalDamage(stats, mob, build) * multiplier;
        }

        private static double GetElementModifier(string weapon, string mobElement)
        {
            // Placeholder: RO element table is complex
            if (mobElement == "Ghost") return 0.25;
            if (mobElement == "Undead") return 1.25;
            return 1.0;
        }
    }
}
