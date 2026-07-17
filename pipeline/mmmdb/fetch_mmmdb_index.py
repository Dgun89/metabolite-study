import urllib.request, socket, json
socket.setdefaulttimeout(60)
def gt(url):
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req) as r:
        return r.read().decode('utf-8','replace')
cdx="http://web.archive.org/cdx/search/cdx?url=mmdb.iab.keio.ac.jp/download/*&output=json&filter=statuscode:200&collapse=urlkey&limit=500"
data=json.loads(gt(cdx))
hdr=data[0]; rows=data[1:]
print("columns:", hdr)
csvrows=[row for row in rows if row[2].endswith('.csv')]
print("archived csv rows:", len(csvrows))
files={}
for row in csvrows:
    ts=row[1]; orig=row[2]
    fn=orig.rsplit('/',1)[-1]
    if fn not in files or ts>files[fn][0]:
        files[fn]=(ts,orig)
print("unique csv files:", len(files))
for fn in sorted(files):
    print("  ", fn, files[fn][0])
json.dump({k:list(v) for k,v in files.items()}, open("mmmdb_archive_index.json","w"))
