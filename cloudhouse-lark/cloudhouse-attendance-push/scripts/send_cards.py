#!/usr/bin/env python3
"""串行私聊推送卡片清单（小云 bot），逐条留痕。manifest: [{label,open_id,card,key,expect}]。"""
import argparse
import json
import subprocess
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--log", default="send_log.ndjson")
    ap.add_argument("--ids-out", default="sent_ids.json")
    ap.add_argument("--delay", type=float, default=0.6)
    a = ap.parse_args()
    entries = json.load(open(a.manifest))
    results = []
    with open(a.log, "a") as log:
        for e in entries:
            r = subprocess.run(["lark-cli", "im", "+messages-send", "--as", "bot",
                                "--user-id", e["open_id"], "--msg-type", "interactive",
                                "--content", f"@{e['card']}", "--idempotency-key", e["key"]],
                               capture_output=True, text=True)
            rec = {"label": e["label"], "open_id": e["open_id"], "key": e["key"]}
            try:
                out = json.loads(r.stdout)
            except Exception:
                out = {}
            if r.returncode == 0 and out.get("ok"):
                rec.update(ok=True, message_id=out["data"]["message_id"])
            else:
                rec.update(ok=False, error=(r.stderr or r.stdout)[:500])
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            results.append(rec)
            print(f"{e['label']}: {'OK ' + rec.get('message_id', '') if rec['ok'] else 'FAIL ' + rec.get('error', '')[:150]}")
            time.sleep(a.delay)
    ids = [r["message_id"] for r in results if r["ok"]]
    json.dump(ids, open(a.ids_out, "w"))
    fails = [(r["label"], r.get("error", "")[:80]) for r in results if not r["ok"]]
    print(f"sent {len(ids)}/{len(results)}; fails={fails}")


if __name__ == "__main__":
    main()