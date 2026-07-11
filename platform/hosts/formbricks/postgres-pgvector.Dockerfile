# noshit-f1-formbricks — postgres:15-alpine + pgvector (built locally, base REUSED).
#
# Why this exists: Formbricks v3.16.1's baked Prisma migrations run
# `CREATE EXTENSION IF NOT EXISTS "vector"` (migration
# 20241017124431_add_documents_and_insights) and declare vector(512) columns on
# its Insight/Document tables — the extension is a HARD migration-time
# requirement, so the app will not boot against a stock postgres. The platform's
# resident postgres image (postgres:15-alpine) does not carry pgvector.
#
# Rather than pull the ~430 MB Debian `pgvector/pgvector:pg15` image (a second DB
# image, over this leg's disk budget), we build pgvector from source AGAINST THE
# RESIDENT postgres:15-alpine — its server headers (postgres.h) and PGXS ship in
# the image (verified). The final image is the pristine postgres:15-alpine with
# ~1 MB of extension artifacts copied in; every base layer is SHARED with the
# resident image, so the net new on-disk footprint is negligible. This is the
# faithful realization of the "reuse postgres:15-alpine" rule given the app's
# hard pgvector dependency. See README deviation #1.
#
# Pinned: postgres:15-alpine (PG 15.18) + pgvector v0.8.0. Build with:
#   sg docker -c "docker build -f postgres-pgvector.Dockerfile -t <tag> ."
# (setup.sh does this idempotently.)

ARG PG_IMAGE=postgres:15-alpine

# --- build stage: compile pgvector against the image's own PG15 via PGXS -------
FROM ${PG_IMAGE} AS build
ARG PGVECTOR_VERSION=v0.8.0
# build-base = gcc/make/musl-dev; no clang/llvm — we build with_llvm=no (no JIT
# bitcode), which pgvector fully supports. wget+ca-certificates to fetch source.
RUN apk add --no-cache --virtual .pgvector-build build-base wget ca-certificates \
 && wget -O /tmp/pgvector.tar.gz \
      "https://github.com/pgvector/pgvector/archive/refs/tags/${PGVECTOR_VERSION}.tar.gz" \
 && mkdir -p /tmp/pgvector \
 && tar -xzf /tmp/pgvector.tar.gz -C /tmp/pgvector --strip-components=1 \
 && cd /tmp/pgvector \
 && make with_llvm=no PG_CONFIG=/usr/local/bin/pg_config \
 && make with_llvm=no install PG_CONFIG=/usr/local/bin/pg_config \
 && apk del .pgvector-build

# --- final stage: pristine postgres:15-alpine + the compiled extension only ----
FROM ${PG_IMAGE}
# vector.so -> pkglibdir; vector.control + vector--*.sql -> sharedir/extension.
COPY --from=build /usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/vector.so
COPY --from=build /usr/local/share/postgresql/extension/vector.control /usr/local/share/postgresql/extension/vector.control
COPY --from=build /usr/local/share/postgresql/extension/vector--*.sql /usr/local/share/postgresql/extension/
