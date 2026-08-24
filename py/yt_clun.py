import re
import json
import time
import requests
from urllib.parse import quote, unquote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from base.spider import Spider


class Spider(Spider):

    HOST = "https://www.youtube.com"
    API = "https://www.youtube.com/youtubei/v1/"
    KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"

    CLIENTS = {
        "web": {
            "ctx": {"clientName": "WEB", "clientVersion": "2.20240611.00.00"},
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "cn": "1",
            "cv": "2.20240611.00.00",
        },
        "android": {
            "ctx": {"clientName": "ANDROID", "clientVersion": "20.04.46", "platform": "MOBILE", "osName": "Android", "osVersion": "14", "androidSdkVersion": 35},
            "ua": "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip",
            "cn": "3",
            "cv": "20.04.46",
        },
        "ios": {
            "ctx": {"clientName": "IOS", "clientVersion": "20.04.4", "deviceModel": "iPhone16,2"},
            "ua": "com.google.ios.youtube/20.04.4 (iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)",
            "cn": "5",
            "cv": "20.04.4",
        },
        "vr": {
            "ctx": {"clientName": "ANDROID_VR", "clientVersion": "1.65.10", "deviceMake": "Oculus", "deviceModel": "Quest 3", "androidSdkVersion": 32, "osName": "Android", "osVersion": "12L"},
            "ua": "com.google.android.apps.youtube.vr.oculus/1.65.10 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip",
            "cn": "28",
            "cv": "1.65.10",
        },
    }

    CATS = ["热门推荐", "音乐MV", "游戏", "影视剪辑", "纪录片", "科技数码", "新闻资讯"]

    def getName(self):
        return "YouTube"

    def init(self, extend):
        self.cookie = ""
        self.jcfg = {}
        try:
            self.session = requests.Session()
            retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[408, 429, 500, 502, 503, 504], allowed_methods=["GET", "POST"])
            adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        except Exception:
            self.session = requests
        try:
            self.log("yt extend:" + str(extend)[:500])
        except Exception:
            pass
        try:
            e = extend
            if isinstance(e, str):
                e = e.strip()
                if not e:
                    return
                if e.startswith("{"):
                    e = json.loads(e)
                elif e.startswith("["):
                    return
                else:
                    e = {"json": e}
            if isinstance(e, dict):
                if "class" in e or "filters" in e or "recommend" in e:
                    self.jcfg = e
                else:
                    self.cookie = str(e.get("cookie") or "")
                    j = e.get("json")
                    if isinstance(j, dict):
                        self.jcfg = j
                    elif isinstance(j, str) and j.strip():
                        d = self._load_json_file(j.strip())
                        if d:
                            self.jcfg = d
                        elif j.strip().startswith("{"):
                            try:
                                self.jcfg = json.loads(j)
                            except Exception:
                                pass
        except Exception:
            pass

    def _load_json_file(self, path):
        if path.startswith("http://") or path.startswith("https://"):
            try:
                import requests as _rq
                r = _rq.get(path, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    try:
                        self.log("yt ext loaded(url):" + path)
                    except Exception:
                        pass
                    return d
            except Exception:
                pass
            try:
                self.log("yt ext NOT FOUND:" + path)
            except Exception:
                pass
            return {}
        import os
        cands = []
        if path.startswith("/"):
            cands.append(path)
        else:
            base = path.lstrip("./")
            for root in ("/storage/emulated/0/", "/sdcard/",
                         "/storage/emulated/0/TV/", "/storage/emulated/0/tvbox/",
                         "/storage/emulated/0/box/", "/storage/emulated/0/Download/",
                         "/data/user/0/com.fongmi.vodplus/files/",
                         "/data/user/0/com.fongmi.android.tv/files/"):
                cands.append(root + base)
            try:
                cands.append(os.path.join(os.getcwd(), base))
            except Exception:
                pass
            cands.append(path)
        for p in cands:
            try:
                if os.path.isfile(p):
                    with open(p, encoding="utf-8") as f:
                        d = json.load(f)
                        try:
                            self.log("yt ext loaded:" + p)
                        except Exception:
                            pass
                        return d
            except Exception:
                continue
        try:
            self.log("yt ext NOT FOUND:" + path)
        except Exception:
            pass
        return {}

    def isVideoFormat(self, url):
        return True

    def isTextFormat(self, url):
        return False

    def _jcfg_classes(self):
        cs = self.jcfg.get("class") or []
        return [{"type_id": c.get("type_id", ""), "type_name": c.get("type_name", "")} for c in cs if c.get("type_id")]

    def homeContent(self, filter):
        classes = self._jcfg_classes()
        if classes:
            recs = self._search_items(self.jcfg_recommend())
            return {"class": classes, "list": recs, "filters": self.jcfg.get("filters") or {}}
        return {"class": [{"type_id": c, "type_name": c} for c in self.CATS], "list": [], "filters": {}}

    def jcfg_recommend(self):
        r = str(self.jcfg.get("recommend") or "")
        if r.startswith("LIST:"):
            r = r[5:].split(",")[0].split("|")[0]
        return r.strip() or "trending music video"

    def homeVideoContent(self):
        return {"list": self._search_items(self.jcfg_recommend())}

    def categoryContent(self, tid, pg, filter, extend):
        ex = {}
        try:
            ex = json.loads(extend) if isinstance(extend, str) and extend.strip() else (extend or {})
        except Exception:
            ex = {}
        chosen = []
        flist = self.jcfg.get("filters") or {}
        for k, v in (ex or {}).items():
            if not v:
                continue
            for grp in flist.get(tid) or []:
                vv = {str(x.get("n")): x.get("v", "") for x in grp.get("value") or []}
                if str(v) in vv:
                    chosen.append(str(vv[v]))
        if tid.startswith("LIST:"):
            qs = [" ".join(chosen).strip()] if chosen else [x.strip() for x in tid[5:].split(",") if x.strip()]
        elif tid == "GETTRENDS":
            qs = ["trending videos this week"]
        else:
            qs = [" ".join(chosen).strip() or tid]
        qs = [q for q in qs if q] or [tid]
        seen = set()
        items = []
        per = max(1, 24 // max(1, len(qs)))
        for q in qs:
            res = self._post("search", {"query": q}, "web")
            cnt = 0
            if res:
                secs = res.get("contents", {}).get("twoColumnSearchResultsRenderer", {}) \
                         .get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                for sec in secs:
                    for it in sec.get("itemSectionRenderer", {}).get("contents", []):
                        vr = it.get("videoRenderer")
                        if vr and cnt < per:
                            vid0 = vr.get("videoId", "")
                            if vid0 and vid0 not in seen:
                                seen.add(vid0)
                                items.append(self._parse_vr(vr))
                                cnt += 1
        return {"list": items, "page": int(pg or 1), "pagecount": 99, "limit": len(items), "total": len(items)}

    def detailContent(self, array):
        vid = array[0]
        d = self._player(vid)
        vd = (d or {}).get("videoDetails", {}) if d else {}
        mf = ((d or {}).get("microformat") or {}).get("playerMicroformatRenderer", {}) if d else {}
        title = vd.get("title") or vid
        desc = vd.get("shortDescription", "") or ""
        dur = int(vd.get("lengthSeconds") or 0)
        is_live = bool(vd.get("isLive") or vd.get("isLiveContent"))
        thumbs = vd.get("thumbnail", {}).get("thumbnails", [])
        thumb = thumbs[-1].get("url", "") if thumbs else ("https://i.ytimg.com/vi/" + vid + "/mqdefault.jpg")
        author = vd.get("author", "")
        date = str(mf.get("publishDate", "") or "")
        vc = 0
        try:
            vc = int(vd.get("viewCount") or 0)
        except Exception:
            vc = 0
        parts = []
        if author:
            parts.append("📺 频道: " + author)
        if date:
            parts.append("📅 发布: " + date[:10])
        if vc >= 100000000:
            parts.append("👁 观看: %.1f亿次" % (vc / 100000000.0))
        elif vc >= 10000:
            parts.append("👁 观看: %.1f万次" % (vc / 10000.0))
        elif vc > 0:
            parts.append("👁 观看: %d次" % vc)
        if desc:
            parts.append("\n📝 简介:\n" + desc)
        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": thumb,
            "type_name": "YouTube",
            "vod_year": date[:10],
            "vod_area": author,
            "vod_remarks": ("直播中" if is_live else ("%d分钟" % (dur // 60)) if dur else ""),
            "vod_actor": author,
            "vod_director": author,
            "vod_content": "\n".join(parts)[:2000],
        }
        eps_hls, eps_mp4 = [], []
        sd = (d or {}).get("streamingData", {}) or {}
        has_hls = bool(sd.get("hlsManifestUrl"))
        eps_hls.append(("直播" if is_live else "第01集") + "$hls_" + vid)
        muxed = []
        vonly = []
        if d:
            for f in (sd.get("formats") or []) + (sd.get("adaptiveFormats") or []):
                m = f.get("mimeType", "")
                u = f.get("url")
                if not u or "video" not in m:
                    continue
                h = int(f.get("height") or 0)
                if h <= 0:
                    continue
                if any(x in m for x in ("mp4a", "opus", "vorbis")):
                    muxed.append((h, u, f))
                else:
                    vonly.append(f)
            muxed.sort(key=lambda x: -x[0])
            seen_h = set()
            for h, u, f in muxed:
                if h in seen_h:
                    continue
                seen_h.add(h)
                cs = self._codec_short(f)
                lbl = self._quality_label(h) + (("·" + cs) if cs else "")
                eps_mp4.append("%s$mp4_%d_%s" % (lbl, h, vid))
            mx = muxed[0][0] if muxed else 0
            vh = {}
            for f in vonly:
                h = int(f.get("height") or 0)
                if h <= mx or h in seen_h:
                    continue
                old = vh.get(h)
                if not old or int(f.get("bitrate") or 0) > int(old.get("bitrate") or 0):
                    vh[h] = f
            for h in sorted(vh.keys(), reverse=True):
                seen_h.add(h)
                f = vh[h]
                cs = self._codec_short(f)
                lbl = self._quality_label(h) + (("·" + cs) if cs else "")
                eps_mp4.append("%s$vpure_%d_%s" % (lbl, h, vid))
            eps_mp4.append("音轨$audio_" + vid)
        if not has_hls and not muxed:
            eps_mp4.insert(0, "第01集$mp4_0_" + vid)
        if not d:
            eps_mp4.insert(0, "第01集$mp4_0_" + vid)
        flags = ["HLS", "MP4"]
        urls = ["#".join(eps_hls), "#".join(eps_mp4)]
        flags.append("SABR")
        urls.append(("直播" if is_live else "第01集") + "$sabr_" + vid)
        vod["vod_play_from"] = "$$$".join(flags)
        vod["vod_play_url"] = "$$$".join(urls)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        return {"list": self._search_items(key)}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("_")
        kind = parts[0]
        vid = "_".join(parts[1:])
        want_h = 0
        if kind in ("mp4", "vpure"):
            try:
                want_h = int(parts[1])
            except Exception:
                want_h = 0
            vid = "_".join(parts[2:])
        d = self._player(vid)
        hls = ""
        muxed = []
        vonly = []
        if d:
            sd = d.get("streamingData", {})
            hls = sd.get("hlsManifestUrl", "") or ""
            for f in (sd.get("formats") or []) + (sd.get("adaptiveFormats") or []):
                m = f.get("mimeType", "")
                u = f.get("url")
                if not u or "video" not in m:
                    continue
                h = int(f.get("height") or 0)
                if any(x in m for x in ("mp4a", "opus", "vorbis")):
                    muxed.append((h, u))
                else:
                    vonly.append((h, u))
            muxed.sort(key=lambda x: -x[0])
            vonly.sort(key=lambda x: -x[0])
        play_url = ""
        parse = 0
        if kind == "hls":
            play_url = hls or (muxed[0][1] if muxed else "")
        elif kind == "mp4":
            if want_h:
                exact = [u for h, u in muxed if h == want_h]
                play_url = exact[0] if exact else (muxed[0][1] if muxed else (hls or ""))
            else:
                play_url = muxed[0][1] if muxed else (hls or "")
        elif kind == "vpure":
            if want_h:
                exact = [u for h, u in vonly if h == want_h]
                if exact:
                    play_url = "http://127.0.0.1:9978/proxy?do=py&type=mpd&vid=%s&h=%d" % (vid, want_h)
                    parse = 0
                    ret = {
                        "parse": 0,
                        "playUrl": "",
                        "url": play_url,
                        "header": json.dumps({"User-Agent": "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip"}),
                        "format": "application/dash+xml",
                    }
                    subs = self._subs(vid, flag)
                    if subs:
                        ret["subs"] = json.dumps(subs)
                    dm = self._danmaku(vid)
                    if dm:
                        ret["danmaku"] = dm
                    return ret
        elif kind == "audio":
            best_a = ""
            best_b = -1
            if d:
                sd = d.get("streamingData", {})
                for f in (sd.get("adaptiveFormats") or []):
                    m = f.get("mimeType", "")
                    u = f.get("url")
                    if not u or "audio" not in m:
                        continue
                    b = int(f.get("bitrate") or 0)
                    if b > best_b:
                        best_b, best_a = b, u
            play_url = best_a
        elif kind == "sabr" and d:
            sabr = (d.get("streamingData", {}) or {}).get("serverAbrStreamingUrl", "")
            if sabr:
                play_url = sabr
        elif kind == "dash" and vid:
            play_url = "http://127.0.0.1:9978/proxy?do=py&type=mpd&vid=" + vid
            ret = {
                "parse": 0,
                "playUrl": "",
                "url": play_url,
                "header": json.dumps({"User-Agent": "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip"}),
                "format": "application/dash+xml",
            }
            subs = self._subs(vid, flag)
            if subs:
                ret["subs"] = json.dumps(subs)
            dm = self._danmaku(vid)
            if dm:
                ret["danmaku"] = dm
            return ret
        if not play_url:
            return {"parse": 1, "playUrl": "", "jx": "https://www.youtube.com/watch?v=" + vid}
        ret = {
            "parse": parse,
            "playUrl": "",
            "url": play_url,
            "header": json.dumps({"User-Agent": "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip"}),
        }
        subs = self._subs(vid, flag)
        if subs:
            ret["subs"] = json.dumps(subs)
        dm = self._danmaku(vid)
        if dm:
            ret["danmaku"] = dm
        return ret

    def localProxy(self, param):
        t = param.get("type", "")
        if t == "mpd":
            return self._proxy_mpd(param)
        if t == "vtt":
            return self._proxy_vtt(param)
        return [404, "text/plain", b"not found"]

    def _proxy_mpd(self, param):
        vid = param.get("vid", "")
        if not vid:
            return [404, "text/plain", b"no vid"]
        want_h = 0
        try:
            want_h = int(param.get("h") or 0)
        except Exception:
            want_h = 0
        d = self._player(vid)
        if not d:
            return [404, "text/plain", b"player failed"]
        sd = d.get("streamingData", {})
        dur_s = int((d.get("videoDetails", {}) or {}).get("lengthSeconds") or 0)
        UA = "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip"
        vraw, araw = [], []
        seen_h = set()
        for f in (sd.get("adaptiveFormats") or []):
            m = f.get("mimeType", "") or ""
            u = f.get("url")
            if not u:
                continue
            ir, ix = self._ranges_of(f)
            if "video/" in m:
                h = int(f.get("height") or 0)
                if h in seen_h or h <= 0:
                    continue
                if want_h and h != want_h:
                    continue
                seen_h.add(h)
                vraw.append((h, max(int(f.get("bitrate") or 0), 1),
                             int(f.get("width") or h * 16 // 9),
                             self._codecs_of(m) or "avc1.64001f", u, ir, ix))
            elif "mp4a" in m:
                araw.append((int(f.get("bitrate") or 0), self._codecs_of(m) or "mp4a.40.2", u, ir, ix))
        need_probe_v = [j for j in vraw if not j[5]]
        need_probe_a = [j for j in araw if not j[3]]
        if need_probe_v or need_probe_a:
            jobs = need_probe_v + need_probe_a
            rngs = {}
            try:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(8, max(1, len(jobs)))) as ex:
                    fut = {ex.submit(self._probe_boxes, j[4], UA): j for j in jobs}
                    for fu, j in fut.items():
                        try:
                            r = fu.result(timeout=10)
                            if r:
                                rngs[j[4]] = r
                        except Exception:
                            pass
            except Exception:
                pass
            vraw = [j if j[5] else (j[0], j[1], j[2], j[3], j[4]) + ((rngs[j[4]], rngs[j[4]]) if j[4] in rngs else (None, None)) for j in vraw]
            araw = [j if j[3] else (j[0], j[1], j[2]) + ((rngs[j[2]], rngs[j[2]]) if j[2] in rngs else (None, None)) for j in araw]
        vraw = [j for j in vraw if j[5] and j[6]]
        araw = [j for j in araw if j[3] and j[4]]
        araw.sort(key=lambda x: -x[0])
        if not vraw or not araw:
            return [404, "text/plain", b"no tracks"]
        av = araw[0]
        esc = lambda s: s.replace(chr(38), chr(38) + "amp;").replace(chr(60), chr(38) + "lt;").replace('"', chr(38) + "quot;")
        P = []
        A = P.append
        A('<?xml version="1.0" encoding="UTF-8"?>')
        A('<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT%dS" minBufferTime="PT1.5S" profiles="urn:mpeg:dash:profile:isoff-main:2011">' % dur_s)
        A('<Period id="P0">')
        A('<AdaptationSet id="0" contentType="video" mimeType="video/mp4" segmentAlignment="true" startWithSAP="1">')
        for i, j in enumerate(sorted(vraw, key=lambda x: -x[1])):
            h, bw, w, cd, u, ir, ix = j
            ie, (sa, sb) = ir, ix
            A('<Representation id="v%d" bandwidth="%d" width="%d" height="%d" frameRate="30" codecs="%s">' % (i, bw, w, h, cd))
            A('<BaseURL>%s</BaseURL>' % esc(u))
            A('<SegmentBase timescale="90000" indexRange="%d-%d"><Initialization range="0-%d"/></SegmentBase>' % (sa, sb, ie))
            A('</Representation>')
        A('</AdaptationSet>')
        A('<AdaptationSet id="1" contentType="audio" mimeType="audio/mp4" segmentAlignment="true" startWithSAP="1" lang="und">')
        au = av[2]
        ie, (sa, sb) = av[3], av[4]
        A('<Representation id="a0" bandwidth="%d" audioSamplingRate="44100" codecs="%s">' % (max(av[0], 1), av[1]))
        A('<BaseURL>%s</BaseURL>' % esc(au))
        A('<SegmentBase timescale="44100" indexRange="%d-%d"><Initialization range="0-%d"/></SegmentBase>' % (sa, sb, ie))
        A('<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>')
        A('</Representation>')
        A('</AdaptationSet>')
        A('</Period>')
        A('</MPD>')
        return [200, "application/dash+xml", "\n".join(P).encode("utf-8")]

    def _ranges_of(self, f):
        try:
            ir = f.get("initRange") or {}
            ix = f.get("indexRange") or {}
            ie = int(ir.get("end") or 0)
            sa = int(ix.get("start") or 0)
            sb = int(ix.get("end") or 0)
            if ie > 0 and sb > sa:
                return ie, (sa, sb)
        except Exception:
            pass
        return None, None

    def _probe_boxes(self, u, ua):
        try:
            r = requests.get(u, headers={"User-Agent": ua, "Range": "bytes=0-524287"}, stream=True, timeout=8)
            buf = r.raw.read(524288)
            r.close()
        except Exception:
            return None
        if not buf:
            return None
        off = 0
        init_end = None
        sidx = None
        n = len(buf)
        while off + 8 <= n:
            try:
                size = int.from_bytes(buf[off:off + 4], "big")
                typ = buf[off + 4:off + 8]
            except Exception:
                break
            if size < 8 or off + size > n:
                break
            if typ == b"moov":
                init_end = off + size - 1
            elif typ == b"sidx":
                sidx = (off, off + size - 1)
            off += size
        if init_end is None:
            init_end = 1023
        if sidx is None:
            sidx = (init_end + 1, init_end + 2047)
        return init_end, sidx

    def _proxy_vtt(self, param):
        u = unquote(param.get("u", ""))
        if not u:
            return [404, "text/plain", b"no url"]
        try:
            r = requests.get(u, timeout=10,
                             headers={"User-Agent": "com.google.android.youtube/20.04.46 (Linux; U; Android 14) gzip"})
            txt = r.text
            if "<transcript>" in txt or "<timedtext" in txt:
                import html as _h
                out = ["WEBVTT", ""]
                for m in re.finditer(r'<text start="([\d.]+)"(?: dur="[\d.]+")?[^>]*>(.*?)</text>', txt, re.S):
                    t0 = float(m.group(1))
                    body = _h.unescape(re.sub(r"<[^>]+>", "", m.group(2))).replace("\n", " ")
                    out.append(self._ts(t0) + " --> " + self._ts(t0 + 3.0))
                    out.append(body)
                    out.append("")
                txt = "\n".join(out)
            return [200, "text/vtt", txt.encode("utf-8")]
        except Exception as e:
            return [404, "text/plain", str(e).encode()]

    def _ts(self, sec):
        ms = int(round(sec * 1000))
        return "%02d:%02d:%02d.%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)

    def _codecs_of(self, mime):
        mm = re.search(r'codecs="([^"]+)"', mime)
        return mm.group(1) if mm else ""

    def _quality_label(self, h):
        if h >= 2160:
            return "4K"
        if h >= 1440:
            return "2K"
        return "%dp" % h

    def _codec_short(self, f):
        m = (f.get("mimeType") or "").lower()
        c = self._codecs_of(f.get("mimeType", "")).lower()
        if "av01" in c:
            return "AV1"
        if "vp9" in c or "vp09" in c or "vp9" in m:
            return "VP9"
        if "avc" in c or "h264" in c:
            return "H264"
        return ""

    def _subs(self, vid, flag=""):
        try:
            d = self._player(vid)
            tracks = (((d or {}).get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}).get("captionTracks") or []
            subs = []
            seen_lang = set()
            for t in tracks:
                lang = t.get("languageCode", "")
                if not lang or lang in seen_lang:
                    continue
                seen_lang.add(lang)
                base = t.get("baseUrl", "")
                if not base:
                    continue
                nm = ((t.get("name") or {}).get("simpleText")) or ""
                if not nm:
                    runs = (t.get("name") or {}).get("runs") or []
                    nm = "".join(x.get("text", "") for x in runs) or lang
                if t.get("kind") == "asr":
                    nm += "(自动)"
                vurl = base.replace("fmt=srv3", "fmt=vtt")
                if "fmt=vtt" not in vurl:
                    vurl = base + "&fmt=vtt"
                subs.append({"name": nm[:20], "url": vurl})
                if len(subs) >= 8:
                    break
            return subs
        except Exception:
            return []

    def _danmaku(self, vid):
        return ""

    def _search_items(self, query):
        res = self._post("search", {"query": query}, "web")
        items = []
        if res:
            secs = res.get("contents", {}).get("twoColumnSearchResultsRenderer", {}) \
                     .get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
            for sec in secs:
                for it in sec.get("itemSectionRenderer", {}).get("contents", []):
                    vr = it.get("videoRenderer")
                    if vr:
                        items.append(self._parse_vr(vr))
        return items

    def _post(self, ep, extra, client_name):
        try:
            c = self.CLIENTS[client_name]
            ctx = dict(c["ctx"])
            ctx["hl"] = "en"
            ctx["gl"] = "US"
            payload = {"context": {"client": ctx}}
            payload.update(extra)
            url = "%s%s?prettyPrint=false&key=%s" % (self.API, ep, self.KEY)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": c["ua"],
                "X-YouTube-Client-Name": c["cn"],
                "X-YouTube-Client-Version": c["cv"],
                "Origin": "https://www.youtube.com",
                "X-Goog-Api-Format-Version": "2",
            }
            if self.cookie:
                headers["Cookie"] = self.cookie
            r = self.session.post(url, data=json.dumps(payload).encode(), headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            try:
                self.log("yt post error:" + str(e))
            except Exception:
                pass
        return None

    def _player(self, vid):
        got = None
        for cl in ("android", "ios", "vr"):
            for attempt in range(2):
                try:
                    d = self._post("player", {"videoId": vid, "contentCheckOk": True, "racyCheckOk": True}, cl)
                except Exception:
                    d = None
                st = ((d or {}).get("playabilityStatus") or {}).get("status", "")
                if st == "OK" and d.get("streamingData"):
                    got = d
                    break
            if got:
                break
        if got:
            return got
        got = self._player_watch(vid)
        if not got:
            return None
        sd = got.get("streamingData", {})
        if not sd.get("hlsManifestUrl"):
            try:
                for cl in ("ios", "vr", "android"):
                    if cl == (got.get("context", {}).get("client", {}).get("clientName") or "").lower():
                        continue
                    d = self._post("player", {"videoId": vid, "contentCheckOk": True, "racyCheckOk": True}, cl)
                    st = ((d or {}).get("playabilityStatus") or {}).get("status", "")
                    if st == "OK":
                        asd = d.get("streamingData", {}) or {}
                        if asd.get("hlsManifestUrl"):
                            sd["hlsManifestUrl"] = asd["hlsManifestUrl"]
                        if not sd.get("serverAbrStreamingUrl") and asd.get("serverAbrStreamingUrl"):
                            sd["serverAbrStreamingUrl"] = asd["serverAbrStreamingUrl"]
                        for f in asd.get("formats") or []:
                            m = f.get("mimeType", "")
                            u = f.get("url")
                            if u and any(x in m for x in ("mp4a", "opus", "vorbis")) and "video" in m:
                                if f not in (sd.get("formats") or []):
                                    sd.setdefault("formats", []).append(f)
                        if sd.get("hlsManifestUrl"):
                            break
            except Exception:
                pass
        return got

    def _player_watch(self, vid):
        try:
            r = self.session.get("https://www.youtube.com/watch?v=" + vid + "&hl=en",
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                                          "Accept-Language": "en-US,en;q=0.9"}, timeout=15)
            if r.status_code != 200:
                return None
            m = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var|const|</script>)', r.text, re.S)
            if not m:
                return None
            d = json.loads(m.group(1))
            if ((d.get("playabilityStatus") or {}).get("status") == "OK" and d.get("streamingData")):
                d.setdefault("_client_ua", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
                return d
        except Exception:
            pass
        return None

    def _parse_vr(self, vr):
        t = vr.get("title", {})
        title = "".join(x.get("text", "") for x in t.get("runs", [])) or t.get("simpleText", "")
        dur_txt = vr.get("lengthText", {}).get("simpleText", "")
        views = vr.get("viewCountText", {}).get("simpleText", "")
        pub = vr.get("publishedTimeText", {}).get("simpleText", "")
        owner_runs = vr.get("ownerText", {}).get("runs", [{}])
        owner = owner_runs[0].get("text", "") if owner_runs else ""
        thumbs = vr.get("thumbnail", {}).get("thumbnails", [])
        pic = thumbs[-1].get("url", "") if thumbs else ""
        pic = pic.replace("/default.jpg", "/hqdefault.jpg")
        remarks = dur_txt or pub or views
        return {"vod_id": vr.get("videoId", ""), "vod_name": title, "vod_pic": pic,
                "vod_remarks": remarks, "vod_year": pub, "vod_area": owner,
                "vod_content": (title + " " + views).strip()}
