FROM almalinux:8 AS builder
WORKDIR /src
RUN dnf install -y python3.12-pip binutils && dnf clean all

COPY requirements-build.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements-build.txt

COPY bolt.py LICENSE ./
ARG TARGETARCH
RUN test "$TARGETARCH" = amd64 \
    && version="$(python3.12 -c 'from bolt import __version__; print(__version__)')" \
    && python3.12 -m PyInstaller --onefile --name bolt --runtime-tmpdir /run/user/0 \
    --add-data "LICENSE:." bolt.py \
    && mv dist/bolt "dist/bolt_v${version}_linux_${TARGETARCH}" \
    && binary="./dist/bolt_v${version}_linux_${TARGETARCH}" \
    && "$binary" --help \
    && test "$("$binary" --version)" = "bolt, version $version"

FROM scratch AS artifact
COPY --from=builder /src/dist/ /
