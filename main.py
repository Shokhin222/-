from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QSpinBox, QStatusBar, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "products.txt"
REPORT_FILE = APP_DIR / "session_report.txt"
TIME_FORMAT = "%d.%m.%Y %H:%M:%S"


def now_text() -> str:
    """Return date/time in the exact format required by the assignment."""
    return datetime.now().strftime(TIME_FORMAT)


class BaseEntity(ABC):
    """Abstract base class for all domain entities."""

    @abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError


class Product(BaseEntity):
    """Warehouse product with validated properties and comparison support."""

    def __init__(self, product_id: str, name: str, category: str,
                 price: float, quantity: int):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.price = price
        self.quantity = quantity

    @property
    def product_id(self) -> str:
        return self._product_id

    @product_id.setter
    def product_id(self, value: str) -> None:
        if not value.strip():
            raise ValueError("ID товара не может быть пустым")
        self._product_id = value.strip()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Название товара не может быть пустым")
        self._name = value.strip()

    @property
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        if not value.strip():
            raise ValueError("Категория не может быть пустой")
        self._category = value.strip()

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        numeric_value = float(value)
        if numeric_value < 0:
            raise ValueError("Цена не может быть отрицательной")
        self._price = numeric_value

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int) -> None:
        numeric_value = int(value)
        if numeric_value < 0:
            raise ValueError("Количество не может быть отрицательным")
        self._quantity = numeric_value

    def get_id(self) -> str:
        return self.product_id

    @property
    def total_value(self) -> float:
        return self.price * self.quantity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Product):
            return NotImplemented
        return self.product_id == other.product_id

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Product):
            return NotImplemented
        return self.name.casefold() < other.name.casefold()

    def __str__(self) -> str:
        return f"{self.name} ({self.quantity} шт.)"

    def __repr__(self) -> str:
        return (
            f"Product(product_id={self.product_id!r}, name={self.name!r}, "
            f"category={self.category!r}, price={self.price!r}, "
            f"quantity={self.quantity!r})"
        )


class CustomMap:
    """Small key/value mapping implemented with a list of pairs, not dict."""

    def __init__(self):
        self._pairs: list[list[object]] = []

    @property
    def pairs(self) -> tuple:
        return tuple((pair[0], pair[1]) for pair in self._pairs)

    def set(self, key: object, value: object) -> None:
        for pair in self._pairs:
            if pair[0] == key:
                pair[1] = value
                return
        self._pairs.append([key, value])

    def get(self, key: object, default: object = None) -> object:
        for pair in self._pairs:
            if pair[0] == key:
                return pair[1]
        return default

    def remove(self, key: object) -> bool:
        for index, pair in enumerate(self._pairs):
            if pair[0] == key:
                self._pairs.pop(index)
                return True
        return False

    def __len__(self) -> int:
        return len(self._pairs)

    def __contains__(self, key: object) -> bool:
        return any(pair[0] == key for pair in self._pairs)

    def __iter__(self):
        for pair in self._pairs:
            yield pair[0]


class Inventory:
    """Domain service for managing product objects."""

    def __init__(self):
        self._products: list[Product] = []

    @property
    def products(self) -> tuple[Product, ...]:
        return tuple(self._products)

    def add(self, product: Product) -> None:
        if product in self._products:
            raise ValueError("Товар с таким ID уже существует")
        self._products.append(product)

    def remove(self, product_id: str) -> bool:
        for product in self._products:
            if product.product_id == product_id:
                self._products.remove(product)
                return True
        return False

    def find(self, query: str) -> tuple[Product, ...]:
        term = query.casefold().strip()
        if not term:
            return self.products
        return tuple(
            product for product in self._products
            if term in product.name.casefold()
            or term in product.category.casefold()
            or term in product.product_id.casefold()
        )

    def change_quantity(self, product_id: str, delta: int) -> None:
        for product in self._products:
            if product.product_id == product_id:
                product.quantity = product.quantity + delta
                return
        raise ValueError("Товар не найден")

    @property
    def total_items(self) -> int:
        return sum(product.quantity for product in self._products)

    @property
    def total_value(self) -> float:
        return sum(product.total_value for product in self._products)

    def category_counts(self) -> CustomMap:
        result = CustomMap()
        for product in self._products:
            current = int(result.get(product.category, 0))
            result.set(product.category, current + 1)
        return result

    def save(self, path: Path = DATA_FILE) -> None:
        with path.open("w", encoding="utf-8") as file:
            for product in self._products:
                # A pipe in a field is replaced to keep the file format simple.
                fields = (
                    product.product_id.replace("|", "/"),
                    product.name.replace("|", "/"),
                    product.category.replace("|", "/"),
                    f"{product.price:.2f}",
                    str(product.quantity),
                )
                file.write("|".join(fields) + "\n")

    def load(self, path: Path = DATA_FILE) -> None:
        if not path.exists():
            self._seed_demo_data()
            return
        loaded: list[Product] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.rstrip("\n").split("|")
                if len(parts) != 5:
                    continue
                try:
                    loaded.append(Product(
                        parts[0], parts[1], parts[2], float(parts[3]), int(parts[4])
                    ))
                except (ValueError, TypeError):
                    continue
        self._products = loaded
        if not self._products:
            self._seed_demo_data()

    def _seed_demo_data(self) -> None:
        # Ten user-created objects are included on the first run.
        self._products = [
            Product("P001", "Клавиатура", "Периферия", 2490, 14),
            Product("P002", "Мышь беспроводная", "Периферия", 1790, 22),
            Product("P003", "Монитор 24 дюйма", "Мониторы", 15990, 7),
            Product("P004", "USB-C кабель", "Кабели", 590, 35),
            Product("P005", "SSD 1 ТБ", "Накопители", 7490, 9),
            Product("P006", "Оперативная память 16 ГБ", "Комплектующие", 4290, 12),
            Product("P007", "Веб-камера", "Периферия", 3290, 5),
            Product("P008", "Наушники", "Аудио", 2890, 18),
            Product("P009", "Блок питания", "Комплектующие", 5190, 6),
            Product("P010", "Коврик для мыши", "Аксессуары", 790, 30),
        ]


# Ten custom UI component classes. Each inherits a Qt widget and customizes
# its appearance or behavior rather than merely placing standard widgets.
class AppTitleLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setObjectName("appTitle")
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFont(QFont("Arial", 18, QFont.Weight.Bold))

    def sizeHint(self):
        size = super().sizeHint()
        size.setHeight(max(size.height(), 34))
        return size


class FieldLabel(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(max(size.width(), 90))
        return size


class SearchInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Поиск по ID, названию или категории…")
        self.setClearButtonEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
            event.accept()
            return
        super().keyPressEvent(event)


class ProductNameInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Например, Механическая клавиатура")
        self.setMaxLength(80)

    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(max(size.width(), 180))
        return size


class ProductIdInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Например, P011")
        self.setMaxLength(20)

    def keyPressEvent(self, event):
        # Keep normal editing behavior while preventing accidental whitespace IDs.
        if event.text().isspace() and event.text():
            event.accept()
            return
        super().keyPressEvent(event)


class CategorySelector(QComboBox):
    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.addItems([
            "Периферия", "Комплектующие", "Кабели", "Мониторы",
            "Накопители", "Аудио", "Аксессуары"
        ])
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

    def showPopup(self):
        # Refresh the popup width so long category names remain readable.
        self.setMinimumContentsLength(max(self.minimumContentsLength(), 12))
        super().showPopup()


class QuantityInput(QSpinBox):
    def __init__(self):
        super().__init__()
        self.setRange(0, 1_000_000)
        self.setValue(1)
        self.setSuffix(" шт.")

    def stepBy(self, steps: int) -> None:
        # Qt still handles the stepping, with the configured non-negative range.
        super().stepBy(steps)


class PriceInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("0.00")
        self.setMaxLength(14)

    def focusOutEvent(self, event):
        raw = self.text().strip().replace(",", ".")
        if raw:
            try:
                self.setText(f"{float(raw):.2f}")
            except ValueError:
                pass
        super().focusOutEvent(event)


class ActionButton(QPushButton):
    def __init__(self, text: str, role: str = "primary"):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("role", role)
        self.setMinimumHeight(34)

    def sizeHint(self):
        size = super().sizeHint()
        size.setHeight(max(size.height(), 34))
        return size


class ProductTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 6)
        self.setHorizontalHeaderLabels(
            ["ID", "Название", "Категория", "Цена", "Кол-во", "Стоимость"]
        )
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

    def sizeHint(self):
        size = super().sizeHint()
        size.setHeight(max(size.height(), 360))
        return size


class InventoryStatusBar(QStatusBar):
    def __init__(self):
        super().__init__()
        self.showMessage("Готово к работе")

    def showMessage(self, message: str, timeout: int = 0) -> None:
        # Prefix status messages to make the app feedback easy to identify.
        super().showMessage(f"Склад: {message}", timeout)


class InventoryMainWindow(QMainWindow):
    """Main application window. It also customizes the close event."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Warehouse Desk — учёт склада")
        self.resize(1120, 760)
        self._login = "warehouse_user"
        self._time_in = now_text()
        self._inventory = Inventory()
        self._inventory.load()
        self._build_ui()
        self._refresh_table()
        self._update_summary()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        heading_box = QVBoxLayout()
        heading_box.addWidget(AppTitleLabel("Warehouse Desk"))
        subtitle = QLabel("Система учёта товаров и остатков")
        subtitle.setObjectName("subtitle")
        heading_box.addWidget(subtitle)
        header.addLayout(heading_box)
        header.addStretch()
        self._summary_label = QLabel()
        self._summary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        header.addWidget(self._summary_label)
        root.addLayout(header)

        search_row = QHBoxLayout()
        self._search = SearchInput()
        self._search.textChanged.connect(self._refresh_table)
        search_row.addWidget(self._search, 1)
        self._clear_search = ActionButton("Сбросить", "secondary")
        self._clear_search.clicked.connect(self._search.clear)
        search_row.addWidget(self._clear_search)
        root.addLayout(search_row)

        body = QHBoxLayout()
        body.setSpacing(16)

        self._table = ProductTable()
        self._table.itemSelectionChanged.connect(self._load_selected_to_form)
        body.addWidget(self._table, 3)

        form_frame = QFrame()
        form_frame.setObjectName("formCard")
        form = QFormLayout(form_frame)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(11)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self._id_input = ProductIdInput()
        self._name_input = ProductNameInput()
        self._category_input = CategorySelector()
        self._price_input = PriceInput()
        self._quantity_input = QuantityInput()

        form.addRow(FieldLabel("ID товара"), self._id_input)
        form.addRow(FieldLabel("Название"), self._name_input)
        form.addRow(FieldLabel("Категория"), self._category_input)
        form.addRow(FieldLabel("Цена, ₽"), self._price_input)
        form.addRow(FieldLabel("Количество"), self._quantity_input)

        self._add_button = ActionButton("Добавить товар")
        self._add_button.clicked.connect(self._add_product)
        form.addRow(self._add_button)

        self._update_button = ActionButton("Изменить количество", "secondary")
        self._update_button.clicked.connect(self._adjust_selected)
        form.addRow(self._update_button)

        self._delete_button = ActionButton("Удалить выбранный", "danger")
        self._delete_button.clicked.connect(self._delete_selected)
        form.addRow(self._delete_button)

        self._reset_button = ActionButton("Очистить форму", "secondary")
        self._reset_button.clicked.connect(self._clear_form)
        form.addRow(self._reset_button)

        body.addWidget(form_frame, 1)
        root.addLayout(body, 1)

        footer = QHBoxLayout()
        self._stock_bar = QProgressBar()
        self._stock_bar.setRange(0, 100)
        self._stock_bar.setFormat("Заполненность демонстрационного индикатора: %p%")
        footer.addWidget(self._stock_bar, 1)
        self._save_button = ActionButton("Сохранить склад", "primary")
        self._save_button.clicked.connect(self._save_inventory)
        footer.addWidget(self._save_button)
        root.addLayout(footer)

        self.setCentralWidget(central)
        self.setStatusBar(InventoryStatusBar())
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background: #f4f6fa; }
            QWidget { color: #202939; font-size: 13px; }
            #appTitle { color: #172b4d; }
            #subtitle { color: #667085; }
            #formCard { background: white; border: 1px solid #dce2ea;
                        border-radius: 10px; }
            QLineEdit, QComboBox, QSpinBox {
                background: white; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 7px; min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #356ae6;
            }
            QTableWidget {
                background: white; alternate-background-color: #f8fafc;
                border: 1px solid #dce2ea; border-radius: 8px;
                gridline-color: #e7ebf0;
            }
            QHeaderView::section {
                background: #eaf0fa; color: #344054;
                border: none; padding: 9px; font-weight: bold;
            }
            QPushButton {
                background: #356ae6; color: white; border: none;
                border-radius: 6px; padding: 7px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #2456c7; }
            QPushButton[role="secondary"] {
                background: #e8edf5; color: #26364d;
            }
            QPushButton[role="secondary"]:hover { background: #d8e0ed; }
            QPushButton[role="danger"] { background: #c93636; }
            QPushButton[role="danger"]:hover { background: #a92424; }
            QProgressBar {
                border: 1px solid #dce2ea; border-radius: 6px;
                background: white; text-align: center; min-height: 20px;
            }
            QProgressBar::chunk { background: #4b9b75; border-radius: 5px; }
            QStatusBar { background: #eaf0fa; color: #344054; }
        """)

    def _refresh_table(self, _text: str = "") -> None:
        products = self._inventory.find(self._search.text() if hasattr(self, "_search") else "")
        self._table.setRowCount(0)
        for product in products:
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = (
                product.product_id,
                product.name,
                product.category,
                f"{product.price:,.2f}",
                str(product.quantity),
                f"{product.total_value:,.2f}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                self._table.setItem(row, column, item)
        self._update_summary()

    def _update_summary(self) -> None:
        if not hasattr(self, "_summary_label"):
            return
        self._summary_label.setText(
            f"Позиций: {len(self._inventory.products)}\n"
            f"Остаток: {self._inventory.total_items} шт.   •   "
            f"Стоимость: {self._inventory.total_value:,.2f} ₽"
        )
        max_value = max(self._inventory.total_items, 1)
        self._stock_bar.setValue(min(100, int(self._inventory.total_items / max_value * 100))) if hasattr(self, "_stock_bar") else None

    def _selected_product_id(self) -> str | None:
        selected = self._table.selectionModel().selectedRows()
        if not selected:
            return None
        item = self._table.item(selected[0].row(), 0)
        return item.text() if item else None

    def _load_selected_to_form(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            return
        for product in self._inventory.products:
            if product.product_id == product_id:
                self._id_input.setText(product.product_id)
                self._name_input.setText(product.name)
                self._category_input.setCurrentText(product.category)
                self._price_input.setText(str(product.price))
                self._quantity_input.setValue(product.quantity)
                return

    def _add_product(self) -> None:
        try:
            price_text = self._price_input.text().strip().replace(",", ".")
            if not price_text:
                raise ValueError("Укажи цену товара")
            product = Product(
                self._id_input.text().strip(),
                self._name_input.text(),
                self._category_input.currentText(),
                float(price_text),
                self._quantity_input.value(),
            )
            self._inventory.add(product)
            self._save_inventory(silent=True)
            self._refresh_table()
            self._clear_form()
            self.statusBar().showMessage("Товар добавлен", 4000)
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, "Не удалось добавить товар", str(error))

    def _adjust_selected(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(self, "Выбор товара", "Сначала выбери товар в таблице.")
            return
        current_quantity = self._quantity_input.value()
        target = next((p for p in self._inventory.products if p.product_id == product_id), None)
        if target is None:
            return
        delta = current_quantity - target.quantity
        try:
            self._inventory.change_quantity(product_id, delta)
            self._save_inventory(silent=True)
            self._refresh_table()
            self.statusBar().showMessage("Количество товара обновлено", 4000)
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка", str(error))

    def _delete_selected(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.information(self, "Выбор товара", "Выбери строку для удаления.")
            return
        answer = QMessageBox.question(
            self, "Подтверждение", f"Удалить товар {product_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._inventory.remove(product_id)
            self._save_inventory(silent=True)
            self._refresh_table()
            self._clear_form()
            self.statusBar().showMessage("Товар удалён", 4000)

    def _clear_form(self) -> None:
        self._id_input.clear()
        self._name_input.clear()
        self._price_input.clear()
        self._quantity_input.setValue(1)
        self._category_input.setCurrentIndex(0)
        self._table.clearSelection()

    def _save_inventory(self, silent: bool = False) -> None:
        try:
            self._inventory.save()
            if not silent:
                self.statusBar().showMessage(f"Склад сохранён в {DATA_FILE.name}", 5000)
        except OSError as error:
            QMessageBox.critical(self, "Ошибка сохранения", str(error))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist inventory and append the required login session report."""
        self._save_inventory(silent=True)
        try:
            is_new = not REPORT_FILE.exists()
            with REPORT_FILE.open("a", encoding="utf-8") as report:
                if is_new:
                    report.write("+-----------------------------------------------+\n")
                    report.write("| login         | time_in           | time_out          |\n")
                    report.write("|---------------|-------------------|-------------------|\n")
                report.write(
                    f"| {self._login:<13} | {self._time_in:<17} | {now_text():<17} |\n"
                )
                report.write("+-----------------------------------------------+\n")
        except OSError as error:
            QMessageBox.warning(self, "Ошибка отчёта", f"Не удалось сохранить отчёт:\n{error}")
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Warehouse Desk")
    window = InventoryMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
