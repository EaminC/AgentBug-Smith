```
<file>gpt_engineer/core/default/steps.py</file>
<original>def salvage_correct_hunks(
    messages: List,
    files_dict: FilesDict,
    memory: BaseMemory,
) -> tuple[FilesDict, List[str]]:
    error_messages = []
    ai_response = messages[-1].content.strip()

    diffs = parse_diffs(ai_response)
    # validate and correct diffs

    for _, diff in diffs.items():
        # if diff is a new file, validation and correction is unnecessary
        if not diff.is_new_file():
            problems = diff.validate_and_correct(
                file_to_lines_dict(files_dict[diff.filename_pre])
            )
            error_messages.extend(problems)
    files_dict = apply_diffs(diffs, files_dict)
    memory.log(IMPROVE_LOG_FILE, "\n\n".join(x.pretty_repr() for x in messages))
    memory.log(DIFF_LOG_FILE, "\n\n".join(error_messages))
    return files_dict, error_messages
</original>
<patched>def salvage_correct_hunks(
    messages: List,
    files_dict: FilesDict,
    memory: BaseMemory,
) -> tuple[FilesDict, List[str]]:
    error_messages = []
    ai_response = messages[-1].content.strip()

    diffs = parse_diffs(ai_response)
    # validate and correct diffs

    for _, diff in diffs.items():
        # if diff is a new file, validation and correction is unnecessary
        if not diff.is_new_file():
            # Prevent KeyError if file missing from files_dict (e.g., environment yaml files)
            if diff.filename_pre not in files_dict:
                error_messages.append(f"Warning: File '{diff.filename_pre}' not found in files_dict during diff validation.")
                continue
            problems = diff.validate_and_correct(
                file_to_lines_dict(files_dict[diff.filename_pre])
            )
            error_messages.extend(problems)
    files_dict = apply_diffs(diffs, files_dict)
    memory.log(IMPROVE_LOG_FILE, "\n\n".join(x.pretty_repr() for x in messages))
    memory.log(DIFF_LOG_FILE, "\n\n".join(error_messages))
    return files_dict, error_messages
</patched>
```