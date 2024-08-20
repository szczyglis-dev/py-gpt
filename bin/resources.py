import os


def generate_icons_file(source_dir, output_file):
    svg_files = [f for f in os.listdir(source_dir) if f.endswith('.svg')]
    svg_files.sort()

    qrc_content = '<RCC>\n'
    for svg_file in svg_files:
        file_path = os.path.join(source_dir, svg_file)
        qrc_content += '    <qresource prefix="/icons">\n'
        qrc_content += f'        <file alias="{svg_file}">{file_path}</file>\n'
        qrc_content += '    </qresource>\n'
    qrc_content += '</RCC>'

    with open(output_file, 'w') as file:
        file.write(qrc_content)
    print(f"Generated: {output_file}")

def generate_js_file(source_dir, output_file):
    js_files = [f for f in os.listdir(source_dir) if f.endswith('.js')]
    js_files.sort()

    qrc_content = '<RCC>\n'
    for js_file in js_files:
        file_path = os.path.join(source_dir, js_file)
        qrc_content += '    <qresource prefix="/js">\n'
        qrc_content += f'        <file alias="{js_file}">{file_path}</file>\n'
        qrc_content += '    </qresource>\n'
    qrc_content += '</RCC>'

    with open(output_file, 'w') as file:
        file.write(qrc_content)
    print(f"Generated: {output_file}")




if __name__ == '__main__':
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'icons')
    output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'icons.qrc')
    generate_icons_file(source_dir, output_file)

    source_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'js', 'highlight')
    output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'js.qrc')
    generate_js_file(source_dir, output_file)