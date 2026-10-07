import json
import os
from openai import OpenAI

# Initialize client using env vars loaded in app.py
client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL", "https://api.relaymodels.com/v1")
)
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-pro")

class AppraiserAgent:
    """
    👁️ Агент-Оценщик (Инженер компьютерного зрения)
    Определяет текущий стиль, преобладающую цветовую гамму, наличие свободного пространства на полу.
    """
    def analyze_room(self, image_b64: str) -> str:
        prompt = (
            "Ты - опытный дизайнер интерьеров и инженер компьютерного зрения. "
            "Внимательно изучи предоставленное фото комнаты. "
            "Напиши краткое саммари (3-4 предложения): "
            "1. Какой текущий стиль (например, сканди, лофт, неоклассика, минимализм)? "
            "2. Какая преобладающая цветовая гамма (пол, стены, освещение)? "
            "3. Есть ли свободное пространство на полу для мебели? "
            "НЕ подбирай мебель, только опиши то, что видишь."
        )

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_b64}}
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Ошибка анализа комнаты: {e}"

class ArtDirectorAgent:
    """
    🧠 Агент Арт-Директор (Оркестратор и Главный Дизайнер)
    Понимает запрос клиента + учитывает отчет от Агента-Оценщика. Формулирует 'Машинное ТЗ'.
    """
    def formulate_query(self, user_prompt: str, room_summary: str) -> str:
        prompt = f"""
        Ты - Главный Арт-Директор салона мебели Dantone Home.
        У тебя есть отчет об интерьере клиента:
        {room_summary}

        Запрос клиента: "{user_prompt}"

        Твоя задача: сформулировать короткий, емкий поисковый запрос (ТЗ) для агента-кладовщика,
        который будет искать мебель в базе данных.
        Учитывай стиль и цвета комнаты, чтобы мебель подходила идеально.
        Например, если пол деревянный и стиль минимализм, а клиент просит диван, твой запрос должен быть похож на:
        "Современный минималистичный диван подходящий к деревянному полу, нейтральные или контрастные оттенки".

        Верни ТОЛЬКО текст поискового запроса, без лишних слов.
        """

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return user_prompt # Fallback to user prompt

class ClerkAgent:
    """
    🔎 Агент-Кладовщик (Поисковик RAG)
    Ищет по смыслу в каталоге, используя векторный поиск.
    """
    def __init__(self, catalog_path: str):
        self.catalog = []
        if os.path.exists(catalog_path):
            with open(catalog_path, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)

        # Prepare text descriptions for each catalog item for simple matching
        # In a real enterprise app, we'd use embeddings (text-embedding-ada-002).
        # Since we might not have a working embedding model on the relay, we'll use an LLM-based filtering or keyword matching.

    def find_items(self, search_query: str, top_k: int = 3) -> list:
        if not self.catalog:
            return []

        # We use the LLM to select the best items based on the search query.
        catalog_text = ""
        for i, item in enumerate(self.catalog):
            catalog_text += f"ID: {i} | Название: {item['name']} | Цена: {item['price']}\n"

        prompt = f"""
        Ты - Агент-Кладовщик. Твоя задача найти мебель в каталоге, которая лучше всего подходит под ТЗ.

        ТЗ от Арт-Директора: "{search_query}"

        Доступный каталог:
        {catalog_text}

        Выбери до {top_k} товаров, которые лучше всего подходят.
        Верни ТОЛЬКО их ID через запятую (например: 0, 2). Если ничего не подходит, верни пустую строку.
        """

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )

            ids_text = response.choices[0].message.content.strip()
            # Parse IDs
            import re
            ids = [int(s) for s in re.findall(r'\d+', ids_text)]

            selected_items = []
            for item_id in ids:
                if 0 <= item_id < len(self.catalog):
                    selected_items.append(self.catalog[item_id])

            # Fallback if parsing fails or nothing found
            if not selected_items and self.catalog:
               selected_items = self.catalog[:top_k]

            return selected_items
        except Exception as e:
            # Fallback to first few items
            return self.catalog[:top_k] if self.catalog else []

class SalesManagerAgent:
    """
    💼 Агент Менеджер по продажам (Консультант и JSON-кодер)
    Упаковывает текст и формирует строгий JSON с ссылками на фото.
    """
    def generate_response(self, user_prompt: str, selected_items: list) -> dict:
        items_text = ""
        for item in selected_items:
            items_text += f"Название: {item['name']}, Цена: {item['price']}, Ссылка на фото: {item['image'][:30]}... (base64)\n"

        prompt = f"""
        Ты - Менеджер по продажам Dantone Home.
        Клиент спросил: "{user_prompt}"

        Арт-Директор и Кладовщик подобрали следующие товары:
        {items_text}

        Напиши красивый ответ клиенту (до 4 предложений), мягко описывая преимущества выбранных моделей и их цены.

        ВНИМАНИЕ! Ты должен ответить СТРОГО в формате JSON.
        Формат ответа:
        {{
          "reply_text": "твой красивый текст для клиента...",
          "selected_images": ["ссылка1", "ссылка2"]
        }}

        Важно: В массив selected_images вставь точные ссылки (или base64 строки) из предоставленных тебе данных.
        Но так как ссылки длинные (base64), я подставлю их сам. Вместо реальных ссылок верни массив ИМЕН товаров, например ["Диван Ноттингем (Резерв)", "Кресло Оксфорд (Резерв)"].
        """

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=800
            )

            ai_answer_raw = response.choices[0].message.content
            clean_text = ai_answer_raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)

            # Map names back to actual image base64 strings
            item_names = data.get("selected_images", [])
            actual_images = []

            for name in item_names:
                for item in selected_items:
                    # Soft match
                    if name.lower() in item['name'].lower() or item['name'].lower() in name.lower():
                        actual_images.append(item['image'])
                        break

            return {
                "reply_text": data.get("reply_text", "Вот отличный вариант для вас!"),
                "selected_images": actual_images if actual_images else [item['image'] for item in selected_items]
            }

        except Exception as e:
            return {
                "reply_text": f"Произошла ошибка при формировании ответа: {e}",
                "selected_images": [item['image'] for item in selected_items]
            }
