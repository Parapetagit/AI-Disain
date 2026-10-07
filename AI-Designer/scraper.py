import requests
from bs4 import BeautifulSoup
import json
import os
import base64
from io import BytesIO
from PIL import Image
from rembg import remove, new_session

def download_and_process_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Open image from bytes
        img = Image.open(BytesIO(response.content))

        # Use lighter model to avoid OOM
        session = new_session("u2netp")

        # Remove background
        img_no_bg = remove(img, session=session)

        # Convert the resulting image to base64
        buffered = BytesIO()
        img_no_bg.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Failed to process image {url}: {e}")
        return url # fallback to original url if processing fails

def run_parser():
    url = "https://dantonehome.ru/catalog/sofas/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("🤖 Запускаю парсер Dantone Home...")

    # Check if catalog.json already exists to avoid redundant processing during tests
    if os.path.exists("catalog.json"):
        print("catalog.json already exists. Skipping parsing to avoid unnecessary API calls.")
        return

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Ищем карточки (здесь нужно будет поправить класс, если сайт его изменил)
    products = soup.find_all('div', class_='product-card')

    catalog_data = []

    if not products:
        print("⚠️ Карточки не найдены. Создаю резервный (тестовый) каталог Dantone Home...")
        # Если защита сайта нас не пустила, создадим фейковую базу, чтобы сайт работал
        raw_catalog = [
            {"name": "Диван Ноттингем (Резерв)", "price": "227 500 руб.", "image": "https://picsum.photos/id/10/200/300"},
            {"name": "Диван Картрайт (Резерв)", "price": "185 300 руб.", "image": "https://picsum.photos/id/20/200/300"},
            {"name": "Кресло Оксфорд (Резерв)", "price": "85 000 руб.", "image": "https://picsum.photos/id/30/200/300"}
        ]

        for item in raw_catalog:
            print(f"Обработка картинки для {item['name']}...")
            processed_image = download_and_process_image(item['image'])
            catalog_data.append({
                "name": item['name'],
                "price": item['price'],
                "image": processed_image
            })
    else:
        print(f"✅ Найдено карточек: {len(products)}")
        for i, item in enumerate(products):
            if i >= 5: # Limit for testing purposes to not take too long
                break
            try:
                title_elem = item.find(class_='product-card__title')
                price_elem = item.find(class_='product-card__price')
                img_elem = item.find('img')

                title = title_elem.text.strip() if title_elem else "Без названия"
                price = price_elem.text.strip() if price_elem else "Без цены"

                img_url = ""
                if img_elem:
                    img_url = img_elem.get('data-src') or img_elem.get('src') or ""
                    if img_url.startswith('/'):
                        img_url = "https://dantonehome.ru" + img_url

                print(f"Обработка картинки для {title}...")
                processed_image = download_and_process_image(img_url) if img_url else ""

                catalog_data.append({
                    "name": title,
                    "price": price,
                    "image": processed_image
                })
            except Exception as e:
                print(f"Failed to parse product: {e}")
                pass

    # Сохраняем собранные данные в файл JSON
    with open("catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=4)

    print("💾 Данные успешно сохранены в файл catalog.json!")

if __name__ == "__main__":
    run_parser()
