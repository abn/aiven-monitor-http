SET TIME ZONE 'UTC';

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.checks
(
  id     SERIAL PRIMARY KEY,
  type   TEXT  NOT NULL,
  config JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_check_type ON public.checks (type);
CREATE INDEX IF NOT EXISTS idx_check_http_url ON public.checks ((config ->> 'url')) WHERE type = 'http';

CREATE TABLE IF NOT EXISTS public.events
(
  id        UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
  timestamp TIMESTAMPTZ      DEFAULT now() NOT NULL,
  check_id  INTEGER REFERENCES public.checks (id),
  result    JSONB
);
