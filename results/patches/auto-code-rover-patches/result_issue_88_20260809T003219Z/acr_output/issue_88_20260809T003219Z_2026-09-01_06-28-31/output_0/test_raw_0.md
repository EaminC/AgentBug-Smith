```python
# reproducer.py
def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)

import sys

def main():
    import agentscope
    from agentscope.agents import DialogAgent, UserAgent
    from agentscope.message import Msg
    from agentscope.pipelines.functional import sequentialpipeline

    agentscope.init(model_configs=[
        {
            "config_name": "qwen-vl-plus",
            "model_type": "dashscope_text_embedding",
            "model_name": "qwen-vl-plus",
            "api_key": "sk-df---314ae----------------------" 
        }
    ])

    agent_1 = DialogAgent(
        name="助手",
        sys_prompt="你是一位好帮手",
        model_config_name="qwen-vl-plus"
    )
    useragent = UserAgent()

    x = Msg(name='用户', content='帮我描述一下这个图片', url="https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg")

    try:
        # Do one step of the pipeline to trigger the call / error
        x = sequentialpipeline([agent_1, useragent])
    except Exception as e:
        print_stacktrace(e)
        # Check if this is the known 400 error about url
        err_msg = str(e)
        if "Status code: 400" in err_msg and "url error" in err_msg:
            # Issue reproduced
            raise AssertionError("Issue reproduced: 400 url error from qwen-vl-plus model") from e
        else:
            # Some other error - also raise
            raise

if __name__ == "__main__":
    sys.exit(main() or 0)
```
