#!/bin/sh
# Verzamelt de configbestanden die iamscan leest, in een tarball.
#
# Draai dit op de host die beoordeeld wordt. Het script leest alleen; er wordt
# niets gewijzigd en niets verstuurd. Draai het als root, anders blijven
# authorized_keys van andere gebruikers en /etc/sudoers onleesbaar.
#
#   sudo sh collect.sh                 # schrijft ./<hostname>-iamscan.tar.gz
#   sudo sh collect.sh /tmp/uitvoer    # of naar een eigen map
#
# Uitpakken aan de analysekant, met een map per host:
#   mkdir -p dump/hosts && tar -xzf web01-iamscan.tar.gz -C dump/hosts

set -eu

OUTDIR="${1:-.}"
HOST="$(hostname -s 2>/dev/null || hostname)"
WORK="$(mktemp -d)"
STAGE="$WORK/$HOST"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

copy() {
    src="$1"
    [ -r "$src" ] || { echo "overgeslagen (niet leesbaar): $src" >&2; return 0; }
    dst="$STAGE/${src#/}"
    mkdir -p "$(dirname "$dst")"
    cp -p "$src" "$dst"
}

mkdir -p "$STAGE"

copy /etc/passwd
copy /etc/group
copy /etc/sudoers

if [ -d /etc/sudoers.d ]; then
    for f in /etc/sudoers.d/*; do
        [ -f "$f" ] && copy "$f"
    done
fi

copy /etc/ssh/sshd_config

# authorized_keys per home-directory uit passwd, plus root.
awk -F: '$6 != "" { print $6 }' /etc/passwd | sort -u | while read -r home; do
    copy "$home/.ssh/authorized_keys"
done
copy /root/.ssh/authorized_keys

mkdir -p "$OUTDIR"
ARCHIVE="$OUTDIR/$HOST-iamscan.tar.gz"
tar -czf "$ARCHIVE" -C "$WORK" "$HOST"

echo "geschreven: $ARCHIVE"
echo "inhoud:"
tar -tzf "$ARCHIVE" | sed 's/^/  /'
