# 水豚噜噜 Codex 桌面宠物 🍊

> 版权声明: 噜噜🍊ip 版权属于 [铁罐（北京）文化传媒有限公司](https://www.chinalicensingexpo.com/cn/exhibitor/Tieguan-Beijing-Culture-Media-Co-Ltd--8382); 此动画系列原作者为 [小水豚噜噜（小红书）](https://www.xiaohongshu.com/user/profile/5f915da100000000010042e7?xsec_token=ABCoJcky0aypIplxQvqP1l7IMacIPjp1u1Qm4dPQeFlkM%3D&xsec_source=pc_search)所有; 本仓库非官方, 仅二创发电~

## 动画

<table>
  <tr>
    <td align="center"><code>idle</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/01-idle.gif" alt="idle" width="192"></td>
    <td align="center"><code>running-right</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/02-running-right.gif" alt="running-right" width="192"></td>
    <td align="center"><code>running-left</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/03-running-left.gif" alt="running-left" width="192"></td>
  </tr>
  <tr>
    <td align="center"><code>waving</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/04-waving.gif" alt="waving" width="192"></td>
    <td align="center"><code>failed</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/05-failed.gif" alt="failed" width="192"></td>
    <td align="center"><code>waiting</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/06-waiting.gif" alt="waiting" width="192"></td>
  </tr>
  <tr>
    <td align="center"><code>running</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/07-running.gif" alt="running" width="192"></td>
    <td align="center"><code>review</code><br><img src="pet-runs/capybara-lulu/qa/action-gifs/08-review.gif" alt="review" width="192"></td>
    <td></td>
  </tr>
</table>
## 安装 (Codex)

```bash
uv sync --frozen
uv run --frozen python tools/build_vpet_v1.py --install
```

## DeepSeek Harness 插件

除了 Codex 宠物外, 还有一个 DeepSeek Harness 客户端插件版本. 

```powershell
# 生成图集
uv run python tools/build_dsh_pet_assets.py
# 构建客户端 bundle
node dsh-plugin/capylulu-pet/scripts/build-client.mjs
# 安装进 web profile
powershell -ExecutionPolicy Bypass -File dsh-plugin/install.ps1
# 重启 dsh web 生效；卸载用 dsh-plugin/uninstall.ps1
```
