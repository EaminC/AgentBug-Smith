
# Repo identity
Repo Name: gpt-engineer
[![GitHub Repo stars](https://img.shields.io/github/stars/gpt-engineer-org/gpt-engineer?style=social)](https://github.com/gpt-engineer-org/gpt-engineer)
## Typical issue shape
- Missing feature support
- Incorrect behavior under certain conditions
- Dependency issues

## Recurring fix patterns
- Update dependencies (langchain, e.g.)
- Adjust method or class parameters in core files

## Files / modules that change most often
- `gpt_engineer/core/ai.py`
- `gpt_engineer/applications/cli/main.py`
## Pitfalls
- Not validating input parameters leading to runtime errors
- Ignoring dependency changes in release notes

## Test conventions
- Use pytest for testing
- Create unit tests for core functionality

## One concrete worked example

### Title: Missing support for the vision capabilities in the new model gpt-4-turbo
**Issue link**: https://github.com/AntonOsika/gpt-engineer/issues/1112
