# 番茄男频数据追踪

这是一个自动追踪番茄小说男频公开榜单的 GitHub Pages 看板。

在线查看：<https://ethan-tangtang.github.io/fanqie-male-tracker/>

## 看板包含什么

- **新书榜**：男频新书榜中的作品与在读数据。
- **高阅读量作品**：男频阅读榜中的热门作品。
- **高分作品**：从公开作品详情页成功读取评分的作品，按评分及在读量排序。
- **数据快照**：每次抓取会保存在 `data/snapshots/`，当前看板读取 `data/latest.json`。

> 仅采集公开页面。未公开评分的作品不会被标记为高分。

## 如何查看结果

直接打开在线页面：

<https://ethan-tangtang.github.io/fanqie-male-tracker/>

也可以在仓库根目录本地预览：

```powershell
python -m http.server 8000
```

然后在浏览器打开 <http://localhost:8000>。

## 本地运行

需要 Python 3.12+。

```powershell
pip install -r requirements.txt
playwright install chromium

# 抓取公开榜单数据
python scrape_fanqie_male.py

# 根据最新数据生成首页
python build_site.py
```

常用的快速测试命令：

```powershell
python scrape_fanqie_male.py --limit 1 --category-limit 1 --sleep 0
python build_site.py
```

## 在 GitHub 上更新数据

1. 打开仓库的 [Actions](https://github.com/Ethan-Tangtang/fanqie-male-tracker/actions) 页面。
2. 选择 **Daily Fanqie Male Tracker**。
3. 点击 **Run workflow**，再确认运行。
4. 等待工作流完成。它会抓取数据、更新 `data/` 和 `index.html`，并自动发布到 GitHub Pages。
5. 回到在线看板刷新页面即可看到最新结果。

工作流按北京时间每天 08:00 自动运行一次；也可随时手动运行。

## 首次部署或重新发布页面

若只需要将当前已有数据发布到 Pages：

1. 在 Actions 中选择 **Deploy Current Dashboard**。
2. 点击 **Run workflow**。
3. 等待成功后访问在线页面。

GitHub Pages 已配置为 **GitHub Actions** 来源，无需额外服务器或密钥。

## 常见问题

- **高分区为空**：番茄公开详情页没有提供可读取评分时，系统会留空，避免产生虚假评分。
- **抓取失败或数据较少**：页面结构或反爬策略可能发生变化；保留上一次成功的 `data/latest.json`，随后检查抓取脚本的选择器。
- **首次全量运行较慢**：脚本会按分类和详情页逐步访问，并在请求间等待，以降低对公开页面的压力。
