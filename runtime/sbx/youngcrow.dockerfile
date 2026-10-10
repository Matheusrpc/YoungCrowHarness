# Observed linux/amd64 shell-docker base. Other architectures are unverified.
FROM docker.io/docker/sandbox-templates@sha256:5bbe8539825fe1cace6dda2fb66919ef819324d905bea2795b8516aee0198222
USER root
COPY --chown=0:0 --chmod=0644 guardian.py launcher.py relay.py fixture.py /opt/youngcrow/
RUN install -d -o root -g root -m 0700 /var/lib/youngcrow/operations \
    && chmod 0755 /opt/youngcrow \
    && test -x /usr/bin/python3.14 \
    && test -x /usr/bin/docker
USER agent
WORKDIR /home/agent
# Default agent launch refuses: only the trusted root coordinator can use the launcher.
ENTRYPOINT ["/usr/bin/python3.14", "-I", "-B", "/opt/youngcrow/launcher.py"]
CMD []
