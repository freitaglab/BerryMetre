#!/bin/bash
target=$1
if [ ! -f 2024-07-04-raspios-bookworm-arm64-lite.img.xz ]; then
    echo "Downloading image!"
    wget https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2024-07-04/2024-07-04-raspios-bookworm-arm64-lite.img.xz
fi
rpi-imager --cli --sha256 2746d9ff409c34de471f615a94a3f15917dca9829ddbc7a9528f019e97dc4f03 --first-run-script firstrun.sh 2024-07-04-raspios-bookworm-arm64-lite.img.xz $target