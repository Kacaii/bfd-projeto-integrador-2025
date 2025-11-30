import flet as ft

COLORS = {
    "primary": "#0078D4",
    "secondary": "#4CAF50",
    "background": "#F3F6F9",
    "card_bg": "#FFFFFF",
    "danger": "#D60E0E",
    "warning": "#FFA000",
    "text_dark": "#333333",
    "text_muted": "#757575",
}

PAYMENT_METHODS = [
    {"name": "Dinheiro", "icon": ft.icons.MONETIZATION_ON, "key": "F1"},
    {"name": "Crédito", "icon": ft.icons.CREDIT_CARD, "key": "F2"},
    {"name": "Débito", "icon": ft.icons.CREDIT_CARD_OFF, "key": "F3"},
    {"name": "Pix", "icon": ft.icons.QR_CODE_2, "key": "F4"},
]

FKEY_MAP = {"F1": 0, "F2": 1, "F3": 2, "F4": 3}
