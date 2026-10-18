FROM python@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89
COPY --chmod=0755 codex /usr/local/bin/codex
COPY --chmod=0555 bwrap /usr/local/bin/codex-resources/bwrap
COPY --chmod=0555 guardian.py check.py transfer.py mcp.py /opt/youngcrow/
WORKDIR /
ENTRYPOINT ["/usr/local/bin/python3", "-I", "-B", "/opt/youngcrow/guardian.py"]
