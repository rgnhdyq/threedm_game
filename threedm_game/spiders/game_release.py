import scrapy
from threedm_game.items import GameItem
from urllib.parse import urljoin
import re
from datetime import datetime


class GameReleaseSpider(scrapy.Spider):
    name = 'game_release'
    allowed_domains = ['www.3dmgame.com']

    # 自定义设置（可选）
    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,  # 降低请求频率，避免被封
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_TIMES': 2,  # 失败重试次数
    }

    # 平台URL前缀映射
    PLATFORM_PREFIX = {
        'pc': 'pc',
        'ns': 'ns',
        'ps5': 'ps5',
        'xboxseriesx': 'xboxseriesx',
        # 可以添加更多平台
    }

    def __init__(self, start_year='2025', start_month='12', end_year=None, end_month=None,
                 max_pages_per_month=50, platforms='pc', *args, **kwargs):
        """
        初始化爬虫参数

        Args:
            start_year: 起始年份
            start_month: 起始月份
            end_year: 结束年份（默认为起始年份）
            end_month: 结束月份（默认为起始月份）
            max_pages_per_month: 每个月份最大爬取页数（安全限制）
            platforms: 要爬取的平台，用逗号分隔，如 'pc,ns,ps5,xboxseriesx'
        """
        super(GameReleaseSpider, self).__init__(*args, **kwargs)

        # 设置起始年月
        self.start_year = int(start_year)
        self.start_month = int(start_month)

        # 设置结束年月（如果不指定，则仅爬取起始月份）
        self.end_year = int(end_year) if end_year else self.start_year
        self.end_month = int(end_month) if end_month else self.start_month

        # 设置最大页数限制（安全上限）
        self.max_pages_per_month = int(max_pages_per_month)

        # 设置平台列表
        self.platforms = [p.strip().lower() for p in platforms.split(',')]
        # 验证平台是否有效
        self.valid_platforms = []
        for platform in self.platforms:
            if platform in self.PLATFORM_PREFIX:
                self.valid_platforms.append(platform)
            else:
                self.logger.warning(f"不支持的平台: {platform}，支持的平台有: {', '.join(self.PLATFORM_PREFIX.keys())}")

        if not self.valid_platforms:
            self.logger.error("没有有效的平台，爬虫将不会运行")
            return

        # 数据统计
        self.month_count = 0
        self.total_pages_crawled = 0
        self.total_games_crawled = 0
        self.platform_stats = {platform: {'pages': 0, 'games': 0} for platform in self.valid_platforms}

        self.logger.info(f"初始化爬虫: {self.start_year}年{self.start_month}月 至 {self.end_year}年{self.end_month}月")
        self.logger.info(f"每个月份最大爬取页数限制: {max_pages_per_month}")
        self.logger.info(f"爬取平台: {', '.join(self.valid_platforms)}")

    def start_requests(self):
        """生成所有目标月份页面的初始请求"""

        if not self.valid_platforms:
            self.logger.error("没有有效的平台，停止生成请求")
            return

        # 验证日期范围合理性
        if self.start_year > self.end_year or (self.start_year == self.end_year and self.start_month > self.end_month):
            self.logger.error(
                f"日期范围无效: 起始日期({self.start_year}-{self.start_month:02d}) 晚于 结束日期({self.end_year}-{self.end_month:02d})")
            return

        self.logger.info(
            f"开始生成月份请求: {self.start_year}年{self.start_month:02d}月 到 {self.end_year}年{self.end_month:02d}月")

        # 遍历平台
        for platform in self.valid_platforms:
            platform_prefix = self.PLATFORM_PREFIX[platform]

            # 遍历年份范围
            for year in range(self.start_year, self.end_year + 1):
                # 确定当前年份需要爬取的月份范围
                if year == self.start_year:
                    start_m = self.start_month
                else:
                    start_m = 1

                if year == self.end_year:
                    end_m = self.end_month
                else:
                    end_m = 12

                # 遍历月份范围
                for month in range(start_m, end_m + 1):
                    # 格式化月份为两位数
                    month_str = f"{month:02d}"

                    # 构建该月份第一页的URL
                    base_url = f"https://www.3dmgame.com/release/{platform_prefix}{year}{month_str}/"

                    self.logger.info(f"准备爬取 {platform.upper()}平台 {year}年{month}月 数据: {base_url}")
                    self.month_count += 1

                    # 创建请求，并传递平台和月份信息到meta中
                    yield scrapy.Request(
                        url=base_url,
                        callback=self.parse,
                        meta={
                            'platform': platform,  # 平台类型
                            'platform_prefix': platform_prefix,  # URL前缀
                            'year': year,
                            'month': month,
                            'page': 1,  # 第一页
                            'base_url_pattern': f"{platform_prefix}{year}{month_str}",  # 用于构建分页URL
                        },
                        errback=self.handle_month_error,
                        dont_filter=False  # 启用请求去重
                    )

    def parse(self, response):
        """解析页面，提取数据并处理分页"""

        # 从meta中获取当前爬取的信息
        platform = response.meta.get('platform', 'pc')
        platform_prefix = response.meta.get('platform_prefix', 'pc')
        year = response.meta.get('year', 2025)
        month = response.meta.get('month', 12)
        current_page = response.meta.get('page', 1)
        base_pattern = response.meta.get('base_url_pattern', 'pc202512')
        max_page_for_month = self.max_pages_per_month

        self.logger.info(f"正在解析 {platform.upper()}平台 {year}年{month}月 第{current_page}页，URL: {response.url}")
        self.total_pages_crawled += 1
        self.platform_stats[platform]['pages'] += 1

        # ====================== 提取游戏数据 ======================
        game_items = response.css('div.Sale_list > div.lis')

        # 检查是否有游戏数据
        if not game_items:
            self.logger.warning(f"在 {response.url} 未找到游戏数据，可能已到达最后一页或页面结构有变")

            # 特别处理：如果当前页是第一页且没有数据，可能是该月份真的没有游戏
            if current_page == 1:
                self.logger.info(f"{platform.upper()}平台 {year}年{month}月 没有游戏数据")
            else:
                # 如果是第二页及以后没有数据，说明上一页已经是最后一页
                self.logger.info(f"{platform.upper()}平台 {year}年{month}月 共有 {current_page - 1} 页")
            return  # 不再继续翻页

        games_on_page = 0
        for item in game_items:
            game = GameItem()

            # 设置平台类型
            game['platform_type'] = platform

            # 提取游戏名称（中文和英文）
            chinese_name = item.css('div.bt a::text').get()
            english_name = item.css('div.bt span::text').get()
            game['chinese_name'] = chinese_name.strip() if chinese_name else ""
            game['english_name'] = english_name.strip() if english_name else ""

            # 提取游戏详情页链接
            game_url = item.css('div.bt a::attr(href)').get()
            if game_url and game_url != 'javascript:void(0);':
                game['game_url'] = game_url
            else:
                game['game_url'] = ""

            # 提取图片URL
            img_url = item.css('div.img img::attr(data-original)').get()
            if img_url:
                game['image_url'] = img_url
            else:
                # 尝试其他可能的属性
                img_url = item.css('div.img img::attr(src)').get()
                if img_url:
                    game['image_url'] = img_url
                else:
                    game['image_url'] = ""

            # 提取开发发行信息
            info_items = item.css('ul.infolis li')
            for info in info_items:
                text = info.get()
                if '开发：' in text:
                    game['developer'] = info.css('::text').re(r'开发：(.+)')[0] if info.css('::text').re(
                        r'开发：(.+)') else ""
                elif '发行：' in text:
                    game['publisher'] = info.css('::text').re(r'发行：(.+)')[0] if info.css('::text').re(
                        r'发行：(.+)') else ""
                elif '发售：' in text:
                    release_date = info.css('span::text').get()
                    game['release_date'] = release_date.strip() if release_date else ""
                elif '类型：' in text:
                    game['game_type'] = info.css('::text').re(r'类型：(.+)')[0] if info.css('::text').re(
                        r'类型：(.+)') else ""
                elif '平台：' in text:
                    game['platform'] = info.css('::text').re(r'平台：(.+)')[0] if info.css('::text').re(
                        r'平台：(.+)') else ""
                elif '语言：' in text:
                    game['language'] = info.css('::text').re(r'语言：(.+)')[0] if info.css('::text').re(
                        r'语言：(.+)') else ""
                elif '标签：' in text:
                    tags = info.css('a.colr::text').getall()
                    game['tags'] = ','.join([tag.strip() for tag in tags]) if tags else ""

            # 提取评分信息（只保留评分，不保留评分人数）
            score = item.css('div.score_a span::text').get()

            if score:
                try:
                    game['score'] = float(score)
                except ValueError:
                    game['score'] = score
            else:
                game['score'] = ""

            games_on_page += 1
            yield game

        # 检查提取到的游戏数量是否为0（异常情况）
        if games_on_page == 0:
            self.logger.warning(f"解析到游戏条目但提取到0个游戏，可能是页面结构变化或数据异常，停止翻页")
            return

        self.total_games_crawled += games_on_page
        self.platform_stats[platform]['games'] += games_on_page
        self.logger.info(
            f"{platform.upper()}平台 第{current_page}页提取了 {games_on_page} 个游戏，累计 {self.total_games_crawled} 个游戏")

        # ====================== 基于URL规则的分页逻辑 ======================
        # 针对3DM游戏网站的分页规则：
        # 第一页：/pc202503/
        # 第二页：/pc202503_2/
        # 第三页：/pc202503_3/
        # 以此类推...

        # 检查是否达到最大页数限制
        if current_page >= max_page_for_month:
            self.logger.info(f"达到预设的最大页数限制({max_page_for_month})，停止翻页")
            return

        # 构造下一页URL
        next_page_num = current_page + 1

        # 根据页面规则构造URL
        if current_page == 1:
            # 第一页到第二页：pc202503/ -> pc202503_2/
            next_page_url = f"https://www.3dmgame.com/release/{base_pattern}_{next_page_num}/"
        else:
            # 后续页：pc202503_2/ -> pc202503_3/
            next_page_url = f"https://www.3dmgame.com/release/{base_pattern}_{next_page_num}/"

        self.logger.info(f"根据URL规则构造第{next_page_num}页: {next_page_url}")

        # 发送下一页请求
        yield scrapy.Request(
            url=next_page_url,
            callback=self.parse,
            meta={
                'platform': platform,
                'platform_prefix': platform_prefix,
                'year': year,
                'month': month,
                'page': next_page_num,
                'base_url_pattern': base_pattern,
                'is_probe_request': True  # 标记为探测请求
            },
            errback=self.handle_page_error,
            priority=10
        )
        # ====================== 分页逻辑结束 ======================

    def handle_month_error(self, failure):
        """处理月份页面请求错误"""
        request_url = failure.request.url
        platform = failure.request.meta.get('platform', '未知平台')

        # 检查是否为404错误
        if hasattr(failure.value, 'response') and failure.value.response:
            status_code = failure.value.response.status
            if status_code == 404:
                self.logger.warning(f"{platform.upper()}平台月份页面不存在 (404): {request_url}")
                return
            elif status_code >= 500:
                self.logger.error(f"{platform.upper()}平台服务器错误 ({status_code}): {request_url}")
            else:
                self.logger.error(f"{platform.upper()}平台HTTP错误 ({status_code}): {request_url}")
        else:
            # 网络连接错误等
            self.logger.error(
                f"无法访问{platform.upper()}平台月份页面: {request_url}, 错误类型: {type(failure.value).__name__}")

    def handle_page_error(self, failure):
        """处理分页请求错误（如404），用于智能探测的终止判断"""
        request_url = failure.request.url
        platform = failure.request.meta.get('platform', '未知平台')

        # 检查是否为404错误（页面不存在）
        if hasattr(failure.value, 'response') and failure.value.response:
            status_code = failure.value.response.status
            if status_code == 404:
                self.logger.info(f"{platform.upper()}平台爬取完成：已到达最后一页")
                return
            elif status_code == 403:
                self.logger.error(f"{platform.upper()}平台访问被拒绝 (403): {request_url}，可能触发了反爬机制")
            else:
                self.logger.warning(f"{platform.upper()}平台分页请求HTTP错误 ({status_code}): {request_url}")
        elif failure.check(scrapy.exceptions.IgnoreRequest):
            # 忽略的请求，静默处理
            pass
        else:
            # 其他错误（如超时、连接错误）
            error_msg = repr(failure.value) if hasattr(failure.value, '__repr__') else str(failure.value)
            self.logger.warning(f"{platform.upper()}平台分页请求失败: {request_url}, 错误: {error_msg[:100]}...")

    def closed(self, reason):
        """爬虫结束时调用"""
        self.logger.info("=" * 60)
        self.logger.info(f"爬虫任务完成！")
        self.logger.info(f"总计爬取月份: {self.month_count} 个")
        self.logger.info(f"成功爬取页面: {self.total_pages_crawled} 页")
        self.logger.info(f"成功提取游戏: {self.total_games_crawled} 个")

        # 显示各平台统计
        if self.platform_stats:
            self.logger.info("各平台统计:")
            for platform, stats in self.platform_stats.items():
                self.logger.info(f"  {platform.upper()}: {stats['pages']} 页, {stats['games']} 个游戏")

        self.logger.info(f"关闭原因: {reason}")
        self.logger.info("=" * 60)