import scrapy

class GameItem(scrapy.Item):
    chinese_name = scrapy.Field()  # 中文名
    english_name = scrapy.Field()  # 英文名
    developer = scrapy.Field()     # 开发商
    publisher = scrapy.Field()     # 发行商
    release_date = scrapy.Field()  # 发售日期
    game_type = scrapy.Field()     # 游戏类型
    platform = scrapy.Field()      # 平台
    language = scrapy.Field()      # 语言
    tags = scrapy.Field()          # 标签
    score = scrapy.Field()         # 评分
    game_url = scrapy.Field()      # 游戏详情页链接
    image_url = scrapy.Field()     # 图片链接
    platform_type = scrapy.Field() # 平台类型：pc, ns, ps5, xboxseriesx