import twitter
import sqlite3
import kyodaishiki.__shell__ as ksh
import docopt
import re
import json
import sys
import os
import random


COLUMN=("name","consumer_key","consumer_secret","token","token_secret")

def getbot(token,token_secret,consumer_key,consumer_token):
	auth=twitter.OAuth(
		token,
		token_secret,
		consumer_key,
		consumer_token
	)
	return twitter.Twitter(auth=auth)
	

def getbot2(consumer_key,consumer_secret,bearer_token):
	auth=twitter.OAuth2(
		consumer_key=consumer_key,
		consumer_secret=consumer_secret,
		bearer_token=bearer_token
	)
	return twitter.Twitter(auth=auth)
	#return twitter.Twitter(auth=twitter.OAuth2(bearer_token=BEARER_TOKEN))


class BotDB:
	TABLE_NAME="twitter_bot_auth_data"
	def __init__(self,db):
		self.db=db
		self.cur=db.cursor()
	def createTable(self):
		self.cur.execute("create table if not exists {0} (name text,consumer_key text,consumer_secret text,token text,token_secret text)".format(self.TABLE_NAME))
	def append(self,name,consumer_key,consumer_secret,token,token_secret):
		self.cur.execute("insert into {0} values (?,?,?,?,?)".format(self.TABLE_NAME),(name,consumer_key,consumer_secret,token,token_secret))
	def list_name(self):
		return map(lambda data:data[0],self.cur.execute("select name from {0}".format(self.TABLE_NAME)))
	def _get(self,name):
		data=list(self.cur.execute("select * from {0} where name == ?".format(self.TABLE_NAME),[name]))
		return dict(zip(COLUMN,data[0])) if data else None
	def get(self,name):
		data=self._get(name)
		if not data:
			return None
		return getbot(
			data["token"],
			data["token_secret"],
			data["consumer_key"],
			data["consumer_secret"]
			)
	def remove(self,name):
		self.cur.execute("delete from {0} where name == ?".format(self.TABLE_NAME),[name])
		self.db.commit()
	def close(self):
		self.db.close()



def count(s):
	i=0
	for c in s:
		if len(c.encode()) == 1:
			i+=1
		else:
			i+=2
	return i

def slice_(s,n=256):
	i=0
	res=""
	for c in s:
		if len(c.encode()) == 1:
			i+=1
		else:
			i+=2
		if i > n:
			return res
		res+=c
	return res

def upload_video(t_upload,videodata):
	size=len(videodata)
	def init():
		return t_upload.media.upload(command="INIT",total_bytes=size,media_type="video/mp4")
	def append(media_id):
		size=len(videodata)
		SIZE_VAL=1000*1000*5
		n=size//SIZE_VAL+1
		#print("size",size)
		for i in range(n):
			#print("segment",i*SIZE_VAL,min(((i+1)*SIZE_VAL,size)))
			media=videodata[i*SIZE_VAL:min(((i+1)*SIZE_VAL,size))]
			t_upload.media.upload(
				command="APPEND",
				media_id=media_id,
				media=media,
				segment_index=i
				)
	def finalize(media_id):
		return t_upload.media.upload(command="FINALIZE",media_id=media_id)
	res=init()
	#print(res)
	media_id=res["media_id"]
	append(media_id)
	res=finalize(media_id)
	#print(res)
	return media_id

class Docs:
	APPEND="""
	Usage:
		append <botname> <consumer_key> <consumer_secret> <token> <token_secret>
	"""
	REMOVE="""
	Usage:
		remove <name>
	"""
	GET="""
	Usage:
		get <bot_name>
	"""
	LIST="""
	Usage:
		list [<name>]
	"""
	SET="""
	Usage:	
		set bot <name>
	"""
	HELP="""
		append
		get
		upload
		list
		set
	"""

class Command:
	HELP=("H","HELP")
	APPEND=("A","APPEND")
	REMOVE=("RM","REMOVE")
	GET=("G","GET")
	UPLOAD=("UP","UL","UPLOAD")
	LIST=("LS","LIST")
	SET=["SET"]

class Shell(ksh.BaseShell3):	
	def __init__(self,db):
		self.db=db
		self.botdb=BotDB(db)
		self.cur=db.cursor()
		self.current_name=None
		self.current_bot=None
		super().__init__()
		self.botdb.createTable()
	def _execQuery(self,query,output):
		if query.command in Command.HELP:
			print(Docs.HELP,file=output)
		elif query.command in Command.APPEND:
		#append <botname> <consmer_key> <consumer_secret> <token> <token_secret>
			args=docopt.docopt(Docs.APPEND,query.args)
			name=args["<botname>"]
			consumer_key=args["<consumer_key>"]
			consumer_token=args["<consumer_secret>"]
			token=args["<token>"]
			token_secret=args["<token_secret>"]
			self.botdb.append(name,consumer_key,consumer_token,token,token_secret)
			self.botdb.db.commit()
		elif query.command in Command.REMOVE:
			args=docopt.docopt(Docs.REMOVE,query.args)
			name=args["<name>"]
			self.db.remove(name)
		elif query.command in Command.GET:
			args=docopt.docopt(Docs.GET,query.args)
			name=args["<bot_name>"]
			data=self.botdb._get(name)
			print(json.dumps(data,indent=2),file=output)
		elif query.command in Command.LIST:
			args=docopt.docopt(Docs.LIST,query.args)
			sname=args["<name>"] or ""
			for name in self.botdb.list_name():
				if re.match(sname,name):
					print(name,file=output)
		elif query.command in Command.SET:
			args=docopt.docopt(Docs.SET,query.args)
			if args["bot"]:
				name=args["<name>"]
				bot=self.botdb.get(name)
				if not bot:
					print('"{0} doesn\'t exist."'.format(name),file=output)
					return
				self.current_bot=bot
				self.current_name=name
				print("Setted bot data.",file=output)
		else:
			return super().execQuery(query,output)
	def execQuery(self,query,output):
		try:
			return self._execQuery(query,output)
		except KeyboardInterrupt:
			pass
		except SystemExit as e:
			print(e)
	def close(self):
		super().close()
		self.db.close()

if __name__ == "__main__":
#t=getbot()
#t.statuses.update(status="Hello,World!")
	with Shell(sqlite3.connect("a.db")) as sh:
		sh.start()
