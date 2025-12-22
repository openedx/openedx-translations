"""
Validate translation files of different types.
"""
from typing import List

from path import Path
from dataclasses import dataclass

import argparse
import subprocess
import sys
import textwrap
import traceback
import shutil
import os

import i18n.validate


@dataclass
class ValidationResult:
    is_valid: bool = False
    output: str = ''
    skipped: bool = False


def format_exception(e):
    """
    Format exception for printing.
    """
    return f'{e} {traceback.format_exc()}'


def get_translation_files(translation_directory, specific_files: List = None, allowed_types=None) -> List[Path]:
    """
    List all translations '*.po' and '.json' files in the specified directory.
    If specific_files is provided, only return files that match those paths.
    """
    translation_files = []
    translations_dir = Path(translation_directory)

    if specific_files:
        # Convert to absolute paths and filter
        for file_path in specific_files:
            file_path = Path(file_path)

            if file_path.exists() and _is_valid_translation_file(file_path, allowed_types):
                translation_files.append(file_path)
    else:
        # Original behavior - walk all files
        for file_ in translations_dir.walkfiles():
            if _is_valid_translation_file(file_, allowed_types):
                translation_files.append(file_)

    return translation_files


def _is_valid_translation_file(file_path, allowed_types=None):
    """
    Check if a file is a valid translation file in the correct path.
    """
    file_str = str(file_path)

    if file_str.endswith('.po') and '/en/LC_MESSAGES/' not in file_str:
        if not allowed_types or 'po' in allowed_types:
            return True

    if file_str.endswith('.json') and not file_str.endswith('transifex_input.json'):
        if not allowed_types or 'json' in allowed_types:
            return True

    return False


def validate_translation_file(translation_file, error_missing_keys=False):
    """
    Validate a translation file of a supported type.

    Supported types:
        - .po Gettext PO files used in Python applications
        - .json ICU Unicode message files used in React.js applications
    """
    if translation_file.endswith('.po'):
        return validate_po_translation_file(translation_file)
    elif translation_file.endswith('.json'):
        return validate_json_translation_file(translation_file)
    else:
        raise RuntimeError(f'File not supported: {translation_file}')


def validate_json_translation_file(translation_file, error_missing_keys=False):
    """
    Validate a JSON translation file against source.
    """
    # The validation command is ran with the following parameters:
    #    npx @formatjs/cli verify --structural-equality --source-locale en en.json ar.json
    # This repository's structure uses transifex_input.json instead of en.json
    # Therefore it needs to be copied to .git-ignored temp. en.json file
    # so @formatjs/cli command can read it.
    en_file = translation_file.dirname() / '../transifex_input.json'
    required_temp_en_file_path = translation_file.dirname() / 'en.json'

    # Using realpath so the binary file is found even when changing directories in subprocess.
    formatjs_bin = (Path(__file__).parent.parent / 'node_modules/.bin/formatjs').realpath()

    if en_file.exists():
        shutil.copyfile(en_file, required_temp_en_file_path)

        is_valid = True
        output = ""

        extra_args = []
        if error_missing_keys:
            extra_args.append('--missing-keys')

        completed_process = subprocess.run(
            [formatjs_bin, 'verify', *extra_args,
                                 '--structural-equality', '--source-locale=en',
                                 'en.json', translation_file.basename()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=translation_file.dirname(),
        )

        os.unlink(required_temp_en_file_path)

        if completed_process.returncode != 0:
            is_valid = False

        verify_stdout = completed_process.stdout.decode(encoding='utf-8', errors='replace')
        verify_stderr = completed_process.stderr.decode(encoding='utf-8', errors='replace')
        output += f'{verify_stdout}\n{verify_stderr}'.strip() + '\n'

        return ValidationResult(
            is_valid=is_valid,
            output=output,
        )


    return ValidationResult(
        is_valid=False,
        output=(
            f'Missing "transifex_input.json" source file for {translation_file}. '
            f'This script assumes the latter is used in React.js apps. '
            f'If that is not true, the validate_translation_files.py needs to be updated. '
        )
    )


def validate_po_translation_file(po_file):
    """
    Validate a .po translation file and return errors if any.

    This function combines both stderr and stdout output of the `msgfmt` in a
    single variable.
    """
    is_valid = True
    output = ""

    completed_process = subprocess.run(
        ['msgfmt', '-v', '--strict', '--check', po_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if completed_process.returncode != 0:
        is_valid = False

    msgfmt_stdout = completed_process.stdout.decode(encoding='utf-8', errors='replace')
    msgfmt_stderr = completed_process.stderr.decode(encoding='utf-8', errors='replace')
    output += f'{msgfmt_stdout}\n{msgfmt_stderr}\n'

    try:
      problems = i18n.validate.check_messages(po_file)
    except Exception as e:
      output += f'{format_exception(e)}'
      is_valid = False
      problems = []
    if problems:
        is_valid = False

    id_filler = textwrap.TextWrapper(width=79, initial_indent="  msgid: ", subsequent_indent=" " * 9)
    tx_filler = textwrap.TextWrapper(width=79, initial_indent="  -----> ", subsequent_indent=" " * 9)
    for problem in problems:
        desc, msgid = problem[:2]
        output += f"{desc}\n{id_filler.fill(msgid)}\n"
        for translation in problem[2:]:
            output += f"{tx_filler.fill(translation)}\n"
        output += "\n"

    return ValidationResult(
        is_valid=is_valid,
        output=output,
    )


def validate_translation_files(
    translations_dir='translations',
    error_missing_keys=False,
    specific_files=None,
    allowed_types=None,
) -> int:
    """
    Validate translation files and print errors to stderr.

    Returns integer OS Exit code:

      return 0 for valid translation.
      return 1 for invalid translations.
    """
    translations_valid = True

    invalid_lines = []

    translation_files = get_translation_files(translations_dir, specific_files, allowed_types)
    for file_ in translation_files:
        result = validate_translation_file(file_, error_missing_keys)

        if result.is_valid:
            print('VALID: ' + file_)
            print(result.output, '\n' * 2)
        else:
            invalid_lines.append('INVALID: ' + file_)
            invalid_lines.append(result.output + '\n' * 2)
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


def parse_types_argument(parser, args) -> List[str]:
    """
    Parse allowed types from comma-separated string.
    """
    # import pdb; pdb.set_trace()
    allowed_types = [t.strip() for t in args.types.split(',') if t.strip()]

    # Validate allowed types
    valid_types = {'json', 'po'}
    invalid_types = set(allowed_types) - valid_types
    if invalid_types:
        parser.error(f"Invalid file types: {', '.join(invalid_types)}. Valid types are: {', '.join(valid_types)}")

    return allowed_types


def main():  # pragma: no cover
    """
    Parse command line arguments to validate the translation files.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', action='store', type=str, default='translations',
                        help='Directory to search for translation files (default: translations)')
    parser.add_argument('--error-missing-keys', action='store_true', default=False,
                        help=(
                            'Treat missing keys in translation files as errors (default: False). '
                            'Right now only JSON files are supported for this check. '
                        ))
    parser.add_argument('--types', action='store', type=str, default='',
                        help='Comma-separated list of file types to validate (default: json,po). Valid types: json, po')
    parser.add_argument('files', nargs='*',
                        help='Validate the specified files only. Leave empty to validate all files.')
    args = parser.parse_args()

    types_list = parse_types_argument(parser, args)

    sys.exit(validate_translation_files(
        translations_dir=args.dir,
        error_missing_keys=args.error_missing_keys,
        specific_files=args.files if args.files else None,
        allowed_types=types_list,
    ))


if __name__ == '__main__':
    main()  # pragma: no cover
