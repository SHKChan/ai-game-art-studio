# JRPG asset pack (Pixel Forge v0.6)

Rendered offline by `python scripts/make_jrpg_pack.py`. Every file is reproducible from the builder + params listed in
`pack.json`; open the same builder in **Pixel Forge** to tweak colours, speed, outline or glow.

| Folder | Contents |
|---|---|
| `icons/weapons` | 8 kinds × 5 materials (bronze, iron, mithril, gold, dark), 32×32 |
| `icons/armor` | helmet, armor, shield, gauntlet, boots, cloak, ring, amulet × 5 materials |
| `icons/consumables` | HP potion, MP ether, antidote, elixir, phoenix feather, scroll, bomb, onigiri |
| `icons/materials` | ore, ingot, gem, crystal, herb, mushroom, key, coin pouch × 6 colours |
| `icons/skills` | 18 square skill icons (lava burn, meteor, fire pillar, earth spike, whirlpool, gale, ice field, holy judgment, revive, dark vortex, curse, life drain, heal, barrier, haste, slash, thunder, poison) |
| `icons/status` | 20 status badges, 16×16 (ATK/DEF/SPD/MAG up & down, ailments) |
| `effects/<name>/` | `strip.png` (1× sprite strip), `preview.gif` (3×), `meta.json` (frame size, durations, tags, pivot, loop) |
| `preview/` | contact sheets for review |

**Grid effects:** frame width = `cells × 32`. The bottom `cells×32` square is the ground area (it covers the target cells);
the space above is headroom for flames and pillars. `meta.json → pivot` is the centre of the cells, `ground_rect` the
ground square. Tags split one-shot and looping parts — e.g. `lava-burn`: `cast` (0–5) → `burn` (6–11, loop while the
ground burns) → `fade` (12–15).

---

由 `python scripts/make_jrpg_pack.py` 离线生成。网格技能：帧宽 = 格数 × 32，**底部正方形就是地面格子**，上方是火焰 / 光柱的
空间；`meta.json` 里的 `pivot` 是格子中心。熔岩灼地按标签使用：`cast` 施放 → `burn` 循环灼烧 → `fade` 消退。
