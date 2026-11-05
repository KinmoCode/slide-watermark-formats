#!/bin/sh
# Read-only inspection of a .pptx with unzip and grep. Nothing is extracted to disk.
# Usage: sh pptx_inspect.sh deck.pptx [domain]
# SPDX-License-Identifier: MIT
set -eu

deck=${1:?usage: pptx_inspect.sh deck.pptx [domain]}
domain=${2:-}

echo "== slide size"
unzip -p "$deck" ppt/presentation.xml | grep -o '<p:sldSz [^>]*>' || true

echo
echo "== parts"
unzip -Z1 "$deck" | grep -E '^ppt/(slides|slideLayouts|slideMasters)/[^/]+\.xml$' | sort

echo
echo "== external relationships"
unzip -Z1 "$deck" | grep -E '^ppt/(slides|slideLayouts|slideMasters)/_rels/.*\.rels$' | while read -r f; do
  unzip -p "$deck" "$f" \
    | grep -o '<Relationship [^>]*TargetMode="External"[^>]*>' \
    | sed "s|^|$f: |" || true
done

if [ -n "$domain" ]; then
  echo
  echo "== parts that mention $domain"
  unzip -Z1 "$deck" | while read -r f; do
    unzip -p "$deck" "$f" 2>/dev/null | grep -q -i -F "$domain" && echo "$f" || true
  done
fi

echo
echo "== media"
unzip -l "$deck" | grep 'ppt/media/' || true
