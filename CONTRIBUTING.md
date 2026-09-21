# 贡献指南（Contributing）

感谢你考虑为 **NriGlobe** 做贡献！本指南覆盖开发环境、内容接入、代码约定与提交流程。

## 开发环境

- **Python 3.10+**：构建脚本仅使用标准库，无需 `pip install`。
- 前端**零在线依赖**：`lib/three.min.js` 已内置，`index.html` 无 `fetch`，可直接以 `file://` 打开。
- 无需 Node / 打包工具。

## 本地运行

```bash
# 1. 用示例数据预览（无需任何私有数据）
cp data/dataset.example.js data/dataset.js
python server.py 8731
# 打开 http://127.0.0.1:8731/index.html
```

或基于示例源重新编译：

```bash
python scripts/build.py --news content/news --social content/social \
  --out data/dataset.example.js --public
```

## 贡献代码

1. Fork 本仓库到你的**个人 GitHub 账号**，从 `master` 切出特性分支：`git checkout -b feat/your-topic`
2. 保持改动聚焦，一个 PR 解决一件事。
3. 提交信息用中文或英文清晰描述**为什么**改。
4. 向 `iSeacat/NriGlobe` 的 `master` 开 PR。
5. 确保 `python scripts/build.py --public` 能成功产出（校验失败会拒绝写文件并逐条报错）。

## 贡献内容（示例源）

仓库中的 `content/news/`、`content/social/` 是**中性示例**，用于演示构建管线。
如果你有更丰富的演示数据想补充，欢迎 PR——但请注意下方的「保密红线」。

## ⚠️ 保密红线（务必遵守）

本仓库**只含可公开内容**，请勿提交任何真实业务数据：

- ❌ 不要把真实产品线 / 品类名写进任何文件。
- ❌ 不要提交 `config.local.json`、`content/markets.local.json`、`data/dataset.js`（真实情报）。
- ❌ 不要在 `scripts/` 提交含真实情报的日报生成脚本（命名形如 `gen_social_daily_*.py` 已被 `.gitignore` 挡住）。
- ✅ 真实配置走 `config.local.json`（gitignore），真实产品线走 `markets.local.json`（gitignore）。
- ✅ 要生成可公开产物，构建务必加 `--public`，只读中性示例。

若你的 PR 被自动泄露扫描（`scripts/export_public.py`）拦下，说明触碰了红线，请先清理再提交。

## 代码风格

- Python：4 空格缩进，脚本保持无第三方依赖。
- 前端：`index.html` 内联脚本，改动尽量局部、可解释。
- 注释用中文，说明「为什么」而非「是什么」。

## 行为准则

理性、友善、对事不对人。我们保留拒绝不符合项目方向的贡献的权利。

## 联系方式

- 安全相关：见 [SECURITY.md](SECURITY.md)
- 一般问题：开 Issue 或邮件 **opensource@iseacat.cn**
