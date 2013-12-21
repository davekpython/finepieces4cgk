import os
import re
import random
import hashlib
import hmac
import logging
import json
from string import letters
import webapp2
import jinja2
from datetime import datetime, timedelta, tzinfo
import pdb
import sys

from google.appengine.api import memcache
from google.appengine.ext import db, blobstore
from google.appengine.ext.webapp.blobstore_handlers import BlobstoreUploadHandler, BlobstoreDownloadHandler

# itertools

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
								autoescape = True)

secret = 'smile'
								
def render_str(template, **params):
	t = jinja_env.get_template(template)
	return t.render(params)
	
def make_secure_val(val):
	return '%s|%s' % (val, hmac.new(secret, val).hexdigest())
	
def check_secure_val(secure_val):
	val = secure_val.split('|')[0]
	if secure_val == make_secure_val(val):
		return val
		
class BlogHandler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)
		
	def render_str(self, template, **params):
		params['user'] = self.user
		t = jinja_env.get_template(template)
		return t.render(params)
		
	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def render_json(self, d):
		json_txt = json.dumps(d)
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		self.write(json_txt)
		
	def set_secure_cookie(self, name, val):
		cookie_val = make_secure_val(val)
		self.response.headers.add_header(
				'Set-Cookie',
				'%s=%s; Path=/' % (name, cookie_val))
		
	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and check_secure_val(cookie_val)
		
	def login(self, user):
		self.set_secure_cookie('user_id', str(user.key().id()))
		
	def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
		
	def initialize(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		self.user = uid and User.by_id(int(uid))
		
		if self.request.url.endswith('.json'):
			self.format = 'json'
		else:
			self.format = 'html'

def make_salt(length = 5):
	return ''.join(random.choice(letters) for x in xrange(length))
	
def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s,%s' % (salt, h)
	
def valid_pw(name, password, h):
	salt = h.split(',')[0]
	return h == make_pw_hash(name, password, salt)
	
def users_key(group = 'default'):
	return db.Key.from_path('users', group)
		
class User(db.Model):
	name = db.StringProperty(required = True)
	pw_hash = db.StringProperty(required = True)
	email = db.StringProperty()
	
	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid, parent = users_key())
		
	@classmethod
	def by_name(cls, name):
		u = User.all().filter('name =', name).get()
		return u
		
	@classmethod
	def register(cls, name, pw, email = None):
		pw_hash = make_pw_hash(name, pw)
		return User(parent = users_key(),
					name = name,
					pw_hash = pw_hash,
					email = email)
					
	@classmethod
	def login(cls, name, pw):
		u = cls.by_name(name)
		if u and valid_pw(name, pw, u.pw_hash):
			return u
	
def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)
	
class Post(db.Model):
	artist = db.StringProperty(required = True)
	title = db.StringProperty(required = False)
	medium = db.StringProperty(required = False)
	provenance = db.StringProperty(required=False)
	valuation = db.StringProperty(required=False)
	subject = db.StringProperty(required = False)
	remark = db.TextProperty(required = False)
	trash = db.StringProperty(required = False)
	art_object = blobstore.BlobReferenceProperty(required=False)
	made = db.StringProperty(required = False)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)
	
	def render(self):
		self._render_text = self.content.replace('\n', '<br>')
		return render_str("post.html", p = self)
		
	def local_time(self):
		return self.created - timedelta(hours=4)
		
	def as_dict(self):
		time_fmt = '%c'
		d = {'artist':self.artist,
			'title': self.title,
			'medium': self.medium,
			'provenance': self.provenance,
			'valuation': self.valuation,
			'subject': self.subject,
			'remark': self.remark,
			'trash': self.trash,
			'art_object':self.art_object,
			'made': self.made,
			'created': self.created.strftime(time_fmt),
			'last_modified': self.last_modified.strftime(time_fmt)}
		return d

def age_set(key, posts):
	save_time = datetime.now()
	memcache.set(key, (posts,save_time))
	
def age_get(key):
	r = memcache.get(key)
	if r:
		posts, save_time = r
		age = (datetime.now() - save_time).total_seconds()
	else:
		posts, age = None, 0
	return posts, age
				
def top_posts(update = False):
	key = 'top'
	posts, age = age_get(key)
	
	if posts is None or update:
		posts = Post.all().order('-artist')
		posts = list(posts)
		
		age_set(key, posts)		
				
	return posts, age
			
def age_str(age):
	s = 'queried %s seconds ago'
	age = int(age)
	if age == 1:
		s = s.replace('seconds', 'second')
	return s % age

def DaSearching(quest):
		posts, age = top_posts()
		thesearch = list()
		for p in posts:
			if p.artist == quest or p.subject == quest or p.remark == quest:
				thesearch.append(p)
		return thesearch

def gone(posts):
	for p in posts:
		if p.artist:
			db.delete(p)
			
def chunk(stack, n):
	buf = []
	for x in stack:
		buf.append(x)
		if len(buf)==n:
			yield buf
			buf = []
	if buf:
		yield buf
		
def sorter(posts, val, single=False):
	artisttuplelist=list()
	valuelist=list()
	for p in posts:
		valuelist = (p.artist, p.title, p.medium, p.provenance, p.valuation, p.subject, p.made)
		artisttuplelist.append((p, valuelist[val]))
	unsorted=artisttuplelist
	artist_names_list = []
	post_tup_list = []
	if single:
		for tup in artisttuplelist:
			if not tup[1] in artist_names_list:
				post_tup_list.append(tup)
				artist_names_list.append(tup[1])
		unsorted = post_tup_list
	sortedtuplist=sorted(unsorted, key=lambda tup: tup[1].lower())

	return [posttup[0] for posttup in sortedtuplist]
	

class DownloadArtObject(BlogHandler, BlobstoreDownloadHandler):
	def get(self, post_key):
		post = Post.get(post_key)
		self.send_blob(post.art_object)

class UploadArtObject(BlogHandler, BlobstoreUploadHandler):
	def post(self, post_key):
		post = Post.get(post_key)
		post.art_object = (self.get_uploads(post.art_object)[0])
		post.put()
		
class MainPage(BlogHandler):
	def get(self):
		active_objects=[]
		users=[]
		posts, age = top_posts()
		
		for p in posts:
			if p.trash != "True":
				active_objects.append(p)
		val = 0
		sortedlist= sorter(active_objects, val)		

		for group in chunk(sortedlist, 5):
			users.append(group)
		
		age = age_str(age)
		if self.format == 'html':
			self.render('front3.html', posts = posts, age=age, users = users)
		else:
			return self.render_json([p.as_dict() for p in posts])
			
class BlogFront(BlogHandler):
	def get(self, anything=""):
		posts = top_posts(update=False)
		
		if self.format == 'html':
			self.render('front3.html', posts = posts)
		else:
			return self.render_json([p.as_dict() for p in posts])
			
class PostPage(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):

	def get(self, post_id):

		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)
		upload_url = blobstore.create_upload_url('/blog/%s' % str(post.key().id()))

		posts, age = top_posts(update=True)
		age = age_str(age)
		
		# gone(posts)

		if self.user:		
			if self.format == 'html':
				self.render("permalink.html",  post = post, age=age, upload_url=upload_url)
			else:
				self.render_json(posts.as_dict())
		else:
			self.render("nonuserpermalink.html", post = post, age=age)

	def post(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = Post.get(key)

		UpdateArtist=self.request.get('updateartist')
		UpdateTitle=self.request.get('updatetitle')
		UpdateMedium=self.request.get('updatemedium')
		UpdateProvenance=self.request.get('updateprovenance')
		UpdateValuation=self.request.get('updatevaluation')
		UpdateSubject=self.request.get('updatesubject')
		UpdateRemark=self.request.get('updateremark')
		UpdateTrash=self.request.get('updatetrash')
		art_object = self.get_uploads('art_object')
		UpdateMade = self.request.get('updatemade')
				
		if art_object:
			art_object = art_object[0]
			post.art_object=art_object
			post.put()
		if UpdateArtist:
			post.artist = UpdateArtist
			post.put()
		if UpdateTitle:
			post.title=UpdateTitle
			post.put()
		if UpdateMedium:
			post.medium=UpdateMedium
			post.put()
		if UpdateProvenance:
			post.provenance=UpdateProvenance
			post.put()
		if UpdateValuation:
			post.valuation=UpdateValuation
			post.put()
		if UpdateSubject:
			post.subject = UpdateSubject
			post.put()
		if UpdateRemark:
			post.remark = UpdateRemark
			post.put()
		if UpdateMade:
			post.made = UpdateMade
			post.put()
			
		posts, age = top_posts(update = True)
		post = db.get(key)
		self.redirect('/blog/%s' % str(post.key().id()))
				
class Remove(BlogHandler):
	def post(self, post_key):
		key = db.Key.from_path('Post', int(post_key), parent=blog_key()) 
		post = Post.get(key)
		post.trash= "True"
		post.put()
		#posts, age = top_posts(update = True)
		memcache.delete('top')
		
		self.redirect('/')

class dump_trash(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		posts, age = top_posts()
		to_be_dumped=list()
		for p in posts:
			if p.trash == "True":
				to_be_dumped.append(p)
				
		for p in to_be_dumped:
			p.art_object.delete()
			db.delete(p)
			
		# posts, age=top_posts(update=True)
		memcache.delete('top')	
		self.redirect('/')

class take_off_list(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):		
	def get(self, post_key):
		key = db.Key.from_path('Post', int(post_key), parent=blog_key()) 
		post = Post.get(key)
		post.trash= 'five'
		post.put()
		# posts, age=top_posts(update=True)
		memcache.delete('top')
		
		self.redirect('/trashed')
		
		
class Delit(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def post(self, post_key):
		key = db.Key.from_path('Post', int(post_key), parent=blog_key()) 
		post = Post.get(key)
		if post.art_object:
			post.art_object.delete()
		
		db.delete(post)
		memcache.delete('top')
		# posts, age = top_posts(update = True)
		
		self.redirect('/')
		
class Searching(BlogHandler):
	
	def post(self):
		logging.error("getttting")
		
		action = self.request.get('action')
		logging.error(action)

		posts, age = top_posts()
		thesearch = list()
		
		for p in posts:
			if p.artist == action or p.subject == action or p.remark == action:
				thesearch.append(p)

		if thesearch:
			self.render("SearchResults.html", thesearch = thesearch)
		else:
			error = "No Matches Found, Sorry!"
			self.render("SearchResults.html", thesearch=thesearch, error = error)
			
class NewPost(BlogHandler, BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/newpost')
		posts, age = top_posts()
		if self.user:
			self.render("newpost.html", posts = posts, upload_url = upload_url )
		else:
			self.redirect("/login")
						
	def post(self):
		if not self.user:
			self.redirect('/')
			
		artist = self.request.get('artist')
		title = self.request.get('title')
		medium = self.request.get('medium')
		provenance = self.request.get('provenance')
		valuation = self.request.get('valuation')
		subject = self.request.get('subject')
		remark = self.request.get('remark')
		made = self.request.get('made')
		art_object = self.get_uploads('art_object')
		art_object = art_object[0]
		
		if artist:
			p = Post(parent = blog_key(), artist = artist, title = title, medium = medium, provenance = provenance, valuation = valuation, made = made, subject = subject, remark = remark, art_object=art_object)
			p.put()
			posts, age = top_posts(update=True)
			self.redirect('/blog/%s' % str(p.key().id()))
		else:
			error = "An artist name is necessary."
			self.render("newpost.html", artist= artist, subject=subject, remark=remark, error=error)
			
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
	return username and USER_RE.match(username)
	
PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
	return password and PASS_RE.match(password)
	
EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
	return not email or EMAIL.RE.match(email)
	
class Signup(BlogHandler):
	def get(self):
		self.render("signup-form.html")
		
	def post(self):
		have_error = False
		self.username = self.request.get('username')
		self.password = self.request.get('password')
		self.verify = self.request.get('verify')
		self.email = self.request.get('email')
		
		params = dict(username = self.username,
						email = self.email)
					
		if not valid_username(self.username):
			params['error_username'] = "That's not a valid username."
			have_error = True
		if not valid_password(self.password):
			params['error_password'] = "That wasn't a valid password."
			have_error = True
		elif self.password != self.verify:
			params['error_verify'] = "Your passwords didn't match."
			have_error = True
		if not valid_email(self.email):
			params['error_email'] = "That's not a valid email."
			have_error = True
		if have_error:
			self.render('signup-form.html', **params)
		else:
			self.done()
			
	def done(self, *a, **kw):
		self.render("login-form.html", **params)
				
class Register(Signup):
	def done(self):
		u = User.by_name(self.username)
		if u:
			msg = "That user already exists."
			self.render('signup-form.html', error_username = msg)
		else:
			u = User.register(self.username, self.password, self.email)
			u.put()
			self.login(u)
			self.redirect('/welcome')
			
class Login(BlogHandler):
	def get(self):
		self.render('login-form.html')
		
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
				
		u = User.login(username, password)	
		if u:
			self.login(u)
			self.redirect('/')
		else:
			msg = 'Invalid login'
			self.render('login-form.html', error = msg)
			
class Logout(BlogHandler):
	def get(self):
		
		self.logout()
		self.redirect('/')
					
class Welcome(BlogHandler):
	def get(self):
		if self.user:
			self.render('welcome.html', username = self.user.name)
		else:
			self.redirect('/signup')

class Trashed(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/thetrash')
		posts, age = top_posts()
		thelist=list()
		trashed_list=list()
		for p in posts:
			if p.trash=="True":
				trashed_list.append(p)
		val=0
		sortedlist= sorter(trashed_list, val)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("thetrash.html", posts = posts, upload_url = upload_url, thelist = thelist )

class Bymade(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/bymade')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=6
		sortedlist= sorter(not_trashed_list, val, single=True)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("bymade.html", posts = posts, upload_url = upload_url, thelist = thelist )
		
class Byvaluation(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/byvaluation')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=4
		sortedlist= sorter(not_trashed_list, val)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("byvaluation.html", posts = posts, upload_url = upload_url, thelist = thelist )
		
class Byprovenance(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/byprovenance')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=3
		sortedlist= sorter(not_trashed_list, val, single=True)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("byprovenance.html", posts = posts, upload_url = upload_url, thelist = thelist )		
		
class Bymedium(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/bymedium')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=2
		sortedlist= sorter(not_trashed_list, val, single=True)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("bymedium.html", posts = posts, upload_url = upload_url, thelist = thelist )

		
class Bytitle(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/bytitle')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=1
		sortedlist= sorter(not_trashed_list, val)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("bytitle.html", posts = posts, upload_url = upload_url, thelist = thelist )
			
class Byartist(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/byartist')
		posts, age = top_posts()
		thelist=list()
		not_trashed_list=list()
		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		val=0		
		sortedlist= sorter(not_trashed_list, val, single=True)

		for group in chunk(sortedlist, 4):
			thelist.append(group)

		self.render("byartist.html", posts = posts, upload_url = upload_url, thelist = thelist )

class Oneprovenance(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)
		upload_url = blobstore.create_upload_url('/blog/%s' % str(post.key().id()))
		
		posts, age = top_posts()
		provenance = post.get(key)
		one_provenance=list()
		not_trashed_list=list()

		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		
		for p in not_trashed_list:
			if p.provenance == provenance.provenance:
				one_provenance.append(p)

		users=list()
		for group in chunk(one_provenance, 4):
			users.append(group)
				
		self.render("oneprovenance.html", posts = posts, upload_url = upload_url, users = users, provenance = provenance )		
		
class Onemedium(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)
		upload_url = blobstore.create_upload_url('/blog/%s' % str(post.key().id()))
		
		posts, age = top_posts()
		medium = post.get(key)
		one_medium=list()
		not_trashed_list=list()

		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		
		for p in not_trashed_list:
			if p.medium == medium.medium:
				one_medium.append(p)

		users=list()
		for group in chunk(one_medium, 4):
			users.append(group)
				
		self.render("onemedium.html", posts = posts, upload_url = upload_url, users = users, medium = medium )

class Onedate(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)
		upload_url = blobstore.create_upload_url('/blog/%s' % str(post.key().id()))
		
		posts, age = top_posts()
		the_date = post.get(key)
		one_date=list()
		not_trashed_list=list()

		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		
		for p in not_trashed_list:
			if p.made == the_date.made:
				one_date.append(p)

		users=list()
		for group in chunk(one_date, 4):
			users.append(group)
				
		self.render("onedate.html", posts = posts, upload_url = upload_url, users = users, the_date = the_date )
		
		
class Oneartist(BlogHandler, BlobstoreDownloadHandler,  BlobstoreUploadHandler):
	def get(self, post_id):
		key = db.Key.from_path('Post', int(post_id), parent=blog_key())
		post = db.get(key)
		upload_url = blobstore.create_upload_url('/blog/%s' % str(post.key().id()))
		
		posts, age = top_posts()
		artist = post.get(key)
		oneartist=list()
		not_trashed_list=list()

		for p in posts:
			if p.trash!="True":
				not_trashed_list.append(p)		
		
		for p in not_trashed_list:
			if p.artist == artist.artist:
				oneartist.append(p)

		users=list()
		for group in chunk(oneartist, 4):
			users.append(group)
				
		self.render("oneartist.html", posts = posts, upload_url = upload_url, users = users, artist = artist )
			
class Flush(BlogHandler):
	def get(self):
		key = 'top'
		memcache.set(key, (None,datetime.now()))		
		self.redirect('/newpost')

	
app = webapp2.WSGIApplication([('/?(?:\.json)?', MainPage),
								('/blog/?(?:\.json)?', BlogFront),
								('/blog/([0-9]+)(?:\.json)?', PostPage),
								('/newpost', NewPost),
								('/search', Searching),
								('/trashed', Trashed),
								('/byartist', Byartist),
								('/bytitle', Bytitle),
								('/byvaluation', Byvaluation),
								('/bymedium', Bymedium),
								('/byprovenance', Byprovenance),
								('/bymade', Bymade),
								('/oneartist/([0-9]+)(?:\.json)?', Oneartist),
								('/onemedium/([0-9]+)(?:\.json)?', Onemedium),
								('/onedate/([0-9]+)(?:\.json)?', Onedate),
								('/oneprovenance/([0-9]+)(?:\.json)?', Oneprovenance),
								('/remove/([0-9]+)(?:\.json)?', Remove),
								('/delete/([0-9]+)(?:\.json)?', Delit),
								('/dump_trash', dump_trash),
								('/take_off_trashlist/([0-9]+)(?:\.json)?', take_off_list),
								('/signup', Register),
								('/login', Login),
								('/logout', Logout),
								('/welcome', Welcome),
								('/flush', Flush),
								('/download-art-objects/(?P<post_key>[-0-9a-zA-Z]+)', DownloadArtObject),
								('/upload-art-objects', UploadArtObject),
								],
								debug=True)
								