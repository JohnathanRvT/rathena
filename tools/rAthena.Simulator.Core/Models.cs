using System;
using System.Collections.Generic;
using System.Linq;

namespace rAthena.Simulator.Core.Models
{
    public class CharacterBuild
    {
        public string Name { get; set; } = "";
        public string Job { get; set; } = "Novice";
        public int BaseLevel { get; set; } = 1;
        public int JobLevel { get; set; } = 1;
        public int Str { get; set; } = 1;
        public int Agi { get; set; } = 1;
        public int Vit { get; set; } = 1;
        public int Int { get; set; } = 1;
        public int Dex { get; set; } = 1;
        public int Luk { get; set; } = 1;
        public string WeaponType { get; set; } = "Fist";
        public string CombatStyle { get; set; } = "Auto-Attack";
        public bool UseAspdPotion { get; set; }
    }

    public class CharacterStats
    {
        public int MaxHp { get; set; }
        public int MaxSp { get; set; }
        public int TotalStr { get; set; }
        public int TotalAgi { get; set; }
        public int TotalVit { get; set; }
        public int TotalInt { get; set; }
        public int TotalDex { get; set; }
        public int TotalLuk { get; set; }
        public int Atk { get; set; }
        public int MinMatk { get; set; }
        public int MaxMatk { get; set; }
        public double Aspd { get; set; }
        public int Hit { get; set; }
        public int Flee { get; set; }
        public double VariableCastTimeRatio { get; set; }
    }

    public class MobData
    {
        public int Id { get; set; }
        public string AegisName { get; set; } = "";
        public string Name { get; set; } = "";
        public int Level { get; set; }
        public int Hp { get; set; }
        public int BaseExp { get; set; }
        public int JobExp { get; set; }
        public int MvpExp { get; set; }
        public int Attack { get; set; }
        public int Attack2 { get; set; }
        public int Defense { get; set; }
        public int MagicDefense { get; set; }
        public int Str { get; set; }
        public int Agi { get; set; }
        public int Vit { get; set; }
        public int Int { get; set; }
        public int Dex { get; set; }
        public int Luk { get; set; }
        public string Size { get; set; } = "";
        public string Race { get; set; } = "";
        public string Element { get; set; } = "";
        public int ElementLevel { get; set; }
        public List<MobDrop> Drops { get; set; } = new List<MobDrop>();
    }

    public class MobDrop
    {
        public string Item { get; set; } = "";
        public int Rate { get; set; }
    }

    public class ItemData
    {
        public int Id { get; set; }
        public string AegisName { get; set; } = "";
        public string Name { get; set; } = "";
        public int Buy { get; set; }
        public int Sell { get; set; }
        public int Weight { get; set; }
        public string Type { get; set; } = "";
    }

    public class MapSpawn
    {
        public string MapName { get; set; } = "";
        public int MobId { get; set; }
        public int Amount { get; set; }
    }

    public class JobData
    {
        public string Name { get; set; } = "";
        public int HpFactor { get; set; }
        public int HpIncrease { get; set; }
        public int SpFactor { get; set; }
        public int SpIncrease { get; set; }
        public List<JobBonus> Bonuses { get; set; } = new List<JobBonus>();
    }

    public class JobBonus
    {
        public int Level { get; set; }
        public int Str { get; set; }
        public int Agi { get; set; }
        public int Vit { get; set; }
        public int Int { get; set; }
        public int Dex { get; set; }
        public int Luk { get; set; }
    }

    public class SkillData
    {
        public int Id { get; set; }
        public string Name { get; set; } = "";
        public int MaxLevel { get; set; }
    }

    public class AspdData
    {
        public string JobName { get; set; } = "";
        public Dictionary<string, int> BaseAspd { get; set; } = new();
    }

    public class SimulatorData
    {
        public List<MobData> Mobs { get; set; } = new List<MobData>();
        public List<ItemData> Items { get; set; } = new List<ItemData>();
        public List<MapSpawn> Spawns { get; set; } = new List<MapSpawn>();
        public List<JobData> Jobs { get; set; } = new List<JobData>();
        public List<SkillData> Skills { get; set; } = new List<SkillData>();
        public List<AspdData> Aspd { get; set; } = new List<AspdData>();
    }

    public class UserData
    {
        public List<CharacterBuild> SavedBuilds { get; set; } = new List<CharacterBuild>();
    }
}
