"""
Configuration management for JARVIS bot.
Loads settings from config.yaml and environment variables using Pydantic.
"""

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    
    provider: Literal["openai", "anthropic"] = Field(
        description="LLM provider to use"
    )
    model: str = Field(
        description="Model identifier (e.g., gpt-4o-mini, claude-3-5-haiku-20241022)"
    )
    
    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported."""
        if v not in ["openai", "anthropic"]:
            raise ValueError(f"Unsupported LLM provider: {v}")
        return v


class DiscordGatewayConfig(BaseModel):
    """Discord gateway configuration."""
    
    enabled: bool = Field(default=True, description="Enable Discord gateway")


class GatewaysConfig(BaseModel):
    """Gateway configurations."""
    
    discord: DiscordGatewayConfig = Field(default_factory=DiscordGatewayConfig)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    path: str = Field(default="jarvis.db", description="SQLite database file path")


class YAMLConfig(BaseModel):
    """Configuration loaded from config.yaml."""
    
    llm: LLMConfig
    gateways: GatewaysConfig = Field(default_factory=GatewaysConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


class EnvConfig(BaseSettings):
    """Configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    llm_api_key: str = Field(
        description="API key for LLM provider (OpenAI or Anthropic)"
    )
    discord_token: Optional[str] = Field(
        default=None,
        description="Discord bot token"
    )


class Config:
    """
    Main configuration class combining YAML and environment variables.
    
    Usage:
        config = Config.load()
        print(config.llm.provider)
        print(config.env.llm_api_key)
    """
    
    def __init__(self, yaml_config: YAMLConfig, env_config: EnvConfig):
        self.llm = yaml_config.llm
        self.gateways = yaml_config.gateways
        self.database = yaml_config.database
        self.env = env_config
    
    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """
        Load configuration from YAML file and environment variables.
        
        Args:
            config_path: Path to config.yaml file (default: "config.yaml")
            
        Returns:
            Config: Loaded configuration object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        # Load YAML config
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        
        yaml_config = YAMLConfig.model_validate(yaml_data)
        
        # Load environment variables
        env_config = EnvConfig()
        
        # Validate that required gateway tokens are present
        if yaml_config.gateways.discord.enabled and not env_config.discord_token:
            raise ValueError(
                "Discord gateway is enabled but DISCORD_TOKEN environment variable is not set"
            )
        
        return cls(yaml_config=yaml_config, env_config=env_config)
    
    def get_llm_api_key(self) -> str:
        """Get the API key for the configured LLM provider."""
        return self.env.llm_api_key
    
    def get_discord_token(self) -> str:
        """Get Discord bot token."""
        if not self.env.discord_token:
            raise ValueError("Discord token not configured")
        return self.env.discord_token
    
    def get_database_path(self) -> Path:
        """Get database file path as Path object."""
        return Path(self.database.path)
