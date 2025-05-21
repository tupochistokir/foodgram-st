from io import BytesIO
from reportlab.pdfgen import canvas


def render_pdf_shopping_cart(user, items):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 14)
    p.drawString(40, 800, f"Список покупок для {user.username}")
    p.drawString(40, 780, "Продукты:")
    y = 760
    for i, item in enumerate(items, 1):
        text = f"{i}. {item['name']} ({item['unit']}) — {item['amount']}"
        p.drawString(40, y, text)
        y -= 20
        if y < 40:  # Переводим на новую страницу
            p.showPage()
            y = 800
    p.save()
    buffer.seek(0)
    return buffer
