# Clean environment for replay-2026-10-26/replay.sh (Parts A and B), linux/arm64.
# Base image pinned by digest; both JDKs are Eclipse Temurin release archives verified against the
# sha256 published next to each archive on the Adoptium GitHub release page (also returned by
# api.adoptium.net). Maven is not installed: the replay uses the project's Maven wrapper.
# wget is deliberately not installed (the recorded host had none, and mvnw picks wget before curl).
FROM --platform=linux/arm64 ubuntu:24.04@sha256:68ee22004a9109b44973313b02ff7b1de250f1de0f5ecb628d73f579aaff33ac

ARG JDK8_URL=https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u504-b01/OpenJDK8U-jdk_aarch64_linux_hotspot_8u504b01.tar.gz
ARG JDK8_SHA256=57b7ed8af9d48542bb49ff7894448040b17bea0a48b41677d11ecaec6129768d
ARG JDK11_URL=https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.32.1%2B1/OpenJDK11U-jdk_aarch64_linux_hotspot_11.0.32.1_1.tar.gz
ARG JDK11_SHA256=f27033e6f7523c1b0b2565a78e9c0e0abe5596a854ce00ca04ec1b06ece7a935

RUN set -eux; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl git python3 patch perl file procps; \
    rm -rf /var/lib/apt/lists/*; \
    ! command -v wget

RUN set -eux; \
    mkdir -p /opt/jdk8 /opt/jdk11; \
    curl -fsSL "$JDK8_URL" -o /tmp/jdk8.tar.gz; \
    echo "$JDK8_SHA256  /tmp/jdk8.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/jdk8.tar.gz -C /opt/jdk8 --strip-components=1; \
    curl -fsSL "$JDK11_URL" -o /tmp/jdk11.tar.gz; \
    echo "$JDK11_SHA256  /tmp/jdk11.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/jdk11.tar.gz -C /opt/jdk11 --strip-components=1; \
    rm -f /tmp/jdk8.tar.gz /tmp/jdk11.tar.gz; \
    /opt/jdk8/bin/javac -version; /opt/jdk11/bin/javac -version

ENV JAVA8_HOME=/opt/jdk8 \
    JAVA11_HOME=/opt/jdk11 \
    JDK8_URL=$JDK8_URL JDK8_SHA256=$JDK8_SHA256 JDK11_URL=$JDK11_URL JDK11_SHA256=$JDK11_SHA256 \
    LANG=C.UTF-8 TZ=UTC

COPY in_container.sh /usr/local/bin/in_container.sh
RUN chmod 755 /usr/local/bin/in_container.sh
WORKDIR /
ENTRYPOINT ["/usr/local/bin/in_container.sh"]
