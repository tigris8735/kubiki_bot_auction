import pyautogui
import time
from PIL import Image
import cv2
import numpy as np
import pytesseract
import os
import glob
import keyboard
import threading
import random
import datetime

# ------------------------------------------------------------
# 1. ЛОГГИРОВАНИЕ
# ------------------------------------------------------------
LOG_FILE = "bot.log"

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")

# ------------------------------------------------------------
# 2. АВТОМАТИЧЕСКИЙ ПОИСК TESSERACT
# ------------------------------------------------------------
def get_tesseract_path():
    base = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(base, 'Tesseract-OCR', 'tesseract.exe')
    if os.path.exists(candidate):
        return candidate
    standard = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(standard):
        return standard
    standard_x86 = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    if os.path.exists(standard_x86):
        return standard_x86
    raise Exception("Tesseract не найден. Положите папку Tesseract-OCR рядом со скриптом или установите в Program Files.")

pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()
log("Tesseract инициализирован")

# ------------------------------------------------------------
# 3. НАСТРОЙКИ (измените под себя)
# ------------------------------------------------------------
items = ['Боевой набор']
items_prices = [150000]
item_index = 0
auction_button = 'p'
refresh_algorithm_coef = 12
IsUseCache = True
IsSaveImageInCache = False
count_of_page_refreshes_after_buy_lot = 2
clickOK_iterations = 10
pyautogui.PAUSE = 0.0001
pyautogui.FAILSAFE = False

# Задержки
pre_click_delay = 0.05
pre_mouse_move_delay = 0.05
page_post_load_anim_time = 0.2
delay_after_click_page_when_find_page_and_scroll = 0.6
start_bot_sleep_time = 3
before_click_scroll_delay = 0.05
after_drag_scroll_delay = 0.05
mouse_down_sleep_time = 0.01
mouse_drag_delta_time = 0.101
delay_auction_action = 0.5
delay_open_PDA = 3
delay_open_auction = 1
delay_pre_clickOK_position = 0.1
Find_OK_Button_Delay = 0.1
delay_refresh_page_after_clickOK_time = 0.4
before_click_scroll_delay_when_find_scroll = 0.1
after_drag_scroll_delay_when_find_scroll = 0.1

# Глобальные переменные
buy_lot_count = 0
buyoutprice = items_prices[item_index]
item_name = items[item_index]
lots_count = 10
scroll_offset = [90, 180, 269, 360]          # 4 уровня скролла
dir = os.path.dirname(os.path.abspath(__file__))
PageButtonCoords = []
current_page = 0
current_scroll = 0
current_lot = 0

log(f"Настройки загружены. Предмет: {item_name}, макс. цена: {buyoutprice}")

# ------------------------------------------------------------
# 4. ЗАГРУЗКА ИЗОБРАЖЕНИЙ
# ------------------------------------------------------------
OK_Button = Image.open(dir + '/Images/OK_Button.png')
log("Изображение OK_Button загружено")

BuyLot_Button = None
buy_lot_button_path = dir + '/Images/BuyLot_Button.png'
if os.path.exists(buy_lot_button_path):
    BuyLot_Button = Image.open(buy_lot_button_path)
    log("Изображение BuyLot_Button загружено")
else:
    log("Изображение BuyLot_Button не найдено, будет использоваться резервная координата")

x_screenshot, y_screenshot, screenshot_size_x, screenshot_size_y = 1320, 385, 70, 370
pages_images_screenshot_space = (980, 755, 170, 25)
x_price_offset, y_price_offset, price_size_x, price_size_y = 5, 2, 135, 30
good_line_size_y = 37
good_line_local_coord_y = good_line_size_y / 2
scroller_pos_x, scroller_pos_y = 1395, 335
offsets_in_scroll_for_buy_button = [55, 45.25, 35.5, 25.75, 16]
buy_button_pos_x, buy_button_offset_y = 1328, offsets_in_scroll_for_buy_button[0]
ok_button_pos_x, ok_button_pos_y = 961, 570
lot_name_window_x, lot_name_window_y = 1272, 336
sort_lots_button_x, sort_lots_button_y = 1300, 373
auction_button_x, auction_button_y = 560, 406
lot_pos_x = 1272

Page_images = []
Page_images_touched = []
if not IsUseCache:
    IsSaveImageInCache = False

for page_icon in glob.glob(dir + '/Pages/*.png'):
    Page_images.append(Image.open(page_icon))
for page_touched_icon in glob.glob(dir + '/Pages_touched/*.png'):
    Page_images_touched.append(Image.open(page_touched_icon))
log(f"Загружено страниц: {len(Page_images)}")

cache_prices = []
cache_prices_images = []
if IsUseCache:
    for cache_price in glob.glob(dir + '/cache_prices/*.png'):
        cache_prices_image = Image.open(cache_price)
        cache_prices.append(cache_price)
        cache_prices_images.append(cache_prices_image)
    log(f"Загружено кэшированных цен: {len(cache_prices)}")

# Флаг, чтобы не повторять полный перебор страниц/скроллов, если ничего не найдено
scan_complete = False

# ------------------------------------------------------------
# 5. ФУНКЦИИ РАБОТЫ С ИЗОБРАЖЕНИЯМИ И OCR
# ------------------------------------------------------------
def screenshot():
    return pyautogui.screenshot(region=(x_screenshot, y_screenshot, screenshot_size_x, screenshot_size_y))

def cut(image, xoffset, yoffset, xsize, ysize):
    images = []
    for i in range(lots_count):
        images.append(image.crop((xoffset, i * good_line_size_y + yoffset,
                                  xoffset + xsize, i * good_line_size_y + yoffset + ysize)))
    return images

def preprocess_image(image, target_size=(128, 128)):
    preprocessed_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    preprocessed_image = cv2.resize(preprocessed_image, target_size)
    _, preprocessed_image = cv2.threshold(preprocessed_image, 128, 255, cv2.THRESH_BINARY)
    preprocessed_image = np.expand_dims(preprocessed_image, axis=-1)
    preprocessed_image = np.repeat(preprocessed_image, 3, axis=-1)
    return Image.fromarray(preprocessed_image)

def recognize_image(image, psm_config, whitelist):
    config = f'--psm {psm_config} -c tessedit_char_whitelist={whitelist}'
    text = pytesseract.image_to_string(image, config=config, lang='rus')
    return text.strip() if text.strip() else "None"

def FindAndClickPageButton():
    global PageButtonCoords, current_page
    if not Page_images or current_page >= len(Page_images):
        return True
    try:
        pos = pyautogui.locateOnScreen(Page_images_touched[current_page], region=pages_images_screenshot_space, confidence=0.8)
        if not pos:
            pos = pyautogui.locateOnScreen(Page_images[current_page], region=pages_images_screenshot_space, confidence=0.8)
        if not pos:
            return True
        PageButtonCoords = pyautogui.center(pos)
        mouse_move(PageButtonCoords[0] + random.randint(-3, 3), PageButtonCoords[1] + random.randint(-3, 3), False)
        mouse_click()
        time.sleep(page_post_load_anim_time)
        return True
    except Exception as e:
        if not hasattr(FindAndClickPageButton, "_logged"):
            log(f"Не удалось найти иконку страницы {current_page}. Будет использована одна страница.")
            FindAndClickPageButton._logged = True
        return True

def AnalizePage():
    global current_scroll
    if current_scroll != 0:
        mouse_move(scroller_pos_x, scroller_pos_y)
        drag_mouse(None, scroller_pos_y + scroll_offset[current_scroll - 1])
        time.sleep(after_drag_scroll_delay)
    screen = screenshot()
    cuttedprices = CutPrices(screen)
    return TryBuyLot(cuttedprices[current_lot])

def DetermineImageValue(image):
    try:
        idx = cache_prices_images.index(image)
        return cache_prices[idx]
    except:
        cache_prices_images.append(image)
        priceicon = preprocess_image(np.array(image), (512, 150))
        recognized_price = recognize_image(priceicon, 7, '').strip()
        recognized_price = ClearPrice(recognized_price)
        cache_prices.append(recognized_price)
        SaveImageInCache(image, recognized_price)
        return recognized_price

def TryBuyLot(image):
    recognized_price = DetermineImageValue(image)
    if recognized_price == -1 or recognized_price > buyoutprice:
        return False
    log(f"Найдена подходящая цена: {recognized_price} (макс. {buyoutprice})")
    BuyLot(current_lot, recognized_price)
    return True

def FindFirstLotWithPrice(prices_images):
    global current_lot
    for i in range(len(prices_images)):
        current_lot = i
        recognized_price = DetermineImageValue(prices_images[i])
        if recognized_price == -1:
            continue
        return True
    return False

def SaveImageInCache(image, price):
    if IsSaveImageInCache:
        image.save(f'cache_prices/{price}.png')

def FindBuyLotButton():
    if BuyLot_Button is None:
        return None
    try:
        pos = pyautogui.locateCenterOnScreen(BuyLot_Button, confidence=0.7)
        if pos:
            return (pos.x, pos.y)
        pos = pyautogui.locateCenterOnScreen(BuyLot_Button, confidence=0.6)
        return (pos.x, pos.y) if pos else None
    except Exception as e:
        log(f"Ошибка поиска кнопки выкупа по картинке: {e}")
        return None

def BuyLot(lot_number, recognized_price):
    global buy_lot_count, scan_complete
    mouse_move(lot_pos_x, y_screenshot + good_line_local_coord_y + lot_number * good_line_size_y, False)
    mouse_click()
    time.sleep(0.2)
    btn_pos = FindBuyLotButton()
    if btn_pos:
        mouse_move(btn_pos[0], btn_pos[1])
        log("Кнопка выкупа найдена по изображению")
    else:
        mouse_move(buy_button_pos_x, y_screenshot + lot_number * good_line_size_y + buy_button_offset_y)
        log("Кнопка выкупа не найдена, использованы координаты")
    mouse_click()
    buy_lot_count += 1
    log(f"Покупка совершена! Цена: {recognized_price}. Всего покупок: {buy_lot_count}")
    scan_complete = False   # после покупки сбрасываем флаг, чтобы начать новый поиск
    ClickOK()

def FindPageAndScroll():
    global buy_button_offset_y, current_page, current_scroll, scan_complete
    if scan_complete:
        return  # уже всё проверили и ничего нет – не тратим время

    for i in range(len(Page_images)):
        current_page = i
        current_scroll = 0
        buy_button_offset_y = offsets_in_scroll_for_buy_button[0]
        FindAndClickPageButton()
        time.sleep(delay_after_click_page_when_find_page_and_scroll)
        screen = screenshot()
        cuttedprices = CutPrices(screen)
        if FindFirstLotWithPrice(cuttedprices):
            log(f"Лот найден на странице {current_page}, скролл {current_scroll}")
            return
        mouse_move(scroller_pos_x, scroller_pos_y, False)
        time.sleep(before_click_scroll_delay_when_find_scroll)
        pyautogui.mouseDown()
        time.sleep(mouse_down_sleep_time)
        for j in range(len(scroll_offset)):
            current_scroll += 1
            buy_button_offset_y = offsets_in_scroll_for_buy_button[j + 1]
            pyautogui.moveTo(None, scroller_pos_y + scroll_offset[j], mouse_drag_delta_time)
            time.sleep(after_drag_scroll_delay_when_find_scroll)
            screen = screenshot()
            cuttedprices = CutPrices(screen)
            if FindFirstLotWithPrice(cuttedprices):
                log(f"Лот найден на странице {current_page}, скролл {current_scroll}")
                pyautogui.mouseUp()
                time.sleep(mouse_down_sleep_time)
                return
        pyautogui.mouseUp()
        time.sleep(mouse_down_sleep_time)
    # Если дошли сюда – ничего не найдено ни на одной странице
    log("Подходящих лотов не найдено. Ждём следующего обновления.")
    scan_complete = True   # не будем повторять до следующей покупки или таймера

def CutPrices(screenshot):
    return cut(screenshot, x_price_offset, y_price_offset, price_size_x, price_size_y)

def ClickOK_Position():
    mouse_move(ok_button_pos_x, ok_button_pos_y)
    time.sleep(delay_pre_clickOK_position)
    mouse_click(False)

def ClickOK():
    for _ in range(clickOK_iterations):
        if FindImage(OK_Button):
            ClickOK_Position()
            time.sleep(delay_refresh_page_after_clickOK_time)
            log("OK подтверждено")
            break
        time.sleep(Find_OK_Button_Delay)
    MultipleRefreshPage()

def MultipleRefreshPage():
    for _ in range(count_of_page_refreshes_after_buy_lot):
        FindAndClickPageButton()

def ClearPrice(priceRaw):
    price = ''.join(ch for ch in priceRaw if ch.isdigit())
    try:
        return int(price)
    except:
        return -1

def mouse_move(x, y, isNeedInitialDelay=True):
    if isNeedInitialDelay:
        time.sleep(pre_mouse_move_delay)
    pyautogui.moveTo(x, y)

def mouse_click(isNeedInitialDelay=True):
    if isNeedInitialDelay:
        time.sleep(pre_click_delay)
    pyautogui.click()

def drag_mouse(dx, dy, isNeedInitialDelay=True):
    if isNeedInitialDelay:
        time.sleep(before_click_scroll_delay)
    pyautogui.mouseDown()
    time.sleep(mouse_down_sleep_time)
    pyautogui.moveTo(dx, dy, duration=mouse_drag_delta_time)
    time.sleep(after_drag_scroll_delay)
    pyautogui.mouseUp()
    time.sleep(mouse_down_sleep_time)

def OpenAuction():
    log("Открытие аукциона...")
    keyboard.press_and_release(auction_button)
    time.sleep(delay_open_PDA)
    mouse_move(auction_button_x, auction_button_y)
    time.sleep(delay_auction_action)
    mouse_click()
    time.sleep(delay_open_auction)
    mouse_move(lot_name_window_x, lot_name_window_y)
    time.sleep(delay_auction_action)
    mouse_click()
    time.sleep(delay_auction_action)
    keyboard.write(item_name)
    time.sleep(delay_auction_action)
    mouse_move(sort_lots_button_x, sort_lots_button_y)
    time.sleep(delay_auction_action)
    mouse_click()
    time.sleep(delay_auction_action)
    mouse_click()
    time.sleep(delay_auction_action)
    log("Аукцион открыт, поиск начат")

def FindImage(IconImage):
    try:
        pyautogui.locateCenterOnScreen(IconImage, confidence=0.8)
        return True
    except:
        return False

def key_listener():
    global running
    keyboard.wait('f5')
    running = False
    log("Получен сигнал остановки (F5)")

def main():
    global running, iteration, scan_complete
    iteration = 0
    log("Бот запущен. Нажмите F5 для остановки.")
    time.sleep(start_bot_sleep_time)
    OpenAuction()
    while running:
        iteration += 1
        # Каждые refresh_algorithm_coef * 25 итераций – принудительно обновляем поиск
        if (iteration - 1) % (25 * refresh_algorithm_coef) == 0:
            ClickOK_Position()
            scan_complete = False   # разрешаем новый поиск
            FindPageAndScroll()
            continue
        if not FindAndClickPageButton():
            continue
        AnalizePage()
        # Небольшая пауза между итерациями, чтобы снизить нагрузку
        time.sleep(0.02)
    log("Бот остановлен")

if __name__ == "__main__":
    running = True
    key_thread = threading.Thread(target=key_listener)
    key_thread.start()
    main()
    key_thread.join()