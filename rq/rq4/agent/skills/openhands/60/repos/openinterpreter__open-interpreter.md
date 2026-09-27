# Repo identity

Open Interpreter: A command-line tool to communicate with AI models efficiently, focusing on cost management and tokens.\n
# Typical issue shape

Most issues tend to revolve around cost management, especially regarding token consumption with LLMs.\n
# Recurring fix patterns

1. Implement cost warning features when a high token count is detected.
2. Add commands for users to check current token usage.\n
# Files / modules that change most often

- README.md\n- interpreter/terminal_interface/magic_commands.py\n- interpreter/utils/count_tokens.py\n
# Pitfalls

- Users often forget to check their token limits before running intensive models like GPT-4, leading to unexpected charges.

# Test conventions

Tests should include scenarios for both positive and negative token usage cases. Ensure that cost warning functionalities trigger under the expected conditions.\n
# One concrete worked example

## Issue Title: High LLM Costs\n
**Link:** [High LLM Costs](https://github.com/openinterpreter/open-interpreter/issues/596)\n**Details:** The script should show pricing or warn the user about cost being incurred. OpenAI's billing limits don't work so it is easy to exceed your budget.\n
