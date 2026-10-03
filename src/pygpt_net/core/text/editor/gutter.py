#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 10:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


LINE_NUMBER_PADDING = 10
LINE_NUMBER_TEXT_GAP = 5
LINE_NUMBER_FONT_SCALE = 0.85


class LineNumbers(QWidget):
    def number_font(self):
        font = self.parentWidget().font()
        if font.pixelSize() > 0:
            font.setPixelSize(max(1, round(font.pixelSize() * LINE_NUMBER_FONT_SCALE)))
        else:
            font.setPointSizeF(max(1, font.pointSizeF() * LINE_NUMBER_FONT_SCALE))
        return font

    def paintEvent(self, event):
        editor = self.parentWidget()
        painter = QPainter(self)
        dark = editor.palette().base().color().lightness() < 128
        transparent = self.property('transparent_background') is True
        background = editor.palette().base().color() if transparent else QColor('#292b2e' if dark else '#f0f1f2')
        painter.fillRect(event.rect(), background)
        painter.setFont(self.number_font())

        cursor = editor.textCursor()
        first = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end = max(cursor.selectionStart(), cursor.selectionEnd() - 1)
        last = editor.document().findBlock(end).blockNumber()
        block = editor.firstVisibleBlock()
        while block.isValid():
            rect = editor.blockBoundingGeometry(block).translated(editor.contentOffset())
            if rect.top() > event.rect().bottom():
                break
            if block.isVisible() and rect.bottom() >= event.rect().top():
                line_number = block.blockNumber() + 1
                current = first <= block.blockNumber() <= last
                marked = editor.is_line_marked(line_number)
                if marked:
                    painter.fillRect(
                        0,
                        round(rect.top()),
                        self.width(),
                        round(rect.height()),
                        QColor('#493f29' if dark else '#fff0cc'),
                    )
                if current and not transparent:
                    painter.fillRect(
                        0,
                        round(rect.top()),
                        self.width(),
                        round(rect.height()),
                        QColor('#3b424c' if dark else '#dce4ee'),
                    )
                if marked:
                    painter.fillRect(
                        0,
                        round(rect.top()),
                        3,
                        round(rect.height()),
                        QColor('#e5b85c' if dark else '#b87b18'),
                    )
                painter.setPen(QColor(
                    ('#eef2f7' if dark else '#28384a') if current
                    else ('#90949a' if dark else '#777c83')
                ))
                painter.drawText(
                    LINE_NUMBER_PADDING,
                    round(rect.top()),
                    self.width() - 2 * LINE_NUMBER_PADDING,
                    editor.fontMetrics().height(),
                    Qt.AlignRight | Qt.AlignVCenter,
                    str(line_number),
                )
            block = block.next()
