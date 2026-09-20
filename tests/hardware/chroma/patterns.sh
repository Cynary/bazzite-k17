#!/bin/bash
set -euo pipefail
mkdir -p "${1:?Usage: patterns.sh OUTPUT_DIRECTORY}"
cd "$1"
ffmpeg -hide_banner -loglevel error -f lavfi -i "nullsrc=s=1280x720,format=yuv444p10le,geq=lum='64+mod(X,877)':cb='64+896*mod(X,2)':cr='64+896*mod(Y,2)'" -frames:v 1 -c:v libx265 -preset ultrafast -x265-params lossless=1:pools=$(nproc) -color_primaries bt2020 -color_trc smpte2084 -colorspace bt2020nc -color_range tv -y hdr10-pattern.mkv
ffmpeg -hide_banner -loglevel error -f lavfi -i "nullsrc=s=1280x720,format=yuv444p,geq=lum='16+mod(X,220)':cb='16+224*mod(X,2)':cr='16+224*mod(Y,2)'" -frames:v 1 -c:v libx265 -preset ultrafast -x265-params lossless=1:pools=$(nproc) -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -y sdr8-pattern.mkv

ffmpeg -hide_banner -loglevel error -i hdr10-pattern.mkv -frames:v 1 -pix_fmt yuv420p10le -c:v libx265 -preset ultrafast -x265-params lossless=1:pools=$(nproc) -y 420-pattern.mkv
