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

    def __init__(self, start_year='2025', start_month='12', end_year=None, end_month=None, max_pages_per_month=50,
                 *args, **kwargs):
        """
        初始化爬虫参数

        Args:
            start_year: 起始年份
            start_month: 起始月份
            end_year: 结束年份（默认为起始年份）
            end_month: 结束月份（默认为起始月份）
            max_pages_per_month: 每个月份最大爬取页数（安全限制）
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

        # 数据统计
        self.month_count = 0
        self.total_pages_crawled = 0
        self.total_games_crawled = 0
        self.successful_months = []

        self.logger.info(f"初始化爬虫: {self.start_year}年{self.start_month}月 至 {self.end_year}年{self.end_month}月")
        self.logger.info(f"每个月份最大爬取页数限制: {self.max_pages_per_month}")

    def start_requests(self):
        """生成所有目标月份页面的初始请求"""

        # 验证日期范围合理性
        if self.start_year > self.end_year or (self.start_year == self.end_year and self.start_month > self.end_month):
            self.logger.error(
                f"日期范围无效: 起始日期({self.start_year}-{self.start_month:02d}) 晚于 结束日期({self.end_year}-{self.end_month:02d})")
            return

        self.logger.info(
            f"开始生成月份请求: {self.start_year}年{self.start_month:02d}月 到 {self.end_year}年{self.end_month:02d}月")

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
                base_url = f"https://www.3dmgame.com/release/pc{year}{month_str}/"

                self.logger.info(f"准备爬取 {year}年{month}月 数据: {base_url}")
                self.month_count += 1

                # 创建请求，并传递月份信息到meta中
                yield scrapy.Request(
                    url=base_url,
                    callback=self.parse,
                    meta={
                        'current_year': year,
                        'current_month': month,
                        'current_month_str': month_str,
                        'page': 1,  # 第一页
                        'base_url_pattern': f"pc{year}{month_str}",  # 用于构建分页URL
                        'retry_times': 0,  # 重试次数
                        'max_page_for_month': self.max_pages_per_month,  # 该月份最大页数限制
                    },
                    errback=self.handle_month_error,
                    dont_filter=False  # 启用请求去重
                )

    def parse(self, response):
        """解析页面，提取数据并处理分页"""

        # 从meta中获取当前爬取的信息
        current_year = response.meta.get('current_year', 2025)
        current_month = response.meta.get('current_month', 12)
        current_page = response.meta.get('page', 1)
        base_pattern = response.meta.get('base_url_pattern', 'pc202512')
        max_page_for_month = response.meta.get('max_page_for_month', self.max_pages_per_month)

        self.logger.info(f"正在解析 {current_year}年{current_month}月 第{current_page}页，URL: {response.url}")
        self.total_pages_crawled += 1

        # 记录成功的月份
        month_key = f"{current_year}-{current_month:02d}"
        if month_key not in self.successful_months:
            self.successful_months.append(month_key)

        # ====================== 提取游戏数据 ======================
        game_items = response.css('div.Sale_list > div.lis')

        if not game_items:
            self.logger.warning(f"在 {response.url} 未找到游戏数据，可能页面结构有变或该月无数据")
            # 如果第一页就没有数据，可能是该月份没有游戏或页面结构变化
            if current_page == 1:
                self.logger.warning(f"{current_year}年{current_month}月 可能没有游戏数据或页面结构已更新")

        games_on_page = 0
        for item in game_items:
            game = GameItem()

            # 提取图片URL
            img_url = item.css('div.img img::attr(data-original)').get()
            if img_url:
                game['image_url'] = img_url
            else:
                # 尝试其他可能的属性
                img_url = item.css('div.img img::attr(src)').get()
                if img_url:
                    game['image_url'] = img_url

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

            # 提取评分信息
            score = item.css('div.score_a span::text').get()
            rating_count_text = item.css('div.score_a p::text').get()

            if score:
                try:
                    game['score'] = float(score)
                except ValueError:
                    game['score'] = score

            if rating_count_text:
                # 提取评分人数数字
                count_match = re.search(r'(\d+)', rating_count_text)
                if count_match:
                    game['rating_count'] = int(count_match.group(1))
                else:
                    game['rating_count'] = 0
            else:
                game['rating_count'] = 0

            # 判断是否有专题页
            has_special = item.css('a.ztbtn').get()
            game['has_special_page'] = bool(has_special)

            # 记录爬取的年份和月份信息
            game['crawl_year'] = current_year
            game['crawl_month'] = current_month
            game['page_number'] = current_page

            games_on_page += 1
            yield game

        self.total_games_crawled += games_on_page
        self.logger.info(f"第{current_page}页提取了 {games_on_page} 个游戏，累计 {self.total_games_crawled} 个游戏")

        # ====================== 智能分页逻辑 ======================
        # 检查是否达到最大页数限制
        if current_page >= max_page_for_month:
            self.logger.info(f"达到预设的最大页数限制({max_page_for_month})，停止翻页")
            return

        # 策略：优先查找页面上的分页按钮，其次根据URL规律尝试，并通过错误判断终止
        next_page_found_by_element = False

        # 1. 首选方案：解析页面上的分页导航元素
        # 首先检查常见的分页选择器
        next_page_selectors = [
            'a:contains("下一页")::attr(href)',  # 中文"下一页"
            'a:contains("next")::attr(href)',  # 英文"next"
            'a:contains(">")::attr(href)',  # 右箭头
            '.page-next a::attr(href)',  # 常见下一页类名
            '.pagination a:last-child::attr(href)',  # 分页栏最后一个链接
            'a[rel="next"]::attr(href)',  # rel="next"属性
        ]

        for selector in next_page_selectors:
            try:
                next_page_url = response.css(selector).get()
                if next_page_url:
                    next_page_url = urljoin(response.url, next_page_url)
                    # 检查URL是否符合当前月份模式，避免跳到其他月份
                    if base_pattern in next_page_url:
                        self.logger.info(f"通过选择器 '{selector}' 找到下一页: {next_page_url}")
                        next_page_found_by_element = True

                        yield scrapy.Request(
                            url=next_page_url,
                            callback=self.parse,
                            meta={
                                'current_year': current_year,
                                'current_month': current_month,
                                'current_month_str': f"{current_month:02d}",
                                'page': current_page + 1,
                                'base_url_pattern': base_pattern,
                                'max_page_for_month': max_page_for_month
                            },
                            errback=self.handle_page_error
                        )
                        break
            except Exception as e:
                self.logger.debug(f"选择器 '{selector}' 执行出错: {e}")
                continue

        # 2. 备用方案：如果页面没有明确分页元素，则基于URL模式智能递增探测
        if not next_page_found_by_element:
            # 尝试基于当前URL规律构造下一页
            next_page_num = current_page + 1

            # 根据网站URL规则构造下一页URL
            if current_page == 1:
                # 第一页到第二页：pc202512/ -> pc202512_2/
                next_page_url = f"https://www.3dmgame.com/release/{base_pattern}_{next_page_num}/"
            else:
                # 后续页：pc202512_2/ -> pc202512_3/
                next_page_url = f"https://www.3dmgame.com/release/{base_pattern}_{next_page_num}/"

            self.logger.info(f"未找到分页按钮，尝试智能探测第{next_page_num}页: {next_page_url}")

            # 发送探测请求
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                meta={
                    'current_year': current_year,
                    'current_month': current_month,
                    'current_month_str': f"{current_month:02d}",
                    'page': next_page_num,
                    'base_url_pattern': base_pattern,
                    'max_page_for_month': max_page_for_month,
                    'is_probe_request': True  # 标记为探测请求
                },
                errback=self.handle_page_error,
                priority=10  # 降低探测请求的优先级
            )

    def handle_month_error(self, failure):
        """处理月份页面请求错误"""
        request_url = failure.request.url
        retry_times = failure.request.meta.get('retry_times', 0)

        # 检查是否为404错误
        if hasattr(failure.value, 'response') and failure.value.response:
            status_code = failure.value.response.status
            if status_code == 404:
                self.logger.warning(f"月份页面不存在 (404): {request_url}")
                return
            elif status_code >= 500:
                self.logger.error(f"服务器错误 ({status_code}): {request_url}")
            else:
                self.logger.error(f"HTTP错误 ({status_code}): {request_url}")
        else:
            # 网络连接错误等
            self.logger.error(f"无法访问月份页面: {request_url}, 错误类型: {type(failure.value).__name__}")

        # 简单的重试逻辑（可选）
        if retry_times < 2:  # 最多重试2次
            self.logger.info(f"准备第{retry_times + 1}次重试: {request_url}")
            new_request = failure.request.copy()
            new_request.meta['retry_times'] = retry_times + 1
            new_request.dont_filter = True
            yield new_request

    def handle_page_error(self, failure):
        """处理分页请求错误（如404），用于智能探测的终止判断"""
        request_url = failure.request.url
        meta = failure.request.meta
        is_probe_request = meta.get('is_probe_request', False)
        current_page = meta.get('page', 1)

        # 检查是否为404错误（页面不存在）
        if hasattr(failure.value, 'response') and failure.value.response:
            status_code = failure.value.response.status
            if status_code == 404:
                if is_probe_request:
                    self.logger.info(
                        f"探测终止：第{current_page}页不存在 (404)，{meta.get('current_year', '')}年{meta.get('current_month', '')}月 共 {current_page - 1} 页")
                else:
                    self.logger.warning(f"分页不存在 (404): {request_url}")
                return
            elif status_code == 403:
                self.logger.error(f"访问被拒绝 (403): {request_url}，可能触发了反爬机制")
                # 可以考虑增加延时或更换User-Agent
            else:
                self.logger.warning(f"分页请求HTTP错误 ({status_code}): {request_url}")
        elif failure.check(scrapy.exceptions.IgnoreRequest):
            # 忽略的请求，静默处理
            pass
        else:
            # 其他错误（如超时、连接错误）
            error_msg = repr(failure.value) if hasattr(failure.value, '__repr__') else str(failure.value)
            self.logger.warning(f"分页请求失败: {request_url}, 错误: {error_msg[:100]}...")

    def closed(self, reason):
        """爬虫结束时调用"""
        self.logger.info("=" * 60)
        self.logger.info(f"爬虫任务完成！")
        self.logger.info(f"总计爬取月份: {self.month_count} 个")
        self.logger.info(f"成功访问月份: {len(self.successful_months)} 个")
        self.logger.info(f"成功爬取页面: {self.total_pages_crawled} 页")
        self.logger.info(f"成功提取游戏: {self.total_games_crawled} 个")

        if self.successful_months:
            self.logger.info(f"成功爬取的月份: {', '.join(sorted(self.successful_months))}")

        self.logger.info(f"关闭原因: {reason}")
        self.logger.info("=" * 60)