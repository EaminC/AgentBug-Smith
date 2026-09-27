The cause of the issue is that the current filename cleanup in `parse_chat` only removes a limited set of special characters (`[<>"|?*]`), but it does not remove extra formatting characters like backticks (` `) or square brackets (`[]`) if the model wraps filenames in these characters. Since the user reports seeing filenames surrounded by backticks or square brackets, these should be additionally stripped.

The fix is to enhance the sanitization of the extracted filename by stripping leading and trailing backticks and square brackets from the filename string after removing the disallowed characters. This will clean filenames like '`filename`' or '[filename]' to just `filename` and prevent output files with brackets or backticks in their names.

No changes are needed in `to_files` since it relies on `parse_chat` to generate correct file names. The changes should be restricted to the filename cleanup in `parse_chat` by adding a `.strip("`[]")` call after the current substitution.

---

```
<file>gpt_engineer/chat_to_files.py</file>
<original>
4 def parse_chat(chat):  # -> List[Tuple[str, str]]:
5     # Get all ``` blocks and preceding filenames
6     regex = r"(\S+?)\n```\S+\n(.+?)```"
7     matches = re.finditer(regex, chat, re.DOTALL)
8 
9     files = []
10     for match in matches:
11         # Strip the filename of any non-allowed characters and convert / to \
12         path = re.sub(r'[<>"|?*]', "", match.group(1))
13 
14         # Get the code
15         code = match.group(2)
16 
17         # Add the file to the list
18         files.append((path, code))
19 
20     # Get all the text before the first ``` block
21     readme = chat.split("```")[0]
22     files.append(("README.md", readme))
23 
24     # Return the files
25     return files
</original>
<patched>
4 def parse_chat(chat):  # -> List[Tuple[str, str]]:
5     # Get all ``` blocks and preceding filenames
6     regex = r"(\S+?)\n```\S+\n(.+?)```"
7     matches = re.finditer(regex, chat, re.DOTALL)
8 
9     files = []
10     for match in matches:
11         # Strip the filename of any non-allowed characters and convert / to \
12         path = re.sub(r'[<>"|?*]', "", match.group(1))
13         # Additionally remove surrounding backticks and square brackets
14         path = path.strip("`[]")
15 
16         # Get the code
17         code = match.group(2)
18 
19         # Add the file to the list
20         files.append((path, code))
21 
22     # Get all the text before the first ``` block
23     readme = chat.split("```")[0]
24     files.append(("README.md", readme))
25 
26     # Return the files
27     return files
</patched>
```