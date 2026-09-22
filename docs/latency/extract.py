"""Extract anonymized measurements from Moonlight per-frame traces.
Usage: python extract.py LABEL INPUT.csv OUTPUT.csv
Only measured DRM feedback is used; discard first 30 seconds by pacer arrival.
"""
import csv, sys
from pathlib import Path
label, src, dst = sys.argv[1:]
rows = [r for r in csv.DictReader(Path(src).open()) if None not in r and None not in r.values()]
start = int(rows[0]['pacer_arrival_us']) + 30_000_000
ids = {int(r['submission_id']): r for r in rows if r['submission_id_valid'] == '1' and int(r['pacer_arrival_us']) >= start}
pairs = {int(r['latch_submission_id']): (ids[int(r['latch_submission_id'])], int(r['latch_time_us'])) for r in rows if r['latch_valid'] == '1' and r['latch_time_kind'] == '2' and int(r['latch_submission_id']) in ids}
fields = ['sample','elapsed_s','total_ms','decode_wait_ms','prepare_ms','submit_to_flip_ms','other_ms']
with Path(dst).open('w') as f:
    out = csv.DictWriter(f, fieldnames=fields); out.writeheader()
    for n, (r, flip) in enumerate(sorted(pairs.values(), key=lambda p:int(p[0]['frame_reassembled_us']))):
        total = (flip-int(r['frame_reassembled_us']))/1000
        decode = (int(r['decode_complete_us'])-int(r['decoder_output_us']))/1000
        prep = int(r['prepare_us'])/1000
        submit = (flip-int(r['presenter_submission_time_us']))/1000
        assert total >= 0 and decode >= 0 and prep >= 0 and submit >= 0
        out.writerow(dict(zip(fields,[n,round((int(r['pacer_arrival_us'])-start)/1e6,6),total,decode,prep,submit,round(total-decode-prep-submit,6)])))
print(label, len(pairs), 'frames;', sum(r['dropped']=='1' for r in rows if int(r['pacer_arrival_us'])>=start), 'drops')
