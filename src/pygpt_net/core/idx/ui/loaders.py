#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

import copy
import json

from PySide6.QtCore import QTimer
from typing import Dict, Tuple, Any, Optional

from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget, QMessageBox

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.provider.loaders.base import normalize_field
from .field import LoaderField
from pygpt_net.utils import trans


class Loaders:
    def __init__(self, window=None):
        """
        UI - loaders components

        :param window: Window instance
        """
        self.window = window
        self._dirty = False
        self._save_timer = QTimer(window if isinstance(window, QWidget) else None)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.flush)

    def handle_options(
            self,
            select_loader,
            prefix_options,
            prefix_config
    ) -> Tuple[bool, Optional[str], Dict[str, Any], Dict[str, Any]]:
        """
        Handle options

        :param select_loader: loader selection
        :param prefix_options: prefix for options
        :param prefix_config: prefix for config
        :return: bool, loader name, input_params, input_config
        """
        loader = select_loader.get_value()
        if not loader:
            return False, loader, {}, {}
        indexing = self.window.core.idx.indexing
        schemas = (
            (prefix_options, indexing.get_external_instructions().get(loader, {}).get('args', {})),
            (prefix_config, indexing.get_external_config().get(loader, {})),
        )
        results = []
        for prefix, fields in schemas:
            result = {}
            for key, meta in fields.items():
                meta = normalize_field(meta)
                node = self.window.ui.nodes.get(f'{prefix}.{loader}.{key}')
                value = node.text() if node is not None else ''
                label = trans(meta.get('label', key), domain=meta.get('_locale_domain'))
                if not value.strip():
                    if meta.get('required'):
                        self._validation_alert(node, trans('web.loader.required').format(field=label))
                        return False, loader, {}, {}
                    continue
                try:
                    value = self._parse_value(value, meta)
                    result[key] = value
                except (ValueError, TypeError) as error:
                    self.window.core.debug.log(error)
                    self._validation_alert(node, trans('web.loader.invalid.field').format(
                        field=label, type=meta['type']))
                    return False, loader, {}, {}
            results.append(result)
        for prefix, fields in schemas:
            for key, meta in fields.items():
                node = self.window.ui.nodes.get(f'{prefix}.{loader}.{key}')
                if node is not None:
                    section = 'option' if prefix == prefix_options else 'config'
                    self._remember_field(loader, section, key, normalize_field(meta), node.text())
        self.flush()
        return True, loader, results[0], results[1]

    @staticmethod
    def _parse_value(value, meta):
        kind = meta['type']
        if kind == 'int':
            return int(value)
        if kind == 'float':
            return float(value)
        if kind == 'bool':
            if value.strip().lower() not in ('true', 'false', '1', '0'):
                raise ValueError(trans('web.loader.invalid.bool'))
            return value.strip().lower() in ('true', '1')
        if kind == 'list':
            return [item.strip() for item in value.split(',') if item.strip()]
        if kind == 'dict':
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError(trans('web.loader.invalid.dict'))
            return parsed
        return value

    def _remember_field(self, loader, section, key, meta, text):
        if not hasattr(self.window.core, 'config'):
            return
        config = self.window.core.config
        if section == 'option':
            saved = config.get('llama.hub.loaders.options', {})
            saved = copy.deepcopy(saved) if isinstance(saved, dict) else {}
            saved.setdefault(loader, {})[key] = text
            config.set('llama.hub.loaders.options', saved)
        else:
            try:
                value = self._parse_value(text, meta) if text.strip() else None
            except (ValueError, TypeError):
                return  # Keep the last valid global setting while editing a number/JSON.
            self.window.core.idx.indexing.update_loader_args(
                loader, {key: value} if value is not None else {},
                remove=() if value is not None else (key,),
            )
        # Keep both already-created forms in sync without emitting edit signals.
        for prefix in ('dialog.url.loader', 'tool.indexer.web.loader'):
            node = self.window.ui.nodes.get(f'{prefix}.{section}.{loader}.{key}')
            if isinstance(node, LoaderField) and node.text() != text:
                node.setText(text)
        self._dirty = True
        self._save_timer.start()

    def flush(self):
        """Persist edits, including when the attachment dialog is dismissed."""
        self._save_timer.stop()
        if self._dirty:
            self.window.core.config.save()
            self._dirty = False

    def restore_fields(self, prefix_options, prefix_config):
        for section, prefix in (('option', prefix_options), ('config', prefix_config)):
            for name, node in self.window.ui.nodes.items():
                if name.startswith(prefix + '.') and isinstance(node, LoaderField):
                    loader, key = name[len(prefix) + 1:].split('.', 1)
                    value, found = self._saved_value(loader, section, key)
                    if found:
                        node.setText(self._field_text(value))

    def _saved_value(self, loader, section, key):
        if section == 'option':
            saved = self.window.core.config.get('llama.hub.loaders.options', {})
            values = saved.get(loader, {}) if isinstance(saved, dict) else {}
        else:
            values = self.window.core.idx.indexing.get_loader_arguments(loader, 'web')
        return (values.get(key), key in values) if isinstance(values, dict) else (None, False)

    @staticmethod
    def _field_text(value):
        if value is None:
            return ''
        if isinstance(value, dict):
            return json.dumps(value)
        if isinstance(value, list):
            return ', '.join(map(str, value))
        return str(value)

    def _validation_alert(self, node, message):
        parent = node.window() if isinstance(node, QWidget) else self.window
        QMessageBox.warning(parent, trans('web.loader.validation.title'), message)
        if node is not None:
            node.setFocus()

    def setup_loader_options(self):
        """Build source fields using the same schema as the indexer."""
        schemas = self.window.core.idx.indexing.get_external_instructions()
        fields = {
            loader: {key: dict(meta, _locale_domain=meta.get('_locale_domain', schema.get('_locale_domain')))
                     for key, meta in schema['args'].items()}
            for loader, schema in schemas.items()
        }
        return self._build_groups(fields, 'option')

    def setup_loader_config(self):
        """Build reader configuration fields."""
        return self._build_groups(self.window.core.idx.indexing.get_external_config(), 'config')

    def _build_groups(self, schemas, section):
        inputs, groups = {}, {}
        for loader, fields in schemas.items():
            inputs[loader] = {}
            if not fields:
                continue
            # Parent every field before locale refresh can make it visible.
            # Showing an unparented help label creates a native top-level window.
            widget = QWidget(self.window)
            group = QVBoxLayout(widget)
            group.setContentsMargins(5, 0, 5, 0)
            for key, meta in fields.items():
                meta = normalize_field(meta)
                option = LoaderField(self.window, f'web.loader.{loader}.{section}.{key}', meta)
                value, found = self._saved_value(loader, section, key)
                if not found:
                    value = meta.get('value', meta.get('default', ''))
                option.setText(self._field_text(value))
                option.changed.connect(
                    lambda text, loader=loader, section=section, key=key, meta=meta:
                    self._remember_field(loader, section, key, meta, text)
                )
                label = QLabel(widget)
                label.setWordWrap(True)
                label.setBuddy(option.input)
                help_label = HelpLabel('', widget)
                # Keep the field above its input: no competing horizontal size
                # hints can squeeze the form into half the scroll viewport.
                group.addWidget(label)
                group.addWidget(option)
                group.addWidget(help_label)
                option._loader_field = (key, dict(meta), label, help_label)
                self._refresh_field(option)
                inputs[loader][key] = option
            groups[loader] = widget
        return inputs, groups

    def _refresh_field(self, option):
        key, meta, label, help_label = option._loader_field
        domain = meta.get('_locale_domain')
        text = trans(meta.get('label', key), domain=domain)
        label.setText(text + (' *' if meta.get('required') else ''))
        label.setToolTip(key)
        description = trans(meta['description'], domain=domain) if meta.get('description') else ''
        help_label.setText(description)
        help_label.setVisible(bool(description))
        option.update_locale(label.text(), description)

    def update_locale(self):
        """Refresh both live forms without replacing inputs or their values."""
        for node in list(self.window.ui.nodes.values()):
            if isinstance(node, LoaderField) and hasattr(node, '_loader_field'):
                self._refresh_field(node)
