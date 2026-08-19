# -*- coding: utf-8 -*-
import colorsys
import json
import random
import re
import sys
import threading
import time
import requests
import urllib3
urllib3.disable_warnings()
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import unpad
from pyquery import PyQuery as pq
from base64 import b64decode, b64encode
from pprint import pprint
from urllib.parse import urlparse, quote, unquote
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend="{}"):
        self.domin='https://cg51.com'
        self.proxies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }
        self.host=self.host_late(self.gethosts())
        if not self.host:
            self.host=self.domin
        self.headers.update({'Origin': self.host, 'Referer': f"{self.host}/"})
        thread = threading.Thread(target=self.getcnh)
        thread.start()

    def log(self, *args):
        try:
            print(*args)
        except Exception:
            pass

    def getName(self):
        return '51吸瓜'

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        data=pq(requests.get(self.host, headers=self.headers,proxies=self.proxies, verify=False).content)
        result = {}
        classes = []
        for k in list(data('.navbar-nav.mr-auto').children('li').items())[1:-3]:
            if k('ul'):
                for j in k('ul li').items():
                    classes.append({
                        'type_name': j('a').text(),
                        'type_id': j('a').attr('href').strip(),
                    })
            else:
                classes.append({
                    'type_name': k('a').text(),
                    'type_id': k('a').attr('href').strip(),
                })
        result['class'] = classes
        result['list'] = self.getlist(data('#index article a'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        if '@folder' in tid:
            id=tid.replace('@folder','')
            videos=self.getfod(id)
        else:
            pg=int(pg or '1')
            tid=str(tid).strip('/')
            url=f"{self.host}/{tid}/" if pg==1 else f"{self.host}/{tid}/{pg}/"
            data=pq(requests.get(url, headers=self.headers,proxies=self.proxies, verify=False).content)
            videos=self.getlist(data('#archive article a'),tid)
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 1 if '@folder' in tid else 99999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        url=ids[0] if ids[0].startswith("http") else f"{self.host}{ids[0]}"
        data=pq(requests.get(url, headers=self.headers,proxies=self.proxies, verify=False).content)
        vod = {'vod_play_from': '51吸瓜'}
        did = data('script[data-api]').attr('data-api') or ''
        try:
            clist = []
            if data('.tags .keywords a'):
                for k in data('.tags .keywords a').items():
                    title = k.text()
                    href = k.attr('href')
                    clist.append('[a=cr:' + json.dumps({'id': href, 'name': title}) + '/]' + title + '[/a]')
            vod['vod_content'] = ' '.join(clist)
        except:
            vod['vod_content'] = data('.post-title').text()
        try:
            plist=[]
            if data('.dplayer'):
                for c, k in enumerate(data('.dplayer').items(), start=1):
                    config = json.loads(k.attr('data-config'))
                    plist.append(f"视频{c}${did}_dm_{config['video']['url']}")
            vod['vod_play_url']='#'.join(plist)
        except:
            vod['vod_play_url']=f"可能没有视频${url}"
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=pq(requests.get(f"{self.host}/search/{quote(key)}/", headers=self.headers,proxies=self.proxies, verify=False).content)
        return {'list':self.getlist(data('#archive article a')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        # id 形如: <did>_dm_<真实m3u8URL>
        # 直接返回真实 m3u8, 避免经 9978 proxy 时
        # TVBox M3u8Proxy 把 URL 内嵌的 &v=&time= 拆散导致 400
        pid = id
        if '_dm_' in id:
            _, pid = id.split('_dm_', 1)
        return {'parse': 0, 'url': pid, 'header': self.headers}

    def localProxy(self, param):
        try:
            xtype=param.get('type','')
            if 'm3u8' in xtype:
                path,url=unquote(param['pdid']).split('_dm_')
                data=requests.get(url, headers=self.headers,proxies=self.proxies,timeout=10, verify=False).text
                lines = data.strip().split('\n')
                times=0.0
                for i in lines:
                    if i.startswith('#EXTINF:'):
                        times+=float(i.split(':')[-1].replace(',',''))
                thread = threading.Thread(target=self.some_background_task, args=(path,int(times)))
                thread.start()
                print('[INFO] 获取视频时长成功', times)
                return [200, 'text/plain', data]
            elif 'xdm' in xtype:
                url=f"{self.host}{unquote(param['path'])}"
                res = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10, verify=False).json()
                dms=[]
                for k in res:
                    text=k.get('text')
                    children=k.get('children')
                    if text:dms.append(text.strip())
                    if children:
                        for j in children:
                            ctext=j.get('text')
                            if ctext:
                                ctext=ctext.strip()
                                if "@" in ctext:
                                    dms.append(ctext.split(' ',1)[-1].strip())
                                else:
                                    dms.append(ctext)
                return self.xml(dms,int(param['times']))
            url=self.d64(param['url'])
            match = re.search(r"loadBannerDirect\('([^']*)'", url)
            if match:
                url=match.group(1)
            res = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=10, verify=False)
            return [200, res.headers.get('Content-Type'), self.aesimg(res.content)]
        except Exception as e:
            print(e)
            return [500, 'text/html', '']

    def some_background_task(self,path,times):
        try:
            time.sleep(1)
            purl=f"{self.getProxyUrl()}&path={quote(path)}&times={times}&type=xdm"
            self.fetch(f"http://127.0.0.1:9978/action?do=refresh&type=danmaku&path={quote(purl)}")
        except Exception as e:
            print(e)

    def xml(self, dms,times):
        try:
            tsrt=f'共有{len(dms)}条弹幕来袭！！！'
            danmustr = f'<?xml version="1.0" encoding="UTF-8"?>\n<i>\n\t<chatserver>chat.xtdm.com</chatserver>\n\t<chatid>88888888</chatid>\n\t<mission>0</mission>\n\t<maxlimit>99999</maxlimit>\n\t<state>0</state>\n\t<real_name>0</real_name>\n\t<source>k-v</source>\n'
            danmustr += f'\t<d p="0,5,25,16711680,0">{tsrt}</d>\n'
            for i in range(len(dms)):
                base_time = (i / len(dms)) * times
                dm0 = base_time + random.uniform(-3, 3)
                dm0 = round(max(0, min(dm0, times)), 1)
                dm2 = self.get_color()
                dm4 = re.sub(r'[<>&\u0000\b]', '', dms[i])
                tempdata = f'\t<d p="{dm0},1,25,{dm2},0">{dm4}</d>\n'
                danmustr += tempdata
            danmustr += '</i>'
            return [200, "text/xml", danmustr]
        except Exception as e:
            print(e)
            return [500, 'text/html', '']

    def get_color(self):
        # 10% 概率随机颜色, 90% 概率白色
        if random.random() < 0.1:
            h = random.random()
            s = random.uniform(0.7, 1.0)
            v = random.uniform(0.8, 1.0)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            r = int(r * 255)
            g = int(g * 255)
            b = int(b * 255)
            decimal_color = (r << 16) + (g << 8) + b
            return str(decimal_color)
        else:
            return '16777215'

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def gethosts(self):
        """从 cg51 发布站 appConfig 解密获取线路域名列表"""
        try:
            curl = self.getCache('host_51cn')
        except Exception:
            curl = ''
        if curl:
            try:
                data = pq(requests.get(curl, headers=self.headers, proxies=self.proxies, verify=False).content)('a').attr('href')
                if data:
                    parsed_url = urlparse(data)
                    return parsed_url.scheme + "://" + parsed_url.netloc
            except Exception:
                pass
        try:
            page = requests.get(self.domin, headers=self.headers, proxies=self.proxies, verify=False).text
            # 有效定义: 行首非注释的 window.appConfig = {
            m = re.search(r'(?m)^\s*window\.appConfig\s*=\s*\{', page)
            if not m:
                raise Exception("未找到appConfig")
            seg = page[m.start():]
            datas = re.findall(r'(?m)^\s*data:\s*"([^"]+)"', seg)
            keys = re.findall(r'(?m)^\s*key:\s*"([^"]+)"', seg)
            if not datas:
                raise Exception("未找到appConfig.data")
            data_b64 = datas[-1]
            key_str = keys[-1] if keys else '0726001'
            raw = b64decode(data_b64)
            iv = raw[:16]
            ct = raw[16:]
            # sha256(key) 解密 appConfig; 优先 Crypto.Hash (兼容无 hashlib 的 TVBox 环境)
            try:
                key = SHA256.new(key_str.encode()).digest()
            except Exception:
                key = b'\x42\x4b\xe2\x21\x31\x02\x4a\xbd\x0a\x7f\x2a\xff\xf6\xe8\x1c\xe9\x23\x0b\xfa\xa2\x59\xc9\x8f\x26\xdd\xda\xbb\x28\xdc\xa1\xa4\xe0'
            cipher = AES.new(key, AES.MODE_CBC, iv)
            text = unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
            cfg = json.loads(text)
            hosts = []
            for d in cfg.get('domain', []):
                v = d.get('value', '')
                if v:
                    hosts.append(v.rstrip('/'))
            for d in cfg.get('backup_domain', []):
                v = d.get('value', '')
                if v:
                    hosts.append(v.rstrip('/'))
            if hosts:
                self.log(f"cg51线路: {hosts}")
                return hosts
            raise Exception("线路为空")
        except Exception as e:
            self.log(f"获取: {str(e)}")
            return ""

    def getcnh(self):
        try:
            if not self.host:
                return
            url = f"{self.host}/homeway.html"
            data = pq(requests.get(url, headers=self.headers, proxies=self.proxies, timeout=8, verify=False).content)
            a = data('.post-content[itemprop="articleBody"] blockquote p').eq(0)('a')
            href = a.attr('href')
            if href:
                parsed_url = urlparse(href)
                host = parsed_url.scheme + "://" + parsed_url.netloc
                if host:
                    try:
                        self.setCache('host_51cn', host)
                    except Exception:
                        pass
        except Exception as e:
            self.log(f"getcnh: {e}")

    def hstr(self, html):
        pattern = r"(backupLine\s*=\s*\[\])\s+(words\s*=)"
        replacement = r"\1, \2"
        html = re.sub(pattern, replacement, html)
        data = f"""
        var Vx = {{
            range: function(start, end) {{
                const result = [];
                for (let i = start; i < end; i++) {{
                    result.push(i);
                }}
                return result;
            }},

            map: function(array, callback) {{
                const result = [];
                for (let i = 0; i < array.length; i++) {{
                    result.push(callback(array[i], i, array));
                }}
                return result;
            }}
        }};

        Array.prototype.random = function() {{
            return this[Math.floor(Math.random() * this.length)];
        }};

        var location = {{
            protocol: "https:"
        }};

        function executeAndGetResults() {{
            var allLines = lineAry.concat(backupLine);
            var resultStr = JSON.stringify(allLines);
            return resultStr;
        }};
        {html}
        executeAndGetResults();
        """
        return self.p_qjs(data)

    def p_qjs(self, js_code):
        try:
            from com.whl.quickjs.wrapper import QuickJSContext
            ctx = QuickJSContext.create()
            result_json = ctx.evaluate(js_code)
            ctx.destroy()
            return json.loads(result_json)
        except Exception:
            pass
        try:
            return self.host_from_js(js_code)
        except Exception as e:
            self.log(f"线路解析失败: {e}")
            return []

    def host_from_js(self, js_code):
        words = re.search(r"words\s*=\s*'([^']+)'\s*\.split\(\s*',\s*'\s*\)", js_code)
        if not words:
            raise Exception("未找到words")
        words = words.group(1).split(',')
        if not words:
            raise Exception("words为空")
        domains = []
        for m in re.finditer(r"(?:lineAry|backupLine)\s*=\s*Vx\.map\(\s*Vx\.range\(\s*(\d+)\s*,\s*(\d+)\s*\)", js_code):
            seg = js_code[m.start():m.start()+400]
            sfx = re.search(r"words\.random\(\)\s*\+\s*'\.([^']+)'", seg)
            if not sfx:
                continue
            for _ in range(max(int(m.group(2))-int(m.group(1)), 0)):
                domains.append("https://" + random.choice(words) + "." + sfx.group(1))
        if not domains:
            raise Exception("未找到线路")
        return domains

    def get_domains(self):
        html = pq(requests.get(self.domin, headers=self.headers,proxies=self.proxies, verify=False).content)
        html_pattern = r"Base64\.decode\('([^']+)'\)"
        html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
        if not html_match:
            raise Exception("未找到html")
        html = b64decode(html_match.group(1)).decode()
        words_pattern = r"words\s*=\s*'([^']+)'"
        words_match = re.search(words_pattern, html, re.DOTALL)
        if not words_match:
            raise Exception("未找到words")
        words = words_match.group(1).split(',')
        main_pattern = r"lineAry\s*=.*?words\.random\(\)\s*\+\s*'\.([^']+)'"
        domain_match = re.search(main_pattern, html, re.DOTALL)
        if not domain_match:
            raise Exception("未找到主域名")
        domain_suffix = domain_match.group(1)
        domains = []
        for _ in range(3):
            random_word = random.choice(words)
            domain = f"https://{random_word}.{domain_suffix}"
            domains.append(domain)
        return domains

    def getfod(self, id):
        url = f"{self.host}{id}"
        data = pq(requests.get(url, headers=self.headers, proxies=self.proxies, verify=False).content)
        vdata=data('.post-content[itemprop="articleBody"]')
        r=['.txt-apps','.line','blockquote','.tags','.content-tabs']
        for i in r:vdata.remove(i)
        h2s=[h.text() for h in vdata('h2').items()]
        ps=list(vdata('p').items())
        videos=[]
        hi=0
        for idx, p in enumerate(ps):
            a=p('a').attr('href')
            if not a:
                continue
            img=''
            if idx+1 < len(ps):
                img=ps[idx+1]('img').attr('data-xkrkllgl') or ''
            name=(p.text() or '').strip()
            remarks=h2s[hi] if hi < len(h2s) else ''
            video={
                'vod_id': a,
                'vod_name': name if name else remarks,
                'vod_pic': '',
                'vod_remarks': remarks
            }
            if img:
                video['vod_pic']=f"{self.getProxyUrl()}&url={self.e64(img)}"
            videos.append(video)
            hi+=1
        return videos

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',') if u.strip()]
        else:
            urls = list(url_list)

        if not urls:
            return ''

        if len(urls) <= 1:
            return urls[0]

        results = {}
        threads = []

        def test_host(url):
            try:
                start_time = time.time()
                # 用 GET 跟随跳转, 取最终可达域名 (线路会按路径随机跳子域)
                response = requests.get(url, headers=self.headers, proxies=self.proxies, timeout=3.0, allow_redirects=True, verify=False)
                delay = (time.time() - start_time) * 1000
                if response.status_code == 200 and response.url:
                    results[url] = (delay, response.url)
                else:
                    results[url] = (float('inf'), url)
            except Exception as e:
                results[url] = (float('inf'), url)

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        best = min(results.items(), key=lambda x: x[1][0])
        final = best[1][1]
        parsed = urlparse(final)
        return parsed.scheme + "://" + parsed.netloc

    def getlist(self,data,tid=''):
        videos = []
        l='/mrdg' in tid
        for k in data.items():
            a=k.attr('href')
            b=k('h2').text()
            c=k('span[itemprop="datePublished"]').text()
            if a and b and c and a.startswith('/'):
                pic=k('script').text()
                videos.append({
                    'vod_id': f"{a}{'@folder' if l else ''}",
                    'vod_name': b.replace('\n', ' '),
                    'vod_pic': f"{self.getProxyUrl()}&url={self.e64(pic)}&type=img" if pic else '',
                    'vod_remarks': c,
                    'vod_tag':'folder' if l else '',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def aesimg(self, word):
        key = b'f5d965df75336270'
        iv = b'97b60394abc2fbe1'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(word), AES.block_size)
        return decrypted