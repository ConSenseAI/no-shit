# Fake-time sidecar (FIXTURES §2.1 rung 2). glibc base so libfaketime preloads.
# This is the ONE small build in the leg: a package install on a prebuilt image,
# no source compilation. Documenso's own image is musl/alpine and cannot host
# glibc libfaketime, which is exactly the deviation this sidecar works around.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends libfaketime ca-certificates \
 && ln -sf "$(find /usr/lib -name 'libfaketime.so.1' | head -n1)" /opt/libfaketime.so \
 && rm -rf /var/lib/apt/lists/*

COPY scheduler.py /scheduler.py

# LD_PRELOAD + the timestamp-file wiring are set in docker-compose.yml so the
# host can move the clock at runtime by writing data/faketime/faketimerc.
CMD ["python3", "/scheduler.py"]
