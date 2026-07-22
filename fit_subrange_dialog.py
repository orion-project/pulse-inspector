from PySide6.QtWidgets import (
  QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QRadioButton, QMessageBox)

from consts import FitSubrangeMode

class FitSubrangeDialog(QDialog):

  def __init__(self, parent=None):
    super().__init__(parent)

    self.setWindowTitle("Fit Subrange")

    layout = QVBoxLayout(self)

    self.flag_percent = QRadioButton("Percent (%)")
    self.flag_offset = QRadioButton("Offset (mkm)")
    self.flag_delay = QRadioButton("Delay (fs)")
    self.editor = QLineEdit()

    buttons = QDialogButtonBox(
      QDialogButtonBox.StandardButton.Ok |
      QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(self.accept)
    buttons.rejected.connect(self.reject)

    layout.addWidget(self.flag_percent)
    layout.addWidget(self.flag_offset)
    layout.addWidget(self.flag_delay)
    layout.addSpacing(6)
    layout.addWidget(self.editor)
    layout.addSpacing(12)
    layout.addStretch()
    layout.addWidget(buttons)

  def run(self, mode: FitSubrangeMode, value: float) -> tuple[FitSubrangeMode, float]|None:
    self.flag_percent.setChecked(mode == FitSubrangeMode.percent)
    self.flag_offset.setChecked(mode == FitSubrangeMode.offset)
    self.flag_delay.setChecked(mode == FitSubrangeMode.delay)
    self.editor.setText(str(value))

    if self.exec() != QDialog.DialogCode.Accepted:
      return None

    new_mode = FitSubrangeMode.percent
    if self.flag_percent.isChecked():
      new_mode = FitSubrangeMode.percent
    elif self.flag_offset.isChecked():
      new_mode = FitSubrangeMode.offset
    elif self.flag_delay.isChecked():
      new_mode = FitSubrangeMode.delay

    try:
      new_value = float(self.editor.text().strip())
    except ValueError:
      QMessageBox.critical(self, self.windowTitle(), "Invalid numeric value")
      return None

    return (new_mode, new_value)
