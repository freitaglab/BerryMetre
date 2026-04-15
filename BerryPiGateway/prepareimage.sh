#!/bin/bash
set -e
target=$1
baseurl=https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2026-04-14/
imagefile=2026-04-13-raspios-trixie-arm64-lite.img.xz
imageChecksum=5c9caff670594eb43b68afee2a156198cb4e4f58e5dec724b4520c53c0ab5aba  # Checksum of the uncompressed image
uncompressedChecksum=5da77e33b60407a0861bd90a0ab2822214f18d3e0e66ad98fbe2674743dd81b1

# Delete the local cache file until https://github.com/raspberrypi/rpi-imager/issues/974 is fixed
if [ -f ~/.cache/Raspberry\ Pi/Imager/lastdownload.cache ]; then
    rm ~/.cache/Raspberry\ Pi/Imager/lastdownload.cache
fi

# Delete and redownload sha256 of the compressed image
if [ -f $baseurl$imagefile.sha256 ]; then
    rm wget $baseurl$imagefile.sha256
fi
wget $baseurl$imagefile.sha256 -O $imagefile.sha256

if [ ! -f $imagefile ]; then
    echo "(Re-)Downloading image!"
    wget $baseurl$imagefile
fi

# Check if the compressed image has the correct sha256sum
if ! [ "$(sha256sum -c $imagefile.sha256 | awk '{print $2}')" = "OK" ]; then
    echo "Compressed image checksum error"
    exit 1
fi

ssh_key=$(printf '%s\n' "$(cat sshkey.pub)" | sed 's/[&/\]/\\&/g')

# Check if ssh_key is empty
if [[ -z "$ssh_key" ]]; then
  echo "Error: ssh_key is empty. Please provide a valid SSH key in a file named sshkey.pub." >&2
  exit 1
fi
sed -i "s/SSH_KEY/$ssh_key/g" firstrun.sh

rpi-imager --cli --sha256 $uncompressedChecksum --first-run-script firstrun.sh $imagefile $target
