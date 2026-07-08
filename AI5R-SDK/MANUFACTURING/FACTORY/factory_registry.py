from dataclasses import dataclass, field

from MANUFACTURING.LINES import ProductionLine
from MANUFACTURING.RECIPES import ManufacturingRecipe


@dataclass
class FactoryRegistry:
    recipes_by_product_type: dict[str, ManufacturingRecipe] = field(default_factory=dict)
    lines_by_id: dict[str, ProductionLine] = field(default_factory=dict)

    def register_recipe(
        self,
        recipe: ManufacturingRecipe,
        line: ProductionLine,
    ) -> None:
        if not recipe.validate():
            raise ValueError("manufacturing recipe is invalid")
        if not line.validate():
            raise ValueError("production line is invalid")
        if recipe.product_type != line.product_type:
            raise ValueError("recipe and production line product type mismatch")
        if recipe.production_line_id != line.line_id:
            raise ValueError("recipe and production line mismatch")

        self.recipes_by_product_type[recipe.product_type] = recipe
        self.lines_by_id[line.line_id] = line

    def get_recipe(self, product_type: str) -> ManufacturingRecipe:
        recipe = self.recipes_by_product_type.get(product_type)
        if recipe is None:
            raise ValueError(f"recipe not found for product type: {product_type}")
        return recipe

    def get_line(self, line_id: str) -> ProductionLine:
        line = self.lines_by_id.get(line_id)
        if line is None:
            raise ValueError(f"production line not found: {line_id}")
        return line

    def recipe_count(self) -> int:
        return len(self.recipes_by_product_type)

    def line_count(self) -> int:
        return len(self.lines_by_id)
