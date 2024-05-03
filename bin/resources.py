import os


def generate_qrc_file(source_dir, output_file):
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


source_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'data', 'icons')
output_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'pygpt_net', 'icons.qrc')

if __name__ == '__main__':
    generate_qrc_file(source_dir, output_file)