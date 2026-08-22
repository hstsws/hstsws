const HOST = "http://api.hclyz.com:81/mf";
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        const path = url.pathname;
        const params = url.searchParams;

        const m3uHeaders = {
            "Content-Type": "text/plain; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
        };

        const corsHeaders = {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        };

        if (request.method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        try {
            let action = params.get("ac") || path.replace("/", "");
            let tid = params.get("tid") || params.get("t") || "";
            let pg = params.get("pg") || params.get("page") || "1";

            if (action === "live.m3u" || action === "m3u" || path.endsWith(".m3u")) {
                const m3uString = await handleM3U();
                return new Response(m3uString, { headers: m3uHeaders });
            }

            if (tid) {
                return new Response(JSON.stringify(await handleCategory(tid)), { headers: corsHeaders });
            }

            if (action === "detail" || params.get("ids")) {
                let ids = params.get("ids") || "";
                return new Response(JSON.stringify(await handleDetail(ids)), { headers: corsHeaders });
            }

            if (action === "play") {
                let id = params.get("id") || "";
                return new Response(JSON.stringify(await handlePlay(id)), { headers: corsHeaders });
            }

            return new Response(JSON.stringify(await handleHome()), { headers: corsHeaders });

        } catch (err) {
            return new Response(JSON.stringify({ "list": [], "msg": err.message }), {
                status: 500,
                headers: corsHeaders
            });
        }
    }
};

async function handleHome() {
    try {
        const res = await fetch(`${HOST}/json.txt`, { headers: { "User-Agent": UA } });
        const json = await res.json();
        const data = json.pingtai || [];

        const classes = data.slice(1).map(item => {
            return {
                "type_id": item.address,
                "type_name": item.title
            };
        });

        return { "class": classes };
    } catch (e) {
        return { "class": [{ "type_id": "json.txt", "type_name": "⚠️ 列表加载失败" }] };
    }
}

async function handleCategory(tid) {
    try {
        const res = await fetch(`${HOST}/${tid}`, { headers: { "User-Agent": UA } });
        const json = await res.json();
        const zhubo = json.zhubo || [];

        const videos = zhubo.map(vod => {
            const packId = btoa(encodeURIComponent(`${vod.title}|||${vod.address}`));
            // 主播实时封面，取不到时回退占位图
            const pic = (vod.img || "").trim() || "https://raw.githubusercontent.com/fish2018/lib/refs/heads/main/imgs/live.png";
            return {
                "vod_id": packId,
                "vod_name": vod.title,
                "vod_pic": pic,
                "vod_remarks": "📡 在线直播中"
            };
        });

        return {
            "page": 1,
            "pagecount": 1,
            "limit": videos.length,
            "total": videos.length,
            "list": videos
        };
    } catch (e) {
        return { "list": [] };
    }
}

async function handleDetail(ids) {
    try {
        const decoded = decodeURIComponent(atob(ids));
        const [title, address] = decoded.split("|||");

        return {
            "list": [{
                "vod_id": ids,
                "vod_name": title,
                "vod_pic": "",
                "vod_remarks": "国内大秀",
                "vod_content": `欢迎观赏国内聚合直播大秀，当前主播：${title}。全量超低延迟流媒体架构开发，技术发布源：TG频道 @stymei。`,
                "vod_play_from": "✈️ 頻道@stymei",
                "vod_play_url": `原生原画高清流$${address}`
            }]
        };
    } catch (e) {
        return { "list": [] };
    }
}

async function handlePlay(id) {
    return {
        "parse": 0,
        "url": id
    };
}

async function handleM3U() {
    let m3uResult = "#EXTM3U x-tvg-url=\"\"\n";
    try {
        const res = await fetch(`${HOST}/json.txt`, { headers: { "User-Agent": UA } });
        const json = await res.json();
        const platforms = (json.pingtai || []).slice(1);

        platforms.sort((a, b) => parseInt(b.Number || 0) - parseInt(a.Number || 0));

        const topPlatforms = platforms.slice(0, 24);

        const promises = topPlatforms.map(async (p) => {
            try {
                const subRes = await fetch(`${HOST}/${p.address}`, { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(4000) });
                const subJson = await subRes.json();

                // 平台 logo 兜底（xinimg 原样使用，不再做坏的 replace）
                const fallbackLogo = p.xinimg || "";

                return {
                    platformTitle: p.title,
                    fallbackLogo: fallbackLogo,
                    anchors: subJson.zhubo || []
                };
            } catch (err) {
                return null;
            }
        });

        const results = await Promise.all(promises);

        results.forEach(item => {
            if (!item) return;
            item.anchors.forEach(vod => {
                // 每个频道优先用主播自己的实时封面 img，取不到再回退平台 logo
                const logo = (vod.img || "").trim() || item.fallbackLogo;
                m3uResult += `#EXTINF:-1 tvg-logo="${logo}" group-title="${item.platformTitle}",${vod.title}\n`;
                m3uResult += `${vod.address}\n`;
            });
        });

    } catch (e) {
        m3uResult += `#EXTINF:-1 group-title="错误",网络列表加载失败\nhttp://0.0.0.0\n`;
    }
    return m3uResult;
}
