import json
import csv
from datetime import datetime
from scrapy.exceptions import DropItem


class ThreedmGamePipeline:
    def open_spider(self, spider):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON文件
        self.json_file = open(f'game_data_{timestamp}.json', 'w', encoding='utf-8')
        self.json_file.write('[\n')
        self.first_item = True

        # CSV文件
        csv_filename = f'game_data_{timestamp}.csv'
        self.csv_file = open(csv_filename, 'w', encoding='utf-8', newline='')
        fieldnames = [
            'chinese_name', 'english_name', 'developer', 'publisher',
            'release_date', 'game_type', 'platform', 'language',
            'tags', 'score', 'rating_count', 'game_url', 'image_url',
            'crawl_year', 'crawl_month', 'page_number', 'has_special_page'
        ]
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()

        spider.logger.info(f"数据将保存到: {csv_filename} 和 game_data_{timestamp}.json")

    def close_spider(self, spider):
        self.json_file.write('\n]')
        self.json_file.close()
        self.csv_file.close()
        spider.logger.info(f"数据保存完成")

    def process_item(self, item, spider):
        # 简单的数据清洗：检查必填字段
        if not item.get('chinese_name') and not item.get('english_name'):
            raise DropItem(f"游戏名称缺失: {item}")

        # 添加处理时间戳
        item['processed_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 保存到JSON
        if not self.first_item:
            self.json_file.write(',\n')
        json.dump(dict(item), self.json_file, ensure_ascii=False, indent=2)
        self.first_item = False

        # 保存到CSV
        csv_item = {}
        for field in self.csv_writer.fieldnames:
            csv_item[field] = item.get(field, '')
        self.csv_writer.writerow(csv_item)

        return item