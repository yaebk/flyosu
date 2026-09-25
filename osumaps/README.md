# Beatmaps

The `.osz` archives are not in the repository, because they contain the songs.
Download these nine beatmap sets from osu! and put the `.osz` files in this
folder, keeping the default file names, which start with the set ID. The code
relies on that prefix: the set ID is what marks a song as tuning or held-out.
Only the 4K mania difficulties are played; other key counts are skipped.

| set ID | artist – title | role |
|---|---|---|
| [2298007](https://osu.ppy.sh/beatmapsets/2298007) | AAAA – Lobelia (Short Ver.) | tuning |
| [2543258](https://osu.ppy.sh/beatmapsets/2543258) | ONGEKI SHOOTERS – No Limit RED Force (Game Ver.) | tuning |
| [2600298](https://osu.ppy.sh/beatmapsets/2600298) | Metal Scar Radio – Mirairo Rider (Japanese Ver.) (Game Ver.) | tuning |
| [171880](https://osu.ppy.sh/beatmapsets/171880) | xi – Happy End of the World | held-out |
| [251365](https://osu.ppy.sh/beatmapsets/251365) | Halozy – Kanshou no Matenrou | held-out |
| [254581](https://osu.ppy.sh/beatmapsets/254581) | Nightmare – Boulafacet | held-out |
| [309328](https://osu.ppy.sh/beatmapsets/309328) | xi – Hesperides | held-out |
| [315435](https://osu.ppy.sh/beatmapsets/315435) | UNDEAD CORPORATION – The Empress scream off ver | held-out |
| [347453](https://osu.ppy.sh/beatmapsets/347453) | Igorrr & Ruby My Dear – Figue Folle | held-out |

The tuning songs are listed in `TUNING_SONGS` in `experiments/e20_beatmaps.py`;
any other set placed here is held out by default. Star ratings for the 47 4K
difficulties are in `results/star_ratings.json`.
