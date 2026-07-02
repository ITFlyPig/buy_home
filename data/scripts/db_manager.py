"""数据库管理模块 - SQLite数据库操作层

提供统一的数据库CRUD接口，供所有数据采集和处理脚本复用。

数据库表结构：
- schools: 学校信息（小学、初中、九年一贯制）
- communities: 小区信息
- school_community_mapping: 学区映射关系（学校-小区-生源类型）
- community_prices: 小区价格（支持历史记录）
- community_transactions: 小区成交记录
- crawl_tasks: 采集任务状态追踪
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data" / "hangzhou_home.db"

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_name TEXT NOT NULL,
    campus_name TEXT,
    school_code TEXT UNIQUE,
    campus_code TEXT UNIQUE,
    district TEXT NOT NULL,
    district_code TEXT,
    school_type TEXT NOT NULL,
    school_nature TEXT,
    address TEXT,
    lng REAL,
    lat REAL,
    school_tel TEXT,
    student_count INTEGER DEFAULT 0,
    class_count INTEGER DEFAULT 0,
    teacher_count INTEGER DEFAULT 0,
    school_scope TEXT,
    direct_middle_school TEXT,
    school_detail TEXT,
    year TEXT DEFAULT '2026',
    visit_times INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_schools_district ON schools(district);
CREATE INDEX IF NOT EXISTS idx_schools_type ON schools(school_type);
CREATE INDEX IF NOT EXISTS idx_schools_name ON schools(school_name);

CREATE TABLE IF NOT EXISTS communities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    district TEXT,
    districts_json TEXT,
    schools_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_communities_name ON communities(name);
CREATE INDEX IF NOT EXISTS idx_communities_district ON communities(district);

CREATE TABLE IF NOT EXISTS school_community_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_name TEXT NOT NULL,
    campus_code TEXT NOT NULL,
    community_name TEXT NOT NULL,
    street_name TEXT,
    district TEXT NOT NULL,
    student_type TEXT NOT NULL,
    year TEXT DEFAULT '2026',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campus_code, community_name, student_type)
);

CREATE INDEX IF NOT EXISTS idx_mapping_school ON school_community_mapping(school_name);
CREATE INDEX IF NOT EXISTS idx_mapping_community ON school_community_mapping(community_name);
CREATE INDEX IF NOT EXISTS idx_mapping_district ON school_community_mapping(district);

CREATE TABLE IF NOT EXISTS community_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    community_name TEXT NOT NULL,
    avg_price INTEGER,
    min_total INTEGER,
    max_total INTEGER,
    layout TEXT,
    year INTEGER,
    data_source TEXT,
    crawl_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prices_community ON community_prices(community_name);
CREATE INDEX IF NOT EXISTS idx_prices_date ON community_prices(crawl_date);

CREATE TABLE IF NOT EXISTS community_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    community_name TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    area REAL,
    price DECIMAL(12,2),
    total_price DECIMAL(12,2),
    building TEXT,
    floor TEXT,
    orientation TEXT,
    crawl_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trans_community ON community_transactions(community_name);
CREATE INDEX IF NOT EXISTS idx_trans_date ON community_transactions(trade_date);

CREATE TABLE IF NOT EXISTS crawl_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL UNIQUE,
    task_type TEXT NOT NULL,
    district TEXT,
    status TEXT DEFAULT 'pending',
    last_updated TIMESTAMP,
    record_count INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    error_message TEXT,
    next_scheduled_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DBManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_db(self):
        cursor = self.conn.cursor()
        cursor.executescript(CREATE_TABLES_SQL)
        self.conn.commit()
        print(f"[DB] 数据库初始化完成: {self.db_path}")

    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor

    def query(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def query_one(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchone()

    def upsert_school(self, school_data):
        sql = """
        INSERT OR REPLACE INTO schools (
            school_name, campus_name, school_code, campus_code,
            district, district_code, school_type, school_nature,
            address, lng, lat, school_tel, student_count, class_count,
            teacher_count, school_scope, direct_middle_school, school_detail,
            year, visit_times, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            school_data.get("school_name", ""),
            school_data.get("campus_name", ""),
            school_data.get("school_code", ""),
            school_data.get("campus_code", ""),
            school_data.get("district", ""),
            school_data.get("district_code", ""),
            school_data.get("school_type", ""),
            school_data.get("school_nature", ""),
            school_data.get("address", ""),
            school_data.get("lng"),
            school_data.get("lat"),
            school_data.get("school_tel", ""),
            school_data.get("student_count", 0),
            school_data.get("class_count", 0),
            school_data.get("teacher_count", 0),
            school_data.get("school_scope", ""),
            school_data.get("direct_middle_school", ""),
            school_data.get("school_detail", ""),
            school_data.get("year", "2026"),
            school_data.get("visit_times", 0),
            datetime.now().isoformat(),
        )
        self.execute(sql, params)

    def upsert_community(self, community_data):
        sql = """
        INSERT OR REPLACE INTO communities (
            name, district, districts_json, schools_json, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        """
        params = (
            community_data.get("name", ""),
            community_data.get("districts", [])[0] if community_data.get("districts") else "",
            json.dumps(community_data.get("districts", []), ensure_ascii=False),
            json.dumps(community_data.get("schools", []), ensure_ascii=False),
            datetime.now().isoformat(),
        )
        self.execute(sql, params)

    def upsert_school_community_mapping(self, mapping_data):
        sql = """
        INSERT OR REPLACE INTO school_community_mapping (
            school_name, campus_code, community_name, street_name,
            district, student_type, year
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            mapping_data.get("school_name", ""),
            mapping_data.get("campus_code", ""),
            mapping_data.get("community_name", ""),
            mapping_data.get("street_name", ""),
            mapping_data.get("district", ""),
            mapping_data.get("student_type", ""),
            mapping_data.get("year", "2026"),
        )
        self.execute(sql, params)

    def upsert_community_price(self, price_data):
        crawl_date = price_data.get("crawl_date", datetime.now().strftime("%Y-%m-%d"))
        sql = """
        INSERT OR REPLACE INTO community_prices (
            community_name, avg_price, min_total, max_total,
            layout, year, data_source, crawl_date, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            price_data.get("name", price_data.get("community_name", "")),
            price_data.get("avg_price"),
            price_data.get("min_total"),
            price_data.get("max_total"),
            price_data.get("layout", ""),
            price_data.get("year"),
            price_data.get("data_source", ""),
            crawl_date,
            datetime.now().isoformat(),
        )
        self.execute(sql, params)

    def insert_community_transaction(self, transaction_data):
        sql = """
        INSERT INTO community_transactions (
            community_name, trade_date, area, price, total_price,
            building, floor, orientation, crawl_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        crawl_date = transaction_data.get("crawl_date", datetime.now().strftime("%Y-%m-%d"))
        params = (
            transaction_data.get("community_name", ""),
            transaction_data.get("trade_date", ""),
            transaction_data.get("area"),
            transaction_data.get("price"),
            transaction_data.get("total_price"),
            transaction_data.get("building", ""),
            transaction_data.get("floor", ""),
            transaction_data.get("orientation", ""),
            crawl_date,
        )
        self.execute(sql, params)

    def update_crawl_task(self, task_name, **kwargs):
        fields = []
        params = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            params.append(value)
        params.append(task_name)
        sql = f"UPDATE crawl_tasks SET {', '.join(fields)} WHERE task_name = ?"
        self.execute(sql, params)

    def upsert_crawl_task(self, task_name, task_type, **kwargs):
        existing = self.query_one("SELECT id FROM crawl_tasks WHERE task_name = ?", (task_name,))
        if existing:
            self.update_crawl_task(task_name, **kwargs)
        else:
            sql = """
            INSERT INTO crawl_tasks (
                task_name, task_type, district, status, last_updated,
                record_count, total_records, error_message, next_scheduled_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                task_name,
                task_type,
                kwargs.get("district", ""),
                kwargs.get("status", "pending"),
                kwargs.get("last_updated"),
                kwargs.get("record_count", 0),
                kwargs.get("total_records", 0),
                kwargs.get("error_message"),
                kwargs.get("next_scheduled_time"),
            )
            self.execute(sql, params)

    def get_crawl_task(self, task_name):
        return self.query_one("SELECT * FROM crawl_tasks WHERE task_name = ?", (task_name,))

    def get_school_by_campus_code(self, campus_code):
        return self.query_one("SELECT * FROM schools WHERE campus_code = ?", (campus_code,))

    def get_community_by_name(self, name):
        return self.query_one("SELECT * FROM communities WHERE name = ?", (name,))

    def get_latest_price(self, community_name):
        return self.query_one("""
            SELECT * FROM community_prices 
            WHERE community_name = ? 
            ORDER BY crawl_date DESC 
            LIMIT 1
        """, (community_name,))

    def get_all_schools(self):
        return self.query("SELECT * FROM schools ORDER BY district, school_name")

    def get_all_communities(self):
        return self.query("SELECT * FROM communities ORDER BY name")

    def get_all_prices_latest(self):
        return self.query("""
            SELECT p.* FROM community_prices p
            JOIN (
                SELECT community_name, MAX(crawl_date) as max_date
                FROM community_prices
                GROUP BY community_name
            ) latest ON p.community_name = latest.community_name AND p.crawl_date = latest.max_date
            ORDER BY p.community_name
        """)

    def get_school_community_mappings(self):
        return self.query("SELECT * FROM school_community_mapping ORDER BY school_name")

    def get_communities_by_school(self, school_name):
        return self.query("""
            SELECT cm.* FROM communities cm
            JOIN school_community_mapping scm ON cm.name = scm.community_name
            WHERE scm.school_name = ?
            GROUP BY cm.name
        """, (school_name,))

    def get_schools_by_community(self, community_name):
        return self.query("""
            SELECT s.* FROM schools s
            JOIN school_community_mapping scm ON s.campus_code = scm.campus_code
            WHERE scm.community_name = ?
            GROUP BY s.school_name
        """, (community_name,))

    def get_communities_by_district(self, district):
        return self.query("SELECT * FROM communities WHERE district = ? ORDER BY name", (district,))

    def delete_mappings_by_district(self, district):
        self.execute("DELETE FROM school_community_mapping WHERE district = ?", (district,))

    def delete_schools_by_district(self, district):
        self.execute("DELETE FROM schools WHERE district = ?", (district,))

    def get_stats(self):
        stats = {}
        stats["schools"] = self.query_one("SELECT COUNT(*) as cnt FROM schools")[0]
        stats["communities"] = self.query_one("SELECT COUNT(*) as cnt FROM communities")[0]
        stats["mappings"] = self.query_one("SELECT COUNT(*) as cnt FROM school_community_mapping")[0]
        stats["prices"] = self.query_one("SELECT COUNT(*) as cnt FROM community_prices")[0]
        stats["transactions"] = self.query_one("SELECT COUNT(*) as cnt FROM community_transactions")[0]
        return stats

    def get_table_count(self, table_name):
        try:
            result = self.query_one(f"SELECT COUNT(*) as cnt FROM {table_name}")
            return result[0] if result else 0
        except Exception:
            return 0


def get_db():
    return DBManager()


if __name__ == "__main__":
    db = get_db()
    db.init_db()
    print(f"[DB] 数据库统计: {db.get_stats()}")
    db.close()