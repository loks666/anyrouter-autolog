from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'order_app.db'
STATIC_DIR = BASE_DIR / 'static'
INDEX_FILE = STATIC_DIR / 'index.html'

app = FastAPI(title='点餐系统')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


class DishCreate(BaseModel):
	name: str = Field(..., min_length=1)
	description: str | None = None
	price: float = Field(..., gt=0)
	image_url: str | None = None
	available: bool = True


class DishUpdate(BaseModel):
	name: str | None = Field(default=None, min_length=1)
	description: str | None = None
	price: float | None = Field(default=None, gt=0)
	image_url: str | None = None
	available: bool | None = None


class OrderItem(BaseModel):
	dish_id: int
	quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
	customer_name: str = Field(..., min_length=1)
	items: list[OrderItem] = Field(..., min_length=1)


def get_connection() -> sqlite3.Connection:
	connection = sqlite3.connect(DB_PATH)
	connection.row_factory = sqlite3.Row
	return connection


def init_db() -> None:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute(
			'''
			CREATE TABLE IF NOT EXISTS dishes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				description TEXT,
				price REAL NOT NULL,
				image_url TEXT,
				available INTEGER NOT NULL DEFAULT 1,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			'''
		)
		cursor.execute(
			'''
			CREATE TABLE IF NOT EXISTS orders (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				customer_name TEXT NOT NULL,
				items TEXT NOT NULL,
				total REAL NOT NULL,
				created_at TEXT NOT NULL
			)
			'''
		)
		cursor.execute(
			'''
			CREATE TABLE IF NOT EXISTS logs (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				action TEXT NOT NULL,
				detail TEXT NOT NULL,
				created_at TEXT NOT NULL
			)
			'''
		)
		connection.commit()


def seed_dishes() -> None:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute('SELECT COUNT(*) FROM dishes')
		count = cursor.fetchone()[0]
		if count:
			return
		default_dishes = [
			{
				'name': '番茄牛腩饭',
				'description': '慢炖牛腩配酸甜番茄酱汁。',
				'price': 28.0,
				'image_url': '/static/images/beef.svg',
			},
			{
				'name': '香煎鸡排饭',
				'description': '外脆里嫩鸡排搭配时蔬。',
				'price': 24.0,
				'image_url': '/static/images/chicken.svg',
			},
			{
				'name': '时蔬意面',
				'description': '清爽蔬菜与香蒜橄榄油。',
				'price': 22.0,
				'image_url': '/static/images/pasta.svg',
			},
		]
		now = datetime.utcnow().isoformat()
		for dish in default_dishes:
			cursor.execute(
				'''
				INSERT INTO dishes (name, description, price, image_url, available, created_at, updated_at)
				VALUES (?, ?, ?, ?, 1, ?, ?)
				''',
				(dish['name'], dish['description'], dish['price'], dish['image_url'], now, now),
			)
		connection.commit()


def log_action(action: str, detail: str) -> None:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute(
			'INSERT INTO logs (action, detail, created_at) VALUES (?, ?, ?)',
			(action, detail, datetime.utcnow().isoformat()),
		)
		connection.commit()


def dish_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
	return {
		'id': row['id'],
		'name': row['name'],
		'description': row['description'],
		'price': row['price'],
		'image_url': row['image_url'],
		'available': bool(row['available']),
		'created_at': row['created_at'],
		'updated_at': row['updated_at'],
	}


@app.on_event('startup')
def on_startup() -> None:
	init_db()
	seed_dishes()


@app.get('/')
def index() -> FileResponse:
	return FileResponse(INDEX_FILE)


@app.get('/api/dishes')
def list_dishes() -> list[dict[str, Any]]:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute('SELECT * FROM dishes ORDER BY id')
		rows = cursor.fetchall()
	return [dish_row_to_dict(row) for row in rows]


@app.post('/api/dishes', status_code=201)
def create_dish(payload: DishCreate) -> dict[str, Any]:
	now = datetime.utcnow().isoformat()
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute(
			'''
			INSERT INTO dishes (name, description, price, image_url, available, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			''',
			(
				payload.name,
				payload.description,
				payload.price,
				payload.image_url,
				1 if payload.available else 0,
				now,
				now,
			),
		)
		connection.commit()
		dish_id = cursor.lastrowid
	log_action('dish.create', f'新增菜品 #{dish_id}: {payload.name}')
	return get_dish(dish_id)


@app.put('/api/dishes/{dish_id}')
def update_dish(dish_id: int, payload: DishUpdate) -> dict[str, Any]:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,))
		row = cursor.fetchone()
		if row is None:
			raise HTTPException(status_code=404, detail='菜品不存在')
		data = dish_row_to_dict(row)
		updated = {
			'name': payload.name if payload.name is not None else data['name'],
			'description': (
				payload.description if payload.description is not None else data['description']
			),
			'price': payload.price if payload.price is not None else data['price'],
			'image_url': payload.image_url if payload.image_url is not None else data['image_url'],
			'available': (
				payload.available if payload.available is not None else data['available']
			),
		}
		now = datetime.utcnow().isoformat()
		cursor.execute(
			'''
			UPDATE dishes
			SET name = ?, description = ?, price = ?, image_url = ?, available = ?, updated_at = ?
			WHERE id = ?
			''',
			(
				updated['name'],
				updated['description'],
				updated['price'],
				updated['image_url'],
				1 if updated['available'] else 0,
				now,
				dish_id,
			),
		)
		connection.commit()
	log_action('dish.update', f'更新菜品 #{dish_id}: {updated["name"]}')
	return get_dish(dish_id)


@app.delete('/api/dishes/{dish_id}', status_code=204)
def delete_dish(dish_id: int) -> None:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute('SELECT name FROM dishes WHERE id = ?', (dish_id,))
		row = cursor.fetchone()
		if row is None:
			raise HTTPException(status_code=404, detail='菜品不存在')
		cursor.execute('DELETE FROM dishes WHERE id = ?', (dish_id,))
		connection.commit()
	log_action('dish.delete', f'删除菜品 #{dish_id}: {row["name"]}')


@app.post('/api/orders', status_code=201)
def create_order(payload: OrderCreate) -> dict[str, Any]:
	with get_connection() as connection:
		cursor = connection.cursor()
		dish_ids = [item.dish_id for item in payload.items]
		cursor.execute(
			f'SELECT * FROM dishes WHERE id IN ({",".join("?" for _ in dish_ids)})',
			tuple(dish_ids),
		)
		rows = cursor.fetchall()
		if len(rows) != len(dish_ids):
			raise HTTPException(status_code=400, detail='订单包含无效菜品')
		dishes = {row['id']: row for row in rows}
		order_items = []
		total = 0.0
		for item in payload.items:
			row = dishes[item.dish_id]
			if not row['available']:
				raise HTTPException(status_code=400, detail=f'菜品 {row["name"]} 已下架')
			line_total = row['price'] * item.quantity
			order_items.append(
				{
					'dish_id': row['id'],
					'name': row['name'],
					'price': row['price'],
					'quantity': item.quantity,
					'line_total': line_total,
				}
			)
			total += line_total
		now = datetime.utcnow().isoformat()
		cursor.execute(
			'INSERT INTO orders (customer_name, items, total, created_at) VALUES (?, ?, ?, ?)',
			(payload.customer_name, json.dumps(order_items, ensure_ascii=False), total, now),
		)
		connection.commit()
		order_id = cursor.lastrowid
	log_action('order.create', f'创建订单 #{order_id}，客户：{payload.customer_name}，总计：{total:.2f}')
	return {
		'id': order_id,
		'customer_name': payload.customer_name,
		'items': order_items,
		'total': total,
		'created_at': now,
	}


@app.get('/api/logs')
def list_logs(limit: int = 20) -> list[dict[str, Any]]:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute(
			'SELECT * FROM logs ORDER BY id DESC LIMIT ?',
			(limit,),
		)
		rows = cursor.fetchall()
	return [
		{
			'id': row['id'],
			'action': row['action'],
			'detail': row['detail'],
			'created_at': row['created_at'],
		}
		for row in rows
	]


def get_dish(dish_id: int) -> dict[str, Any]:
	with get_connection() as connection:
		cursor = connection.cursor()
		cursor.execute('SELECT * FROM dishes WHERE id = ?', (dish_id,))
		row = cursor.fetchone()
		if row is None:
			raise HTTPException(status_code=404, detail='菜品不存在')
	return dish_row_to_dict(row)
