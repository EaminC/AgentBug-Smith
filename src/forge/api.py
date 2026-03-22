import openai
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List, Dict, Optional

# Load .env: cwd first, then project root with override so project root wins
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"
_cwd_env = Path.cwd() / ".env"
if _cwd_env.exists():
    load_dotenv(_cwd_env)
if _env_path.exists():
    load_dotenv(_env_path, override=True)  # project root overrides shell and cwd


def _getenv_stripped(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    if v is None:
        return default
    return str(v).strip().strip('"').strip("'")


def _getenv_float(key: str, default: float) -> float:
    raw = _getenv_stripped(key)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _getenv_int(key: str, default: int) -> int:
    raw = _getenv_stripped(key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _print_llm_error(exc: BaseException, *, base_url: Optional[str] = None) -> None:
    """Print LLM failure; add hints for connection-type errors."""
    msg = str(exc).strip() or type(exc).__name__
    lines = [f"LLM call error: {msg}"]
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause is not None and str(cause).strip() and str(cause) != msg:
        lines.append(f"  caused by: {cause}")
    low = msg.lower()
    if any(
        x in low
        for x in ("connection", "connect", "network", "timed out", "timeout", "unreachable")
    ):
        lines.append(
            "  hint: check network/VPN; set HTTP_PROXY/HTTPS_PROXY if needed; "
            "ensure root `.env` has a reachable FORGE_BASE_URL and FORGE_API_KEY."
        )
        if base_url:
            lines.append(f"  current FORGE_BASE_URL: {base_url}")
    if _getenv_stripped("FORGE_DEBUG"):
        import traceback

        traceback.print_exc()
    print("\n".join(lines))


class LLMClient:
    """Unified LLM calling interface"""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM client.
        Base URL and API key come from ``.env`` (``FORGE_BASE_URL``, ``FORGE_API_KEY``).
        If ``model`` is passed, it **overrides** ``MODEL`` in the root ``.env``.
        """
        model_val = model or _getenv_stripped("MODEL", "OpenAI/gpt-4o")
        self.model = model_val or "OpenAI/gpt-4o"
        
        api_key = _getenv_stripped("FORGE_API_KEY")
        base_url = _getenv_stripped("FORGE_BASE_URL", "https://api.forge.tensorblock.co/v1") or "https://api.forge.tensorblock.co/v1"
        if not api_key:
            print(
                "warning: FORGE_API_KEY is not set; LLM calls may fail. "
                "Set it in the project root `.env`."
            )

        # Configure OpenAI for old version compatibility
        openai.api_key = api_key
        openai.api_base = base_url

        self._base_url = base_url
        timeout = _getenv_float("FORGE_TIMEOUT", 120.0)
        max_retries = _getenv_int("FORGE_MAX_RETRIES", 2)

        # Try to use new version if available
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                timeout=timeout,
                max_retries=max_retries,
            )
            self.use_new_api = True
        except (ImportError, TypeError):
            self.client = None
            self.use_new_api = False
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> str:
        """
        Call LLM for chat
        
        Args:
            messages: Message list, format: [{"role": "user", "content": "..."}]
            temperature: Generation temperature, default 0.7
            max_tokens: Maximum tokens, default None
            
        Returns:
            LLM response content
        """
        try:
            if self.use_new_api:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return completion.choices[0].message.content
            else:
                # Use old OpenAI API
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                
                completion = openai.ChatCompletion.create(**kwargs)
                return completion.choices[0].message.content
        except Exception as e:
            _print_llm_error(e, base_url=getattr(self, "_base_url", None))
            return ""

    def simple_chat(self,
                    user_message: str,
                    system_prompt: Optional[str] = None,
                    temperature: Optional[float] = None) -> str:
        """
        Simplified chat interface
        
        Args:
            user_message: User message
            system_prompt: System prompt, default None
            temperature: Generation temperature; default from .env AI_TEMPERATURE or 0.7
            
        Returns:
            LLM response content
        """
        if temperature is None:
            try:
                temperature = float((os.getenv("AI_TEMPERATURE") or "0.7").strip().strip('"').strip("'"))
            except (TypeError, ValueError):
                temperature = 0.7
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        return self.chat(messages, temperature=temperature)
    
    def list_models(self) -> List[str]:
        """
        List all available models
        
        Returns:
            List of model IDs
        """
        try:
            if self.use_new_api:
                models = self.client.models.list()
                return [model.id for model in models.data]
            else:
                # Old API doesn't support model listing the same way
                models = openai.Model.list()
                return [model.id for model in models.data]
        except Exception as e:
            print(f"Error getting model list: {e}")
            return []


# Test code
if __name__ == "__main__":
    llm = LLMClient()
    
    # Test simple chat
    response = llm.simple_chat("Hello!", system_prompt="You are a helpful assistant.")
    print(f"Response: {response}")
    
    # Test listing models
    models = llm.list_models()
    print(f"\nAvailable OpenAI models:")
    for model in models:
        if model.startswith("OpenAI/"):
            print(f"  - {model}")