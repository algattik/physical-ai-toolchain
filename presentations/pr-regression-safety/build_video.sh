#!/usr/bin/env bash
# Narrate each slide with macOS `say`, build per-slide video clips, concat to MP4.
set -o errexit -o nounset -o pipefail

cd "$(dirname "$0")"
# VOICE empty => use the macOS default System Voice (no -v flag).
VOICE="${VOICE:-}"
SPEED="${SPEED:-1.0}"
mkdir -p audio clips
: > clips.txt
N=$(ls narration/slide-*.txt | wc -l | tr -d ' ')
echo ">> building video for $N slides (voice: ${VOICE:-default system voice}, speed: ${SPEED}x)"

for n in $(seq 1 "$N"); do
  img=$(printf "slides/slide-%03d.jpg" "$n")
  txt=$(printf "narration/slide-%02d.txt" "$n")
  aud=$(printf "audio/slide-%02d.aiff" "$n")
  clip=$(printf "clips/clip-%02d.mp4" "$n")

  # Synthesize (with timeout) and validate audio; re-synth once if duration is bad.
  # A killed/hung `say` leaves a corrupt aiff (empty duration) -> divide-by-zero below.
  for attempt in 1 2; do
    if [ ! -f "$aud" ]; then
      echo ">> slide $n: synthesizing narration (${VOICE:-default system voice})"
      if [ -n "$VOICE" ]; then
        timeout 90 say -v "$VOICE" -o "$aud" -f "$txt" || true
      else
        timeout 90 say -o "$aud" -f "$txt" || true
      fi
    fi
    d=$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "$aud" 2>/dev/null)
    if [ -n "$d" ] && awk "BEGIN{exit !($d>0)}" 2>/dev/null; then
      break
    fi
    echo ">> slide $n: bad/empty audio (duration='${d:-none}'), re-synthesizing"
    rm -f "$aud"
    [ "$attempt" = 2 ] && { echo "ERROR: slide $n audio failed twice" >&2; exit 1; }
  done

  adur=$(awk "BEGIN{printf \"%.3f\", $d / $SPEED}")
  dur=$(awk "BEGIN{printf \"%.3f\", $adur + 1.0}")
  fout=$(awk "BEGIN{printf \"%.3f\", $adur + 0.5}")

  echo ">> slide $n: encoding clip (audio ${d}s -> ${adur}s @ ${SPEED}x, clip ${dur}s)"
  ffmpeg -y -loglevel error -loop 1 -framerate 30 -i "$img" -i "$aud" \
    -filter_complex \
    "[0:v]scale=1920:1080,fade=t=in:st=0:d=0.3,fade=t=out:st=${fout}:d=0.4,format=yuv420p[v];[1:a]atempo=${SPEED},adelay=300,apad[a]" \
    -map "[v]" -map "[a]" -t "$dur" \
    -c:v libx264 -preset medium -crf 20 -r 30 \
    -c:a aac -ar 48000 -ac 2 -b:a 192k \
    "$clip"
  echo "file '$clip'" >> clips.txt
done

echo ">> concatenating $(wc -l < clips.txt) clips"
ffmpeg -y -loglevel error -f concat -safe 0 -i clips.txt -c copy presentation.mp4
echo ">> done: $(pwd)/presentation.mp4"
