import urllib.request, socket, json, time, os
socket.setdefaulttimeout(90)
idx=json.load(open("mmmdb_archive_index.json"))
os.makedirs("mmmdb_raw", exist_ok=True)
def wb_url(ts, orig):
    return f"http://web.archive.org/web/{ts}id_/{orig}"
def gt(url, tries=4):
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (research data fetch)"})
            with urllib.request.urlopen(req) as r:
                return r.read().decode('utf-8','replace')
        except Exception as e:
            last=e; time.sleep(4)
    raise last
ok=0; fail=[]
for i,fn in enumerate(sorted(idx)):
    dst=f"mmmdb_raw/{fn}"
    if os.path.exists(dst) and os.path.getsize(dst)>50:
        ok+=1; continue
    ts,orig=idx[fn]
    try:
        txt=gt(wb_url(ts,orig))
        open(dst,"w").write(txt)
        ok+=1
        print(f"[{i+1}/44] OK {fn} ({len(txt)}b)", flush=True)
    except Exception as e:
        fail.append(fn); print(f"[{i+1}/44] FAIL {fn} {repr(e)[:80]}", flush=True)
    time.sleep(2)
print("DONE ok=",ok,"fail=",fail)
