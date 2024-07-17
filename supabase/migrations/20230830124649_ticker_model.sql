create sequence "public"."ticker_id_seq";

create table "public"."ticker" (
    "id" integer not null default nextval('ticker_id_seq'::regclass),
    "symbol" character varying(250),
    "company_name" character varying,
    "logo" character varying,
    "option" boolean,
    "is_crypto" boolean,
    "__ts_vector__" tsvector generated always as (to_tsvector('english'::regconfig, (((symbol)::text || ' '::text) || (company_name)::text))) stored
);

alter sequence "public"."ticker_id_seq" owned by "public"."ticker"."id";
CREATE INDEX ix_ticker_id ON public.ticker USING btree (id);
CREATE INDEX ix_video___ts_vector__ ON public.ticker USING gin (__ts_vector__);
CREATE UNIQUE INDEX ticker_pkey ON public.ticker USING btree (id);
alter table "public"."ticker" add constraint "ticker_pkey" PRIMARY KEY using index "ticker_pkey";
