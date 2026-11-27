"""Recipes from TheMealDB (https://www.themealdb.com): free with its public test key "1"."""

from dataclasses import dataclass, field

from app.tools.http import get_json

BASE = "https://www.themealdb.com/api/json/v1/1"
DAY = 86400


@dataclass
class Recipe:
    id: str
    name: str
    category: str = ""
    cuisine: str = ""
    ingredients: list[str] = field(default_factory=list)
    instructions: str = ""
    url: str = ""


def _from_meal(meal: dict) -> Recipe:
    ingredients = []
    for i in range(1, 21):
        item = (meal.get(f"strIngredient{i}") or "").strip()
        amount = (meal.get(f"strMeasure{i}") or "").strip()
        if item:
            ingredients.append(f"{amount} {item}".strip())
    meal_id = str(meal.get("idMeal", ""))
    return Recipe(
        id=meal_id,
        name=str(meal.get("strMeal", "")).strip(),
        category=str(meal.get("strCategory") or ""),
        cuisine=str(meal.get("strArea") or ""),
        ingredients=ingredients,
        instructions=" ".join(str(meal.get("strInstructions") or "").split()),
        url=meal.get("strSource") or f"https://www.themealdb.com/meal/{meal_id}",
    )


def find(query: str, limit: int = 4) -> list[Recipe]:
    """Search by dish name first ("pancakes"); if nothing matches, by main ingredient ("potato")."""
    query = " ".join((query or "").split())[:60]
    if not query:
        return []
    meals = get_json(f"{BASE}/search.php", "recipe", {"s": query}, max_age=DAY).get("meals") or []
    recipes = [_from_meal(m) for m in meals[:limit]]
    if recipes:
        return recipes

    terms = [query]  # try "potatoes", then "potato"
    if query.lower().endswith("oes"):
        terms.append(query[:-2])
    elif query.lower().endswith("s"):
        terms.append(query[:-1])
    for term in terms:
        listed = get_json(f"{BASE}/filter.php", "recipe", {"i": term.replace(" ", "_")}, max_age=DAY).get("meals") or []
        if listed:
            first = get_json(f"{BASE}/lookup.php", "recipe", {"i": listed[0]["idMeal"]}, max_age=DAY).get("meals") or []
            recipes = [_from_meal(first[0])] if first else []
            recipes += [Recipe(id=str(m["idMeal"]), name=m["strMeal"]) for m in listed[1:limit]]
            return recipes
    return []


def recipes_for_milo(query: str) -> tuple[str, list[Recipe]]:
    recipes = find(query)
    if not recipes:
        return (
            f"The recipe collection has nothing for '{query}'. You can still suggest a simple recipe you know, "
            "and say it's your own suggestion.",
            [],
        )
    best, others = recipes[0], recipes[1:]
    lines = [
        f"Best match: {best.name}" + (f" ({best.cuisine} {best.category.lower()})" if best.cuisine else ""),
        "Ingredients: " + "; ".join(best.ingredients),
        "Method: " + best.instructions[:2500],
    ]
    if others:
        lines.append("Other ideas from the collection: " + ", ".join(r.name for r in others))
    lines.append(
        "Adapt this to the person: leave out or swap anything they dislike or can't eat, "
        "and give one step at a time if they're cooking now."
    )
    return "\n".join(lines), [best]
