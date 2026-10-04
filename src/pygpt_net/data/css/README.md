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
