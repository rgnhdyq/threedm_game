2025.12.30 第一次更新
使用方法
# 在项目根目录（有scrapy.cfg的目录）运行

# 1. 爬取所有平台2025年全年数据
scrapy crawl game_release -a start_year=2025 -a start_month=1 -a end_year=2025 -a end_month=12 -a platforms=pc,ns,ps5,xboxseriesx

# 2. 只爬取PC和Switch平台的2025年10-12月数据
scrapy crawl game_release -a start_year=2025 -a start_month=10 -a end_year=2025 -a end_month=12 -a platforms=pc,ns

# 3. 只爬取PC平台2025年3月数据
scrapy crawl game_release -a start_year=2025 -a start_month=3 -a end_year=2025 -a end_month=3 -a platforms=pc

# 4. 爬取PC和PS5平台2024年1月到2025年3月数据
scrapy crawl game_release -a start_year=2024 -a start_month=1 -a end_year=2025 -a end_month=3 -a platforms=pc,ps5

# 5. 设置更大的页数限制（如果需要）
scrapy crawl game_release -a start_year=2025 -a start_month=1 -a end_year=2025 -a end_month=12 -a platforms=pc,ns,ps5,xboxseriesx -a max_pages_per_month=100

# 核心流程说明
# 1. 初始化阶段
读取命令行参数（年份范围、平台列表、最大页数）

验证参数有效性

初始化统计计数器

# 2. 请求生成阶段
三层循环：平台 → 年份 → 月份

为每个(平台, 年份, 月份)组合生成第一页请求

携带元数据：平台类型、年份、月份、页码、URL模式

# 3. 页面解析阶段
数据提取

使用CSS选择器定位游戏条目

从每个条目提取12个字段

添加平台类型标识

分页控制

空页面检测 → 立即停止

数据量异常检测 → 谨慎停止

最大页数限制 → 强制停止

正常情况 → 构造下一页URL

# 4. 错误处理阶段
404错误：正常结束（到达末尾）

403错误：可能触发反爬，记录警告

其他错误：记录日志，继续爬取

# 5. 数据保存阶段
实时写入JSON和CSV文件

爬虫结束时输出完整统计


