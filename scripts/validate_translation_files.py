"""
Validate translation files using GNU gettext `msgfmt` command.

This script is used to validate translation files in the Open edX platform and mark
invalid entries as fuzzy.
"""

import argparse
import os
import os.path
import subprocess
import sys


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
        'po_file': po_file,
        'valid': completed_process.returncode == 0,
        'output': f'{stdout}\n{stderr}'.strip(),
        'stdout': stdout,
        'stderr': stderr,
    }


def get_invalid_msgstr_lines(validation_stderr):
    """
    Parse the error output of `msgfmt` and return line numbers of invalid msgstr lines.
    """
    invalid_msgstr_lines = []
    for line in validation_stderr.splitlines():
        if '.po:' in line:
            _file_name, line_number, _rest = line.split(':', 2)
            invalid_msgstr_lines.append(int(line_number))
    return invalid_msgstr_lines


def get_invalid_msgid_lines(po_file, invalid_msgstr_lines):
    """
    Get the line numbers of invalid msgid lines by their msgstr line numbers.
    """
    with open(po_file, mode='r', encoding='utf-8') as f:
        pofile_lines = f.readlines()

    invalid_msgid_lines = []
    last_msgid_line = None
    for line_number, line_text in enumerate(pofile_lines, start=1):
        if line_text.startswith('msgid'):
            last_msgid_line = line_number

        if line_text.startswith('msgstr') and line_number in invalid_msgstr_lines:
            invalid_msgid_lines.append(last_msgid_line)

    return invalid_msgid_lines


def mark_invalid_entries_as_fuzzy(validation_result):
    """
    Mark invalid entries as fuzzy.
    """
    # Get line numbers of invalid msgstr lines
    invalid_msgstr_lines = get_invalid_msgstr_lines(validation_result['stderr'])
    invalid_msgid_lines = get_invalid_msgid_lines(
        validation_result['po_file'],
        invalid_msgstr_lines,
    )

    with open(validation_result['po_file'], mode='r', encoding='utf-8') as f:
        pofile_lines = f.readlines()

    with open(validation_result['po_file'], mode='w', encoding='utf-8') as f:
        for line_number, line_text in enumerate(pofile_lines, start=1):
            if line_number in invalid_msgid_lines:
                f.write('#, fuzzy\n')
            f.write(line_text)


def validate_translation_files(
    translations_dir='translations',
    mark_fuzzy=False,
):
    """
    Run GNU gettext `msgfmt` and print errors to stderr.

    Returns integer OS Exit code:

      return 0 for valid translation.
      return 1 for invalid translations.
    """
    translations_valid = True
    translations_fixed = False

    stderr_lines = []

    po_files = get_translation_files(translations_dir)
    for po_file in po_files:
        first_attempt = validate_translation_file(po_file)

        if first_attempt['valid']:
            print('VALID: ' + po_file)
            print(first_attempt['output'], '\n' * 2)
        else:
            if mark_fuzzy:
                mark_invalid_entries_as_fuzzy(first_attempt)

            second_attempt = validate_translation_file(po_file)

            if second_attempt['valid']:
                translations_fixed = True
                stderr_lines.append('FIXED: ' + po_file)
                stderr_lines.append('This file was invalid, but it was fixed by`make validate_translation_files`.')
                stderr_lines.append('Previous errors:')
                stderr_lines.append(first_attempt['output'] + '\n')
                stderr_lines.append('New output:')
                stderr_lines.append(second_attempt['output'] + '\n' * 2)
            else:
                stderr_lines.append('INVALID: ' + po_file)
                stderr_lines.append('Attempted to fix the file, but it is still invalid.')

                if mark_fuzzy:
                    stderr_lines.append('Previous errors:')
                else:
                    stderr_lines.append('Errors:')

                stderr_lines.append(first_attempt['output'] + '\n')

                if mark_fuzzy:
                    stderr_lines.append('New errors:')
                    stderr_lines.append(second_attempt['output'] + '\n' * 2)
                translations_valid = False

    # Print validation errors in the bottom for easy reading
    print('\n'.join(stderr_lines), file=sys.stderr)

    if translations_valid:
        exit_code = 0

        if translations_fixed:
            print('---------------------------------------------', file=sys.stderr)
            print('NOTICE:  Some translations were fixed.', file=sys.stderr)
            print('SUCCESS: All translation files are now valid.', file=sys.stderr)
            print('---------------------------------------------', file=sys.stderr)
        else:
            print('-----------------------------------------')
            print('SUCCESS: All translation files are valid.')
            print('-----------------------------------------')
    else:
        exit_code = 1
        print('---------------------------------------', file=sys.stderr)
        print('FAILURE: Some translations are invalid.', file=sys.stderr)
        print('---------------------------------------', file=sys.stderr)

    return exit_code


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mark-fuzzy', dest='mark_fuzzy', action='store_true', default=False)
    parser.add_argument('--dir', action='store', type=str, default='translations')
    args = parser.parse_args()
    sys.exit(validate_translation_files(
        translations_dir=args.dir,
        mark_fuzzy=args.mark_fuzzy,
    ))


if __name__ == '__main__':
    main()  # pragma: no cover
