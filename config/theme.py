# Theme Colors and Styles

DARK_THEME = {
    "primary": "#0084FF",       # Messenger Blue
    "primary_dark": "#006BCE",
    "accent": "#F59E0B",
    "background": "#18191A",    # Messenger Dark BG
    "surface": "#242526",       # Messenger Dark Surface
    "surface_light": "#3A3B3C", # Messenger Dark Hover
    "chat_background": "#1C1E21", # Dark gray for chat area
    "text_primary": "#E4E6EB",
    "text_secondary": "#B0B3B8",
    "border": "#3E4042",
    "success": "#31A24C",
    "error": "#FA383E",
    "bubble_user": "#0084FF",
    "bubble_assistant": "#3E4042",
    "bubble_assistant_text": "#E4E6EB",  # Light text for dark bubbles
    "text_on_primary": "#FFFFFF",
    "input_bg": "#3A3B3C",
    "input_text": "#E4E6EB"
}

LIGHT_THEME = {
    "primary": "#0084FF",
    "primary_dark": "#006BCE",
    "accent": "#F59E0B",
    "background": "#FFFFFF",
    "surface": "#F0F2F5",
    "surface_light": "#E4E6EB",
    "chat_background": "#F8F9FA", # Light gray for chat area
    "text_primary": "#050505",
    "text_secondary": "#65676B",
    "border": "#CED0D4",
    "success": "#31A24C",
    "error": "#FA383E",
    "bubble_user": "#0084FF",
    "bubble_assistant": "#E4E6EB",  # Light gray for assistant messages
    "bubble_assistant_text": "#050505",  # Dark text for light bubbles
    "text_on_primary": "#FFFFFF",
    "input_bg": "#F0F2F5",
    "input_text": "#050505"
}

def get_stylesheet(theme_mode="dark"):
    colors = DARK_THEME if theme_mode == "dark" else LIGHT_THEME
    
    return f"""
    QMainWindow {{
        background-color: {colors['background']};
    }}
    
    QWidget {{
        color: {colors['text_primary']};
        font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 14px;
        font-weight: 400;
    }}
    
    /* Sidebar */
    QWidget#Sidebar {{
        background-color: {colors['background']};
        border-right: 1px solid {colors['border']};
    }}
    
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}
    
    QListWidget::item {{
        padding: 10px;
        border-radius: 8px;
        color: {colors['text_primary']};
    }}
    
    QListWidget::item:selected {{
        background-color: {colors['surface_light']};
        color: {colors['text_primary']};
    }}
    
    QListWidget::item:hover {{
        background-color: {colors['surface']};
    }}
    
    /* Chat Area */
    QWidget#ChatArea {{
        background-color: {colors['chat_background']};
    }}

    QWidget#MessageContainer {{
        background-color: {colors['chat_background']};
    }}

    /* Input Area */
    QWidget#InputArea {{
        background-color: {colors['background']};
        border-top: 1px solid {colors['border']};
    }}

    QTextEdit {{
        background-color: {colors['input_bg']};
        border: none;
        border-radius: 20px;
        padding: 10px 15px;
        color: {colors['input_text']};
        selection-background-color: {colors['primary']};
        selection-color: {colors['text_on_primary']};
    }}
    
    QLineEdit {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 6px 10px;
        color: {colors['text_primary']};
        selection-background-color: {colors['primary']};
        selection-color: {colors['text_on_primary']};
    }}
    
    QLineEdit:focus {{
        border: 1px solid {colors['primary']};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {colors['surface']};
        border: none;
        border-radius: 6px;
        padding: 8px 12px;
        color: {colors['text_primary']};
        font-weight: 600;
    }}
    
    QPushButton:hover {{
        background-color: {colors['surface_light']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['border']};
    }}
    
    QPushButton#PrimaryButton {{
        background-color: {colors['primary']};
        color: {colors['text_on_primary']};
    }}
    
    QPushButton#PrimaryButton:hover {{
        background-color: {colors['primary_dark']};
    }}

    /* Header */
    QWidget#Header {{
        background-color: {colors['background']};
        border-bottom: 1px solid {colors['border']};
    }}
    
    QComboBox {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 5px 10px;
        color: {colors['text_primary']};
    }}
    
    QComboBox:hover {{
        border: 1px solid {colors['primary']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 5px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {colors['text_primary']};
        width: 0;
        height: 0;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['primary']};
        selection-color: {colors['text_on_primary']};
        color: {colors['text_primary']};
        outline: none;
    }}
    
    QComboBox QAbstractItemView::item {{
        padding: 5px;
        color: {colors['text_primary']};
    }}
    
    QComboBox QAbstractItemView::item:hover {{
        background-color: {colors['surface_light']};
    }}
    
    /* Scroll Area */
    QScrollArea {{
        background-color: {colors['chat_background']};
        border: none;
    }}

    /* Scrollbars - Modern minimal style */
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 6px;
        margin: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: {colors['text_secondary']};
        min-height: 30px;
        border-radius: 3px;
        opacity: 0.5;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {colors['primary']};
        width: 8px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        border: none;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: transparent;
        height: 6px;
        margin: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: {colors['text_secondary']};
        min-width: 30px;
        border-radius: 3px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {colors['primary']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        border: none;
    }}

    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    
    /* Menus */
    QMenu {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 5px;
        color: {colors['text_primary']};
    }}
    
    QMenu::item {{
        padding: 8px 25px;
        border-radius: 4px;
        color: {colors['text_primary']};
    }}
    
    QMenu::item:selected {{
        background-color: {colors['primary']};
        color: {colors['text_on_primary']};
    }}
    
    /* Dialogs */
    QDialog {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}
    
    QLabel {{
        color: {colors['text_primary']};
        background: transparent;
    }}
    
    /* CheckBox */
    QCheckBox {{
        color: {colors['text_primary']};
        spacing: 8px;
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {colors['border']};
        background-color: {colors['surface']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {colors['primary']};
        border-color: {colors['primary']};
    }}
    
    QCheckBox::indicator:hover {{
        border-color: {colors['primary']};
    }}
    
    /* SpinBox */
    QSpinBox {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 5px;
        color: {colors['text_primary']};
    }}
    
    QSpinBox:focus {{
        border: 1px solid {colors['primary']};
    }}
    
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: transparent;
        border: none;
        width: 16px;
    }}
    
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {colors['surface_light']};
    }}
    
    QSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 6px solid {colors['text_primary']};
        width: 0;
        height: 0;
    }}
    
    QSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid {colors['text_primary']};
        width: 0;
        height: 0;
    }}
    
    /* MessageBox */
    QMessageBox {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}
    
    QMessageBox QLabel {{
        color: {colors['text_primary']};
    }}
    
    QMessageBox QPushButton {{
        min-width: 80px;
    }}
    
    /* InputDialog */
    QInputDialog {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}
    
    QInputDialog QLabel {{
        color: {colors['text_primary']};
    }}
    
    /* FileDialog */
    QFileDialog {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
    }}
    
    QFileDialog QLabel {{
        color: {colors['text_primary']};
    }}
    
    QFileDialog QPushButton {{
        min-width: 80px;
    }}
    """
