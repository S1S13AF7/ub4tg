# -*- coding: utf-8 -*-
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime

BASE_PY_DIR = r"D:\Misc\projects\Python"
LOCAL_TG_DIR = r"D:\Misc\projects\localhost\tg"
DEFAULT_SYNC_URL = "https://" + "misc.pp.ua" + "/files/0.php"
SCR_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_PATH = os.path.join(SCR_DIR, "push.json")
LOG_PATH = os.path.join(SCR_DIR, "push.txt")

log_lines = []

def log_msg(text: str):
	print(text)
	log_lines.append(text)

def flush_log():
	try:
		dt_now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
		header = f"=== PUSH LOG | {dt_now} ==="
		body = "\n".join([header] + log_lines) + "\n"
		with open(LOG_PATH, "w", encoding="utf-8-sig") as lf:
			lf.write(body)
	except Exception as e:
		print(f"⚠️ Помилка запису {LOG_PATH}: {e}")

def load_push_conf() -> dict:
	conf = {
		"sync_url": DEFAULT_SYNC_URL,
		"tunnel_url": ""
	}
	need_save = False
	if os.path.isfile(CONF_PATH):
		try:
			with open(CONF_PATH, "r", encoding="utf-8-sig") as rf:
				raw = json.load(rf)
				if isinstance(raw, dict):
					for k in conf:
						val = raw.get(k)
						if isinstance(val, str):
							conf[k] = val.strip()
						else:
							need_save = True
					for k, v in raw.items():
						if k not in conf:
							conf[k] = v
				else:
					need_save = True
		except Exception:
			need_save = True
	else:
		need_save = True
	
	if not conf["sync_url"]:
		conf["sync_url"] = DEFAULT_SYNC_URL
		need_save = True
	
	if need_save:
		try:
			with open(CONF_PATH, "w", encoding="utf-8") as wf:
				json.dump(conf, wf, ensure_ascii=False, indent="\t")
		except Exception:
			pass
	
	return conf

def derive_zip_url(sync_url: str) -> str:
	if re.search(r"/[^/?#]+\.php(?:[?#]|$)", sync_url, re.IGNORECASE):
		return re.sub(
			r"/[^/?#]+\.php(?=[?#]|$)",
			"/0.zip",
			sync_url,
			count=1,
			flags=re.IGNORECASE
		)
	return sync_url.rstrip("/") + "/0.zip"

def get_ngrok_https_url(fallback_tunnel: str) -> str:
	api_urls = [
		"http://" + "127.0.0.1" + ":4040/api/tunnels",
		"http://" + "localhost" + ":4040/api/tunnels",
	]
	for api_url in api_urls:
		try:
			req = urllib.request.Request(
				api_url,
				headers={"User-Agent": "push0/1.0"}
			)
			with urllib.request.urlopen(req, timeout=3) as resp:
				data = json.loads(resp.read().decode("utf-8", errors="replace"))
			tunnels = data.get("tunnels") or []
			for t in tunnels:
				if isinstance(t, dict):
					pub = str(t.get("public_url") or "").strip()
					if pub.startswith("https://") and "ngrok" in pub.lower():
						return pub.rstrip("/")
		except Exception:
			continue
	
	return fallback_tunnel.strip().rstrip("/")

def is_remote_up_to_date(local_zip: str, remote_zip_url: str) -> bool:
	l_st = os.stat(local_zip)
	l_ts = int(l_st.st_mtime)
	l_size = int(l_st.st_size)
	
	try:
		req = urllib.request.Request(
			remote_zip_url,
			method="HEAD",
			headers={
				"User-Agent": "push0/1.0",
				"Cache-Control": "no-cache"
			}
		)
		with urllib.request.urlopen(req, timeout=15) as resp:
			if resp.status != 200:
				return False
			lm = resp.headers.get("Last-Modified")
			cl = resp.headers.get("Content-Length")
			r_ts = int(parsedate_to_datetime(lm).timestamp()) if lm else 0
			r_size = int(cl) if (cl and cl.isdigit()) else 0
			
			if r_ts >= l_ts and r_size == l_size:
				log_msg(
					f"ℹ️ На сервері вже актуальний 0.zip "
					f"({r_size} байт, ts={r_ts}). Пропускаю."
				)
				return True
	except Exception as e:
		log_msg(f"⚠️ Не вдалося отримати заголовки віддаленого 0.zip: {e}")
	
	return False

def parse_xhtml_status(body: str) -> str:
	h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.IGNORECASE | re.DOTALL)
	title_txt = re.sub(r"<[^>]+>", "", h1_m.group(1)).strip() if h1_m else ""
	
	divs = re.findall(r"<div[^>]*>(.*?)</div>", body, re.IGNORECASE | re.DOTALL)
	detail_txt = ""
	for d_html in divs:
		cand = re.sub(r"<[^>]+>", "", str(d_html)).strip()
		if cand and cand != ".." and cand != title_txt:
			detail_txt = cand
			break
	
	if title_txt and detail_txt:
		return f"{title_txt} — {detail_txt}"
	return title_txt or detail_txt or body.strip()[:200]

def main():
	try:
		conf = load_push_conf()
		sync_url = conf["sync_url"]
		remote_zip_url = derive_zip_url(sync_url)
		
		src_zip = os.path.join(BASE_PY_DIR, "0.zip")
		if not os.path.isfile(src_zip):
			log_msg(f"❌ Архів не знайдено: {src_zip}")
			sys.exit(1)
		
		if not os.path.isdir(LOCAL_TG_DIR):
			log_msg(f"❌ Локальна тека тунелю не знайдена: {LOCAL_TG_DIR}")
			sys.exit(1)
		
		dst_zip = os.path.join(LOCAL_TG_DIR, "0.zip")
		need_copy = True
		if os.path.isfile(dst_zip):
			src_st = os.stat(src_zip)
			dst_st = os.stat(dst_zip)
			if (
				src_st.st_size == dst_st.st_size
				and int(src_st.st_mtime) == int(dst_st.st_mtime)
			):
				need_copy = False
		
		if need_copy:
			try:
				shutil.copy2(src_zip, dst_zip)
				log_msg(f"📋 Оновлено локальну копію: {dst_zip}")
			except Exception as e:
				log_msg(f"❌ Помилка копіювання у {dst_zip}: {e}")
				sys.exit(1)
		
		if is_remote_up_to_date(dst_zip, remote_zip_url):
			sys.exit(0)
		
		tunnel_base = get_ngrok_https_url(conf["tunnel_url"])
		if not tunnel_base:
			log_msg(
				"⚠️ Активний HTTPS-тунель ngrok не знайдено.\n"
				f"   Можеш вписати його вручну у {CONF_PATH}"
			)
			sys.exit(0)
		
		zip_tunnel_url = f"{tunnel_base}/tg/0.zip"
		encoded_url = urllib.parse.quote(str(zip_tunnel_url), safe="")
		sep = "&" if "?" in sync_url else "?"
		req_url = f"{sync_url}{sep}url={encoded_url}"
		log_msg("🚀 Надсилаю запит синхронізації на сервер...")
		
		req = urllib.request.Request(
			req_url,
			headers={"User-Agent": "push0/1.0"}
		)
		try:
			with urllib.request.urlopen(req, timeout=65) as resp:
				body = resp.read().decode("utf-8", errors="replace")
				log_msg(f"✅ Відповідь сервера: {parse_xhtml_status(body)}")
		except urllib.error.HTTPError as e:
			body = e.read().decode("utf-8", errors="replace")
			info = parse_xhtml_status(body)
			if e.code == 422:
				log_msg(f"ℹ️ Сервер: {info}")
			else:
				log_msg(f"⚠️ HTTP {e.code}: {info}")
		except Exception as e:
			log_msg(f"❌ Помилка запиту: {e}")
	finally:
		flush_log()

if __name__ == "__main__":
	main()
