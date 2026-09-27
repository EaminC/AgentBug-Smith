# Repo Identity

**Aider-AI/aider** - AI Pair Programming in Your Terminal. Aider pairs with LLMs to kickstart new projects or enhance existing codebases.

## Typical Issue Shape
Typical issues revolve around model integration errors, especially involving Vertex AI models failing with `litellm.BadRequestError` due to incorrect model name formatting.

## Recurring Fix Patterns
1. Normalize model names to match expected formats (e.g., removing or replacing terms like "-language-models/").
2. Implement checks in model constructors to ensure stability and proper error handling.

## Files / Modules that Change Most Often
- `aider/models.py`
- `tests/basic/test_coder.py`
- Configuration files related to model settings. 

## Pitfalls
- Overlooking model name normalization can lead to significant operational issues.
- Not regularly syncing with the latest model updates can result in outdated methods.

## Test Conventions
- Use `pytest` for testing local changes.
- Structure all tests under the `tests/` directory to maintain consistency.

## One Concrete Worked Example

**Issue Title:** "Vertex AI models can't use the weak or editor models?"

**Link:** [#4109](https://github.com/Aider-AI/aider/issues/4109)

**Description:** Users reported that operations using the Vertex AI model resulted in errors and incorrect model selection, which prompted a fix to the model name normalizations in `aider/models.py`.

