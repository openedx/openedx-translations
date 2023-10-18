import sys
import os
import os.path
import subprocess


def get_translation_files(translation_directory):
    """
    List all translations '*.po' files in the specified directory.
    """
    po_files = []
    for root, _dirs, files in os.walk(translation_directory):
        for file_name in files:
            pofile_path = os.path.join(root, file_name)
            if file_name.endswith('.po') and '/en/LC_MESSAGES/' not in pofile_path:
                po_files.append(pofile_path)
    return po_files


def validate_translation_file(po_file):
    """
    Validate a translation file and return errors if any.

    This function combines both stderr and stdout output of the `msgfmt` in a
    single variable.
    """
    completed_process = subprocess.run(
        ['msgfmt', '-v', '--strict', '--check', po_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return {
        'valid': completed_process.returncode == 0,
        'output': completed_process.stdout + '\n' + completed_process.stderr
    }


def main():
    """
    Run msgfmt and print errors to stderr.
    """
    translations_valid = True

    po_files = get_translation_files('translations')
    for po_file in po_files:
        result = validate_translation_file(po_file)

        if result['valid']:
            print('VALID: ' + po_file)
            print(result['output'], '\n' * 2)
        else:
            print('INVALID: ' + po_file, file=sys.stderr)
            print(result['output'], '\n' * 2, file=sys.stderr)
            translations_valid = False

    print('-----------------------------------------')
    if translations_valid:
        print('SUCCESS: All translation files are valid.')
        exit_code = 0
    else:
        print('FAILURE: Some translations are invalid. Check the stderr for error messages.')
        exit_code = 1
    print('-----------------------------------------')

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
