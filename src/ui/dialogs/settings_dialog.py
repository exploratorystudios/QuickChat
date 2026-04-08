# Copyright 2025 Exploratory Studios
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QSpinBox, QCheckBox, QPushButton,
                               QFormLayout, QFrame)
from src.services.settings_manager import settings_manager
from src.services.ollama_client import ollama_service
from config.theme import DARK_THEME
import qasync

# Ordered list of (label, token_count) presets. 0 = sentinel for "Custom".
CONTEXT_PRESETS = [
    ("2K  (2,048)",    2048),
    ("4K  (4,096)",    4096),
    ("8K  (8,192)",    8192),
    ("16K (16,384)",  16384),
    ("32K (32,768)",  32768),
    ("64K (65,536)",  65536),
    ("128K (131,072)", 131072),
    ("Custom...",      0),
]

BATCH_SIZES = [128, 256, 512, 1024, 2048]

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(420, 600)
        self.setup_ui()
        # Load models asynchronously
        asyncio.create_task(self.load_models_async())
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        form_layout.addRow("Theme:", self.theme_combo)

        # Default Model (populated from detected models)
        self.model_input = QComboBox()
        self.model_input.setEditable(False)  # Read-only dropdown
        self.model_input.addItem("Loading models...")  # Placeholder
        self.model_input.currentTextChanged.connect(self._on_model_changed)
        form_layout.addRow("Default Model:", self.model_input)

        # Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        form_layout.addRow("Font Size:", self.font_size_spin)

        # Enter to Send
        self.enter_send_check = QCheckBox()
        form_layout.addRow("Enter to Send:", self.enter_send_check)

        # ── Context Size ──────────────────────────────────────────────────────
        ctx_row = QHBoxLayout()
        ctx_row.setSpacing(6)

        self.ctx_preset_combo = QComboBox()
        for label, _ in CONTEXT_PRESETS:
            self.ctx_preset_combo.addItem(label)
        self.ctx_preset_combo.currentTextChanged.connect(self._on_ctx_preset_changed)
        ctx_row.addWidget(self.ctx_preset_combo, 1)

        self.ctx_custom_spin = QSpinBox()
        self.ctx_custom_spin.setRange(512, 2_097_152)
        self.ctx_custom_spin.setSingleStep(512)
        self.ctx_custom_spin.setValue(8192)
        self.ctx_custom_spin.setSuffix(" tokens")
        self.ctx_custom_spin.hide()
        ctx_row.addWidget(self.ctx_custom_spin, 1)

        form_layout.addRow("Context Size:", ctx_row)

        # Model max label (shown below context row)
        self.ctx_max_label = QLabel("Model max: —")
        self.ctx_max_label.setStyleSheet("color: #888888; font-size: 11px;")
        form_layout.addRow("", self.ctx_max_label)
        # ─────────────────────────────────────────────────────────────────────

        layout.addLayout(form_layout)

        # ── Performance section ───────────────────────────────────────────────
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {DARK_THEME['border']};")
        layout.addWidget(separator)

        perf_header = QLabel("Performance")
        perf_header.setStyleSheet(
            f"color: {DARK_THEME['text_secondary']}; font-size: 11px; font-weight: 600;"
            " padding: 2px 0px;"
        )
        layout.addWidget(perf_header)

        perf_layout = QFormLayout()
        perf_layout.setSpacing(8)

        # GPU Layers
        self.gpu_layers_spin = QSpinBox()
        self.gpu_layers_spin.setRange(-1, 999)
        self.gpu_layers_spin.setSpecialValueText("Auto")   # shown when value == -1
        self.gpu_layers_spin.setToolTip(
            "Number of model layers to offload to GPU.\n"
            "Auto = let Ollama decide CPU/GPU placement.\n"
            "0 = CPU only.  N = offload exactly N layers."
        )
        perf_layout.addRow("GPU Layers:", self.gpu_layers_spin)

        # Batch Size
        self.batch_combo = QComboBox()
        for v in BATCH_SIZES:
            self.batch_combo.addItem(str(v), v)
        self.batch_combo.setToolTip(
            "Prompt batch size — larger values process the context faster\n"
            "but use more memory. 512 is a safe default."
        )
        perf_layout.addRow("Batch Size:", self.batch_combo)

        # FP16 KV Cache
        self.f16_kv_check = QCheckBox()
        self.f16_kv_check.setToolTip(
            "Store the KV cache in fp16 instead of fp32.\n"
            "Halves KV cache memory and is faster on most hardware."
        )
        perf_layout.addRow("FP16 KV Cache:", self.f16_kv_check)

        # Lock model in RAM
        self.mlock_check = QCheckBox()
        self.mlock_check.setToolTip(
            "Lock model weights in RAM so the OS cannot swap them out.\n"
            "Eliminates stutter on RAM-adequate systems.\n"
            "Leave off if you are low on memory."
        )
        perf_layout.addRow("Lock Model in RAM:", self.mlock_check)

        layout.addLayout(perf_layout)
        # ─────────────────────────────────────────────────────────────────────

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save_settings)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_THEME['background']};
                color: {DARK_THEME['text_primary']};
            }}
            QLabel {{
                color: {DARK_THEME['text_primary']};
            }}
            QCheckBox {{
                color: {DARK_THEME['text_primary']};
            }}
        """)

    # ── Model loading ─────────────────────────────────────────────────────────

    async def load_models_async(self):
        """Load available models from Ollama asynchronously."""
        try:
            models = await ollama_service.list_models()

            # Clear placeholder
            self.model_input.clear()

            if models:
                self.model_input.addItems(models)
                # Restore previously selected default model if it exists
                default_model = settings_manager.get("default_model", "llama3")
                index = self.model_input.findText(default_model)
                if index >= 0:
                    self.model_input.setCurrentIndex(index)
                else:
                    # If saved model not found, use first available
                    self.model_input.setCurrentIndex(0)
                # Trigger max-context fetch for the selected model
                self._on_model_changed(self.model_input.currentText())
            else:
                self.model_input.addItem("No models found")
        except Exception as e:
            print(f"[SettingsDialog] Error loading models: {e}")
            self.model_input.clear()
            self.model_input.addItem("Error loading models")

    # ── Context controls ──────────────────────────────────────────────────────

    def _on_ctx_preset_changed(self, text):
        """Show custom spinbox only when 'Custom...' is selected."""
        is_custom = text == "Custom..."
        self.ctx_custom_spin.setVisible(is_custom)

    def _on_model_changed(self, model_name):
        """Update the model-max label when the model dropdown changes."""
        if not model_name or model_name in ("Loading models...", "No models found", "Error loading models"):
            self.ctx_max_label.setText("Model max: —")
            return

        max_ctx = ollama_service.get_model_max_context(model_name)
        if max_ctx:
            self.ctx_max_label.setText(f"Model max: {max_ctx:,} tokens")
        else:
            self.ctx_max_label.setText("Model max: detecting…")
            asyncio.create_task(self._fetch_model_max(model_name))

    async def _fetch_model_max(self, model_name):
        """Fetch capabilities (and thus max_context) for a model async."""
        try:
            caps = await ollama_service.get_model_capabilities(model_name)
            max_ctx = caps.get('max_context')
            if max_ctx:
                self.ctx_max_label.setText(f"Model max: {max_ctx:,} tokens")
            else:
                self.ctx_max_label.setText("Model max: unknown")
        except Exception:
            self.ctx_max_label.setText("Model max: unknown")

    def _get_selected_context(self):
        """Return the numeric context size from the current UI state."""
        text = self.ctx_preset_combo.currentText()
        if text == "Custom...":
            return self.ctx_custom_spin.value()
        for label, value in CONTEXT_PRESETS:
            if label == text:
                return value
        return 8192  # Fallback

    # ── Settings load / save ──────────────────────────────────────────────────

    def load_settings(self):
        self.theme_combo.setCurrentText(settings_manager.get("theme", "dark"))
        # Default model will be set by load_models_async
        self.font_size_spin.setValue(settings_manager.get("font_size", 14))
        self.enter_send_check.setChecked(settings_manager.get("enter_to_send", True))

        saved_ctx = settings_manager.get("context_size", 8192)
        # Match saved value to a preset label
        matched = False
        for label, value in CONTEXT_PRESETS:
            if label == "Custom...":
                continue
            if value == saved_ctx:
                idx = self.ctx_preset_combo.findText(label)
                if idx >= 0:
                    self.ctx_preset_combo.setCurrentIndex(idx)
                matched = True
                break
        if not matched:
            # Select "Custom..." and set spinbox value
            idx = self.ctx_preset_combo.findText("Custom...")
            if idx >= 0:
                self.ctx_preset_combo.setCurrentIndex(idx)
            self.ctx_custom_spin.setValue(saved_ctx)
            self.ctx_custom_spin.show()

        # Performance
        self.gpu_layers_spin.setValue(settings_manager.get("num_gpu", -1))
        saved_batch = settings_manager.get("num_batch", 512)
        idx = self.batch_combo.findData(saved_batch)
        if idx >= 0:
            self.batch_combo.setCurrentIndex(idx)
        self.f16_kv_check.setChecked(settings_manager.get("f16_kv", True))
        self.mlock_check.setChecked(settings_manager.get("use_mlock", False))

    def save_settings(self):
        settings_manager.set("theme", self.theme_combo.currentText())
        settings_manager.set("default_model", self.model_input.currentText())
        settings_manager.set("font_size", self.font_size_spin.value())
        settings_manager.set("enter_to_send", self.enter_send_check.isChecked())
        settings_manager.set("context_size", self._get_selected_context())
        # Performance
        settings_manager.set("num_gpu", self.gpu_layers_spin.value())
        settings_manager.set("num_batch", self.batch_combo.currentData())
        settings_manager.set("f16_kv", self.f16_kv_check.isChecked())
        settings_manager.set("use_mlock", self.mlock_check.isChecked())
        self.accept()
