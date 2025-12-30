import scrapy


class GameItem(scrapy.Item):
    # 游戏基本信息
    chinese_name = scrapy.Field()  # 中文名
    english_name = scrapy.Field()  # 英文名
    image_url = scrapy.Field()  # 图片链接
    game_url = scrapy.Field()  # 游戏详情页链接

    # 开发发行信息
    developer = scrapy.Field()  # 开发商
    publisher = scrapy.Field()  # 发行商
    release_date = scrapy.Field()  # 发售日期
    game_type = scrapy.Field()  # 游戏类型
    platform = scrapy.Field()  # 平台
    language = scrapy.Field()  # 语言
    tags = scrapy.Field()  # 标签

    # 评分信息
    score = scrapy.Field()  # 评分
    rating_count = scrapy.Field()  # 评分人数

    # 其他信息
    has_special_page = scrapy.Field()  # 是否有专题页
    crawl_year = scrapy.Field()  # 爬取年份
    crawl_month = scrapy.Field()  # 爬取月份
    page_number = scrapy.Field()  # 页码