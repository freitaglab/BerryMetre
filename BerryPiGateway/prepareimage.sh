#!/bin/bash
set -e
target=$1
baseurl=https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-04-14/
imagefile=2026-04-13-raspios-trixie-arm64-lite.img.xz
imageChecksum=5c9caff670594eb43b68afee2a156198cb4e4f58e5dec724b4520c53c0ab5aba  # Checksum of the uncompressed image

# Delete the local cache file until https://github.com/raspberrypi/rpi-imager/issues/974 is fixed
if [ -f ~/.cache/Raspberry\ Pi/Imager/lastdownload.cache ]; then
    rm ~/.cache/Raspberry\ Pi/Imager/lastdownload.cache
fi

# Delete and redownload sha256 of the compressed image
if [ -f $baseurl$imagefile.sha256 ]; then
    rm wget $baseurl$imagefile.sha256
fi
wget $baseurl$imagefile.sha256 -O $imagefile.sha256

if [ ! -f 2024-07-04-raspios-bookworm-arm64-lite.img.xz ]; then
    echo "(Re-)Downloading image!"
    wget $baseurl$imagefile
fi

# Check if the compressed image has the correct sha256sum
if ! [ "$(sha256sum -c $imagefile.sha256 | awk '{print $2}')" = "OK" ]; then
    echo "Compressed image checksum error"
    exit 1
fi

rpi-imager --cli --sha256 $imageChecksum --first-run-script firstrun.sh $imagefile $target
