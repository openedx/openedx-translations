"""
Validate translation files using GNU gettext `msgfmt` command.
"""
from typing import List

from path import Path
from dataclasses import dataclass

import argparse
import subprocess
import sys
import textwrap
import traceback
import json

import icu
import i18n.validate
import re


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


def get_translation_files(translation_directory, specific_files: List = None) -> List[Path]:
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

            if file_path.exists() and _is_valid_translation_file(file_path):
                translation_files.append(file_path)
    else:
        # Original behavior - walk all files
        for file_ in translations_dir.walkfiles():
            if _is_valid_translation_file(file_):
                translation_files.append(file_)

    return translation_files


def _is_valid_translation_file(file_path):
    """
    Check if a file is a valid translation file.
    """
    file_str = str(file_path)
    if file_str.endswith('.po') and '/en/LC_MESSAGES/' not in file_str:
        return True
    if file_str.endswith('.json') and not file_str.endswith('transifex_input.json'):
        return True
    return False


def validate_translation_file(translation_file, error_missing_keys=False):
    if translation_file.endswith('.po'):
        return validate_po_translation_file(translation_file)
    elif translation_file.endswith('.json'):
        return validate_json_translation_file(translation_file, error_missing_keys)
    else:
        raise RuntimeError(f'File not supported: {translation_file}')


def validate_icu_message(message, locale):
    """Validate ICU MessageFormat string"""
    try:
        # Create MessageFormat object
        _fmt = icu.MessageFormat(message, icu.Locale(locale))
        return True, None
    except Exception as e:
        return False, format_exception(e)


def _extract_placeholder_names_from_pattern(message):
    """
    Extract placeholder names from a message using PyICU MessagePattern.
    """
    pattern = icu.MessagePattern(message)
    placeholders = set()

    # Iterate through pattern parts to find arguments
    for i in range(pattern.countParts()):
        part = pattern.getPart(i)
        part_type = pattern.getPartType(i)

        # ARG_START indicates the beginning of an argument/placeholder
        if part_type == icu.UMessagePatternPartType.ARG_START:
            # The next part should contain the argument name
            if i + 1 < pattern.countParts():
                next_part = pattern.getPart(i + 1)
                next_part_type = pattern.getPartType(i + 1)

                if next_part_type == icu.UMessagePatternPartType.ARG_NAME:
                    arg_name = pattern.getSubstring(next_part)
                    placeholders.add(arg_name)
                elif next_part_type == icu.UMessagePatternPartType.ARG_NUMBER:
                    # Handle numbered arguments like {0}, {1}
                    arg_number = str(next_part.getValue())
                    placeholders.add(arg_number)

    return placeholders


def _simple_validate_placeholders(source_message, target_message):
    """
    Simple first-pass placeholder validation using regex.
    """
    def extract_top_level_placeholders(message):
        """Extract only top-level placeholders, not nested braces inside ICU expressions."""
        placeholders = set()
        brace_depth = 0
        i = 0
        
        while i < len(message):
            if message[i] == '{':
                if brace_depth == 0:
                    # This is a top-level opening brace, extract the placeholder name
                    start = i + 1
                    # Find the placeholder name (everything until comma, space, or closing brace)
                    name_end = start
                    while name_end < len(message) and message[name_end] not in ',} \t\n':
                        name_end += 1
                    
                    if name_end > start:
                        placeholder_name = message[start:name_end]
                        # Only add if it's not empty and looks like a real placeholder
                        if placeholder_name and not placeholder_name.isspace():
                            placeholders.add(placeholder_name)
                
                brace_depth += 1
            elif message[i] == '}':
                brace_depth -= 1
            elif message[i] == '#':
                # The # character is a special placeholder in ICU MessageFormat
                placeholders.add('#')
            
            i += 1
        
        return placeholders

    source_placeholders = extract_top_level_placeholders(source_message)
    target_placeholders = extract_top_level_placeholders(target_message)

    if source_placeholders != target_placeholders:
        return False, (
            f"Placeholder mismatch: source has {sorted(source_placeholders)}, target has {sorted(target_placeholders)}"
        )

    return True, None


def validate_placeholders(source_message, target_message):
    """
    Validate placeholders using PyICU MessagePattern.
    """
    try:
        is_first_pass_valid, simple_validation_error = _simple_validate_placeholders(
            source_message,
            target_message,
        )

        if not is_first_pass_valid:
            # Fail quickly, if first pass catches errors to avoid any potential errors using PyICU
            return is_first_pass_valid, simple_validation_error

        source_placeholders = _extract_placeholder_names_from_pattern(source_message)
        target_placeholders = _extract_placeholder_names_from_pattern(target_message)

        if not source_placeholders and not target_placeholders:
            return True, None  # Neither has placeholders, so no placeholder issues

        if source_placeholders != target_placeholders:
            return False, (
                f"Placeholder mismatch: source has {sorted(source_placeholders)}, target has {sorted(target_placeholders)}"
            )

        return True, None
    except Exception as e:  # noqa
        return False, f'Error occurred while parsing the message "{format_exception(e)}"'


def validate_json_translation_messages(
    en_messages,
    target_locale,
    target_messages,
    error_missing_keys=False,
):
    """
    Validate parsed JSON translations according to ICU format.
    """
    errors = []

    for key, en_message in en_messages.items():
        if key not in target_messages:
            if error_missing_keys:
                errors.append(f"Missing key: '{target_locale}' -> '{key}' for message '{en_message}'")
            continue

        target_message = target_messages[key]

        # Validate source message
        en_valid, en_error = validate_icu_message(en_message, 'en')
        if not en_valid:
            errors.append(f"Invalid source message '{target_locale}' -> '{key}': '{en_message}' '{target_message}' {en_error}")
            continue

        # Validate target message
        target_valid, target_error = validate_icu_message(target_message, target_locale)
        if not target_valid:
            errors.append(f"Invalid target message '{target_locale}' -> '{key}': '{en_message}' '{target_message}' {target_error}")

        # Additional placeholder validation
        placeholder_valid, placeholder_error = validate_placeholders(en_message, target_message)
        if not placeholder_valid:
            errors.append(f"Placeholder validation failed for '{target_locale}' -> '{key}': '{en_message}' '{target_message}' {placeholder_error}")

        # # Validate plural rules
        # TODO: Needs validate_plurals
        # if not validate_plurals(en_message, target_message):
        #     errors.append(f"Invalid plural use in '{key}' between '{en_message}' and '{target_message}'")

    return ValidationResult(
        is_valid=not errors,
        output='\n'.join(errors),
    )


def validate_json_translation_file(translation_file, error_missing_keys=False):
    """Validate translation file against source"""
    en_file = translation_file.dirname() / '../transifex_input.json'

    if en_file.exists():
        # Gets 'ar' from 'ar.json'
        target_locale = str(translation_file.basename()).replace('.json', '')
        with open(en_file, 'r', encoding='utf-8') as f:
            en_messages = json.load(f)

        with open(translation_file, 'r', encoding='utf-8') as f:
            target_messages = json.load(f)

        return validate_json_translation_messages(
            en_messages=en_messages,
            target_locale=target_locale,
            target_messages=target_messages,
            error_missing_keys=error_missing_keys,
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
):
    """
    Run GNU gettext `msgfmt` and print errors to stderr.

    Returns integer OS Exit code:

      return 0 for valid translation.
      return 1 for invalid translations.
    """
    translations_valid = True

    invalid_lines = []

    translation_files = get_translation_files(translations_dir, specific_files)
    for f in translation_files:
        result = validate_translation_file(f, error_missing_keys)

        if result.is_valid:
            print('VALID: ' + f)
            print(result.output, '\n' * 2)
        else:
            invalid_lines.append('INVALID: ' + f)
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


def main():  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', action='store', type=str, default='translations',
                        help='Directory to search for translation files (default: translations)')
    parser.add_argument('--error-missing-keys', action='store_true', default=False,
                        help=(
                            'Treat missing keys in translation files as errors (default: False). '
                            'Right now only JSON files are supported for this check. '
                        ))
    parser.add_argument('files', nargs='*',
                        help='Test the provided specific files only.')
    args = parser.parse_args()
    sys.exit(validate_translation_files(
        translations_dir=args.dir,
        error_missing_keys=args.error_missing_keys,
        specific_files=args.files if args.files else None,
    ))


if __name__ == '__main__':
    main()  # pragma: no cover
