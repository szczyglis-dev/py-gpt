import os

def generate_resource_file(source_dirs, output_file, file_extension, resource_prefix, excluded = None):
    files = []
    for source_dir in source_dirs:
        for f in os.listdir(source_dir):
            if f.endswith(file_extension) or file_extension == '*':
                files.append((f, os.path.join(source_dir, f)))
    files.sort()

    qrc_content = '<RCC>\n'
    qrc_content += f'    <qresource prefix="{resource_prefix}">\n'
    root = os.path.join(os.path.dirname(os.path.join(__file__)), "..", "src", "pygpt_net")
    for file_name, file_path in files:
        if excluded and file_name in excluded:
            continue
        # remove abs path, keep relative path with prefix: ./data/js, ./data/icons, etc.
        rel_path = os.path.relpath(file_path, root)
        qrc_content += f'        <file alias="{file_name}">{rel_path}</file>\n'
    qrc_content += '    </qresource>\n'
    qrc_content += '</RCC>'

    with open(output_file, 'w') as file:
        file.write(qrc_content)
    print(f"Generated: {output_file}")

if __name__ == '__main__':
    # icons
    icons_source_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'icons')
    icons_output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'icons.qrc')
    generate_resource_file([icons_source_dir], icons_output_file, '.svg', '/icons')

    # javascript
    js_source_dirs = [
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'highlight'),
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'katex'),
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'markdown-it'),
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js'),
    ]
    js_output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'js.qrc')
    excluded = [
        "highlight.js" # exclude to leave only highlight.min.js
    ]
    generate_resource_file(js_source_dirs, js_output_file, '.js', '/js', excluded)

    # CSS
    css_source_dirs = [
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'katex'),
    ]
    css_output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'css.qrc')
    generate_resource_file(css_source_dirs, css_output_file, '.css', '/css')

    # fonts
    fonts_source_dirs = [
        os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'katex', 'fonts'),
    ]
    fonts_output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'fonts.qrc')
    generate_resource_file(fonts_source_dirs, fonts_output_file, '*', '/fonts')