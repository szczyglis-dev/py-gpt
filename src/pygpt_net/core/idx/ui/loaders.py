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

import json
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
                    kind = meta['type']
                    if kind == 'int':
                        value = int(value)
                    elif kind == 'float':
                        value = float(value)
                    elif kind == 'bool':
                        if value.strip().lower() not in ('true', 'false', '1', '0'):
                            raise ValueError(trans('web.loader.invalid.bool'))
                        value = value.strip().lower() in ('true', '1')
                    elif kind == 'list':
                        value = [item.strip() for item in value.split(',') if item.strip()]
                    elif kind == 'dict':
                        value = json.loads(value)
                        if not isinstance(value, dict):
                            raise ValueError(trans('web.loader.invalid.dict'))
                    result[key] = value
                except (ValueError, TypeError) as error:
                    self.window.core.debug.log(error)
                    self._validation_alert(node, trans('web.loader.invalid.field').format(
                        field=label, type=meta['type']))
                    return False, loader, {}, {}
            results.append(result)
        return True, loader, results[0], results[1]

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
            group = QVBoxLayout()
            group.setContentsMargins(5, 0, 5, 0)
            for key, meta in fields.items():
                meta = normalize_field(meta)
                option = LoaderField(self.window, f'web.loader.{loader}.{section}.{key}', meta)
                value = meta.get('value', meta.get('default', ''))
                if value is not None:
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value) if isinstance(value, dict) else ', '.join(map(str, value))
                    option.setText(str(value))
                label = QLabel()
                label.setWordWrap(True)
                label.setBuddy(option.input)
                help_label = HelpLabel('')
                # Keep the field above its input: no competing horizontal size
                # hints can squeeze the form into half the scroll viewport.
                group.addWidget(label)
                group.addWidget(option)
                group.addWidget(help_label)
                option._loader_field = (key, dict(meta), label, help_label)
                self._refresh_field(option)
                inputs[loader][key] = option
            widget = QWidget()
            widget.setLayout(group)
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
