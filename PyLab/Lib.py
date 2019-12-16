from PyQt5.QtCore import (Qt)
from PyQt5.QtWidgets import (QApplication, QLineEdit, QPushButton, QComboBox, QCheckBox)
from PyQt5.QtGui import (QDoubleValidator, QIntValidator)


class MyComboBox(QComboBox):
    def __init__(self, *args, items=[], current_text=None, current_index=None,
                 current_text_changed_handler=None,
                 current_index_changed_handler=None,
                 min_width=None, max_width=None, **kwargs):
        super(MyComboBox, self).__init__(*args, **kwargs)
        self.addItems(items)
        if current_text:
            self.setCurrentText(current_text)
        elif current_index:
            self.setCurrentIndex(current_index)
        if current_text_changed_handler:
            self.currentTextChanged.connect(current_text_changed_handler)
        if current_index_changed_handler:
            self.currentTextChanged.connect(current_index_changed_handler)
        if min_width:
            self.setMinimumWidth(min_width)
        if max_width:
            self.setMaximumWidth(max_width)

    def setValue(self, value):
        self.setCurrentText(value)

    def getValue(self):
        return self.currentText()


class MyPushButton(QPushButton):
    def __init__(self, *args, name='', handler=None, fixed_width=None, min_width=None, max_width=None, **kwargs):
        super(MyPushButton, self).__init__(*args, **kwargs)
        self.setText(name)
        self.clicked.connect(handler)
        if fixed_width:
            self.setFixedWidth(fixed_width)
        if min_width:
            self.setMinimumWidth(min_width)
        if max_width:
            self.setMaximumWidth(max_width)


class MyLineEdit(QLineEdit):
    def __init__(self, *args, name='',
                 text_changed_handler=None,
                 text_edited_handler=None,
                 editing_finished_handler=None,
                 min_width=None, max_width=None, **kwargs):
        super(MyLineEdit, self).__init__(*args, **kwargs)
        self.setText(name)
        if text_changed_handler:
            self.textChanged.connect(text_changed_handler)
        if text_edited_handler:
            self.textEdited.connect(text_edited_handler)
        if editing_finished_handler:
            self.editingFinished.connect(editing_finished_handler)
        if min_width:
            self.setMinimumWidth(min_width)
        if max_width:
            self.setMaximumWidth(max_width)

    def getValue(self):
        return self.text()


class MyCheckBox(QCheckBox):
    def __init__(self, *args, is_checked=False,
                 handler=None, fixed_width=None, min_width=None, max_width=None, **kwargs):
        super(MyCheckBox, self).__init__(*args, **kwargs)
        if len(args): # args[0] should be a name of checkbox
            self.name = args[0]
        else:
            self.name = None
        self.setChecked(is_checked)
        if handler:
            self.stateChanged.connect(handler)
        if min_width:
            self.setMinimumWidth(min_width)
        if max_width:
            self.setMaximumWidth(max_width)

    def getValue(self):
        return self.checkState()


class MyDoubleBox(QLineEdit):
    def __init__(self, *args, validator=QDoubleValidator(-999, 999, 3), value='-10', max_width=None,
                 min_width=None,
                 text_changed_handler=None, text_edited_handler=None, editing_finished_handler=None,
                 **kwargs):
        super(MyDoubleBox, self).__init__(*args, **kwargs)
        # if validator:
        # print(validator)
        self.setValidator(validator)
        self.decimals = validator.decimals()
        self.total_symbols = self.decimals + 1 + int(validator.bottom() < 0) +\
                             max([len(str(int(abs(validator.bottom())))),
                                  len(str(int(abs(validator.top()))))])
        self.text_mask = '%%0%d.%df' % (self.total_symbols, self.decimals)
        # print(self.text_mask)
        if type(value) in [int, float]:
            value = str(value)
        if self.validator().validate(value, 0):
            self._value = float(value)
            self.setText(self.text_mask % self._value)
        else:
            print("BAD VALUE", value)

        self.text_edited_handler = text_edited_handler
        self.textEdited.connect(self.text_edited)
        if text_changed_handler:
            self.textChanged.connect(text_changed_handler)
        if editing_finished_handler:
            self.editingFinished.connect(editing_finished_handler)
        if max_width:
            self.setMaximumWidth(max_width)
        if min_width:
            self.setMinimumWidth(min_width)


    def keyPressEvent(self, QKeyEvent):
        p = 0
        if QKeyEvent.key() == Qt.Key_Up:
            p = 1
        if QKeyEvent.key() == Qt.Key_Down:
            p = -1
        if p == 0:
            return super(MyDoubleBox, self).keyPressEvent(QKeyEvent)
        pos = self.cursorPosition()
        # print("position", pos)
        if pos < self.total_symbols-self.decimals:
            power = (self.total_symbols - self.decimals - 1) - pos
        elif pos > self.total_symbols-self.decimals:
            power = (self.total_symbols - self.decimals) - pos
        else:
            # cursor is before dot
            return
        value = self._value + p * pow(10, power)
        # print('Validator', self.validator().validate(self.text_mask%(value),0))
        if self.validator().validate(self.text_mask % value, 0)[0] == 2:
            self._value = value
            self.setText(self.text_mask % self._value)
        self.setCursorPosition(pos)

    def text_edited(self):
        if self.validator().validate(self.text(), 0):
            self._value = float(self.text())
            self.setText(self.text_mask % self._value)
        if self.text_edited_handler:
            self.text_edited_handler()

    def value(self):
        return self._value

    def setValue(self, value):
        if type(value) in [int,float]:
            value = str(value)
        if self.validator().validate(value, 0):
            self._value = float(value)
            self.setText(self.text_mask % self._value)
            return 0
        else:
            print('MyDoubleBox, value is not inside specified range. value=', value)
            return 1

    def getValue(self):
        return self._value


class MyIntBox(QLineEdit):
    def __init__(self, *args, validator=QIntValidator(-999, 999), value=-10, max_width=None,
                 min_width=None,
                 text_changed_handler=None,
                 text_edited_handler=None,
                 editing_finished_handler=None,
                 **kwargs):
        super(MyIntBox, self).__init__(*args, **kwargs)
        # if validator:
        self.setValidator(validator)
        self.total_symbols = int(validator.bottom() < 0) + max([len(str(int(abs(validator.bottom())))),
                                                                len(str(int(abs(validator.top()))))])
        self.text_mask = '%%0%dd' % self.total_symbols
        # print(self.text_mask)
        if type(value) in [int, float]:
            value = str(int(value))
        if self.validator().validate(value, 0):
            self._value = int(value)
            self.setText(self.text_mask % self._value)
        else:
            print("BAD VALUE", value)
        self.text_edited_handler = text_edited_handler
        self.textEdited.connect(self.text_edited)
        if text_changed_handler:
            self.textChanged.connect(text_changed_handler)
        if editing_finished_handler:
            self.editingFinished.connect(editing_finished_handler)
        if max_width:
            self.setMaximumWidth(max_width)
        if min_width:
            self.setMinimumWidth(min_width)


    def keyPressEvent(self, QKeyEvent):
        p = 0
        if QKeyEvent.key() == Qt.Key_Up:
            p = 1
        if QKeyEvent.key() == Qt.Key_Down:
            p = -1
        if p == 0:
            return super(MyIntBox, self).keyPressEvent(QKeyEvent)
        pos = self.cursorPosition()
        # print("position", pos)
        power = self.total_symbols - pos
        value = self._value + int(p * pow(10, power))
        # print('Validator', self.validator().validate(self.text_mask%(value),0))
        if self.validator().validate(self.text_mask % value, 0)[0] == 2:
            self._value = value
            self.setText(self.text_mask % self._value)
        self.setCursorPosition(pos)

    def text_edited(self):
        if self.validator().validate(self.text(), 0):
            self._value = int(self.text())
            self.setText(self.text_mask % self._value)
        if self.text_edited_handler:
            self.text_edited_handler()

    def value(self):
        return self._value

    def setValue(self, value):
        if type(value) in [int,float]:
            value = str(value)
        if self.validator().validate(value, 0):
            self._value = int(value)
            self.setText(self.text_mask % self._value)
            return 0
        else:
            print('MyIntBox, value is not inside specified range. value=', value)
            return 1

    def getValue(self):
        return self._value


if __name__ == '__main__':
    # folder = 'settings'
    import sys
    app = QApplication(sys.argv)
    ex = MyDoubleBox()
    ex.show()
    sys.exit(app.exec_())
