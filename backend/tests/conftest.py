"""Test configuration that keeps the suite independent from local credentials."""

import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:password@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
