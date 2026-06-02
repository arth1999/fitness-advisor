"""Merge Sanotsu food JSON files into fitness-advisor's food-database.json."""
import json
import os
import glob

SOURCE_DIR = r"D:\04_claude_code\01_Fitness\fitness-advisor\temp_sanotsu\json_data_vision_251206_Qwen2-5-VL-72B-Instruct"
GI_FILE = r"D:\04_claude_code\01_Fitness\fitness-advisor\temp_sanotsu\json_gi_of_foods\glycemic_index_of_foods.json"
OUTPUT = r"D:\04_claude_code\01_Fitness\fitness-advisor\assets\food-database.json"

# Fields that should be kept as strings (not converted to float)
STRING_FIELDS = {"foodCode", "foodName", "remark"}

# Field mapping: Sanotsu field -> our field
FIELD_MAP = {
    "foodCode": "food_code",
    "foodName": "name_zh",
    "edible": "edible_pct",
    "water": "water_g",
    "energyKCal": "energy_kcal",
    "energyKJ": "energy_kj",
    "protein": "protein_g",
    "fat": "fat_g",
    "CHO": "carbs_g",
    "dietaryFiber": "fiber_g",
    "cholesterol": "cholesterol_mg",
    "ash": "ash_g",
    "vitaminA": "vitamin_a_ug",
    "carotene": "carotene_ug",
    "retinol": "retinol_ug",
    "thiamin": "thiamin_mg",
    "riboflavin": "riboflavin_mg",
    "niacin": "niacin_mg",
    "vitaminC": "vitamin_c_mg",
    "vitaminETotal": "vitamin_e_total_mg",
    "vitaminE1": "vitamin_e_alpha_mg",
    "vitaminE2": "vitamin_e_beta_gamma_mg",
    "vitaminE3": "vitamin_e_delta_mg",
    "Ca": "calcium_mg",
    "P": "phosphorus_mg",
    "K": "potassium_mg",
    "Na": "sodium_mg",
    "Mg": "magnesium_mg",
    "Fe": "iron_mg",
    "Zn": "zinc_mg",
    "Se": "selenium_ug",
    "Cu": "copper_mg",
    "Mn": "manganese_mg",
    "remark": "remark",
}

# Category mapping based on filename prefix
CATEGORY_MAP = {
    "谷类": "谷类及其制品",
    "薯类": "薯类淀粉及其制品",
    "干豆类": "干豆类及其制品",
    "蔬菜类": "蔬菜类及其制品",
    "水果类": "水果类及其制品",
    "畜肉类": "畜肉类及其制品",
    "禽肉类": "禽肉类及其制品",
    "鱼虾蟹贝类": "水产类",
    "蛋类": "蛋类及其制品",
    "乳类": "乳类及其制品",
    "植物油": "油脂类",
    "动物油脂类": "油脂类",
    "坚果种子类": "坚果种子类",
    "菌藻类": "菌藻类",
    "其他类": "其他",
}

def load_gi_data():
    """Load GI index data."""
    gi_map = {}
    if not os.path.exists(GI_FILE):
        print("  GI file not found, skipping GI data")
        return gi_map
    with open(GI_FILE, "r", encoding="utf-8") as f:
        gi_list = json.load(f)
    for group in gi_list:
        for item in group.get("list", []):
            name = item.get("foodName", "")
            gi_map[name] = item.get("GI", None)
    print(f"  Loaded {len(gi_map)} GI entries")
    return gi_map

def get_category(filename):
    """Determine category from filename."""
    for key, cat in CATEGORY_MAP.items():
        if key in filename:
            return cat
    return "其他"

def transform_food(item, category, gi_map):
    """Transform one food item to our schema."""
    food = {"category": category}
    for src_field, dst_field in FIELD_MAP.items():
        val = item.get(src_field, "")
        if val == "" or val == "Tr" or val == "..." or val == "-" or val is None:
            food[dst_field] = None
        elif src_field in STRING_FIELDS:
            food[dst_field] = str(val)
        else:
            try:
                food[dst_field] = float(val)
            except (ValueError, TypeError):
                # Text like "微量" -> keep as string remark, null for numeric fields
                if dst_field == "remark":
                    food[dst_field] = str(val)
                else:
                    food[dst_field] = None
    # Add GI if available
    food["gi"] = gi_map.get(item.get("foodName", ""), None)
    return food

def main():
    gi_map = load_gi_data()

    json_files = sorted(glob.glob(os.path.join(SOURCE_DIR, "*.json")))
    print(f"Found {len(json_files)} food JSON files")

    all_foods = []
    categories_seen = set()
    total_count = 0

    for fpath in json_files:
        fname = os.path.basename(fpath)
        category = get_category(fname)
        categories_seen.add(category)

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data:
            food = transform_food(item, category, gi_map)
            all_foods.append(food)
            count += 1

        print(f"  {fname}: {count} foods -> {category}")
        total_count += count

    print(f"\nTotal: {total_count} foods across {len(categories_seen)} categories")
    print(f"Categories: {sorted(categories_seen)}")

    # Build output
    output = {
        "_description": "中国常见食材营养数据库 - 来自《中国食物成分表》（第6版 标准版）",
        "_source": "《中国食物成分表》标准版第6版，经 Sanotsu/china-food-composition-data Qwen2.5-VL-72B OCR提取",
        "_note": "每100g可食部数据。edible_pct=可食部比例。'Tr'=微量记为null。含GI（血糖生成指数）数据。",
        "_fields": {
            "food_code": "食物编码（中国食物成分表原始编码）",
            "name_zh": "中文名称",
            "category": "食物分类",
            "edible_pct": "可食部（%）",
            "water_g": "水分（克）",
            "energy_kcal": "热量（千卡）",
            "energy_kj": "热量（千焦）",
            "protein_g": "蛋白质（克）",
            "fat_g": "脂肪（克）",
            "carbs_g": "碳水化合物（克）",
            "fiber_g": "膳食纤维（克）",
            "cholesterol_mg": "胆固醇（毫克）",
            "ash_g": "灰分（克）",
            "vitamin_a_ug": "维生素A（微克RE）",
            "carotene_ug": "胡萝卜素（微克）",
            "retinol_ug": "视黄醇（微克）",
            "thiamin_mg": "硫胺素维生素B1（毫克）",
            "riboflavin_mg": "核黄素维生素B2（毫克）",
            "niacin_mg": "烟酸（毫克）",
            "vitamin_c_mg": "维生素C（毫克）",
            "vitamin_e_total_mg": "维生素E总量（毫克）",
            "vitamin_e_alpha_mg": "α-维生素E（毫克）",
            "vitamin_e_beta_gamma_mg": "β+γ-维生素E（毫克）",
            "vitamin_e_delta_mg": "δ-维生素E（毫克）",
            "calcium_mg": "钙（毫克）",
            "phosphorus_mg": "磷（毫克）",
            "potassium_mg": "钾（毫克）",
            "sodium_mg": "钠（毫克）",
            "magnesium_mg": "镁（毫克）",
            "iron_mg": "铁（毫克）",
            "zinc_mg": "锌（毫克）",
            "selenium_ug": "硒（微克）",
            "copper_mg": "铜（毫克）",
            "manganese_mg": "锰（毫克）",
            "gi": "血糖生成指数（GI值）",
            "remark": "备注"
        },
        "foods": all_foods
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nWritten: {OUTPUT}")
    print(f"File size: {os.path.getsize(OUTPUT) / 1024:.0f} KB")
    return output

if __name__ == "__main__":
    main()
