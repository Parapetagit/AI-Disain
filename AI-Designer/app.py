import streamlit as st
import streamlit.components.v1 as components
import os
import json
from dotenv import load_dotenv
import base64

# --- 1. БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧА ---
# Load dotenv BEFORE importing agents so the OpenAI client initializes correctly
load_dotenv()

from agents import AppraiserAgent, ArtDirectorAgent, ClerkAgent, SalesManagerAgent
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    st.error("⚠️ Ключ не найден! Убедитесь, что создали файл .env с переменной API_KEY")
    st.stop()

st.set_page_config(page_title="AI Дизайнер Dantone Home", layout="wide")

# --- 2. ЗАГРУЗКА ДАННЫХ ИЗ НАШЕЙ БАЗЫ (JSON) ---
CATALOG_PATH = "catalog.json"
try:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)
except FileNotFoundError:
    st.error(f"⚠️ Файл {CATALOG_PATH} не найден. Сначала запустите скрипт scraper.py!")
    st.stop()

# --- 3. ИНИЦИАЛИЗАЦИЯ АГЕНТОВ ---
appraiser = AppraiserAgent()
art_director = ArtDirectorAgent()
clerk = ClerkAgent(CATALOG_PATH)
sales_manager = SalesManagerAgent()

def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# --- 4. КОМПОНЕНТ ИНТЕРАКТИВНОГО ХОЛСТА (DRAG & DROP) ---
def draggable_canvas(background_b64, items_urls):
    if not background_b64:
        return
        
    items_html = ""
    for url in items_urls:
        if url: # CSS mix-blend-mode: multiply убирает белый фон, но у нас уже вырезано с rembg, так что будет прозрачным!
            items_html += f'<img src="{url}" class="draggable" style="mix-blend-mode: normal;">\n'

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
            background-color: #f8f9fa;
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

# --- 5. ПАМЯТЬ СЕССИИ ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "bg_image_b64" not in st.session_state:
    st.session_state.bg_image_b64 = None
if "current_items" not in st.session_state:
    st.session_state.current_items = []
if "room_summary" not in st.session_state:
    st.session_state.room_summary = None

# --- 6. ИНТЕРФЕЙС САЙТА ---
st.title("🛋️ AI Дизайнер Dantone Home (Virtual Staging)")
st.caption(f"Интерактивный холст с Мультиагентной системой | Модель: {os.getenv('MODEL_NAME', 'gemini-3.1-pro')}")

# Делим экран: Слева Холст и Чат, Справа Настройки и Каталог
col_main, col_sidebar = st.columns([2, 1])

with col_sidebar:
    st.subheader("📸 Шаг 1. Загрузите комнату")
    uploaded_file = st.file_uploader("Выберите фото вашей комнаты", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file and st.session_state.bg_image_b64 != encode_image(uploaded_file):
        with st.spinner("Агент-Оценщик изучает вашу комнату... 👁️"):
            b64_image = encode_image(uploaded_file)
            st.session_state.bg_image_b64 = b64_image

            # Agent 2: Appraiser analyzes the room
            st.session_state.room_summary = appraiser.analyze_room(f"data:image/jpeg;base64,{b64_image}")

        st.success("Фото загружено и проанализировано! Теперь напишите запрос в чат.")
        st.info(f"**Анализ комнаты:**\n{st.session_state.room_summary}")

    elif st.session_state.room_summary:
        st.info(f"**Анализ комнаты:**\n{st.session_state.room_summary}")
    
    st.markdown("---")
    st.subheader("🛒 Актуальный ассортимент")
    with st.container(height=500):
        for item in catalog_data:
            st.markdown(f"**{item['name']}**")
            st.write(f"💰 {item['price']}")
            if item['image']:
                # Image can be base64 from rembg, which is nice and transparent!
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
        role = msg["role"]
        content = msg["content"]
        st.chat_message(role).write(content)

    # 3. Ввод от пользователя
    user_input = st.chat_input("Напишите: 'Поставь сюда диван Ноттингем и кресло'...")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        with st.chat_message("assistant"):
            if not st.session_state.room_summary:
                st.warning("Пожалуйста, сначала загрузите фотографию комнаты!")
            else:
                with st.spinner("Арт-Директор думает над концепцией... 🧠"):
                    search_query = art_director.formulate_query(user_input, st.session_state.room_summary)
                    st.write(f"*(Внутреннее ТЗ: {search_query})*")

                with st.spinner("Агент-Кладовщик ищет идеальную мебель... 🔎"):
                    selected_items = clerk.find_items(search_query)

                with st.spinner("Менеджер по продажам готовит ответ... 💼"):
                    final_response = sales_manager.generate_response(user_input, selected_items)
                    
                    reply_text = final_response.get("reply_text", "Готово!")
                    selected_images = final_response.get("selected_images", [])
                    
                    st.session_state.messages.append({"role": "assistant", "content": reply_text})
                    st.session_state.current_items = selected_images
                    
                    st.write(reply_text)
                    
                    # ПЕРЕЗАГРУЖАЕМ СТРАНИЦУ, чтобы обновить Холст!
                    st.rerun()
