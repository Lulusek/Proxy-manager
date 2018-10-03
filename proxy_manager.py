import requests
import re
import traceback
import pickle
import threading
import time
import fili_links
from requests_html import HTMLSession
from urllib.request import urlopen

#handling specific exceptions
import atexit

s = HTMLSession() #i need global htmlsession bcs i can't create new one in thread other than main
s.browser					#https://github.com/kennethreitz/requests-html/issues/155


MAX_SIZE = 40
MIN_SIZE = 10

proxies = []
proxy_rank = {}

#RUN ON THREAD

def get_proxies_from_file(): #call after getting proxies
	curr_proxies = []
	curr_rank = {}
	try:
		with open('proxy_rank.txt', 'rb') as f:
			curr_rank = pickle.load(f)
			
		curr_proxies = list(curr_rank.keys())
	
	except:
		print(traceback.format_exc())
		print("Can't load proxies... Initializing...")
		#curr_rank = get_fresh_rank(curr_proxies)
		
	finally:
		return curr_proxies, curr_rank 

def get_fresh_rank(proxies): 
	print('Initializing proxy rank')
	curr_rank = {}
	for i in range(len(proxies)):
		curr_rank[proxies[i]] = 0
	return curr_rank
	
def rank_proxy(proxy, points):
	proxy_rank[proxy] += points
	if proxy_rank[proxy] >= 100:
			proxy_rank[proxy] = 100
	elif proxy_rank[proxy] <= -100:
			#proxy_rank[proxy] = -100
			del_proxy(proxy)
	save_proxies()

	
def get_proxies_from_web(amount=50):
	amount_val = 1
	if amount <= 30:
		amount_val = 0
	elif amount <= 50:
		amount_val = 1
	elif amount <= 100:
		amount_val = 2
	elif amount <= 200:
		amount_val = 3
	elif amount <= 300:
		amount_val = 4
	else:
		amount_val = 5
		
	url = 'http://spys.one/free-proxy-list/PL/'
	headers = {
					'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
					'Host': 'spys.one',
					'Content-Length': '29',
					'Content-Type': 'application/x-www-form-urlencoded'
					}

	data = f'xpp={amount_val}&xf1=0&xf2=1&xf4=0&xf5=1' #xf2=ssl,xf5=http
	
	#with HTMLSession() as s:
	site = s.post(url, headers=headers, data=data)
	site.html.render(reload=False)#, keep_page=True) #without reload it will download site again WITHOUT data=data 
																									 #keep page to be sure about closing chromium

	html = site.html.html
	
	#with open('a.html', 'w+') as f:
	#	f.write(html)
	
	#s.close()
	
	matching_proxies = re.findall('<font class="spy\d\d">([\d.]+)<script type="text/javascript">.+?</font>(\d+)</font>', html) 
	full_proxies = [ip + ':' + proxy for ip, proxy in matching_proxies]
	#print(full_proxies)
	return full_proxies


test_url = 'https://fili.cc/embed?type=episode&code=585107ee991f90203df583ca&code2=585107ee991f90203df583d7&salt=5b700f1e88beda06d556ca26'
CHANGING_URL = False
def check_proxy(proxy):
	my_proxy = {'https': 'http://' + str(proxy)}
	headers = {
					'Connection': 'close',
					'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0'
					}
	try:
		while CHANGING_URL:
			time.sleep(0.1)
			
		with requests.get(test_url, headers=headers, proxies=my_proxy, timeout=5) as r:
			#print(r.headers)
			if not 'Content-Encoding' in r.headers: #test url is bad
				if not CHANGING_URL:
					change_test_url()
			if r.ok:
				re.search("var url = '(.+)';", r.text).group(1) #i need to be sure it can avoid captcha
				#print(proxy, 'works good, response time:', r.elapsed.total_seconds())
				return True
			else:
				return False
	except:
		#print(traceback.format_exc())
		#print(proxy, "works bad")
		return False
		

def change_test_url():
	print('Changing test url')
	global CHANGING_URL
	CHANGING_URL = True
	global test_url
	test_url = fili_links.get('https://fili.cc/serial/forever/s01e02/look-before-you-leap/588', s)[0]
	print('test url:', test_url)
	CHANGING_URL = False
	
	
def add_proxy(new_proxy):
	if len(proxies)+1 > MAX_SIZE: #+1 bcs i'll add new one
		for i in range(len(proxies)+1 - MAX_SIZE):
			index = proxies.index(get_sorted_proxies().pop())
			proxy_to_del = proxies[index]
			del_proxy(proxy_to_del)

	proxies.append(new_proxy)
	proxy_rank[new_proxy] = 0
	
	save_proxies()

	
def del_proxy(proxy):
	print('Deleting proxy:', proxy)
	if proxy in proxies:
		del proxies[proxies.index(proxy)]
	if proxy in proxy_rank:
		del proxy_rank[proxy]
	
	if len(proxies) < MIN_SIZE:
		Appender(MAX_SIZE-MIN_SIZE).append_new_proxies()
		
	save_proxies()


def get_sorted_proxies():
	if not proxies:
		Appender(MAX_SIZE).start()
		
	sorted_rank = sorted(proxy_rank.items(), key=lambda kv: kv[1], reverse=True)
	sorted_proxies = []

	for proxy, rank in sorted_rank:
		sorted_proxies.append(proxy)
	return sorted_proxies
		
		
def save_proxies():
	try:
		with open('proxy_rank.txt', 'wb') as f:
			pickle.dump(proxy_rank, f, protocol=0)
	except:
		print(traceback.format_exc())
		print("Can't save rank")

		
class Appender():
	def __init__(self, count):
		self.count = count
		self.unique_id = str(time.time()) #for compatibility when few Appender works simultaneously
		
		
	def stop(self):
		self.stop = True
		
		
	def append_new_proxies(self, check_all=False):
		self.proxies_added = []
		self.stop = False
		
		if check_all == False:
			self.amount = 50
			self.threads = 50
		else:
			self.amount = 500
			self.threads = 500 #to fasten
			
		new_proxies = [proxy for proxy in get_proxies_from_web(self.amount) if proxy not in proxies]

		if new_proxies:
			#checking if there is at least 1 proxy for each chunk, if no - shrink threads to max
			if not len(new_proxies) > self.threads:
				self.threads = len(new_proxies)

			for i in range(self.threads):
				start = len(new_proxies)//self.threads * i
				end = len(new_proxies)//self.threads * (i+1)
				
				#FOR CHECKING ALL NEW PROXIES WHEN DIVISION IS WITH REST
				if i == self.threads-1:
					end = len(new_proxies)
					
				new_proxies_chunk = new_proxies[start:end]
				thread_name = self.unique_id + 'AppChunk' + str(i)
				threading.Thread(name=thread_name, target=self.__chunk, args=(new_proxies_chunk,), daemon=True).start()
				
			while len(self.proxies_added) <= self.count:
				app_chunks_len = len([thread for thread in threading.enumerate() if thread.name.startswith(self.unique_id +'AppChunk')])
				
				#print(app_chunks_len)
				if app_chunks_len == 0:
					break
				time.sleep(0.3)
				
			#stop working threads bcs i already have needed proxies
			self.stop = True 

		if len(self.proxies_added) < self.count:
			if check_all == False: #to be sure check_all won't be called x times bcs it can do infinity loop
				print("Got only " + str(len(self.proxies_added)) + " proxies, trying again...")
				self.count = self.count-len(self.proxies_added)
				self.append_new_proxies(check_all=True)
			else:
				print("Can't find all proxies, got only " + str(len(self.proxies_added)))
		
		
	def __chunk(self, new_proxies): #__chunk gets chunk of new_proxies
		for proxy in new_proxies:
			if len(self.proxies_added) >= self.count or self.stop:
				break
			if check_proxy(proxy):
				self.proxies_added.append(proxy)
				if not self.stop: #to be sure
					add_proxy(proxy)
							

class Supervisor():
	def start(self):
		chunks_len = MAX_SIZE//10
		
		for i in range(chunks_len):
			start = MAX_SIZE//chunks_len * i
			end = MAX_SIZE//chunks_len * (i+1) - 1 #-1 bcs start and end can't have the same index
						
			if i == chunks_len-1:
				end = MAX_SIZE
			
			threading.Thread(name='Spv'+str(i), target=self.__chunk, args=(start, end), daemon=True).start()
			
			
	def stop(self):
		self.stop = True
		
		
	def __chunk(self, start, end):
		while True:
			if self.stop == True:
				break
			
			while not self.have_connection():
				time.sleep(3)
				
			time.sleep(1)
			
			curr_start = start
			curr_end = end
			
			if not start <= len(proxies):
				continue
			if not end <= len(proxies): 
				curr_end = len(proxies)
			
			for i in range(curr_start, curr_end):
				try:
					curr_proxy = proxies[i]
					if check_proxy(curr_proxy):
						#print('Good proxy', curr_proxy)
						if curr_proxy in proxy_rank: #bcs it can be changed
							rank_proxy(curr_proxy, 5)
					else:
						#print('Bad proxy', curr_proxy)
						if curr_proxy in proxy_rank:
							rank_proxy(curr_proxy, -5)
				except IndexError: #can occur when something is deleting on thread
					print('IndexError (its still ok)')
					break
		
	def have_connection(self):
		try:
			with urlopen(url='https://google.pl'): # mam internet, więc zawinił jakiś z komponentów
				pass
			return True
		except:
			print('NIE MAM POŁĄCZENIA Z NETEM')
			return False
		
def wait_for_main_thread():
	print('CLOSING PROXY MANAGER')
	s.browser.close()
	s.close()

	
#atexit.register(wait_for_main_thread) #https://stackoverflow.com/questions/45267439/fatal-python-error-and-bufferedwriter
def start():
	global proxies
	global proxy_rank
	if not proxies:
		proxies, proxy_rank = get_proxies_from_file()


		if len(proxies) < (MAX_SIZE+MIN_SIZE)/2:
			Appender((MAX_SIZE+MIN_SIZE)-len(proxies)).append_new_proxies()

		#print(get_proxies_from_web(100))
		Supervisor().start()

	# for proxy in proxies:
		# check_proxy(proxy)

	#time.sleep(10)



