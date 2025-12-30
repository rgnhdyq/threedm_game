BOT_NAME = 'threedm_game'

SPIDER_MODULES = ['threedm_game.spiders']
NEWSPIDER_MODULE = 'threedm_game.spiders'

# 遵守robots.txt规则
ROBOTSTXT_OBEY = False

# 配置请求头，模拟浏览器
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 并发设置
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1  # 下载延迟，避免被封

# 启用中间件
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
}

# 启用管道
ITEM_PIPELINES = {
    'threedm_game.pipelines.ThreedmGamePipeline': 300,
}

# 日志级别
LOG_LEVEL = 'INFO'

# 编码设置
FEED_EXPORT_ENCODING = 'utf-8'