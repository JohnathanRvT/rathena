using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Text.Json;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using rAthena.Simulator.Core.Models;

namespace rAthena.DataExtractor
{
    class Program
    {
        static void Main(string[] args)
        {
            var rAthenaPath = "../../";
            var outputFolder = "../rAthena.Simulator/wwwroot/data";
            Directory.CreateDirectory(outputFolder);

            var deserializer = new DeserializerBuilder()
                .WithNamingConvention(PascalCaseNamingConvention.Instance)
                .IgnoreUnmatchedProperties()
                .Build();

            Console.WriteLine("Parsing Items...");
            var items = ParseItems(rAthenaPath, deserializer);

            Console.WriteLine("Parsing Mobs...");
            var mobs = ParseMobs(rAthenaPath, deserializer);

            Console.WriteLine("Parsing Spawns...");
            var spawns = ParseSpawns(rAthenaPath);

            Console.WriteLine("Parsing Jobs...");
            var jobs = ParseJobs(rAthenaPath, deserializer);

            Console.WriteLine("Parsing Skills...");
            var skills = ParseSkills(rAthenaPath, deserializer);

            Console.WriteLine("Parsing ASPD...");
            var aspd = ParseAspd(rAthenaPath, deserializer);

            var simulatorData = new SimulatorData
            {
                Items = items,
                Mobs = mobs,
                Spawns = spawns,
                Jobs = jobs,
                Skills = skills,
                Aspd = aspd
            };

            var options = new JsonSerializerOptions { WriteIndented = false };
            string jsonString = JsonSerializer.Serialize(simulatorData, options);
            File.WriteAllText(Path.Combine(outputFolder, "data.json"), jsonString);

            Console.WriteLine($"Extracted {items.Count} items, {mobs.Count} mobs, {spawns.Count} spawns, {jobs.Count} jobs, {skills.Count} skills, and {aspd.Count} aspd configs.");
        }

        static List<ItemData> ParseItems(string root, IDeserializer deserializer)
        {
            var items = new List<ItemData>();
            string[] files = { "db/pre-re/item_db_equip.yml", "db/pre-re/item_db_etc.yml", "db/pre-re/item_db_usable.yml" };
            foreach (var file in files)
            {
                var fullPath = Path.Combine(root, file);
                if (!File.Exists(fullPath)) continue;

                var yamlContent = File.ReadAllText(fullPath);
                var doc = deserializer.Deserialize<Dictionary<string, object>>(yamlContent);
                if (doc != null && doc.ContainsKey("Body") && doc["Body"] is List<object> body)
                {
                    foreach (var itemObj in body)
                    {
                        var dict = itemObj as Dictionary<object, object>;
                        if (dict == null) continue;

                        var item = new ItemData
                        {
                            Id = GetInt(dict, "Id"),
                            AegisName = GetString(dict, "AegisName"),
                            Name = GetString(dict, "Name"),
                            Buy = GetInt(dict, "Buy"),
                            Sell = GetInt(dict, "Sell"),
                            Weight = GetInt(dict, "Weight"),
                            Type = GetString(dict, "Type")
                        };
                        items.Add(item);
                    }
                }
            }
            return items;
        }

        static List<MobData> ParseMobs(string root, IDeserializer deserializer)
        {
            var mobs = new List<MobData>();
            var fullPath = Path.Combine(root, "db/pre-re/mob_db.yml");
            if (File.Exists(fullPath))
            {
                var yamlContent = File.ReadAllText(fullPath);
                var doc = deserializer.Deserialize<Dictionary<string, object>>(yamlContent);
                if (doc != null && doc.ContainsKey("Body") && doc["Body"] is List<object> body)
                {
                    foreach (var mobObj in body)
                    {
                        var dict = mobObj as Dictionary<object, object>;
                        if (dict == null) continue;

                        var mob = new MobData
                        {
                            Id = GetInt(dict, "Id"),
                            AegisName = GetString(dict, "AegisName"),
                            Name = GetString(dict, "Name"),
                            Level = GetInt(dict, "Level"),
                            Hp = GetInt(dict, "Hp"),
                            BaseExp = GetInt(dict, "BaseExp"),
                            JobExp = GetInt(dict, "JobExp"),
                            Attack = GetInt(dict, "Attack"),
                            Attack2 = GetInt(dict, "Attack2"),
                            Defense = GetInt(dict, "Defense"),
                            MagicDefense = GetInt(dict, "MagicDefense"),
                            MvpExp = GetInt(dict, "MvpExp"),
                            Str = GetInt(dict, "Str"),
                            Agi = GetInt(dict, "Agi"),
                            Vit = GetInt(dict, "Vit"),
                            Int = GetInt(dict, "Int"),
                            Dex = GetInt(dict, "Dex"),
                            Luk = GetInt(dict, "Luk"),
                            Size = GetString(dict, "Size"),
                            Race = GetString(dict, "Race"),
                            Element = GetString(dict, "Element"),
                            ElementLevel = GetInt(dict, "ElementLevel")
                        };

                        if (dict.ContainsKey("Drops") && dict["Drops"] is List<object> drops)
                        {
                            foreach (var dropObj in drops)
                            {
                                var dropDict = dropObj as Dictionary<object, object>;
                                if (dropDict != null)
                                {
                                    mob.Drops.Add(new MobDrop
                                    {
                                        Item = GetString(dropDict, "Item"),
                                        Rate = GetInt(dropDict, "Rate")
                                    });
                                }
                            }
                        }

                        mobs.Add(mob);
                    }
                }
            }
            return mobs;
        }

        static List<JobData> ParseJobs(string root, IDeserializer deserializer)
        {
            var jobs = new List<JobData>();
            var fullPath = Path.Combine(root, "db/pre-re/job_stats.yml");
            if (File.Exists(fullPath))
            {
                var yamlContent = File.ReadAllText(fullPath);
                var doc = deserializer.Deserialize<Dictionary<string, object>>(yamlContent);
                if (doc != null && doc.ContainsKey("Body") && doc["Body"] is List<object> body)
                {
                    foreach (var jobGroupObj in body)
                    {
                        var groupDict = jobGroupObj as Dictionary<object, object>;
                        if (groupDict == null) continue;

                        var hpFactor = GetInt(groupDict, "HpFactor");
                        var hpIncrease = GetInt(groupDict, "HpIncrease");
                        var spFactor = GetInt(groupDict, "SpFactor");
                        var spIncrease = GetInt(groupDict, "SpIncrease");

                        var bonuses = new List<JobBonus>();
                        if (groupDict.ContainsKey("BonusStats") && groupDict["BonusStats"] is List<object> bonusList)
                        {
                            foreach (var bObj in bonusList)
                            {
                                var bDict = bObj as Dictionary<object, object>;
                                if (bDict != null)
                                {
                                    bonuses.Add(new JobBonus
                                    {
                                        Level = GetInt(bDict, "Level"),
                                        Str = GetInt(bDict, "Str"),
                                        Agi = GetInt(bDict, "Agi"),
                                        Vit = GetInt(bDict, "Vit"),
                                        Int = GetInt(bDict, "Int"),
                                        Dex = GetInt(bDict, "Dex"),
                                        Luk = GetInt(bDict, "Luk")
                                    });
                                }
                            }
                        }

                        if (groupDict.ContainsKey("Jobs") && groupDict["Jobs"] is Dictionary<object, object> jobsDict)
                        {
                            foreach (var jobNameObj in jobsDict.Keys)
                            {
                                jobs.Add(new JobData
                                {
                                    Name = jobNameObj.ToString() ?? "",
                                    HpFactor = hpFactor,
                                    HpIncrease = hpIncrease,
                                    SpFactor = spFactor,
                                    SpIncrease = spIncrease,
                                    Bonuses = bonuses
                                });
                            }
                        }
                    }
                }
            }
            return jobs;
        }

        static int GetInt(Dictionary<object, object> dict, string key)
        {
            if (dict.ContainsKey(key))
            {
                var val = dict[key]?.ToString();
                if (int.TryParse(val, out int result)) return result;
            }
            return 0;
        }

        static string GetString(Dictionary<object, object> dict, string key)
        {
            if (dict.ContainsKey(key))
            {
                return dict[key]?.ToString() ?? "";
            }
            return "";
        }

        static List<SkillData> ParseSkills(string root, IDeserializer deserializer)
        {
            var skills = new List<SkillData>();
            var fullPath = Path.Combine(root, "db/pre-re/skill_db.yml");
            if (File.Exists(fullPath))
            {
                var yamlContent = File.ReadAllText(fullPath);
                var doc = deserializer.Deserialize<Dictionary<string, object>>(yamlContent);
                if (doc != null && doc.ContainsKey("Body") && doc["Body"] is List<object> body)
                {
                    foreach (var skillObj in body)
                    {
                        var dict = skillObj as Dictionary<object, object>;
                        if (dict == null) continue;

                        var skill = new SkillData
                        {
                            Id = GetInt(dict, "Id"),
                            Name = GetString(dict, "Name"),
                            MaxLevel = GetInt(dict, "MaxLevel")
                        };
                        skills.Add(skill);
                    }
                }
            }
            return skills;
        }

        static List<AspdData> ParseAspd(string root, IDeserializer deserializer)
        {
            var aspd = new List<AspdData>();
            var fullPath = Path.Combine(root, "db/pre-re/job_aspd.yml");
            if (File.Exists(fullPath))
            {
                var yamlContent = File.ReadAllText(fullPath);
                var doc = deserializer.Deserialize<Dictionary<string, object>>(yamlContent);
                if (doc != null && doc.ContainsKey("Body") && doc["Body"] is List<object> body)
                {
                    foreach (var groupObj in body)
                    {
                        var groupDict = groupObj as Dictionary<object, object>;
                        if (groupDict == null) continue;

                        var baseAspd = new Dictionary<string, int>();
                        if (groupDict.ContainsKey("BaseASPD") && groupDict["BaseASPD"] is Dictionary<object, object> aspdDict)
                        {
                            foreach (var weapon in aspdDict)
                            {
                                if (int.TryParse(weapon.Value?.ToString(), out int val))
                                {
                                    baseAspd[weapon.Key.ToString() ?? ""] = val;
                                }
                            }
                        }

                        if (groupDict.ContainsKey("Jobs") && groupDict["Jobs"] is Dictionary<object, object> jobsDict)
                        {
                            foreach (var job in jobsDict.Keys)
                            {
                                aspd.Add(new AspdData { JobName = job.ToString() ?? "", BaseAspd = baseAspd });
                            }
                        }
                    }
                }
            }
            return aspd;
        }

        static List<MapSpawn> ParseSpawns(string root)
        {
            var spawns = new List<MapSpawn>();
            var mobsPath = Path.Combine(root, "npc/pre-re/mobs");
            if (!Directory.Exists(mobsPath)) return spawns;

            var spawnFiles = Directory.GetFiles(mobsPath, "*.txt", SearchOption.AllDirectories);

            var regex = new Regex(@"^([^,]+),.*?\tmonster\t.*?\t(\d+),(\d+)", RegexOptions.Compiled);

            foreach (var file in spawnFiles)
            {
                foreach (var line in File.ReadLines(file))
                {
                    var match = regex.Match(line.Trim());
                    if (match.Success)
                    {
                        spawns.Add(new MapSpawn
                        {
                            MapName = match.Groups[1].Value,
                            MobId = int.Parse(match.Groups[2].Value),
                            Amount = int.Parse(match.Groups[3].Value)
                        });
                    }
                }
            }
            return spawns;
        }
    }
}
