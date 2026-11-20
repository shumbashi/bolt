FROM ghcr.io/yt-dlp/manylinux2014_x86_64-shared@sha256:f8d174f295fae0c52b5d7686989b9f98268c296b130fca0063a8356de2324ff8 AS builder
WORKDIR /src

COPY requirements-build.txt .
# Build the bootloader against the same glibc 2.17 as the bundled Python.
RUN PYINSTALLER_COMPILE_BOOTLOADER=1 py3.13 -m pip install --no-cache-dir \
    --no-binary pyinstaller -r requirements-build.txt

COPY bolt.py LICENSE ./
ARG TARGETARCH
RUN test "$TARGETARCH" = amd64 \
    && version="$(py3.13 -c 'from bolt import __version__; print(__version__)')" \
    && py3.13 -m PyInstaller --onefile --name bolt --runtime-tmpdir /run/user/0 \
    --add-data "LICENSE:." bolt.py \
    && ./dist/bolt --help \
    && test "$(./dist/bolt --version)" = "bolt, version $version"

FROM centos:7 AS centos7
COPY --from=builder /src/dist/bolt /bolt_linux_amd64
COPY tests/check-binary.sh /check-binary.sh
RUN sh /check-binary.sh

FROM almalinux:8 AS alma8
COPY --from=centos7 /bolt_linux_amd64 /bolt_linux_amd64
COPY tests/check-binary.sh /check-binary.sh
RUN sh /check-binary.sh

FROM almalinux:9 AS alma9
COPY --from=alma8 /bolt_linux_amd64 /bolt_linux_amd64
COPY tests/check-binary.sh /check-binary.sh
RUN sh /check-binary.sh

FROM scratch AS artifact
COPY --from=alma9 /bolt_linux_amd64 /bolt_linux_amd64
