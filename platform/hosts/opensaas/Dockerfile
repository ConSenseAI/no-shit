FROM node:24.14.1-bookworm-slim@sha256:e484ae3f1e3c378021c967fd42254f343c302a9263e412280eac32bf5bca7008

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/toolchain
COPY toolchain-package.json package.json
COPY toolchain-package-lock.json package-lock.json
RUN npm ci --ignore-scripts \
    && ln -s /opt/toolchain/node_modules/.bin/wasp /usr/local/bin/wasp \
    && npm cache clean --force

WORKDIR /opt/opensaas
COPY .run/source/template/app/ /opt/opensaas/
RUN DATABASE_URL=postgresql://opensaas:opensaas-local@db:5432/opensaas \
    wasp install
COPY container-entrypoint.sh /usr/local/bin/opensaas-entrypoint
RUN chmod 0755 /usr/local/bin/opensaas-entrypoint

EXPOSE 2369
ENTRYPOINT ["/usr/local/bin/opensaas-entrypoint"]
