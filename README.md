2025.12.30 第一次更新
使用方法
# 在项目根目录（有scrapy.cfg的目录）运行

# 爬取2025年10月到12月数据，自动探测所有页面
scrapy crawl game_release -a start_year=2025 -a start_month=10 -a end_year=2025 -a end_month=12

# 爬取2025年全年数据，每月份最多探测30页（安全限制）
scrapy crawl game_release -a start_year=2025 -a start_month=1 -a end_year=2025 -a end_month=12 -a max_pages_per_month=30

# 仅爬取2025年12月数据
scrapy crawl game_release -a start_year=2025 -a start_month=12

# 爬取2024年11月到2025年2月数据
scrapy crawl game_release -a start_year=2024 -a start_month=11 -a end_year=2025 -a end_month=2

