CREATE SEQUENCE "public"."options_cache_id_seq";

create table if not exists public.options_cache
(
    "id" INTEGER NOT NULL DEFAULT nextval('options_cache_id_seq'::regclass),
    "root" varchar(250),
    "stockPrice" real,
    "expirDate" INTEGER,
    "dte" INTEGER,
    "callMidIv" real,
    "callAskPrice" real,
    "putAskPrice" real,
    "created_at" timestamp with time zone not null default now()

);

ALTER SEQUENCE "public"."options_cache_id_seq" OWNED BY "public"."options_cache"."id";
CREATE UNIQUE INDEX options_cache_pkey ON public.options_cache USING btree (id);
CREATE INDEX ix_options_cache_id ON public.options_cache USING btree (id);
ALTER TABLE "public"."options_cache"
ADD CONSTRAINT "options_cache_pkey" PRIMARY KEY USING INDEX "options_cache_pkey";



create table if not exists public.options_ticker
(
    "root" varchar(250) NOT NULL
);


CREATE UNIQUE INDEX options_ticker_pkey ON public.options_ticker USING btree (root);
CREATE INDEX ix_options_ticker_root ON public.options_ticker USING btree (root);
ALTER TABLE "public"."options_ticker"
ADD CONSTRAINT "options_ticker_pkey" PRIMARY KEY USING INDEX "options_ticker_pkey";