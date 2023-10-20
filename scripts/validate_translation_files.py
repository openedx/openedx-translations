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
    )

    stdout = completed_process.stdout.decode(encoding='utf-8', errors='replace')
    stderr = completed_process.stderr.decode(encoding='utf-8', errors='replace')

    return {
        'valid': completed_process.returncode == 0,
        'output': f'{stdout}\n{stderr}',
    }


def main(translations_dir='translations'):
    """
    Run GNU gettext `msgfmt` and print errors to stderr.

    Returns integer OS Exit code:

      return 0 for valid translation.
      return 1 for invalid translations.
    """
    translations_valid = True

    invalid_lines = []

    po_files = get_translation_files(translations_dir)
    for po_file in po_files:
        result = validate_translation_file(po_file)

        if result['valid']:
            print('VALID: ' + po_file)
            print(result['output'], '\n' * 2)
        else:
            invalid_lines.append('INVALID: ' + po_file)
            invalid_lines.append(result['output'] + '\n' * 2)
            translations_valid = False

    # Print validation errors in the bottom for easy reading
    print('\n'.join(invalid_lines), file=sys.stderr)

    if translations_valid:
        print('-----------------------------------------')
        print('SUCCESS: All translation files are valid.')
        print('-----------------------------------------')
        exit_code = 0
    else:
        print('---------------------------------------', file=sys.stderr)
        print('FAILURE: Some translations are invalid.', file=sys.stderr)
        print('---------------------------------------', file=sys.stderr)
        exit_code = 1

    return exit_code


if __name__ == '__main__':
    sys.exit(main())  # pragma: no cover
