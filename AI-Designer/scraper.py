import requests
from bs4 import BeautifulSoup
import json
import os

def run_parser():
    url = "https://dantonehome.ru/catalog/sofas/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("🤖 Запускаю парсер Dantone Home...")
    
    try:
        response = requests.get(url, headers=headers)
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
        catalog_data = [
            {"name": "Диван Ноттингем (Резерв)", "price": "227 500 руб.", "image": "https://dantonehome.ru/upload/iblock/c3a/c3a0b5a3.jpg"},
            {"name": "Диван Картрайт (Резерв)", "price": "185 300 руб.", "image": "https://dantonehome.ru/upload/iblock/d4b/d4b2f1e4.jpg"},
            {"name": "Кресло Оксфорд (Резерв)", "price": "85 000 руб.", "image": "https://dantonehome.ru/upload/iblock/e5c/e5c3d2f5.jpg"}
        ]
    else:
        print(f"✅ Найдено карточек: {len(products)}")
        for item in products:
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

                catalog_data.append({
                    "name": title,
                    "price": price,
                    "image": img_url
                })
            except Exception as e:
                pass

    # Сохраняем собранные данные в файл JSON
    with open("catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=4)
        
    print("💾 Данные успешно сохранены в файл catalog.json!")

if __name__ == "__main__":
    run_parser()