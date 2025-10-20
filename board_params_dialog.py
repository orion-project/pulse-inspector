import logging
from enum import Enum
from PySide6.QtWidgets import (
  QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QSpinBox, QCheckBox,
  QComboBox, QLineEdit, QDoubleSpinBox)

from board import board
from config import Parameter

log = logging.getLogger(__name__)

class EDITOR(Enum):
  str = 0
  int = 1
  float = 2
  bool = 3
  opts = 4

class BoardParamsDialog(QDialog):
  _editors = {}

  def __init__(self, parent=None):
    super().__init__(parent)

    self.setWindowTitle("Firmware Parameters")

    self.layout = QVBoxLayout(self)
    self.layout.setSpacing(2)

    for code in board.config.param_codes():
      spec = board.config.param_spec(code)
      self._create_param_editor(spec)

    buttons = QDialogButtonBox(
      QDialogButtonBox.StandardButton.Ok |
      QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(self.accept)
    buttons.rejected.connect(self.reject)
    self.layout.addSpacing(12)
    self.layout.addStretch()
    self.layout.addWidget(buttons)

    self._populate()

  def _create_param_editor(self, spec: Parameter):
    make_label = True
    warn_label = QLabel()
    warn_label.setVisible(False)
    warn_label.setWordWrap(True)
    warn_label.setStyleSheet("QLabel{color: red; font-size: 13px;}")
    if spec.options:
      if len(spec.options) == 2 \
        and spec.options[0] == "0" and spec.options[1] == "1":
        editor = QCheckBox(spec.title)
        self._editors[spec.name] = (EDITOR.bool, editor, warn_label)
        make_label = False
      else:
        editor = QComboBox()
        self._editors[spec.name] = (EDITOR.opts, editor, warn_label)
        for opt in spec.options:
          editor.addItem(opt)
    elif spec.range:
      if isinstance(spec.range[0], float):
        editor = QDoubleSpinBox()
        self._editors[spec.name] = (EDITOR.float, editor, warn_label)
        editor.setDecimals(spec.precision)
      elif isinstance(spec.range[0], int):
        editor = QSpinBox()
        self._editors[spec.name] = (EDITOR.int, editor, warn_label)
      else:
        raise Exception(f"Invalid range definition for parameter {spec.title}")
      editor.setMinimum(spec.range[0])
      editor.setMaximum(spec.range[1])
      if spec.step:
        editor.setSingleStep(spec.step)
    else:
      editor = QLineEdit()
      self._editors[spec.name] = (EDITOR.str, editor, warn_label)
    editor.setFixedHeight(30)
    if make_label:
      label = QLabel(spec.title)
      label.setWordWrap(True)
      self.layout.addWidget(label)
    self.layout.addWidget(editor)
    self.layout.addWidget(warn_label)
    self.layout.addSpacing(10)

  def _populate(self):
    warnings = {}
    for name in self._editors:
      (kind, editor, _) = self._editors[name]
      val = board.params.get(name)
      if val is None:
        warnings[name] = "Protocol mismatch: there is no such value in the firmware"
        continue
      if not isinstance(val, str):
        warnings[name] = f"Application error: all values expected to be string, but got {type(val)}"
        continue
      try:
        if kind == EDITOR.str:
          editor.setText(val)
        elif kind == EDITOR.int:
          int_val = int(val)
          spec = board.config.param_spec(name)
          if int_val < spec.range[0] or int_val > spec.range[1]:
            warnings[name] = f"Protocol mismatch: firmware returned a value that is out of range ({val})"
            continue
          editor.setValue(int_val)
        elif kind == EDITOR.float:
          float_val = float(val)
          spec = board.config.param_spec(name)
          if float_val < spec.range[0] or float_val > spec.range[1]:
            warnings[name] = f"Protocol mismatch: firmware returned a value that is out of range ({val})"
            continue
          editor.setValue(float_val)
        elif kind == EDITOR.bool:
          if val != "0" and val != "1":
            warnings[name] = f"Protocol mismatch: firmware returned a value that is not listed in the options ({val})"
            continue
          editor.setChecked(val == "1")
        elif kind == EDITOR.opts:
          spec = board.config.param_spec(name)
          if not val in spec.options:
            warnings[name] = f"Protocol mismatch: firmware returned a value that is not listed in the options ({val})"
            continue
          editor.setCurrentText(val)
        else:
          warnings[name] = "Application error: not implemented"
      except ValueError:
        warnings[name] = "Protocol mismatch: invalid value format"
        continue
    for name in warnings:
      (_, editor, warn_label) = self._editors[name]
      editor.setEnabled(False)
      warn_label.setText(warnings[name])
      warn_label.setVisible(True)

  def run(self) -> dict:
    if self.exec() != QDialog.DialogCode.Accepted:
      return None
    changes = {}
    for name in self._editors:
      (kind, editor, _) = self._editors[name]
      if not editor.isEnabled():
        continue
      val = None
      if kind == EDITOR.str:
        val = editor.text().strip()
      elif kind == EDITOR.int:
        val = str(editor.value())
      elif kind == EDITOR.float:
        spec = board.config.param_spec(name)
        val = f"{editor.value():.{spec.precision}f}"
      elif kind == EDITOR.bool:
        val = "1" if editor.isChecked() else "0"
      elif kind == EDITOR.opts:
        val = editor.currentText()
      if val is None:
        continue
      if val == board.params[name]:
        continue
      changes[name] = val
    return changes
