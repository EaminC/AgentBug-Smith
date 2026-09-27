
# Repo identity
**Name:** MLE-Agent  
**URL:** [MLSysOps/MLE-agent](https://github.com/MLSysOps/MLE-agent)  
**Description:** MLE-Agent is a pairing LLM agent for machine learning engineers and researchers.  

# Typical issue shape
Most issues involve requests for enhancements and feature support, such as API integrations, performance improvements, and implementation of best practices for machine learning models.

# Recurring fix patterns
Common fixes include updating API integration logic, modifying model training parameters, and enhancing existing debugging methods to ensure compatibility with newer libraries.

# Files / modules that change most often
- `mle/agents/coder.py`  
- `mle/cli.py`  
- `mle/model/gemini.py`  

# Pitfalls
Issues often arise from unclear API specifications or outdated dependencies that lead to integration issues, so it's crucial to keep track of library changes.

# Test conventions
Testing is generally done via unit tests located in respective test directories and should validate that newly integrated features work correctly and yield expected results.

# One concrete worked example
**Issue Title:** "Gemini Support"  
**Issue URL:** [#166](https://github.com/MLSysOps/MLE-agent/issues/166)  
**Description:** Feature Request: Gemini API support.  
  
For more detailed information on what was changed, refer to the linked pull request [#230](https://github.com/MLSysOps/MLE-agent/pull/230).
