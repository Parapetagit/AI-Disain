import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
import base64

# --- 1. БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧА ---
load_dotenv()
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    st.error("⚠️ Ключ не найден! Убедитесь, что создали файл .env с переменной API_KEY")
    st.stop()

# --- 2. ПОДКЛЮЧЕНИЕ К RELAYMODELS ---
client = OpenAI(
    api_key=API_KEY,
    base_url=os.getenv("BASE_URL", "https://api.relaymodels.com/v1")
)
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-pro")

st.set_page_config(page_title="AI Дизайнер Dantone Home", layout="wide")

# --- 3. ЗАГРУЗКА ДАННЫХ ИЗ НАШЕЙ БАЗЫ (JSON) ---
try:
    with open("catalog.json", "r", encoding="utf-8") as f:
        catalog_data = json.load(f)
except FileNotFoundError:
    st.error("⚠️ Файл catalog.json не найден. Сначала запустите скрипт scraper.py!")
    st.stop()

# Формируем текст каталога для ИИ
CATALOG_TEXT = "КАТАЛОГ DANTONE HOME:\n"
for item in catalog_data:
    CATALOG_TEXT += f"Название: {item['name']}, Цена: {item['price']}, Ссылка на фото: {item['image']}\n"

# --- 4. НАСТРОЙКИ ИИ (СИСТЕМНЫЙ ПРОМПТ ДЛЯ ВЫВОДА JSON) ---
SYSTEM_PROMPT = f"""
Ты официальный AI-дизайнер Dantone Home. 
Твоя задача — общаться с клиентом и подбирать мебель.
Выбирай позиции ТОЛЬКО из этого каталога:
{CATALOG_TEXT}

ВНИМАНИЕ! Ты должен отвечать СТРОГО в формате JSON. Никакого текста до или после JSON.
Формат твоего ответа должен быть таким:
{{
  "reply_text": "Тут твой ответ клиенту, рассказ про мебель и итоговая цена...",
  "selected_images": ["ссылка_на_фото_1", "ссылка_на_фото_2"]
}}

Если клиент просит добавить товар, добавь его ссылку в массив selected_images.
Если клиент просит убрать товар, удали его ссылку из массива.
Ссылки бери СТРОГО из каталога один в один.
"""

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# Вспомогательная функция для парсинга ответа ИИ
def parse_ai_response(response_text):
    try:
        # Очищаем от возможных маркеров markdown (```json ... ```)
        clean_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("reply_text", "Ответ сгенерирован."), data.get("selected_images", [])
    except Exception as e:
        return f"Обычный ответ: {response_text}", []

# --- 5. КОМПОНЕНТ ИНТЕРАКТИВНОГО ХОЛСТА (DRAG & DROP) ---
def draggable_canvas(background_b64, items_urls):
    if not background_b64:
        return
        
    items_html = ""
    for url in items_urls:
        if url: # CSS mix-blend-mode: multiply убирает белый фон (делает его прозрачным на светлых фото)
            items_html += f'<img src="{url}" class="draggable" style="mix-blend-mode: multiply;">\n'

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        #canvas-container {{
            position: relative;
            width: 100%;
            border: 2px dashed #ccc;
            border-radius: 10px;
            overflow: hidden;
        }}
        #bg-image {{
            width: 100%;
            display: block;
        }}
        .draggable {{
            position: absolute;
            top: 50%;
            left: 50%;
            width: 200px;
            cursor: grab;
            transform: translate(-50%, -50%);
            z-index: 10;
            filter: drop-shadow(5px 5px 5px rgba(0,0,0,0.3)); /* Добавляем тень мебели */
        }}
        .draggable:active {{
            cursor: grabbing;
        }}
    </style>
    </head>
    <body>
        <div id="canvas-container">
            <img id="bg-image" src="data:image/jpeg;base64,{background_b64}">
            {items_html}
        </div>
        <script>
            const draggables = document.querySelectorAll('.draggable');
            draggables.forEach(item => {{
                let isDragging = false;
                let startX, startY, initialX, initialY;

                item.addEventListener('mousedown', (e) => {{
                    isDragging = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    initialX = item.offsetLeft;
                    initialY = item.offsetTop;
                    item.style.zIndex = 100; 
                }});

                document.addEventListener('mousemove', (e) => {{
                    if (!isDragging) return;
                    e.preventDefault();
                    const dx = e.clientX - startX;
                    const dy = e.clientY - startY;
                    item.style.left = initialX + dx + 'px';
                    item.style.top = initialY + dy + 'px';
                }});

                document.addEventListener('mouseup', () => {{
                    isDragging = false;
                    item.style.zIndex = 10;
                }});
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=600)

# --- 6. ПАМЯТЬ СЕССИИ ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
if "bg_image_b64" not in st.session_state:
    st.session_state.bg_image_b64 = None
if "current_items" not in st.session_state:
    st.session_state.current_items = []

# --- 7. ИНТЕРФЕЙС САЙТА ---
st.title("🛋️ AI Дизайнер Dantone Home (Virtual Staging)")
st.caption(f"Интерактивный холст | Модель: {MODEL_NAME}")

# Делим экран: Слева Холст и Чат, Справа Настройки и Каталог
col_main, col_sidebar = st.columns([2, 1])

with col_sidebar:
    st.subheader("📸 Шаг 1. Загрузите комнату")
    uploaded_file = st.file_uploader("Выберите фото вашей комнаты", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        # Сохраняем фон в память
        st.session_state.bg_image_b64 = encode_image(uploaded_file)
        st.success("Фото загружено! Теперь напишите ИИ в чат.")
    
    st.markdown("---")
    st.subheader("🛒 Актуальный ассортимент")
    with st.container(height=500):
        for item in catalog_data:
            st.markdown(f"**{item['name']}**")
            st.write(f"💰 {item['price']}")
            if item['image']:
                st.image(item['image'], width=120)
            st.divider()

with col_main:
    # 1. Отрисовываем интерактивный холст, если есть фото
    if st.session_state.bg_image_b64:
        st.subheader("🎨 Интерактивный холст (Двигайте мебель мышкой)")
        draggable_canvas(st.session_state.bg_image_b64, st.session_state.current_items)
    else:
        st.info("👈 Пожалуйста, загрузите фото вашей комнаты в меню справа, чтобы увидеть магию!")

    st.markdown("---")
    st.subheader("💬 Чат с дизайнером")
    
    # 2. Отрисовываем историю чата
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
            
        role = msg["role"]
        content = msg["content"]
        
        # Разбираем сообщение для красивого отображения
        if role == "user":
            display_text = content[0]["text"] if isinstance(content, list) else content
            st.chat_message("user").write(display_text)
        elif role == "assistant":
            # ИИ отвечает в JSON, поэтому мы парсим его текст для истории
            reply_text, _ = parse_ai_response(content)
            st.chat_message("assistant").write(reply_text)

    # 3. Ввод от пользователя
    user_input = st.chat_input("Напишите: 'Поставь сюда диван Ноттингем и кресло'...")
    
    if user_input:
        # Формируем запрос
        if uploaded_file:
            user_msg_content = [
                {"type": "text", "text": user_input},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{st.session_state.bg_image_b64}"}}
            ]
        else:
            user_msg_content = user_input

        # Добавляем вопрос пользователя в память и на экран
        st.session_state.messages.append({"role": "user", "content": user_msg_content})
        st.chat_message("user").write(user_input)

        # Отправляем запрос к ИИ
        with st.chat_message("assistant"):
            with st.spinner("Анализирую интерьер, расставляю мебель..."):
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=st.session_state.messages,
                        max_tokens=1500,
                        response_format={"type": "json_object"}
                    )
                    
                    ai_answer_raw = response.choices[0].message.content
                    
                    # Записываем сырой JSON-ответ ИИ в историю (чтобы ИИ помнил свой JSON)
                    st.session_state.messages.append({"role": "assistant", "content": ai_answer_raw})
                    
                    # Парсим ответ
                    reply_text, selected_images = parse_ai_response(ai_answer_raw)
                    
                    # Обновляем ссылки на мебель в памяти
                    st.session_state.current_items = selected_images
                    
                    st.write(reply_text)
                    
                    # ПЕРЕЗАГРУЖАЕМ СТРАНИЦУ, чтобы обновить Холст!
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Ошибка API: {e}")