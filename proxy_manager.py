import requests
import re
import traceback
import pickle
import threading
import time

#handling specific exceptions
import atexit
import gc

MAX_SIZE = 50
MIN_SIZE = 30

proxies = []
proxy_rank = {}

#RUN ON THREAD

def get_proxies_from_file():
	curr_proxies = []
	try:
		lines = [line.rstrip('\n') for line in open('proxies.txt')]
		for line in lines:
			curr_proxies.append(f'{line}')
			
	except FileNotFoundError:
		print("Can't find proxies.txt... Creating new one")
		
	finally:
		return curr_proxies

def get_rank_from_file(): #call after getting proxies
	try:
		with open('proxy_rank.txt', 'rb') as f:
			curr_rank = pickle.load(f)
			
		print(curr_rank)
		
		for proxy in proxies:
			if not proxy in curr_rank:
				curr_rank[proxy] = 0
		
		print(curr_rank)
		
		proxies_to_del_from_rank = []
		for proxy, rank in curr_rank.items():
			if not proxy in proxies:
				proxies_to_del_from_rank.append(proxy)
				
		for proxy in proxies_to_del_from_rank:
			del curr_rank[proxy]
		
		save_rank()
	
	except:
		print(traceback.format_exc())
		print("Can't load proxy rank... Initializing...")
		curr_rank = get_fresh_rank(proxies)
		
	finally:
		return curr_rank

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
	save_rank()

	
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

	with requests.post(url, headers=headers, data=data) as r:
		if r.ok:
			content = r.text #text is encoded
			new_proxies = re.findall('<font class=spy\d\d>([\d.]+)<script', content)
			return new_proxies[:amount]
		else:
			print("Can't get new proxies from site")
			return None


def check_proxy(proxy):
	my_proxy = {'https': 'http://' + str(proxy)}
	url = 'http://httpbin.org/get'#'https://www.google.pl/'
	try:
		with requests.get(url, proxies=my_proxy, timeout=0.2) as r:
			#print(r.headers)
			if r.ok:
				print(proxy, 'dziala, response time:', r.elapsed.total_seconds())
				return True
			else:
				return False
	except:
		#print(traceback.format_exc())
		print(proxy, 'nie działa')
		return False
		
		
def add_proxy(new_proxy):
	if len(proxies)+1 > MAX_SIZE: #+1 bcs i'll add new one
		sorted_proxies = get_sorted_proxies()
		for i in range(len(proxies)+1 - MAX_SIZE):
			index = proxies.index(sorted_proxies.pop())
			proxy_to_del = proxies[index]
			del_proxy(proxy_to_del)

	proxies.append(new_proxy)
	proxy_rank[new_proxy] = 0
	
	save_proxies()
	save_rank()
	
	
def del_proxy(proxy):
	print('Deleting proxy:', proxy)
	if proxy in proxies:
		del proxies[proxies.index(proxy)]
	if proxy in proxy_rank:
		del proxy_rank[proxy]
	
	if len(proxies) < MIN_SIZE:
		Appender(MAX_SIZE-MIN_SIZE).append_new_proxies()
		
	save_proxies()
	save_rank()

		
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
		with open('proxies.txt', 'w') as f:
			f.write('\n'.join(proxies))
			print('Proxies saved')
	except:
		print(traceback.format_exc())
		print("Can't save proxies")
		
		
def save_rank():
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
			self.threads = 10
		else:
			self.amount = 500
			self.threads = 20 #to fasten
			
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
			print("Got only " + str(len(self.proxies_added)) + " proxies, trying again...")
			self.count = self.count-len(self.proxies_added)
			self.append_new_proxies(check_all=True)
		
		
	def __chunk(self, new_proxies): #__chunk gets chunk of new_proxies
		for proxy in new_proxies:
			if len(self.proxies_added) > self.count or self.stop:
				break
			if check_proxy(proxy):
				add_proxy(proxy)
				self.proxies_added.append(proxy)
				

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
						rank_proxy(curr_proxy, 5)
					else:
						#print('Bad proxy', curr_proxy)
						rank_proxy(curr_proxy, -5)
				except IndexError: #can occur when something is deleting on thread
					print('IndexError')
					break
			
def wait_for_main_thread():
	pass
	# for obj in gc.get_objects():
		# if isinstance(obj, Supervisor):
			# obj.stop()
	
atexit.register(wait_for_main_thread) #https://stackoverflow.com/questions/45267439/fatal-python-error-and-bufferedwriter

proxies = get_proxies_from_file()

if proxies:
	proxy_rank = get_rank_from_file()
else:
	proxy_rank = get_fresh_rank(proxies)

if len(proxies) < MAX_SIZE:
	Appender(MAX_SIZE-len(proxies)).append_new_proxies()

s = Supervisor()
s.start()

time.sleep(5)

#s.stop()
print(get_sorted_proxies())
#print(threading.enumerate()[2])
#Supervisor().start()

#print(proxies)
#print(len(proxies))

#rank_proxy_init(proxies)
#proxy_rank = read_rank()

#zrobić przy get_sorted_proxies sprawdzanie czy są w ogóle jakieś proxies, jak nie ma to szybko zrobić je i zwrócić
#gdzieś przy proxy_rank jest luka, bo nie jest usuwany 