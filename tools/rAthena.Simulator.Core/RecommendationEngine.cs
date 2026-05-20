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

                foreach (var spawn in map)
                {
                    var mob = data.Mobs.FirstOrDefault(m => m.Id == spawn.MobId);
                    if (mob == null) continue;

                    // Improved MVP detection
                    if (settings.ExcludeMvp && mob.MvpExp > 0) continue;

                    double ttk = Calculator.CalculateTTK(stats, mob, build);
                    double killsPerHour = 3600.0 / ttk;

                    // Factor in spawn amount: if 1 mob spawns, we can't kill 100/hr if it has 5 min spawn time
                    // But simplified: 1 mob = max 30 kills/hr, etc.
                    killsPerHour = Math.Min(killsPerHour, spawn.Amount * 100);

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
