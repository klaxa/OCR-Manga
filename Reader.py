#!/usr/bin/env python
import tkinter as tk
from PIL import Image, ImageTk
import os
import pyocr
import pyocr.builders
import myougiden_api
import threading
tool = pyocr.get_available_tools()[0]

def best_fit(width, height, image):
	(x, y) = image.size
	scale = width / x
	if y * scale > height:
		scale = height / y
	#print(scale)
	return image.resize((int(x * scale), int(y * scale)), Image.BILINEAR)


class LookupThread(threading.Thread):
	def run(self):
		self.dirty = False
		image, app = (self._args)
		try:
			string = app.image_to_dict(image)
			if not self.dirty:
				app.draw_dict(string)
			
		finally:
			# Avoid a refcycle if the thread is running a function with
			# an argument that has a member that points to the thread.
			del self._target, self._args, self._kwargs


class Application(tk.Frame):
	def __init__(self, master=None):
		tk.Frame.__init__(self, master)
		if os.path.isfile("last_page"):
			last_page = open("last_page", "r")
			try:
				self.current_page = int(last_page.read())
			except:
				self.current_page = 0
			last_page.close()
		else:
			self.current_page = 0
		self.pack(fill=tk.BOTH, expand=1)
		self.createWidgets()
		self.current_page_oid = 0
		self.current_page_image = None
		self.drawing_box = False
		self.box_oid = 0
		self.box_coords = (0, 0, 0, 0)
		self.lookup = None
		self.tkimage = None
		self.rotation = 0
		self.fullscreen = False

	def createWidgets(self):
		#self.quitButton = tk.Button(self, text='Quit',
		#	command=self.quit)
		#self.quitButton.grid()
		self.update()
		(width, height) = (self.winfo_width(), self.winfo_height())
		self.frame = tk.Canvas(self, width=width, height=height, cursor="tcross")
		self.frame.pack(fill=tk.BOTH)
		self.frame.bind('<Left>', self.next_image)
		self.frame.bind('<Right>', self.prev_image)
		#self.frame.bind('<r>', self.rotate)
		self.frame.bind('<Configure>', self.resize_event)
		self.frame.focus_set()
		self.frame.bind('<Button-1>', self.start_drawing_box)
		self.frame.bind('<ButtonRelease-1>', self.stop_drawing_box)
		self.frame.bind('<Double-Button-1>', self.clear_box)
		self.frame.bind('<Button-2>', self.side_tap)
		self.frame.bind('<Motion>', self.draw_box)
		self.frame.bind('<F11>', self.toggle_fullscreen)
	
	def toggle_fullscreen(self, event=None):
		self.fullscreen = not self.fullscreen  # Just toggling the boolean
		self.master.attributes("-fullscreen", self.fullscreen)
		self.update_screen()
	
	def side_tap(self, event):
		if event.x < (self.frame.winfo_width() / 2):
			self.change_image(1)
		else:
			self.change_image(-1)
	
	def resize_event(self, event):
		self.frame.width = event.width   #>>>854
		self.frame.height = event.height #>>>404
		self.frame.config(width=self.frame.width, height=self.frame.height)
		self.update_screen()
	
	def update_screen(self):
		self.change_image(0)
	
	def rotate(self, event):
		self.rotation = (self.rotation + 1) % 4
		self.update_screen()
	
	def clear_box(self, event):
		self.drawing_box = False		
		if self.box_oid != 0:
			self.frame.delete(self.box_oid)
		self.frame.delete("text")
		self.frame.delete("selection")
	def start_drawing_box(self, event):
		textbox = self.frame.bbox("text")
		selectionbox = self.frame.bbox(self.box_oid)
		for bbox in textbox, selectionbox:
			if bbox is not None:
				(x, y, x2, y2) = bbox
				mx = event.x
				my = event.y
				if mx > x and mx < x2 and my > y and my < y2:
					self.clear_box(None)
					return
		
		self.drawing_box = True
		x = event.x
		y = event.y
		self.box_coords = (x, y, x, y)
		if self.box_oid != 0:
			self.frame.delete(self.box_oid)
		self.box_oid = self.frame.create_rectangle(x, y, x, y, fill="black", stipple="gray50")
		self.frame.addtag_withtag("selection", self.box_oid)
	
	def stop_drawing_box(self, event):
		try:
			self.drawing_box = False
			(ix, iy, ix2, iy2) = self.frame.bbox(self.current_page_oid)
			(bx, by, bx2, by2) = self.frame.bbox(self.box_oid)
			px = (bx - ix) / (ix2 - ix)
			py = (by - iy) / (iy2 - iy)
			px2 = (bx2 - ix) / (ix2 - ix)
			py2 = (by2 - iy)/ (iy2 - iy)
			#print("%f, %f, %f, %f" % (px, py, px2, py2))
		
			(width, height) = self.current_page_image.size
			cx = int(px * width)
			cx2 = int(px2 * width)
			cy = int(py * height)
			cy2 = int(py2 * height)
			#print("%d, %d, %d, %d" % (cx, cy, cx2, cy2))
			ocr_image = self.current_page_image.crop((cx, cy, cx2, cy2))
			#draw = ImageDraw.Draw(self.current_page_image)
			#draw.rectangle([cx, cy, cx2, cy2], outline="black")
			#ocr_image = image
			if self.lookup is not None:
				self.lookup.dirty = True
			self.lookup = LookupThread(args=(ocr_image,self))
			self.lookup.start()
			#self.image_to_dict(ocr_image)
		except:
			pass
		
		
		
	def draw_box(self, event):
		if not self.drawing_box:
			return
		(x, y, x2, y2) = self.box_coords
		x2 = event.x
		y2 = event.y
		self.box_coords = (x, y, x2, y2)
		self.frame.delete(self.box_oid)
		self.box_oid = self.frame.create_rectangle(x, y, x2, y2, outline="#00AA00", fill="#00AA00", stipple="gray50")
	
	def change_image(self, amount):
		self.clear_box(None)
		new_page = self.current_page + amount
		if new_page < 0 or new_page > len(images) - 2:
			return
		self.current_page = new_page
		image = Image.open(images[self.current_page])
		if self.rotation != 0:
			image = image.rotate(-90 * self.rotation)
		(width, height) = (self.frame.winfo_width(), self.frame.winfo_height())
		image = best_fit(width, height, image)
		self.tkimage = ImageTk.PhotoImage(image)
		self.frame.delete(self.current_page_oid)
		self.current_page_oid = self.frame.create_image(int(width/2), 0, image=self.tkimage, anchor=tk.N)
		self.current_page_image = image
		last_page = open("last_page", "w")
		last_page.write(str(self.current_page))
		last_page.close()
	
	
	def prev_image(self, event):
		self.change_image(-1)
	
	def next_image(self, event):
		self.change_image(1)
		
	def image_to_dict(self, image):
		size = image.size
		image = image.resize((size[0] * 2, size[1] * 2), Image.BILINEAR)
		string = tool.image_to_string(image, lang="jpn", builder=pyocr.builders.TextBuilder(5))
		string = string.strip()
		if string != "":
			dict_entry = myougiden_api.run([string])
		else:
			dict_entry = None
			string = "No character recognized"
		#image.save("/tmp/export.png")
		if dict_entry is not None and string != "No character recognized":
			string = "\n".join(dict_entry)
		else:
			dict_entry = myougiden_api.run(string[:-1])
			dict_entry2 = myougiden_api.run(string[1:])
			dict_entry3 = myougiden_api.run(string[1:])
			result = ""
			result2 = ""
			result3 = ""
			if dict_entry is not None:
				result = "\n".join(dict_entry)
			if dict_entry2 is not None:
				result2 = "\n".join(dict_entry2)
			if dict_entry2 is not None:
				result3 = "\n".join(dict_entry3)
			string = result + result2 + result3
		print(string)
		return string
	
	def draw_dict(self, string):
		self.text = self.frame.create_text(5, 5, width=500, anchor=tk.NW, text=string)
		self.frame.addtag_withtag("text", self.text)
		(x, y, x2, y2) = self.frame.bbox(self.text)
		self.textbox = self.frame.create_rectangle(x, y, x2, y2, fill="white", outline="white")
		self.frame.addtag_withtag("text", self.textbox)
		self.frame.tag_lower(self.textbox, self.text)
		

directory = '/home/klaxa/Images/manga/'

images = sorted([os.path.join(directory, filename) for filename in os.listdir('/home/klaxa/Images/manga/')])
app = Application()
app.master.title('Yurimon reader')
app.update_screen()
app.mainloop()

