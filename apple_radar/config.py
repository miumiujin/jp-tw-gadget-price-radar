from pathlib import Path
import yaml


DEFAULT_CONFIG = Path("config/products.yaml")


def load_products(path=DEFAULT_CONFIG):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["products"]
