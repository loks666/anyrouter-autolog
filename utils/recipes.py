from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Ingredient:
	name: str
	amount: float | None = None
	unit: str | None = None
	notes: str | None = None
	to_buy: bool = True

	def to_dict(self) -> dict:
		return {
			'name': self.name,
			'amount': self.amount,
			'unit': self.unit,
			'notes': self.notes,
			'to_buy': self.to_buy,
		}

	@staticmethod
	def from_dict(data: dict) -> 'Ingredient':
		return Ingredient(
			name=data['name'],
			amount=data.get('amount'),
			unit=data.get('unit'),
			notes=data.get('notes'),
			to_buy=data.get('to_buy', True),
		)


@dataclass
class Recipe:
	name: str
	ingredients: list[Ingredient] = field(default_factory=list)
	steps: list[str] = field(default_factory=list)

	def to_dict(self) -> dict:
		return {
			'name': self.name,
			'ingredients': [ingredient.to_dict() for ingredient in self.ingredients],
			'steps': self.steps,
		}

	@staticmethod
	def from_dict(data: dict) -> 'Recipe':
		return Recipe(
			name=data['name'],
			ingredients=[Ingredient.from_dict(item) for item in data.get('ingredients', [])],
			steps=list(data.get('steps', [])),
		)


class RecipeBook:
	def __init__(self, path: Path) -> None:
		self.path = path
		self.recipes: dict[str, Recipe] = {}

	def load(self) -> None:
		if not self.path.exists():
			self.recipes = {}
			return

		data = json.loads(self.path.read_text(encoding='utf-8'))
		self.recipes = {
			recipe_data['name']: Recipe.from_dict(recipe_data)
			for recipe_data in data.get('recipes', [])
		}

	def save(self) -> None:
		payload = {'recipes': [recipe.to_dict() for recipe in self.recipes.values()]}
		self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

	def list_recipes(self) -> list[str]:
		return sorted(self.recipes.keys())

	def get_recipe(self, name: str) -> Recipe | None:
		return self.recipes.get(name)

	def add_recipe(self, recipe: Recipe) -> None:
		if recipe.name in self.recipes:
			raise ValueError(f'Recipe "{recipe.name}" already exists')
		self.recipes[recipe.name] = recipe

	def update_recipe(self, recipe: Recipe) -> None:
		self.recipes[recipe.name] = recipe

	def remove_recipe(self, name: str) -> None:
		if name not in self.recipes:
			raise ValueError(f'Recipe "{name}" does not exist')
		del self.recipes[name]

	def shopping_list(self, recipe_names: Iterable[str] | None = None) -> list[Ingredient]:
		selected = self.recipes.values() if recipe_names is None else [self.recipes[name] for name in recipe_names]
		aggregated: dict[tuple[str, str | None], Ingredient] = {}

		for recipe in selected:
			for ingredient in recipe.ingredients:
				if not ingredient.to_buy:
					continue
				key = (ingredient.name, ingredient.unit)
				if ingredient.amount is None or key not in aggregated:
					aggregated[key] = Ingredient(
						name=ingredient.name,
						amount=ingredient.amount,
						unit=ingredient.unit,
						notes=ingredient.notes,
						to_buy=True,
					)
					continue
				aggregated_item = aggregated[key]
				if aggregated_item.amount is not None:
					aggregated_item.amount += ingredient.amount

		return sorted(aggregated.values(), key=lambda item: item.name)
