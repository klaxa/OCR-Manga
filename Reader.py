#!/usr/bin/env python
import tkinter as tk
from PIL import Image, ImageTk
import os
import pyocr
import pyocr.builders
import myougiden_api
import threading
import argparse
import textwrap

tool = pyocr.get_available_tools()[0]

special_chars = "{}[]!\"§$%&/()\n\\.,-~\' "
colors = dict()
colors["35"] = "#cd00cd"
colors["31"] = "#cd0000"
colors["33"] = "#cdcd00"
colors["32"] = "#00cd00"
colors["0"] = "#000000"

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
			if not self.dirty and string is not None:
				app.clear_box()
				app.draw_dict(string)
			
		finally:
			# Avoid a refcycle if the thread is running a function with
			# an argument that has a member that points to the thread.
			del self._target, self._args, self._kwargs


class Application(tk.Frame):
	def __init__(self, images, master=None):
		tk.Frame.__init__(self, master)
		self.images = images
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
		self.text = []

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
	
	def clear_box(self, event=None):
		self.drawing_box = False		
		#if self.box_oid != 0:
		#	self.frame.delete(self.box_oid)
		self.frame.delete("text")
		#self.frame.delete("selection")
	
	def start_drawing_box(self, event):
		textbox = self.frame.bbox("text")
		selectionbox = self.frame.bbox(self.box_oid)
		for bbox in textbox, selectionbox:
			if bbox is not None:
				(x, y, x2, y2) = bbox
				mx = event.x
				my = event.y
				if mx > x and mx < x2 and my > y and my < y2:
					self.clear_box()
					if self.box_oid != 0:
						self.frame.delete(self.box_oid)
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
		new_page = self.current_page + amount
		if new_page < 0 or new_page > len(self.images) - 2:
			return
		self.clear_box()
		self.current_page = new_page
		self.master.title("Yurimon reader (%d/%d)" % (new_page, len(self.images)))
		image = Image.open(self.images[self.current_page])
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
		bid = self.box_oid
		size = image.size
		image = image.resize((size[0] * 3, size[1] * 3), Image.BICUBIC)
		string = tool.image_to_string(image, lang="jpn", builder=pyocr.builders.TextBuilder(5))
		string = string_filtered = "".join([c for c in string.strip() if c not in special_chars])
		self.clear_box()
		self.draw_dict("Looking up " + string)
		if string != "":
			dict_entry = myougiden_api.run(string)
		else:
			dict_entry = None
		#image.save("/tmp/export.png")
		if dict_entry is not None and string != "":
			string = dict_entry.strip("\n")
		else:
			self.clear_box()
			self.draw_dict(string + " not recognized, looking up:\n" + string[:-1].strip())
			dict_entry = myougiden_api.run(string[:-1].strip())
			if self.box_oid != bid:
				return None
			self.draw_dict(string + " not recognized, looking up:\n" + string[1:].strip())
			if self.box_oid != bid:
				return None
			dict_entry2 = myougiden_api.run(string[1:].strip())
			self.draw_dict(string + " not recognized, looking up:\n" + string[1:-1].strip())
			if self.box_oid != bid:
				return None
			dict_entry3 = myougiden_api.run(string[1:-1].strip())
			result = ""
			result2 = ""
			result3 = ""
			if dict_entry is not None:
				result = dict_entry
			if dict_entry2 is not None:
				result2 = dict_entry2
			if dict_entry2 is not None:
				result3 = dict_entry3
			string = result + result2 + result3
			string = string.strip("\n")
		if string == "":
			string = "Nothing recognized"
		print(string)
		return textwrap.fill(string, 120, replace_whitespace=False, drop_whitespace=False)
	
	def draw_dict(self, string):
		words = parse_color_string(string)
		self.text = []
		margin = 5
		xoff = 0
		yoff = 0
		for w in words:
			(color, text) = w
			if len(self.text) != 0:
				(x, y, x2, y2) = self.frame.bbox(self.text[-1])
				if text == "\n":
					(a, b, c, yoff) = self.frame.bbox("text")
					xoff = 0
					yoff -= 1
					text = ""
				else:
					xoff = x2
					
			self.text.append(self.frame.create_text(margin + xoff, margin + yoff, fill=color, anchor=tk.NW, text=text, font="14"))
			self.frame.addtag_withtag("text", self.text[-1])
		(x, y, x2, y2) = self.frame.bbox("text")
		self.textbox = self.frame.create_rectangle(x, y, x2, y2, fill="white", outline="white")
		self.frame.addtag_withtag("text", self.textbox)
		self.frame.tag_lower(self.textbox, self.text[0])
		

def parse_color_string(string):
	escape = "\x1b"
	parts = string.split(escape)
	color_tuples = []
	new_parts = []
	for part in parts:
		if "\n" in part:
			more_parts = part.split("\n")
			for p in more_parts	:
				if p != "":
					new_parts.append(p)
					new_parts.append("\n")
		else:
			new_parts.append(part)
	parts = new_parts
	for part in parts:
		if part.startswith("["):
			temp = part.split("m")
			color = temp[0].strip("[")
			text = "m".join(temp[1:])
			if len(text) == 0:
				continue
			try:
				color_tuples.append((colors[color], text))
			except KeyError:
				color_tuples.append((colors["0"], text))
		else:
			if len(part) == 0:
				continue
			color_tuples.append((colors["0"], part))
	return color_tuples

def main():
	parser = argparse.ArgumentParser(description="OCR Manga Reader")
	parser.add_argument('directory', metavar='directory')

	args = parser.parse_args()
	images = sorted([os.path.join(args.directory, filename) for filename in os.listdir(args.directory)])
	app = Application(images)
	app.master.title('Yurimon reader')
	app.update_screen()
	app.mainloop()

if __name__ == "__main__":
	main()


