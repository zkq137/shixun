"""
Database connection module for MySQL (talent_pipeline_platform).
"""

import pymysql
from pymysql.cursors import DictCursor

DB_CONFIG = {
    "host": "39.107.99.7",
    "port": 3306,
    "user": "devuser",
    "password": "0721",
    "database": "talent_pipeline_platform",
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def query_all(sql, params=None):
    """查询多条记录"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=None):
    """查询单条记录"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchone()
    finally:
        conn.close()


def execute(sql, params=None):
    """执行 INSERT / UPDATE / DELETE"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params or ())
        conn.commit()
        return affected
    finally:
        conn.close()
