#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from utils.recipes import Ingredient, Recipe, RecipeBook


DEFAULT_DB_PATH = Path('recipes.json')


def parse_ingredients(raw: str) -> list[Ingredient]:
	data = json.loads(raw)
	if not isinstance(data, list):
		raise ValueError('ingredients must be a JSON list')
	return [Ingredient.from_dict(item) for item in data]


def parse_steps(raw: str) -> list[str]:
	data = json.loads(raw)
	if not isinstance(data, list):
		raise ValueError('steps must be a JSON list')
	return [str(item) for item in data]


def load_book(path: Path) -> RecipeBook:
	book = RecipeBook(path)
	book.load()
	return book


def cmd_list(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	for name in book.list_recipes():
		print(name)


def cmd_show(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	recipe = book.get_recipe(args.name)
	if not recipe:
		raise SystemExit(f'Recipe "{args.name}" not found')
	print(json.dumps(recipe.to_dict(), ensure_ascii=False, indent=2))


def cmd_add(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	recipe = Recipe(name=args.name, ingredients=parse_ingredients(args.ingredients), steps=parse_steps(args.steps))
	book.add_recipe(recipe)
	book.save()
	print(f'Added recipe: {args.name}')


def cmd_update(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	ingredients = parse_ingredients(args.ingredients) if args.ingredients else None
	steps = parse_steps(args.steps) if args.steps else None

	existing = book.get_recipe(args.name)
	if not existing:
		raise SystemExit(f'Recipe "{args.name}" not found')

	updated = Recipe(
		name=args.name,
		ingredients=ingredients if ingredients is not None else existing.ingredients,
		steps=steps if steps is not None else existing.steps,
	)
	book.update_recipe(updated)
	book.save()
	print(f'Updated recipe: {args.name}')


def cmd_delete(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	book.remove_recipe(args.name)
	book.save()
	print(f'Deleted recipe: {args.name}')


def cmd_shopping_list(args: argparse.Namespace) -> None:
	book = load_book(args.db)
	recipe_names = args.recipes.split(',') if args.recipes else None
	if recipe_names:
		missing = [name for name in recipe_names if name not in book.recipes]
		if missing:
			raise SystemExit(f'Recipes not found: {", ".join(missing)}')
	items = book.shopping_list(recipe_names)
	output = [item.to_dict() for item in items]
	print(json.dumps(output, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description='Recipe manager')
	parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH, help='Path to recipes.json')
	subparsers = parser.add_subparsers(dest='command', required=True)

	list_parser = subparsers.add_parser('list', help='List recipes')
	list_parser.set_defaults(func=cmd_list)

	show_parser = subparsers.add_parser('show', help='Show recipe details')
	show_parser.add_argument('name', help='Recipe name')
	show_parser.set_defaults(func=cmd_show)

	add_parser = subparsers.add_parser('add', help='Add a recipe')
	add_parser.add_argument('name', help='Recipe name')
	add_parser.add_argument('--ingredients', required=True, help='JSON list of ingredients')
	add_parser.add_argument('--steps', required=True, help='JSON list of steps')
	add_parser.set_defaults(func=cmd_add)

	update_parser = subparsers.add_parser('update', help='Update a recipe')
	update_parser.add_argument('name', help='Recipe name')
	update_parser.add_argument('--ingredients', help='JSON list of ingredients')
	update_parser.add_argument('--steps', help='JSON list of steps')
	update_parser.set_defaults(func=cmd_update)

	delete_parser = subparsers.add_parser('delete', help='Delete a recipe')
	delete_parser.add_argument('name', help='Recipe name')
	delete_parser.set_defaults(func=cmd_delete)

	shopping_parser = subparsers.add_parser('shopping-list', help='List ingredients to buy')
	shopping_parser.add_argument('--recipes', help='Comma-separated recipe names (default: all)')
	shopping_parser.set_defaults(func=cmd_shopping_list)

	return parser


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	args.func(args)


if __name__ == '__main__':
	main()
