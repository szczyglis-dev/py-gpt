# Application theme palette

Edit colors in `<theme>/app.xml`. QSS uses explicit `{APP_*}` placeholders:

| XML name | QSS token | Used for |
| --- | --- | --- |
| `appSurface` | `{APP_SURFACE}` | Application and structural backgrounds |
| `appControlBackground` | `{APP_CONTROL_BACKGROUND}` | Inputs and closed combo boxes |
| `appListBackground` | `{APP_LIST_BACKGROUND}` | Lists, tables and popups |
| `appTextColor` | `{APP_TEXT_COLOR}` | Normal text |
| `appMutedTextColor` | `{APP_MUTED_TEXT_COLOR}` | Help and secondary text |
| `appBorderColor` | `{APP_BORDER_COLOR}` | Controls and popup outlines |
| `appFocusBorderColor` | `{APP_FOCUS_BORDER_COLOR}` | Focused input outlines |
| `appFocusBackground` | `{APP_FOCUS_BACKGROUND}` | Focused input backgrounds |

The shared corner radius lives in the base `app.xml`: `appRadius` (10px),
used as `{APP_RADIUS}`.
A theme XML can override these with `<dimension>` entries.

These are template values expanded before Qt receives QSS, not CSS `var()` or
Qt `qproperty-*` values. `qproperty-*` still sets actual widget properties.
The existing `{QTMATERIAL_*}` placeholders remain supported.

Resolution order is shared dimensions, bundled Light/Dark compatibility
palette, bundled selected palette, then the selected profile XML. Missing
entries in legacy profile XMLs fall back to the current bundled theme; values
are rebuilt on every load and never inherited from the previous theme.

Shared geometry and focus rules belong in the base `app.css`. Component and
state-specific colors stay in theme files. The context list and file tree are
borderless; toolbox right-edge exceptions and compact composer tabs keep their
own rules. Tabs retain their Qt Material underline. The bottom chat input
keeps its normal background and border when focused. Flush toolbox controls
have neither rounded right corners nor a right border. Combo popup containers
paint the theme list background instead of relying on native transparency.
