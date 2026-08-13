# CapyLulu Animation Master

Platform-neutral animation workspace for the complete custom pet `水豚噜噜`.
The animation master is the authority in this repository: actions, frame
counts, timing, and loops are designed for Lulu first, without being limited by
Codex or any other downstream platform.

## 成品 GIF 与出处

`水豚噜噜`角色/IP 原作归属
[铁罐（北京）文化传媒有限公司](https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382)，
原作内容账号为
[平头哥_猛兽狂欢](https://space.bilibili.com/66698693)。以下 GIF 均为本仓库在用户指导下，
使用 OpenAI ImageGen 与 Codex/Pillow 确定性流程制作的非官方像素动画改编；并非原作官方动画。
每项均单独保留角色原作和本 GIF 的动作/派生出处，便于脱离本段单独引用。

<table>
  <tr>
    <td align="center" valign="top" width="33%">
      <strong><code>idle</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/01-idle.gif" alt="CapyLulu idle animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong>逐帧复用本仓库 <code>failed</code> gold 睡眠循环</sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>running-right</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/02-running-right.gif" alt="CapyLulu running right animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong><a href="pet-runs/capybara-lulu/sequence-drafts/v1-action-work/drag-directional/six-gold-rerun-v2/">本项目原创右向拖动母序列</a></sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>running-left</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/03-running-left.gif" alt="CapyLulu running left animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · Codex/Pillow 确定性镜像<br>
      <strong>动作出处：</strong><code>running-right</code> 的逐像素水平镜像</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="33%">
      <strong><code>waving</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/04-waving.gif" alt="CapyLulu waving animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>姿态参考：</strong>小红书 <a href="https://www.xiaohongshu.com/explore/69ff34e10000000036031e82">噜噜</a>；辅助参考 <a href="https://www.xiaohongshu.com/explore/693faf47000000001e030d4c">遇见一只噜</a></sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>failed</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/05-failed.gif" alt="CapyLulu failed animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong>本项目原创趴睡、侧翻与回滚循环</sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>waiting</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/06-waiting.gif" alt="CapyLulu waiting animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong>本项目原创独角兽拥抱等待循环</sub>
    </td>
  </tr>
  <tr>
    <td align="center" valign="top" width="33%">
      <strong><code>working</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/07-working.gif" alt="CapyLulu working animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong>本项目原创水墨小虾绘制与换页循环</sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>running</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/08-running.gif" alt="CapyLulu running animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · Codex/Pillow 确定性复用<br>
      <strong>动作出处：</strong>逐帧复用本仓库 <code>review</code> gold 专注聆听循环</sub>
    </td>
    <td align="center" valign="top" width="33%">
      <strong><code>review</code> · gold</strong><br>
      <img src="pet-runs/capybara-lulu/qa/action-gifs/09-review.gif" alt="CapyLulu review animation" width="192"><br>
      <sub><strong>角色原作：</strong><a href="https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382">铁罐（北京）文化传媒有限公司</a> / <a href="https://space.bilibili.com/66698693">平头哥_猛兽狂欢</a><br>
      <strong>GIF 制作：</strong>本仓库 · OpenAI ImageGen + Codex/Pillow<br>
      <strong>动作出处：</strong>本项目原创耳机专注聆听循环</sub>
    </td>
  </tr>
</table>

更细的逐帧 lineage、哈希与生成工具记录分别见
[`official-frames-v1-manifest.json`](pet-runs/capybara-lulu/official-frames-v1-manifest.json)
与 [`imagegen-jobs.json`](pet-runs/capybara-lulu/imagegen-jobs.json)。

## Animation-master contract

Each action is tuned and accepted as an independent looping GIF before any
platform package or whole-pet atlas is assembled. The active contract is
`pet-runs/capybara-lulu/official-frames-v1-manifest.json`; its current frame
sources are normalized `192x208` transparent PNGs under
`pet-runs/capybara-lulu/official-frames-v1/`.

The `official-frames-v1` path is retained as lineage naming. Neither `v1` nor
the current `192x208` canvas is a Codex contract or a permanent platform limit.
Platform adapters are downstream derivatives: they may select, resample, or
retime approved master actions, but they must not redefine or constrain the
master.

The current nine actions are:

1. `idle` — approved gold sleeping action; exact master alias of `failed`
2. `running-right` — approved gold six-gold full-rerun action
3. `running-left` — approved gold exact mirror of `running-right`
4. `waving` — approved gold twelve-frame hover response
5. `failed` — approved gold action with a reversible prone-to-side sleeping roll
6. `waiting` — approved gold action
7. `working` — approved gold ink-painting action with a completed page change
8. `running` — approved gold action
9. `review` — approved gold action

This nine-action set is the current frozen gold milestone. The sofa-based
`looking-around` candidate remains under
`sequence-drafts/new-state-candidates/looking-around/` and is deliberately
excluded until its motion is refined and approved.

`jumping` was retired because its cheer overlapped `waving`. Its former source
frames are preserved only as draft lineage under
`pet-runs/capybara-lulu/sequence-drafts/v1-retired-variants/jumping-overlaps-waving/`.

## Build and inspect the action GIFs

```bash
uv run --frozen python tools/build_action_gifs.py
```

Build the current Codex V1 adapter without installing it:

```bash
uv run --frozen python tools/build_vpet_v1.py
```

Build and install it into the local Codex custom-pet directory:

```bash
uv run --frozen python tools/build_vpet_v1.py --install
```

The action-only command writes the independent previews, a complete gallery,
and their validation report:

- `pet-runs/capybara-lulu/qa/action-gifs/*.gif`
- `pet-runs/capybara-lulu/qa/action-gifs/gallery.md`
- `pet-runs/capybara-lulu/qa/action-gifs/validation.json`

It intentionally does not rebuild a spritesheet. `idle`, `running-right`,
`running-left`, `waving`, `failed`, `waiting`, `working`, `running`, and
`review` are hash-locked and strictly enforced by the build so an unrelated
edit cannot silently change any of the nine approved gold actions.

## Iteration review rule

Every animation iteration must rebuild and display every active GIF in
manifest `action_order`, even when only one action changed. The generated
`gallery.md` is the canonical full-review index; a review is incomplete if it
shows only the edited action.

## Codex adapter

`pet-runs/capybara-lulu/final/` is the current installable Codex V1 adapter.
It maps the complete animation master into Codex's fixed 8-column by 9-row,
`1536x1872` custom-pet spritesheet contract. The adapter uses the sleeping
`failed` artwork for both `idle` and `failed`, uses `waving` for Codex's required
hover/`jumping` row, and maps the approved `working` action to Codex's task-active
`running` row. The adapter isolates Lulu's orange/yellow-and-green silhouette
from the paper, ink dish, brush, and black ink, then normalizes every working
frame against the equal-weight medians of four approved, unobscured reference
actions: `running-right`, `running-left`, `waving`, and `review`. It combines
silhouette equivalent diameter with bounding-box geometric mean. A second
semantic-contour pass includes detached paws and limbs, then applies the closest
safe common target ratio that keeps Lulu and its dark outline inside Codex's
fixed cell across the complete loop. The resulting per-frame scales are about
`1.12x`–`1.21x`; their variation compensates for source-frame size drift, so the
measured output silhouette stays constant. Lulu, paper, ink dish, and brush are
still enlarged together; every other action remains pixel-identical.
The full measurement record is
`pet-runs/capybara-lulu/qa/working-scale-feature-report.json`. This adapter-only
normalization never changes any approved gold master frame.

The installed local package is `~/.codex/pets/capybara-lulu/`. Its app-facing
identity is `custom:capybara-lulu`.

Experimental and historical assets remain under
`pet-runs/capybara-lulu/sequence-drafts/` and are excluded from the active
action set.
