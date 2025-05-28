from io import BytesIO
from reportlab.pdfgen import canvas

# Константы для рендеринга PDF
PAGE_MARGIN_X = 40
PAGE_TOP_Y = 800
PAGE_HEADER_OFFSET = 20
PAGE_TITLE_Y = PAGE_TOP_Y
PAGE_SUBTITLE_Y = PAGE_TOP_Y - PAGE_HEADER_OFFSET
LINE_START_Y = PAGE_SUBTITLE_Y - PAGE_HEADER_OFFSET
LINE_HEIGHT = 20
PAGE_BOTTOM_Y = 40
FONT_NAME = 'Helvetica'
FONT_SIZE = 14


def render_pdf_shopping_cart(user, items):
    """
    Генерирует PDF-файл со списком покупок для пользователя.

    :param user: экземпляр пользователя, для которого генерируется список
    :param items: список словарей с ключами 'name', 'unit', 'amount'
    :return: BytesIO с содержимым PDF
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont(FONT_NAME, FONT_SIZE)

    # Заголовок
    p.drawString(
        PAGE_MARGIN_X,
        PAGE_TITLE_Y,
        f"Список покупок для {user.username}"
    )
    # Подзаголовок
    p.drawString(
        PAGE_MARGIN_X,
        PAGE_SUBTITLE_Y,
        "Продукты:"
    )

    # Печать строк списка
    y = LINE_START_Y
    for index, item in enumerate(items, start=1):
        text = f"{index}. {item['name']} ({item['unit']}) — {item['amount']}"
        p.drawString(PAGE_MARGIN_X, y, text)
        y -= LINE_HEIGHT

        # Проверка на конец страницы
        if y < PAGE_BOTTOM_Y:
            p.showPage()
            p.setFont(FONT_NAME, FONT_SIZE)
            y = PAGE_TOP_Y

    # Завершаем документ
    p.save()
    buffer.seek(0)
    return buffer
