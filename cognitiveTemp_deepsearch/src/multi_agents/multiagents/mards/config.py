from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = "sk-1f72cfd14cb447f794cec45bad2e27ac"
    tavily_api_key: str = "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"
    deepseek_base_url: str = "https://api.deepseek.com/v1/chat/completions"
    deepseek_model: str = "deepseek-chat"
    log_level: str = "INFO"
    request_timeout: int = 120  # 增加到 120 秒
    max_retries: int = 3

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
