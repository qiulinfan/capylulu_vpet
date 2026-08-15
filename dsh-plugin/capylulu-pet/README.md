# capylulu-pet — 水豚噜噜 DeepSeek Harness 插件

把 Codex CLI 里的水豚噜噜桌面宠物迁移成 DeepSeek Harness Web GUI 的客户端插件：
一只漂浮在界面右下角、会随会话状态切换动画的水豚。

## 状态 → 动画映射

| 宠物状态 | 触发条件 | 动画 |
| --- | --- | --- |
| `idle` 睡觉中 | 没有选中会话 | 六帧香香睡觉循环 |
| `waiting` 等你吩咐 | 选中会话但 agent 未在运行 | 抱独角兽贴贴循环 |
| `running` 干活中 | 当前会话 `running` | 画水墨小虾的专注工作循环（Codex 归一化版本） |
| `wave` 打招呼 | 点击宠物 / 一轮任务刚刚完成 | 四帧挥手致意 |
| `failed` 出错了 | 当前会话出现 failed 的后台任务 | 打滚睡觉的安抚循环 |

动画素材从已安装的 Codex 适配器图集
（`pet-runs/capybara-lulu/final/spritesheet.webp`）按行裁剪，
运行时以 base64 data URL 直接内联在 `lib/client.js` 里（本地回环加载，无网络请求）。

## 目录结构

- `assets/` — 生成的紧凑图集 `atlas.webp` + `manifest.json`（由 `tools/build_dsh_pet_assets.py` 生成）
- `src/client.js` — 插件源码模板（含 `__ATLAS_DATA_URL__` / `__MANIFEST_JSON__` 占位符）
- `scripts/build-client.mjs` — 零依赖构建脚本，把图集内联进 `lib/client.js`
- `lib/client.js` — 构建产物（`window.__ModuleLoader__.load` 客户端 bundle）

## 构建

```powershell
# 1. 重新生成图集（改了动画素材才需要）
uv run python tools/build_dsh_pet_assets.py

# 2. 构建客户端 bundle
node dsh-plugin/capylulu-pet/scripts/build-client.mjs
```

## 安装（把宠物装进你的 web profile）

```powershell
powershell -ExecutionPolicy Bypass -File dsh-plugin/install.ps1
```

脚本做的事：

1. 把 `capylulu-pet` 包复制到 `~/.dsh/profiles/web/node_modules/`
2. 在 `~/.dsh/profiles/web/cordis.patch.yml` 里幂等追加一条 `dsh.client` 名录条目
   （`- insert:` 里的 `id: capylulu-pet` / `name: capylulu-pet`）

然后**重启 `dsh web`**（或下次启动时）生效：

- 服务端：client-modules 激活扫描把该条目并入 `window.__DSH_BOOT__` 启动图，
  并在 `/plugins/capylulu-pet/client.js` 提供 bundle。
- 浏览器：外壳内核加载启动图 → 物化插件 → `apply(ctx)` 把宠物注册进
  `shell.overlay` 槽位（ui-layout 声明的 root 级 list 槽），随 AppFrame 渲染。

## 卸载

```powershell
powershell -ExecutionPolicy Bypass -File dsh-plugin/uninstall.ps1
```

删除 `cordis.patch.yml` 里的 `capylulu-pet` insert 条目，并移除
`~/.dsh/profiles/web/node_modules/capylulu-pet`。

## 插件契约（DSH 客户端插件要点）

- `package.json` 声明 `dsh.client.platform: "web"` 与 `exports["./client"]`；
  node 侧 `dsh-client-modules` 扫描启用中的 loader 条目，把每个声明了
  `dsh.client` 的包并入浏览器启动图，并服务 `/plugins/<id>/client.js`。
- bundle 是 classic script：调用 `window.__ModuleLoader__.load({id, factory})`，
  factory 的 `require` 从模块表解析（`react` 由 app-shell 静态注册表提供）。
- 插件导出 `{ apply(ctx), inject }`；`inject: ["slots"]` 是 cordis 服务注入，
  `ctx.slots.register` 把组件注册进已声明的槽位（这里是 `shell.overlay`，
  root 作用域 list 槽，全组件都能拿到 `useSessions` 全局标准钩子）。

## 版权

噜噜🍊 IP 版权属于 铁罐（北京）文化传媒有限公司；原作者 小水豚噜噜（小红书）。
本插件为二创非官方项目。
