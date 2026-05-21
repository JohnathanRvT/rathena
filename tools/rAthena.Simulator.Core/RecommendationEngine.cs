using System;
using System.Collections.Generic;
using System.Linq;
using rAthena.Simulator.Core.Models;

namespace rAthena.Simulator.Core
{
    public class RecommendationEngine
    {
        public static List<MapRecommendation> GetRecommendations(CharacterStats stats, CharacterBuild build, SimulatorData data, SimulationSettings settings)
        {
            var results = new List<MapRecommendation>();
            var maps = data.Spawns.GroupBy(s => s.MapName);

            foreach (var map in maps)
            {
                double totalExpHr = 0;
                double totalZenyHr = 0;
                var mobDetails = new List<MobRecommendationDetail>();

                // Aggregating spawn amounts first to avoid duplicates in display
                var mapSpawns = map.GroupBy(s => s.MobId).Select(g => new { MobId = g.Key, Amount = g.Sum(s => s.Amount) });

                foreach (var spawn in mapSpawns)
                {
                    var mob = data.Mobs.FirstOrDefault(m => m.Id == spawn.MobId);
                    if (mob == null) continue;

                    if (settings.ExcludeMvp && mob.MvpExp > 0) continue;

                    // Unbeatable check: if hit chance is 5% (cap) and we can't do enough damage
                    double hitChance = (80.0 + stats.Hit - mob.Dex) / 100.0;
                    if (hitChance < 0.10) continue; // Heuristic: Skip if < 10% hit chance

                    double ttk = Calculator.CalculateTTK(stats, mob, build);
                    if (double.IsInfinity(ttk) || ttk > 300) continue; // Skip if takes > 5 mins to kill one

                    double killsPerHour = 3600.0 / ttk;

                    // Capacity check: Can't kill more than what's available
                    double mapCapacityHr = spawn.Amount * 120.0;
                    killsPerHour = Math.Min(killsPerHour, mapCapacityHr);

                    double expHr = killsPerHour * mob.BaseExp * settings.BaseExpRate * settings.ExpManual;

                    double mobZeny = 0;
                    foreach (var drop in mob.Drops)
                    {
                        var item = data.Items.FirstOrDefault(i => i.AegisName == drop.Item);
                        if (item == null) continue;

                        double effectiveRate = drop.Rate * settings.DropRate / 10000.0;
                        if (settings.UseGum) effectiveRate *= 2.0;
                        effectiveRate = Math.Min(effectiveRate, 1.0);

                        double price = item.Sell > 0 ? item.Sell : item.Buy / 2.0;
                        if (settings.UseOc) price *= 1.24;

                        mobZeny += effectiveRate * price;
                    }
                    double zenyHr = killsPerHour * mobZeny;

                    totalExpHr += expHr;
                    totalZenyHr += zenyHr;

                    mobDetails.Add(new MobRecommendationDetail
                    {
                        MobName = mob.Name,
                        KillsPerHour = killsPerHour,
                        ExpPerHour = expHr,
                        ZenyPerHour = zenyHr
                    });
                }

                if (totalExpHr > 0 || totalZenyHr > 0)
                {
                    results.Add(new MapRecommendation
                    {
                        MapName = map.Key,
                        ExpPerHour = totalExpHr,
                        ZenyPerHour = totalZenyHr,
                        MobDetails = mobDetails.OrderByDescending(m => m.ExpPerHour).ToList()
                    });
                }
            }

            return results.OrderByDescending(r => r.ExpPerHour).Take(50).ToList();
        }
    }

    public class SimulationSettings
    {
        public int BaseExpRate { get; set; } = 1;
        public int DropRate { get; set; } = 1;
        public double ExpManual { get; set; } = 1.0;
        public bool UseGum { get; set; }
        public bool UseOc { get; set; }
        public bool ExcludeMvp { get; set; }
    }

    public class MapRecommendation
    {
        public string MapName { get; set; } = "";
        public double ExpPerHour { get; set; }
        public double ZenyPerHour { get; set; }
        public List<MobRecommendationDetail> MobDetails { get; set; } = new();
        public bool ShowDetails { get; set; }
    }

    public class MobRecommendationDetail
    {
        public string MobName { get; set; } = "";
        public double KillsPerHour { get; set; }
        public double ExpPerHour { get; set; }
        public double ZenyPerHour { get; set; }
    }
}
