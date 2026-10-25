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

# Read local settings like the SSH key from a file outside the repository
configfile=${BERRYCELLS_CONFIG:-~/.config/berrycells/config.env}
if [ ! -f "$configfile" ]; then
  echo "Error: $configfile not found. Create it with a line BERRYCELLS_SSH_KEY='ssh-rsa ...'." >&2
  exit 1
fi
source "$configfile"

# Check if the SSH key is empty
if [[ -z "$BERRYCELLS_SSH_KEY" ]]; then
  echo "Error: BERRYCELLS_SSH_KEY is empty. Please provide a valid SSH key in $configfile." >&2
  exit 1
fi
ssh_key=$(printf '%s\n' "$BERRYCELLS_SSH_KEY" | sed 's/[&/\]/\\&/g')

# Generate firstrun.sh from the template (firstrun.sh is ignored by git as it contains the key)
sed "s/SSH_KEY/$ssh_key/g" firstrun.sh.template > firstrun.sh

rpi-imager --cli --sha256 $uncompressedChecksum --first-run-script firstrun.sh $imagefile $target
